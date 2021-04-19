"""Automation routines for lab calibration."""
import h5py
import logging
import numpy as np
import os
import questionary as qs
import re
import socket
import subprocess
import sys
import time
import u3
from contextlib import contextmanager
from functools import partial
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from typing import Optional, Union

from .config import config
from .utils import block_on_question

console = Console()
logger = logging.getLogger(__name__)

STANDARD_VOLTAGES = {"External": 37, "Match": 34, "Short": 31.3, "Open": 28}


def _get_voltage_settings(voltage):
    if voltage == 37:
        return 1, 1, 1, 0
    elif voltage == 34:
        return 1, 1, 0, 0
    elif voltage == 31.3:
        return 1, 0, 1, 0
    elif voltage == 28:
        return 0, 1, 1, 0
    elif voltage == 0:
        return 1, 1, 1, 1
    else:
        raise ValueError(f"Voltage {voltage} not understood.")


def _set_voltage(voltage):
    settings = _get_voltage_settings(voltage)

    config.u3io.getFeedback(u3.BitStateWrite(4, settings[0]))
    config.u3io.getFeedback(u3.BitStateWrite(5, settings[1]))
    config.u3io.getFeedback(u3.BitStateWrite(6, settings[2]))
    time.sleep(0.1)
    config.u3io.getFeedback(u3.BitStateWrite(7, settings[3]))


def take_s11(fname, voltage, print_settings=True):
    """Take S11 with particular voltage settings."""
    _set_voltage(voltage)

    logger.info(f"Taking {fname} measurement at {voltage}V...")
    measure_s11(fname=f"{fname}.s1p", print_settings=print_settings)
    config.u3io.getFeedback(u3.BitStateWrite(7, 1))
    logger.info(f"... saved as '{fname}.s1p'")


def take_all_load_s11(repeat_num: int):
    """Take all S11 measurements for a load."""
    """"--------------------------------
    Run S11 for 1 hour for temperature stability of SP4T switch
    -----------------------------------

     """

    for i, (name, voltage) in enumerate(STANDARD_VOLTAGES.items()):
        take_s11(f"{name}{repeat_num:02}", voltage=voltage, print_settings=not i)


@contextmanager
def fastspec_process(run_time, init_time=0, post_time=0, stdout=None):
    """Start a fastspec process, do some stuff while it's running, then wait for it to finish.

    Examples
    --------
    >>> with fastspec_process(run_time=120) as fspec:
    >>>     do_something_else()  # this will run concurrently
    >>> do_something_after()  # this will run after fspec is done.
    """
    # Code to acquire resource
    if run_time:
        # run for a certain amount of time

        fpipe = subprocess.Popen(
            [
                config.fastspec_path,
                "-i",
                config.fastspec_ini,
                "-s",
                str(run_time),
                "-p",
            ],
            stdout=stdout,
        )

    else:
        # run forever
        fpipe = subprocess.Popen(
            [config.fastspec_path, "-i", config.fastspec_ini, "-p"], stdout=stdout
        )

    if init_time:
        time.sleep(init_time)

    try:
        yield fpipe
    finally:
        # Code to release resource
        if run_time:
            fpipe.wait()
        else:
            fpipe.terminate()

        if post_time:
            time.sleep(post_time)


