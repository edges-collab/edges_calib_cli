"""PLotting functionality for autocal."""
import numpy as np
from matplotlib import pyplot as plt
from typing import List


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
