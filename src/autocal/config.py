"""Configuration options for the package."""
import u3
import yaml
from LabJackPython import NullHandleException
from pathlib import Path

from .utils import singleton


@singleton
class Config:
    """Configuration object.

    Parameters
    ----------
    fname
        Filename where configuration is kept.
    init
        Whether to initialize the u3 object on read.
    """

    def __init__(self, fname: [str, Path], init=True):
        self.config_path = Path(fname).expanduser().absolute()

        if not self.config_path.exists():
            raise IOError(
                "The configuration file at ~/.edges-autocal does not exist yet! Run `autocal init`."
            )

        with open(self.config_path, "r") as fl:
            settings = yaml.load(fl, Loader=yaml.FullLoader)

        self.fastspec_dir = Path(settings["fastspec_dir"])
        self.calib_dir = Path(settings["calib_dir"])
        self.spec_dir = Path(settings["spec_dir"])

        self.fastspec_path = self.fastspec_dir / "fastspec_single"
        self.fastspec_ini = self.fastspec_dir / "edges.ini"

        self.u3io = None

        if init:
            self.initialize()

    def initialize(self):
        """Initialize the u3 object."""
        self.u3io = u3.U3()
        self.u3io.configIO(FIOAnalog=15)
        self.u3io.getFeedback(u3.BitDirWrite(4, 1))
        self.u3io.getFeedback(u3.BitDirWrite(5, 1))
        self.u3io.getFeedback(u3.BitDirWrite(6, 1))
        self.u3io.getFeedback(u3.BitDirWrite(7, 1))


try:
    config = Config("~/.edges-autocal")
except IOError:
    config = None
except NullHandleException:
    config = Config("~/.edges-autocal", init=False)
