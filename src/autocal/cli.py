"""CLI functions for autocal."""
import click
import datetime as dt
import logging
import questionary as qs
import re
import signal
import subprocess
import sys
import time
import u3
import yaml
from edges_io.io import LOAD_ALIASES, CalibrationObservation
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler

from . import automation
from .automation import vna_calib, vna_calib_receiver_reading
from .config import config
from .temp_sensor_with_time_U6 import temp_sensor as tmpsense
from .utils import int_validator, power_handler

logging.basicConfig(
    level="NOTSET",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)

console = Console()

main = click.Group()


@main.command()
def init():
    """Initialize settings for EDGES autocal."""
    console.rule("Setting up edges-autocal")

    calib_dr = Path(
        qs.path(
            "Directory in which calibration data should be saved:",
            only_directories=True,
        )
    )
    spect_dir = Path(
        qs.path("Directory in which spectra are kept:", only_directories=True)
    )
    pxspec = Path(qs.path("Path to fastspec repo:", only_directories=True))

    with open(Path("~/.edges-autocal").expanduser(), "w") as fl:
        yaml.dump(
            {"calib_dir": calib_dr, "spec_dir": spect_dir, "fastspec_dir": pxspec}, fl
        )

    console.print(
        ":checkmark: [green] Success! Configuration written to ~/.edges-autocal"
    )


@main.command()
def run():
    """Run a calibration of a load."""
    console.rule("Running automated calibration")

    if config is None:
        logger.error("You have not initialized autocal. Run `autocal init`.")
        sys.exit()

    signal.signal(signal.SIGINT, power_handler)

    time = int(
        qs.text(
            "Time (seconds) to run calibration:", validate=int_validator(minval=39)
        ).ask()
    )
    now = dt.datetime.now()
    date_str = f"{now.year}_{now.month:02}_{now.day:02}_040_to_200MHz"

    temp = qs.select(
        "Select temperature for calibration",
        choices=["35", "25", "15", "custom"],
        default="25",
    ).ask()
    if temp == "custom":
        temp = int(
            qs.text(
                "Enter temperature in °C:", validate=int_validator(minval=0, maxval=100)
            ).ask()
        )

    receiver = qs.select(
        "Which receiver are you calibrating?",
        choices=["Receiver01", "Receiver02", "Receiver03"],
        default="Receiver01",
    ).ask()
    obs_path = config.calib_dir / f"{receiver}_{temp}C_{date_str}"
    rec = int(receiver[-1])

    # ------------------------------------------------------------------
    # check any calibration folder created in last two weeks.
    # If so, no new folder is created. Calib data will be saved in that folder
    # considering that it is a part of continuous calibration process
    folders = config.calib_dir.glob("*")
    calobs = None
    for folder in folders:
        match = re.match(CalibrationObservation.pattern, folder.name)

        if match is None:
            continue

        existing_date = dt.datetime(
            int(match["year"]), int(match["month"]), int(match["day"])
        )
        if (
            (temp == int(match["temp"]))
            and (now - existing_date).days <= 14
            and (rec == int(match["rcv_num"]))
        ):

            keep_going = qs.confirm(
                "Previous calibration exists for these specs within the last 2 weeks. Add these measurements to those?"
            ).ask()
            if keep_going:
                receiver = folder.name
            else:
                logger.error(f"Please remove the existing folder: {folder.name}")
                sys.exit()
            f"{now.year}_{now.month:02}_{now.day:02}_040_to_200MHz"
            calobs = CalibrationObservation(folder)
            obs_path = calobs.path

    # ---------------------------------------------------------
    #       Clean up any previous ,acq or .csv files
    # ---------------------------------------------------------
    load = qs.select(
        "Select a load for calibration",
        choices=[
            "Ambient",
            "HotLoad",
            "LongCableOpen",
            "LongCableShort",
            "AntSim1",
            "AntSim2",
            "AntSim3",
            "SwitchingState",
            "ReceiverReading",
        ],
        default="Ambient",
    )

    # ------------------------------------------------------
    if calobs:
        run_num_spec = calobs.run_num["Spectra"].get(LOAD_ALIASES.inverse[load], 0)
        run_num_res = calobs.run_num["Resistance"].get(LOAD_ALIASES.inverse[load], 0)
        run_num_s11 = calobs.run_num["S11"].get(LOAD_ALIASES.inverse[load], 0)
        if not (run_num_res == run_num_spec == run_num_s11):
            raise ValueError(
                "Existing S11, Resistance and Spectra run numbers don't match. Please fix!"
            )
        run_num = run_num_spec + 1
    else:
        run_num = 1

    console.print(f"Performing run number {run_num}")

    spec_path = obs_path / "Spectra"
    res_path = obs_path / "Resistance"
    s11_path = obs_path / "S11" / load

    # ---------------------------------------------
    # ---------------------------------------------
    # remove all residue *.acq and *.csv files from previous run

    clear_acq = config.spec_dir.glob("*.acq")
    for item in clear_acq:
        item.unlink()

    cwd = Path(".")
    clear_csv = cwd.glob("*.csv")
    for item in clear_csv:
        item.unlink()

    # -------------------------------------------------------
    # Create directory structure for no directory within seven days
    # ------------------------------------------------------
    if not s11_path.exists():
        s11_path.mkdir()
    if not spec_path.exists():
        spec_path.mkdir()
    if not res_path.exists():
        res_path.mkdir()

    # ------------------------------------------------------
    #      Starting load calibration
    # ------------------------------------------------------
    if load not in ["SwitchingState", "ReceiverReading"]:
        automation.run_load(load, time)

    elif load == "SwitchingState":
        automation.measure_switching_state_s11()
    elif load == "ReceiverReading":
        automation.measure_receiver_reading()

    # ------------------------------------------------------
    # Move the spectra
    # ------------------------------------------------------
    for fl in config.spec_dir.glob("*.acq"):
        dest_path = spec_path / f"{load}_{run_num}_{fl.name}"
        stem = fl.stem
        fl.replace(dest_path)

    for fl in cwd.glob("*.csv"):
        dest_path = res_path / f"{load}_{run_num}_{stem}.csv"
        fl.replace(dest_path)

    for fl in cwd.glob("*.s1p"):
        dest_path = s11_path / fl
        fl.replace(dest_path)

    console.rule("[green bold]Finished Calibration!")