def run_load(
    load: str,
    run_time: float,
    min_warmup_iters=2,
    max_warmup_iters: int = 50,
    show_fastspec_output=True,
):
    """Run a full calibration of a load."""
    if load in [
        "AntSim1",
        "AntSim2",
        "AntSim3",
        "HotLoad",
        "LongCableOpen",
        "LongCableShort",
    ]:
        config.u3io.configIO(FIOAnalog=15)

    config.u3io.getFeedback(u3.BitDirWrite(4, 1))
    config.u3io.getFeedback(u3.BitDirWrite(5, 1))
    config.u3io.getFeedback(u3.BitDirWrite(6, 1))
    config.u3io.getFeedback(u3.BitDirWrite(7, 1))

    console.rule(f"Starting {load} Calibration")

    block_on_question(f"Connected {load} load to receiver input?")

    if load in ["Ambient", "HotLoad"]:
        block_on_question(
            f"Ensured high-pass filter is connected to ports of {load} Load?"
        )

        block_on_question(
            f"Ensured voltage supply connected to Ambient Load is set to "
            f"{'0V' if load == 'Ambient' else '12V'}?"
        )

    if load in ["LongCableOpen"]:
        block_on_question("Ensured Open is connected to LongCable?")
    if load in ["LongCableShort"]:
        block_on_question("Ensured Short is connected to LongCable?")

    block_on_question("Ensured thermistor port is connected to labjack?")

    console.print(
        "[bold]Starting the spectrum observing program and temperature monitoring program"
    )

    with fastspec_process(
        run_time, stdout=None if show_fastspec_output else subprocess.DEVNULL
    ):
        epipe = subprocess.Popen(["autocal", "temp-sensor"])

    console.rule("[bold]Finished taking spectra.")

    # Warmup before taking S11.
    console.print("[bold]Starting S11 Warmup")
    _take_warmup_s11(min_warmup_iters, max_warmup_iters)

    console.print("")
    console.print("[bold]Taking First Repeat of S11 measurements...")
    take_all_load_s11(1)
    console.print("[bold]Taking Second Repeat of S11 measurements...")
    take_all_load_s11(2)

    epipe.terminate()


def _take_warmup_s11(min_warmup_iters, max_warmup_iters):
    warmup_count = 0
    warmup_re = []
    warmup_im = []
    for warmup_count in range(max_warmup_iters):
        warmup_s11 = SP4T_warmup_s11(print_settings=False)
        freqs = warmup_s11[:, 0]
        warmup_re.append(warmup_s11[:, 1])
        warmup_im.append(warmup_s11[:, 2])

        # Here we put some conditions on when we think it's
        # "converged" in its warmup
        if warmup_count >= max(1, (min_warmup_iters - 1)):  # do _at least_ 1 warmup.
            rms_diff_re = np.sqrt(
                np.mean(
                    np.square(warmup_re[warmup_count] - warmup_re[warmup_count - 1])
                )
            )
            rms_diff_this_re = np.sqrt(
                np.mean(
                    np.square(
                        warmup_re[warmup_count][::2] - warmup_re[warmup_count][1::2]
                    )
                )
            )

            rms_diff_im = np.sqrt(
                np.mean(
                    np.square(warmup_im[warmup_count] - warmup_im[warmup_count - 1])
                )
            )
            rms_diff_this_im = np.sqrt(
                np.mean(
                    np.square(
                        warmup_im[warmup_count][::2] - warmup_im[warmup_count][1::2]
                    )
                )
            )

            if (
                rms_diff_re <= rms_diff_this_re / 2
                and rms_diff_im <= rms_diff_this_im / 2
            ):
                break

            logger.info(
                f"On iteration {warmup_count}, RMS_DIFF=({rms_diff_re}, {rms_diff_im}) vs. RMS_INTRINSIC=({rms_diff_this_re, rms_diff_this_im})"
            )

    with h5py.File("warmup_s11.h5", "w") as fl:
        fl["freqs"] = freqs
        fl["s11"] = np.array(warmup_re) + 1j * np.array(warmup_im)


def measure_receiver_reading(show_fastspec_output=False):
    """Measure receiver reading S11."""
    console.rule("Performing Receiver Reading Measurement")
    block_on_question(
        "Ensured fastspec is running in a different terminal for a minimum of 4 hours to "
        "stabilize the receiver?"
    )

    block_on_question(
        "Ensure the VNA is connected with M-M SMA and calibrated with `autocal cal-vna -r`?"
    )

    for repeat in [1, 2]:

        with fastspec_process(
            init_time=4 * 60 * 60 if repeat == 1 else 0,
            run_time=0,
            stdout=None if show_fastspec_output else subprocess.DEVNULL,
        ):
            # this runs fastspec for four hours before doing the following, then stops
            # fastspec right after the last S11 is taken. The second repeat does not
            # run for four hours first.
            for load in ["Match", "Open", "Short"]:
                block_on_question(
                    f"{load} load connected to VNA {load}{repeat:02} measurement?"
                )

                receiver_s11(f"{load}{repeat:02}.s1p")

            # Block here before we release fastspec, so that it doesn't cool down
            # before the second repeat while waiting for user input.
            block_on_question("ReceiverReading load connected to VNA?")

        # Get the receiver reading
        _set_voltage(0)
        receiver_s11(fname=f"ReceiverReading{repeat:02}.s1p")
        config.u3io.getFeedback(u3.BitStateWrite(7, 1))


