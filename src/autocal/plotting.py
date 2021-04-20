"""PLotting functionality for autocal."""
import numpy as np
from edges_io.io import FieldSpectrum
from matplotlib import pyplot as plt
from pathlib import Path
from typing import List, Union


def s11_warmup_plot(
    freq: np.ndarray,
    s11_re: List[np.ndarray],
    s11_im: List[np.ndarray],
    temperatures: np.ndarray,
    filename=None,
):
    """Plot all the S11 measurements taken in warmup, to illustrate convergence."""
    nfreq = len(freq)
    assert len(s11_re) == len(s11_im)

    freq0 = freq[0]
    freq1 = freq[nfreq // 2]
    freq2 = freq[-1]

    s11_re = np.array(s11_re)
    s11_im = np.array(s11_im)

    fig, ax = plt.subplots(5, 1, sharex=True)

    ax[0].plot(s11_re[:, 0])
    ax[0].plot(s11_im[:, 0])
    ax[0].set_title(f"{freq0:.2f} MHz")

    ax[1].plot(s11_re[:, nfreq // 2])
    ax[1].plot(s11_im[:, nfreq // 2])
    ax[1].set_title(f"{freq1:.2f} MHz")

    ax[2].plot(s11_re[:, -1])
    ax[2].plot(s11_im[:, -1])
    ax[2].set_title(f"{freq2:.2f} MHz")

    ax[3].plot(np.sqrt(np.mean(np.square(s11_re[1:] - s11_re[:-1]), axis=1)))
    ax[3].plot(np.sqrt(np.mean(np.square(s11_im[1:] - s11_im[:-1]), axis=1)))
    ax[3].set_title("RMS of difference between measurements")

    ax[4].plot(temperatures)
    ax[4].set_title(f"{freq0:.2f} MHz")
    ax[4].set_title("Thermistor Temp.")

    if filename:
        plt.savefig(filename)


def spectrum_plot_golden(
    load: str, in_file: List[Union[str, Path]], golden_file: [str, Path], filename=None
):
    """Plot an ACQ file against a golden set."""
    data = FieldSpectrum(in_file).data
    gdata = np.load(golden_file)

    plt.plot(data.raw_frequency, np.mean(data.spectra["Q"], axis=0), color="C0")
    plt.plot(gdata["freq"], gdata[f"mean_Q_{load}"], color="C1")
    plt.fill_between(
        gdata["freq"],
        gdata[f"lower_quartile_Q_{load}"],
        gdata[f"upper_quartile_Q_{load}"],
        color="C1",
        alpha=0.4,
    )

    if filename:
        plt.savefig(filename)
