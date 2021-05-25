"""CLI functions for autocal."""
import atexit
import click
import datetime as dt
import functools
import logging
import numpy as np
import questionary as qs
import re
import signal
import subprocess
import sys
import time
import warnings
import yaml
from edges_io.io import LOAD_ALIASES, CalibrationObservation
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from typing import Optional, Tuple

from . import automation
from ._redis_tools import array_to_redis, redis
from .automation import power_handler, vna_calib, vna_calib_receiver_reading
from .config import config
from .temp_sensor_with_time_U6 import temp_sensor as tmpsense
from .utils import float_validator, int_validator

try:
    import u3
except ImportError:
    warnings.warn(
        "Could not import u3 -- will not be able to run most of the functions!"
    )

# add a comment testing
logging.basicConfig(
    level="INFO",
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
        ).ask()
    )
    spect_dir = Path(
        qs.path("Directory in which spectra are kept:", only_directories=True).ask()
    )
    pxspec = Path(qs.path("Path to fastspec repo:", only_directories=True).ask())

    with open(Path("~/.edges-autocal").expanduser(), "w") as fl:
        yaml.dump(
            {
                "calib_dir": str(calib_dr),
                "spec_dir": str(spect_dir),
                "fastspec_dir": str(pxspec),
            },
            fl,
        )

    console.print(
        ":heavy_check_mark: [green] Success! Configuration written to ~/.edges-autocal"
    )


def definer(func):
    """Make a function that writes to the definition.yaml."""

    @functools.wraps(func)
    def inner(def_file, *args, **kwargs):
        with open(def_file, "r") as fl:
            defn = yaml.load(fl, Loader=yaml.FullLoader) or {}

        defn = func(defn, *args, **kwargs)

        with open(def_file, "w") as fl:
            yaml.dump(defn, fl)

    return inner


@definer
def write_purpose(defn):
    """Add a message/notes to the definition."""
    purpose = defn.get("purpose", "")
    if purpose:
        console.print(
            Panel(
                purpose, title="Existing Stated Purpose", width=min(150, console.width)
            )
        )
        change_purpose = not qs.confirm("Is this purpose still accurate?").ask()

    if not purpose or change_purpose:
        purpose = qs.text("What is the purpose of this calibration?").ask()
        defn["purpose"] = purpose

    return defn


