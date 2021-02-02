"""Automation routines for lab calibration."""
import logging
import numpy as np
import questionary as qs
import re
import socket
import subprocess
import time
import u3
from rich.console import Console

from .config import config

console = Console()
logger = logging.getLogger(__name__)


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


def take_s11(fname, voltage):
    """Take S11 with particular voltage settings."""
    settings = _get_voltage_settings(voltage)

    config.u3io.getFeedback(u3.BitStateWrite(4, settings[0]))
    config.u3io.getFeedback(u3.BitStateWrite(5, settings[1]))
    config.u3io.getFeedback(u3.BitStateWrite(6, settings[2]))
    time.sleep(0.1)
    config.u3io.getFeedback(u3.BitStateWrite(7, settings[3]))

    logger.info(f"Taking {fname} measurement at {voltage}V...")
    measure_s11(f"{fname}.s1p")
    config.u3io.getFeedback(u3.BitStateWrite(7, 1))
    logger.info(f"... saved as '{fname}.s1p'")


def take_all_s11(repeat_num: int):
    """Take all S11 measurements for a load."""
    take_s11(f"External{repeat_num:02}", voltage=37)
    take_s11(f"Match{repeat_num:02}", voltage=34)
    take_s11(f"Short{repeat_num:02}", voltage=31.3)
    take_s11(f"Open{repeat_num:02}", voltage=28)


def run_load(load, run_time):
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

    if qs.confirm(f"Connected {load} load to receiver input?").ask():
        pass

    if load in ["Ambient", "HotLoad"]:
        if qs.confirm(
            f"Ensured high-pass filter is connected to ports of {load} Load?"
        ).ask():
            pass

        if qs.confirm(
            f"Ensured voltage supply connected to Ambient Load is set to "
            f"{'0V' if load == 'Ambient' else '12V'}?"
        ).ask():
            pass

    if (
        load in ["LongCableOpen"]
        and qs.confirm("Ensured Open is connected to LongCable?").ask()
    ):
        pass

    if (
        load in ["LongCableShort"]
        and qs.confirm("Ensured Short is connected to LongCable?").ask()
    ):
        pass

    if qs.confirm("Ensured thermistor port is connected to labjack?").ask():
        pass

    console.print(
        "[bold]Starting the spectrum observing program and temperature monitoring program"
    )

    subprocess.Popen(
        [config.fastspec_path, "-i", config.fastspec_ini, "-s", str(run_time), "-p"]
    )

    epipe = subprocess.Popen(["autocal", "temp_sensor"])
    time.sleep(run_time + 60)

    console.rule("[bold]Finished taking spectra.")

    console.print("")
    console.print("[bold]Taking First Set of S11 measurements...")
    take_all_s11(1)
    console.print("[bold]Taking Second Set of S11 measurements...")
    take_all_s11(2)

    # TODO: why don't we termine `pipe`?
    epipe.terminate()


def measure_receiver_reading():
    """Measure receiver reading S11."""
    console.rule("Performing Receiver Reading Measurement")
    if qs.confirm(
        "Ensured fastspec is running in a different terminal for a minimum of 4 hours to "
        "stabilize the receiver?"
    ).ask():
        pass

    if qs.confirm(
        "Ensure the VNA is connected with M-M SMA and calibrated with `autocal cal-vna -r`?"
    ).ask():
        pass

    for i in range(2):
        for load in ["Match", "Open", "Short", "ReceiverReading"]:
            if qs.confirm(
                f"Matched load connected to VNA {load}{i:02} measurement?"
            ).ask():
                receiver_s11(f"{load}{i:02}.s1p")


def measure_switching_state_s11():
    """Measure SwitchingState S11."""
    config.u3io.configIO(FIOAnalog=15)
    config.u3io.getFeedback(u3.BitDirWrite(4, 1))
    config.u3io.getFeedback(u3.BitDirWrite(5, 1))
    config.u3io.getFeedback(u3.BitDirWrite(6, 1))
    config.u3io.getFeedback(u3.BitDirWrite(7, 1))

    console.rule("Starting SwitchingState measurements")

    for repeat in range(2):
        for load, voltage in {
            "ExternalMatch": 37,
            "ExternalOpen": 37,
            "ExternalShort": 37,
            "Match": 34,
            "Open": 31.3,
            "Short": 28,
        }.items():
            if qs.confirm(f"{load} connected to receiver input?").ask():
                take_s11(f"{load}{repeat:02}", voltage, 1, 1, 1, 0)