@main.command()
@click.option("-r/-R", "--receiver-reading/--not-receiver-reading", default=False)
def cal_vna(receiver_reading):
    """Calibrate the VNA."""
    if not receiver_reading:
        vna_calib()
    else:
        vna_calib_receiver_reading()


@main.command()
def fastspec():
    """Simply run fastspec as it is continuously."""
    # TODO: should we set the signal handler here?
    subprocess.call([config.fastspec_path, "-i", config.fastspec_ini, "-p"])


@main.command()
def temp_sensor():
    """Run a temperature sensor."""
    tmpsense()


@main.command()
def test_power_supply_box():
    """Test setting voltages on power supply box."""
    d = u3.U3()
    d.configIO(FIOAnalog=15)
    d.getFeedback(u3.BitDirWrite(4, 1))
    d.getFeedback(u3.BitDirWrite(5, 1))
    d.getFeedback(u3.BitDirWrite(6, 1))
    d.getFeedback(u3.BitDirWrite(7, 1))

    voltage = qs.select(
        "Select a voltage output", choices=["37V", "34V", "31.3V", "28V", "0V"]
    ).ask()

    if voltage == "37V":
        d.getFeedback(u3.BitStateWrite(4, 1))
        d.getFeedback(u3.BitStateWrite(5, 1))
        d.getFeedback(u3.BitStateWrite(6, 1))
        time.sleep(0.1)
        d.getFeedback(u3.BitStateWrite(7, 0))
    elif voltage == "34V":
        d.getFeedback(u3.BitStateWrite(4, 1))
        d.getFeedback(u3.BitStateWrite(5, 1))
        d.getFeedback(u3.BitStateWrite(6, 0))
        time.sleep(0.1)
        d.getFeedback(u3.BitStateWrite(7, 0))
    elif voltage == "31.3":
        d.getFeedback(u3.BitStateWrite(4, 1))
        d.getFeedback(u3.BitStateWrite(5, 0))
        d.getFeedback(u3.BitStateWrite(6, 1))
        time.sleep(0.1)
        d.getFeedback(u3.BitStateWrite(7, 0))
    elif voltage == "28V":
        d.getFeedback(u3.BitStateWrite(4, 0))
        d.getFeedback(u3.BitStateWrite(5, 1))
        d.getFeedback(u3.BitStateWrite(6, 1))
        time.sleep(0.1)
        d.getFeedback(u3.BitStateWrite(7, 0))
    elif voltage == "0V":
        d.getFeedback(u3.BitStateWrite(4, 1))
        d.getFeedback(u3.BitStateWrite(5, 1))
        d.getFeedback(u3.BitStateWrite(6, 1))
        time.sleep(0.1)
        d.getFeedback(u3.BitStateWrite(7, 1))
