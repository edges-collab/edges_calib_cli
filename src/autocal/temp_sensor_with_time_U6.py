"""Functions for the temperature sensor measurements."""

import csv
import datetime
import logging
import math
import time
import u6

logger = logging.getLogger(__name__)

ABS_ZERO = 273.15


def temp_sensor(filename="Temperature.csv"):
    """Measure thermistor temperature."""
    connection = u6.U6()

    with open(filename, "w") as csvfile:
        fieldnames = [
            "Date",
            "Time",
            "LNA Voltage",
            "LNA Thermistor (Ohm)",
            "LNA (C)",
            "SP4T Voltage",
            "SP4T Thermistor (Ohm)",
            "SP4T (C)",
            "Load Voltage",
            "Load-thermistor (Ohm)",
            "Load (C)",
            "Room_Temp(C)",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        while True:
            now = datetime.datetime.now()
            date = now.strftime("%m/%d/%Y")
            times = now.strftime("%H:%M:%S")
            internal_temp = connection.getTemperature() - ABS_ZERO

            # -----------------------------------------------------------------------------------
            # Read Labjack Voltage
            # -----------------------------------------------------------------------------------
            lna_voltage = connection.getAIN(3)
            sp4t_voltage = connection.getAIN(0)
            load_voltage = connection.getAIN(1)
            vs = connection.getAIN(2)  # measure the Vs (V) of labjack
            # -----------------------------------------------------------------------------------
            # Calculate the resistence from voltage
            # -----------------------------------------------------------------------------------
            lna_resistance = (lna_voltage * 9918) / (vs - lna_voltage)
            sp4t_resistance = (sp4t_voltage * 9960) / (vs - sp4t_voltage)
            load_resistance = (load_voltage * 9923) / (vs - load_voltage)

            # -----------------------------------------------------------------------------------
            # Calculate the temperature with curve fitting
            # -----------------------------------------------------------------------------------
            f = (
                0.129675e-2,
                0.197374e-3,
                0.304e-6,
                1.03514e-3,
                2.33825e-4,
                7.92467e-8,
            )

            try:  # Hello leroy Fixes the value error causing a crash
                lna_deg_cels = (
                    1
                    / (
                        f[0]
                        + f[1] * math.log(lna_resistance)
                        + f[2] * math.pow(math.log(lna_resistance), 3)
                    )
                    - ABS_ZERO
                )
                sp4t_deg_cels = (
                    1
                    / (
                        f[0]
                        + f[1] * math.log(sp4t_resistance)
                        + f[2] * math.pow(math.log(sp4t_resistance), 3)
                    )
                    - ABS_ZERO
                )
                load_deg_cels = (
                    1
                    / (
                        f[3]
                        + f[4] * math.log(load_resistance)
                        + f[5] * math.pow(math.log(load_resistance), 3)
                    )
                    - ABS_ZERO
                )
            except ValueError:
                continue

            time.sleep(30)

            row = {
                "Date": date,
                "Time": times,
                "LNA Voltage": lna_voltage,
                "LNA Thermistor (Ohm)": lna_resistance,
                "LNA (C)": lna_deg_cels,
                "SP4T Voltage": sp4t_voltage,
                "SP4T Thermistor (Ohm)": sp4t_resistance,
                "SP4T (C)": sp4t_deg_cels,
                "Load Voltage": load_voltage,
                "Load-thermistor (Ohm)": load_resistance,
                "Load (C)": load_deg_cels,
                "Room_Temp(C)": internal_temp,
            }
            writer.writerow(row)
            logger.info(row)