def _binblock_raw(data_in):
    # Find the start position of the IEEE header, which starts with a '#'.
    startpos = data_in.find(b"#")
    logger.debug(f"Startpos: {startpos}")

    # Check for problem with start position.
    if startpos < 0:
        raise IOError("No start of block found")

    # Find the number that follows '#' symbol.  This is the number of digits in the block
    # length.
    size_of_length = int(str(data_in[startpos + 1]))
    logger.debug(f"size_of_length: {size_of_length}")
    logger.debug(f"data_in: {data_in}")

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


def measure_s11(fname=None):
    """Measure S11 once a load has been connected."""
    # Create a TCP/IP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _setup(s)

    # -----------------------------------------------------
    #       set the output power level there are different level of attenuation
    #       check document Agilent E5070B/E5071B ENA programmers guide page no 705
    s.send(b"SOUR:POW:ATT 0;*OPC?\n")
    s.send(b"SOUR:POW 0;*OPC?\n")
    time.sleep(0.5)
    # -----------------------------------------------------

    s.send(b"SENS:SWE:POIN 641;*OPC?\n")
    s.send(b"SENS:BWID 100;*OPC?\n")
    s.send(b"SENS:AVER:STAT 1;*OPC?\n")
    s.send(b"SENS:AVER:CLE;*OPC?\n")

    s.send(b"SENS:AVER:COUN 10;*OPC?\n")
    s.send(b"INIT:CONT ON;*OPC?\n")
    time.sleep(10)
    s.send(b"DISP:WIND1:TRAC1:Y:AUTO;*OPC?\n")

    _print_vna_settings(0, 10)

    console.print()
    console.rule("Starting Measurements")
    # FIXME: why is the above MESSAGE commented??
    s.send(b"DISP:WIND1:TRAC1:Y:AUTO;*OPC?\n")
    time.sleep(70)

    s.send(b"INIT:CONT OFF;*OPC?\n")
    time.sleep(5)

    # Read Phase value and transfer to host controller
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
    data_p_re = data_p_array.reshape(length / 3, 3)

    # Read Magnitude value and transfer to host controller
    # -----------------------------------------------------------
    s.send(b"CALC1:FORM REAL;*OPC?\n")
    s.send(b'MMEM:STOR:FDAT "D:\\Auto\\EDGES_m.csv";*OPC?\n')
    s.send(b'MMEM:TRAN? "D:\\Auto\\EDGES_m.csv";*OPC?\n')
    time.sleep(1)
    data_mag = s.recv(180000)

    binary_data_m = _binblock_raw(data_mag)
    data_m = re.split("\r\n|,", binary_data_m)
    length = len(data_m[5:])
    data_m_array = np.array(data_m[5:])
    data_m_re = data_m_array.reshape(length / 3, 3)

    # Reshape Magnitude, phase and save as S11.csv in host controller
    # -----------------------------------------------------------
    s11 = np.empty([np.size(data_m_re, 0), 3])
    s11[:, 0] = data_m_re[:, 0]
    s11[:, 1] = data_m_re[:, 1]
    s11[:, 2] = data_p_re[:, 1]
    console.print("S11=", s11)
    fname = fname or "S11.csv"
    np.savetxt(fname, s11, delimiter=",")
    s.close()