@definer
def write_history(defn, run_num, load, now):
    """Write a line to the history in definition.yaml."""
    history = defn.get("history", [])
    history.append(
        f"Ran {load}, run_num={run_num}, at {now.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    defn["history"] = history
    return defn


@definer
def write_resistance(defn, male=True, run_num=1):
    """Write a male/female resistance to file."""
    resistance = float(
        qs.text(
            "Please measure the resistance (Ohms):", validate=float_validator(40, 60),
        ).ask()
    )
    if "measurements" not in defn:
        defn["measurements"] = {}

    if f"{run_num:02}" not in defn["measurements"]:
        defn["measurements"][run_num] = {}

    defn["measurements"][run_num][f"resistance_{'m' if male else 'f'}"] = resistance
    return defn


@main.command()
@click.option(
    "-w",
    "--min-warmup-iters",
    default=2,
    type=int,
    help="Minimum number of iterations to run S11 warmup",
)
@click.option(
    "-W",
    "--max-warmup-iters",
    default=50,
    type=int,
    help="Maximum number of iterations to run S11 warmup",
)
@click.option(
    "-f/-F",
    "--show-fastspec/--no-show-fastspec",
    default=True,
    help="Whether to show fastspec output",
)
def run(min_warmup_iters, max_warmup_iters, show_fastspec):
    """Run a calibration of a load."""
    console.rule("Running automated calibration")

    if config is None:
        logger.error("You have not initialized autocal. Run `autocal init`.")
        sys.exit()

    signal.signal(signal.SIGINT, power_handler)

    calobs, now, obs_path, time = get_observation()

    load = qs.select(
        "Select a load for calibration",
        choices=[
            "Ambient",
            "HotLoad",
            "LongCableOpen",
            "LongCableShorted",
            "AntSim1",
            "AntSim2",
            "AntSim3",
            "SwitchingState",
            "ReceiverReading",
        ],
        default="Ambient",
    ).ask()

    run_num = get_run_num(calobs, load)

    console.print(f"Performing run number {run_num}")

    def_file, res_path, s11_path, spec_path = create_directory_structure(
        load, obs_path, run_num
    )

    # ------------------------------------------------------
    #      Starting load calibration
    # ------------------------------------------------------
    if load not in ["SwitchingState", "ReceiverReading"]:
        automation.run_load(
            load,
            time,
            min_warmup_iters=min_warmup_iters,
            max_warmup_iters=max_warmup_iters,
            show_fastspec=show_fastspec,
        )

    elif load == "SwitchingState":
        automation.measure_switching_state_s11()
        write_resistance(def_file, male=True, run_num=run_num)

    elif load == "ReceiverReading":
        automation.measure_receiver_reading(show_fastspec=show_fastspec)
        write_resistance(def_file, male=False, run_num=run_num)

    # ------------------------------------------------------
    # Move the spectra
    # ------------------------------------------------------
    cleanup(load, res_path, run_num, s11_path, spec_path)

    write_history(def_file, run_num=run_num, load=load, now=now)
    console.rule("[green bold]Finished Calibration!")


def cleanup(load, res_path, run_num, s11_path, spec_path):
    """Move raw files into correct locations."""
    # Receiver reading and switching state we don't want any ACQ files saved
    if load in ["ReceiverReading", "SwitchingState"]:
        for fl in config.spec_dir.glob("*.acq"):
            fl.unlink()

    for fl in config.spec_dir.glob("*.acq"):
        dest_path = spec_path / f"{load}_{run_num:02}_{fl.name}"
        stem = fl.stem
        fl.replace(dest_path)
    for fl in Path(".").glob("*.csv"):
        dest_path = res_path / f"{load}_{run_num:02}_{stem}.csv"
        fl.replace(dest_path)
    for fl in Path(".").glob("*.s1p"):
        dest_path = s11_path / fl
        fl.replace(dest_path)


def create_directory_structure(
    load, obs_path, run_num
) -> Tuple[Path, Path, Path, Path]:
    """Create an empty directory structure for an observation."""
    spec_path = obs_path / "Spectra"
    res_path = obs_path / "Resistance"
    s11_path = obs_path / "S11" / f"{load}{run_num:02}"
    def_file = obs_path / "definition.yaml"

    # remove all residue *.acq and *.csv files from previous run
    for item in config.spec_dir.glob("*.acq"):
        item.unlink()
    for item in Path(".").glob("*.csv"):
        item.unlink()

    # -------------------------------------------------------
    # Create directory structure for no directory within seven days
    # ------------------------------------------------------
    if not s11_path.exists():
        s11_path.mkdir(parents=True)
    if not spec_path.exists():
        spec_path.mkdir(parents=True)
    if not res_path.exists():
        res_path.mkdir(parents=True)
    if not def_file.exists():
        def_file.touch()
    write_purpose(def_file)

    return def_file, res_path, s11_path, spec_path


def get_run_num(calobs: Optional[CalibrationObservation], load: str) -> int:
    """Obtain the correct run number for this load."""
    if load == "SwitchingState":
        load_alias = "switching_state"
    elif load == "ReceiverReading":
        load_alias = "receiver_reading"
    elif load in LOAD_ALIASES.inverse:
        load_alias = LOAD_ALIASES.inverse[load]
    else:
        load_alias = load

    if calobs is not None and load_alias in calobs.s11.run_num:
        run_num = calobs.s11.run_num[load_alias]
        run_num = int(
            qs.text(
                f"Existing run_number={run_num}. Set this run_num: ",
                validate=int_validator(run_num + 1),
                default=str(run_num + 1),
            ).ask()
        )
    else:
        run_num = 1
    return run_num


def get_observation() -> Tuple[CalibrationObservation, dt.datetime, Path, int]:
    """Get parameters of the observation itself."""
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
        temp = qs.text(
            "Enter temperature in °C:", validate=int_validator(minval=0, maxval=100)
        ).ask()
    temp = int(temp)

    receiver = qs.select(
        "Which receiver are you calibrating?",
        choices=["Receiver01", "Receiver02", "Receiver03"],
        default="Receiver01",
    ).ask()

    obs_path = config.calib_dir / f"{receiver}_{temp}C_{date_str}"
    rec = int(receiver[-2:])

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
                "Previous calibration directory exists for these specs within the last 2"
                " weeks. Add these measurements to those? "
            ).ask()
            if not keep_going:
                logger.error(f"Please remove the existing folder: {folder.name}")
                sys.exit()

            calobs = CalibrationObservation(
                folder, include_previous=False, compile_from_def=False
            )

            obs_path = calobs.path
    return calobs, now, obs_path, time


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
def mock_temp_sensor():
    """Mock run of the temp sensor in a different process."""
    epipe = subprocess.Popen(["autocal", "temp-sensor"])
    time.sleep(60)
    epipe.terminate()