def measure_switching_state_s11(min_warmup_iters=2, max_warmup_iters=50):
    """Measure SwitchingState S11."""
    config.u3io.configIO(FIOAnalog=15)
    config.u3io.getFeedback(u3.BitDirWrite(4, 1))
    config.u3io.getFeedback(u3.BitDirWrite(5, 1))
    config.u3io.getFeedback(u3.BitDirWrite(6, 1))
    config.u3io.getFeedback(u3.BitDirWrite(7, 1))

    console.rule("Starting Warmup")
    _take_warmup_s11(min_warmup_iters, max_warmup_iters)

    console.rule("Starting SwitchingState measurements")

    for repeat in range(1, 3):
        for load, voltage in {
            "ExternalMatch": 37,
            "ExternalOpen": 37,
            "ExternalShort": 37,
            "Match": 34,
            "Open": 28,
            "Short": 31.3,
        }.items():
            if load.startswith("External"):
                block_on_question(f"{load} connected to receiver input?")
            take_s11(f"{load}{repeat:02}", voltage)


def _binblock_raw(data_in):
    # Find the start position of the IEEE header, which starts with a '#'.
    data_in = data_in.decode()
    startpos = data_in.find("#")
    logger.debug(f"Startpos: {startpos}")

    # Check for problem with start position.
    if startpos < 0:
        raise IOError("No start of block found")

    # Find the number that follows '#' symbol.  This is the number of digits in the block
    # length.
    size_of_length = int(data_in[startpos + 1])
    logger.debug(f"size_of_length: {size_of_length}")

    # Now that we know how many digits are in the size value, get the size of the data file.
    image_size = int(data_in[(startpos + 2) : (startpos + 2 + size_of_length)])

    # Get the length from the header
    offset = startpos + size_of_length

    # Extract the data out into a list.
    return data_in[offset : offset + image_size]


def _setup(s):
    server_address = ("10.206.161.72", 5025)  # ip address of NA
    logger.info(
        f"Connecting to network analyser {server_address[0]} port {server_address[1]}"
    )

    s.connect(server_address)
    s.send(b"*IDN?\n")
    time.sleep(0.05)
    data = s.recv(200)
    logger.info(f"Connected to ENA: {data}")

    # Define data format for Data transfer reference SCPI
    s.send(b"FORM:DATA ASCii;*OPC?\n")
    s.send(b"SENS:FREQ:START 40e6;*OPC?\n")
    s.send(b"SENS:FREQ:STOP 200e6;*OPC?\n")


