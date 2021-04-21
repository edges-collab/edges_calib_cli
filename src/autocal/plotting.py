"""PLotting functionality for autocal."""
import numpy as np
from matplotlib import pyplot as plt
from typing import Dict, List


def s11_warmup_plot(
    freq: np.ndarray,
    s11_re: Dict[str, List[np.ndarray]],
    s11_im: Dict[str, List[np.ndarray]],
    temperatures: np.ndarray,
    filename=None,
):
    """Plot all the S11 measurements taken in warmup, to illustrate convergence."""
    nfreq = len(freq)
    assert len(s11_re) == len(s11_im)

    freq0 = freq[0]
    freq1 = freq[nfreq // 2]
    freq2 = freq[-1]

    fig, ax = plt.subplots(5, 1, sharex=True, figsize=(12, 12))

    for i, load in enumerate(s11_re.keys()):
        ax[0].plot(s11_re[load][:, 0], ls="-", color=f"C{i}", label=f"{load} (Re)")
        ax[0].plot(s11_im[load][:, 0], ls="--", color=f"C{i}", label=f"{load} (Im)")
        ax[0].set_title(f"{freq0:.2f} MHz")

        ax[1].plot(s11_re[load][:, nfreq // 2])
        ax[1].plot(s11_im[load][:, nfreq // 2])
        ax[1].set_title(f"{freq1:.2f} MHz")

        ax[2].plot(s11_re[load][:, -1])
        ax[2].plot(s11_im[load][:, -1])
        ax[2].set_title(f"{freq2:.2f} MHz")

        ax[3].plot(
            np.sqrt(np.mean(np.square(s11_re[load][1:] - s11_re[load][:-1]), axis=1))
        )
        ax[3].plot(
            np.sqrt(np.mean(np.square(s11_im[load][1:] - s11_im[load][:-1]), axis=1))
        )
        ax[3].set_title("RMS of difference between measurements")

    ax[4].plot(temperatures)
    ax[4].set_title(f"{freq0:.2f} MHz")
    ax[4].set_title("Thermistor Temp.")

    ax[0].legend()

    if filename:
        plt.savefig(filename)