@main.command()
def test_power_supply_box():
    """Test setting voltages on power supply box."""
    config.u3io.configIO(FIOAnalog=15)
    config.u3io.getFeedback(u3.BitDirWrite(4, 1))
    config.u3io.getFeedback(u3.BitDirWrite(5, 1))
    config.u3io.getFeedback(u3.BitDirWrite(6, 1))
    config.u3io.getFeedback(u3.BitDirWrite(7, 1))

    voltage = qs.select(
        "Select a voltage output", choices=["37V", "34V", "31.3V", "28V", "0V"]
    ).ask()

    if voltage == "37V":
        config.u3io.getFeedback(u3.BitStateWrite(4, 1))
        config.u3io.getFeedback(u3.BitStateWrite(5, 1))
        config.u3io.getFeedback(u3.BitStateWrite(6, 1))
        time.sleep(0.1)
        config.u3io.getFeedback(u3.BitStateWrite(7, 0))
    elif voltage == "34V":
        config.u3io.getFeedback(u3.BitStateWrite(4, 1))
        config.u3io.getFeedback(u3.BitStateWrite(5, 1))
        config.u3io.getFeedback(u3.BitStateWrite(6, 0))
        time.sleep(0.1)
        config.u3io.getFeedback(u3.BitStateWrite(7, 0))
    elif voltage == "31.3V":
        config.u3io.getFeedback(u3.BitStateWrite(4, 1))
        config.u3io.getFeedback(u3.BitStateWrite(5, 0))
        config.u3io.getFeedback(u3.BitStateWrite(6, 1))
        time.sleep(0.1)
        config.u3io.getFeedback(u3.BitStateWrite(7, 0))
    elif voltage == "28V":
        config.u3io.getFeedback(u3.BitStateWrite(4, 0))
        config.u3io.getFeedback(u3.BitStateWrite(5, 1))
        config.u3io.getFeedback(u3.BitStateWrite(6, 1))
        time.sleep(0.1)
        config.u3io.getFeedback(u3.BitStateWrite(7, 0))
    elif voltage == "0V":
        config.u3io.getFeedback(u3.BitStateWrite(4, 1))
        config.u3io.getFeedback(u3.BitStateWrite(5, 1))
        config.u3io.getFeedback(u3.BitStateWrite(6, 1))
        time.sleep(0.1)
        config.u3io.getFeedback(u3.BitStateWrite(7, 1))


@main.command()
@click.option("-r", "--repeat-num", type=int, default=1)
def s11(repeat_num):
    """Directly run all S11's for a particular load. Useful for quick testing."""
    automation.take_all_load_s11(repeat_num)


@main.command()
@click.option("-p/-P", "--plot/--no-plot", default=True)
def mock_s11_warmup(plot):
    """Mock the S11 warmup iterations and visualization."""
    warmup_re = np.zeros(100)
    warmup_im = np.ones(100)
    temps = np.array([0, 0.1, 0.2])

    if plot:
        bokeh_plot_module = Path(__file__).parent / "_bokeh_plots.py"
        bk_pipe = subprocess.Popen(["bokeh", "serve", str(bokeh_plot_module)])
        atexit.register(bk_pipe.terminate)

    count = 0
    for count in range(100):
        time.sleep(0.1)

        warmup_re = np.vstack((warmup_re, count * np.ones(100)))
        warmup_im = np.vstack((warmup_im, 2 * count * np.ones(100)))
        temps = np.concatenate((temps, [np.random.normal()]))

        if plot:
            array_to_redis(redis, warmup_re[:, 0], "re_begin")
            array_to_redis(redis, warmup_re[:, 100 // 2], "re_mid")
            array_to_redis(redis, warmup_re[:, -1], "re_end")
            array_to_redis(redis, warmup_im[:, 0], "im_begin")
            array_to_redis(redis, warmup_im[:, 100 // 2], "im_mid")
            array_to_redis(redis, warmup_im[:, -1], "im_end")
            array_to_redis(redis, temps, "temps")
            array_to_redis(
                redis,
                np.sqrt(
                    np.mean(np.square(warmup_re[:, 1:] - warmup_re[:, :-1]), axis=1)
                ),
                "re_rms",
            )
            array_to_redis(
                redis,
                np.sqrt(
                    np.mean(np.square(warmup_im[:, 1:] - warmup_im[:, :-1]), axis=1)
                ),
                "im_rms",
            )

    print("Finishing up.")