def measure_s11(
    fname: Optional[Union[str, Path]] = None,
    print_settings: bool = True,
    count: int = 10,
    power: float = 0.0,
    sleep_after_display: int = 70,
    sleep_after_init: int = 5,
) -> np.ndarray:
    """Measure S11 using a VNA."""
    # Create a TCP/IP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _setup(s)

    # -----------------------------------------------------
    # Set the output power level.
    # There are different levels of attenuation;
    # check document Agilent E5070B/E5071B ENA programmers
    # guide page no 705
    s.send(b"SOUR:POW:ATT 0;*OPC?\n")
    s.send(b"SOUR:POW %f;*OPC?\n" % float(power))
    time.sleep(0.5)
    # -----------------------------------------------------

    s.send(b"SENS:SWE:POIN 641;*OPC?\n")
    s.send(b"SENS:BWID 100;*OPC?\n")
    s.send(b"SENS:AVER:STAT 1;*OPC?\n")
    s.send(b"SENS:AVER:CLE;*OPC?\n")

    s.send(b"SENS:AVER:COUN %d;*OPC?\n" % count)
    s.send(b"INIT:CONT ON;*OPC?\n")
    time.sleep(10)
    s.send(b"DISP:WIND1:TRAC1:Y:AUTO;*OPC?\n")

    if print_settings:
        _print_vna_settings(power, count)

    logger.info("Starting VNA Measurements")

    # FIXME: why is the above MESSAGE commented??
    s.send(b"DISP:WIND1:TRAC1:Y:AUTO;*OPC?\n")
    time.sleep(sleep_after_display)

    s.send(b"INIT:CONT OFF;*OPC?\n")
    time.sleep(sleep_after_init)

    # -----------------------------------------------------------

    # Read Imaginary value and transfer to host controller
    # -----------------------------------------------------------

    # Define data type and chanel for Data transfer reference
    # SCPI Programer guide E5061A
    s.send(b"CALC1:FORM IMAG;*OPC?\n")

    # save data internal memory
    s.send(b'MMEM:STOR:FDAT "D:\\Auto\\EDGES_p.csv";*OPC?\n')
    # transfer data to host controller
    s.send(b'MMEM:TRAN? "D:\\Auto\\EDGES_p.csv";*OPC?\n')
    time.sleep(1)
    data_phase = s.recv(
        180000
    )  # buffer size for receiving data currently set as 15Kbytes

    binary_data_p = _binblock_raw(data_phase)
    data_p = re.split("\r\n|,", binary_data_p)
    length = len(data_p[5:])
    data_p_array = np.array(data_p[5:])
    data_p_re = data_p_array.reshape(length // 3, 3)
    # Read Imaginary value and transfer to host controller
    # -----------------------------------------------------------

    # ----------------------------------------------------------
    # Read Real value and transfer to host controller

    s.send(b"CALC1:FORM REAL;*OPC?\n")
    s.send(b'MMEM:STOR:FDAT "D:\\Auto\\EDGES_m.csv";*OPC?\n')
    s.send(b'MMEM:TRAN? "D:\\Auto\\EDGES_m.csv";*OPC?\n')
    time.sleep(1)
    data_mag = s.recv(180000)

    binary_data_m = _binblock_raw(data_mag)
    data_m = re.split("\r\n|,", binary_data_m)
    length = len(data_m[5:])
    data_m_array = np.array(data_m[5:])
    data_m_re = data_m_array.reshape(length // 3, 3)
    # Read Real value and transfer to host controller
    # -----------------------------------------------------------

    # Reshape Magnitude, phase and save as S11.csv in host controller
    # -----------------------------------------------------------
    s11 = np.empty([np.size(data_m_re, 0), 3])
    s11[:, 0] = data_m_re[:, 0]  # Frequency points
    s11[:, 1] = data_m_re[:, 1]  # real part
    s11[:, 2] = data_p_re[:, 1]  # imaginary part
    if fname:
        _save_s11(s11, fname)
    s.close()
    return s11


def _save_s11(s11: np.ndarray, fname: Union[str, Path] = "S11.csv"):
    np.savetxt(fname, s11, delimiter="\t", header="Hz S RI R 50")


SP4T_warmup_s11 = partial(measure_s11, count=2)
receiver_s11 = partial(
    measure_s11, count=30, power=-35.00, sleep_after_display=230, sleep_after_init=0
)


def vna_calib():
    """Calibrate a VNA."""
    # create a TCP/IP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _setup(s)

    # ------------------------------------------------------
    #       set the output power level there are different level of attenuation
    #       check document Agilent E5070B/E5071B ENA programmers guide page no 705
    s.send(b"SOUR:POW:ATT 0;*OPC?\n")
    s.send(b"SOUR:POW 0.00;*OPC?\n")
    # -----------------------------------------------------

    s.send(b"SENS1:CORR:COLL:CKIT 1;*OPC?\n")

    s.send(b"SENS:SWE:POIN 641;*OPC?\n")
    s.send(b"SENS:BWID 100;*OPC?\n")
    s.send(b"SENS:AVER:STAT 1;*OPC?\n")
    s.send(b"SENS:AVER:CLE;*OPC?\n")

    s.send(b"SENS:AVER:COUN 10;*OPC?\n")

    _print_vna_settings(0, 10)

    console.print("Remaining procedure is done in the front panel of VNA:")
    console.print("  1. Select Calibrate from the main menu")
    console.print("  2. Again select Calibrate")
    console.print("  3. Select 1-Port Cal")
    console.print("  4. Connect open to VNA port-1")
    console.print("  5. Select open and wait for 10 average")
    console.print("  6. Connect Short to VNA port-1")
    console.print("  7. Select Short and wait for 10 average")
    console.print("  8. Connect Load to VNA port-1")
    console.print("  9. Select Load and wait for 10 average")
    console.print("  10. Select Done")

    block_on_question("Confirm that all these steps were taken?")

    console.print(
        "[green] :heavy_check_mark: VNA Calibration is completed for all loads except "
        "ReceiverReading "
    )
    s.close()


def _print_vna_settings(rf_power, n_averaging):
    message = f"""
    IF                 = 100 Hz
    Start freq         = 40  MHz
    Stop freq          = 200 MHz
    No. of freq points = 641
    RF power output    = {rf_power} dBm
    No. of averaging   = {n_averaging}
    Calibration kit    = '85033E Agilent'
    """

    console.print()
    console.print(Panel(message, title="VNA Settings", width=min(150, console.width)))
    console.print()


def vna_calib_receiver_reading():
    """Calibrate a VNA for the Receiver Reading."""
    # create a TCP/IP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _setup(s)

    # ------------------------------------------------------
    #       set the output power level there are different level of attenuation
    #       check document Agilent E5070B/E5071B ENA programmers guide page no 705
    s.send(b"SOUR:POW:ATT 30;*OPC?\n")
    s.send(b"SOUR:POW -35.00;*OPC?\n")
    # -----------------------------------------------------

    s.send(b"SENS1:CORR:COLL:CKIT 1;*OPC?\n")

    s.send(b"SENS:SWE:POIN 641;*OPC?\n")
    s.send(b"SENS:BWID 100;*OPC?\n")
    s.send(b"SENS:AVER:STAT 1;*OPC?\n")
    s.send(b"SENS:AVER:CLE;*OPC?\n")

    s.send(b"SENS:AVER:COUN 30;*OPC?\n")

    _print_vna_settings(-35, 30)

    console.print("[bold blue] Remaning procedure is done in the front pannel of VNA ")
    console.print(
        "Step1: Connect Male to Male SMA adapter to Port-1 and selete Calibrate from the main menu"
    )
    console.print("Step2: Again select Calibrate")
    console.print("Step3: Select 1-Port Cal, Use female calibration kit")
    console.print("Step4: Connect open to VNA port-1")
    console.print("Step5: Select open and wait for 30 average")
    console.print("Step6: Connect Short to VNA port-1")
    console.print("Step7: Select Short and wait for 30 average")
    console.print("Step8: Connect Load to VNA port-1")
    console.print("Step9: Select Load and wait for 30 average")
    console.print("Step10: Select Done")

    block_on_question("Confirm all steps taken?")

    console.print("[green]:checkmark: VNA Calibration is completed for ReceiverReading")

    s.close()


def power_handler(signum, frame):
    """Switch off the 48V sp4t power supply controller while detecting ctrl+C."""
    logger.warning("Ctrl+C detected exiting calibration")
    config.p.terminate()
    config.e.terminate()
    config.u3io.getFeedback(u3.BitStateWrite(4, 1))
    config.u3io.getFeedback(u3.BitStateWrite(5, 1))
    config.u3io.getFeedback(u3.BitStateWrite(6, 1))
    config.u3io.getFeedback(u3.BitStateWrite(7, 1))
    time.sleep(1)
    logger.warning("Exiting cleanly...")
    exit(signum)