def receiver_s11(fname):
    """Measure Receiver S11."""
    # Create a TCP/IP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _setup(s)

    # -----------------------------------------------------
    #       set the output power level there are different level of attenuation
    #       check document Agilent E5070B/E5071B ENA programmers guide page no 705
    s.send(b"SOUR:POW:ATT 30;*OPC?\n")
    s.send(b"SOUR:POW -35.00;*OPC?\n")
    time.sleep(0.5)
    # -----------------------------------------------------

    s.send(b"SENS:SWE:POIN 641;*OPC?\n")
    s.send(b"SENS:BWID 100;*OPC?\n")
    s.send(b"SENS:AVER:STAT 1;*OPC?\n")
    s.send(b"SENS:AVER:CLE;*OPC?\n")

    s.send(b"SENS:AVER:COUN 30;*OPC?\n")
    s.send(b"INIT:CONT ON;*OPC?\n")
    time.sleep(10)
    s.send(b"DISP:WIND1:TRAC1:Y:AUTO;*OPC?\n")

    _print_vna_settings(-35, 30)

    console.rule("Starting Measurements")
    # FIXME: what message?
    s.send(b"DISP:WIND1:TRAC1:Y:AUTO;*OPC?\n")
    time.sleep(230)
    s.send(b"INIT:CONT OFF;*OPC?\n")

    # ___________________________________________________________
    # Read Phase value and transfer to host controller
    # -----------------------------------------------------------
    # Define data type and chanel for Data transfer
    # reference SCPI Programer guide E5061A
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
    data_p_re = data_p_array.reshape(length / 3, 3)

    # ___________________________________________________________
    # Read Magnitude value and transfer to host controller
    # -----------------------------------------------------------
    s.send(b"CALC1:FORM REAL;*OPC?\n")
    s.send(b'MMEM:STOR:FDAT "D:\\Auto\\EDGES_m.csv";*OPC?\n')
    s.send(b'MMEM:TRAN? "D:\\Auto\\EDGES_m.csv";*OPC?\n')
    time.sleep(1)
    data_mag = s.recv(180000)

    binary_data_m = _binblock_raw(data_mag)
    data_m = re.split("\r\n|,", binary_data_m)
    length = len(data_m[5:])
    data_m_array = np.array(data_m[5:])
    data_m_re = data_m_array.reshape(length / 3, 3)

    # ___________________________________________________________
    # Reshape Magnitude, phase and save as S11.csv in host controller
    # -----------------------------------------------------------
    s11 = np.empty([np.size(data_m_re, 0), 3])
    s11[:, 0] = data_m_re[:, 0]
    s11[:, 1] = data_m_re[:, 1]
    s11[:, 2] = data_p_re[:, 1]
    console.print("S11=", s11)
    fname = fname or "S11.csv"
    np.savetxt(fname, s11, delimiter=",")

    s.close()


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

    console.print("Remaning procedure is done in the front pannel of VNA ")
    console.print("Step1: Selete Calibrate from the main menu")
    console.print("Step2: Again select Calibrate")
    console.print("Step3: Select 1-Port Cal")
    console.print("Step4: Connect open to VNA port-1")
    console.print("Step5: Select open and wait for 10 average")
    console.print("Step6: Connect Short to VNA port-1")
    console.print("Step7: Select Short and wait for 10 average")
    console.print("Step8: Connect Load to VNA port-1")
    console.print("Step9: Select Load and wait for 10 average")
    console.print("Step10: Select Done")

    if qs.confirm("Confirm that all these steps were taken?").ask():
        console.print(
            "[green] :heavy_check_mark: VNA Calibration is completed for all loads except ReceiverReading"
        )
    s.close()


def _print_vna_settings(rf_power, n_averaging):
    console.print()
    console.rule("Settings for VNA calibration")
    console.print("IF                 =100Hz")
    console.print("Start freq         =40MHz")
    console.print("Stop freq          =200MHz")
    console.print("No. of freq points =641")
    console.print(f"RF power output    ={rf_power}dBm")
    console.print(f"No. of averaging   ={n_averaging}")
    console.print("Calibration kit    =85033E Agilent")
    console.rule()
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
    console.print("Step5: Select open and wait for 10 average")
    console.print("Step6: Connect Short to VNA port-1")
    console.print("Step7: Select Short and wait for 10 average")
    console.print("Step8: Connect Load to VNA port-1")
    console.print("Step9: Select Load and wait for 10 average")
    console.print("Step10: Select Done")

    if qs.confirm("Confirm all steps taken?").ask():
        console.print(
            "[green]:checkmark: VNA Calibration is completed for ReceiverReading"
        )

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
