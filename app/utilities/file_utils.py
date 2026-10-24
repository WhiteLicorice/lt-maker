from __future__ import annotations
from enum import Enum
import os, subprocess, sys

class Pltfm(Enum):
    """Enum for allowing us to switch on platforms.
    Generic versions exist because there will likely be
    sub-platform specific code, e.g. for Ubutnu or Windows 10,
    that are not applicable to all windows, but I'm not
    trying to future-proof excessively here. Add sub-platforms as necessary.
    """
    UNKNOWN = 'unknown'
    WINDOWS = 'windows_generic'
    MAC = 'mac_generic'
    LINUX = 'linux_generic'

    def is_windows(self) -> bool:
        return 'windows' in self.value

    @staticmethod
    def windows() -> bool:
        return Pltfm.current_platform().is_windows()

    def is_mac(self) -> bool:
        return 'mac' in self.value

    @staticmethod
    def mac() -> bool:
        return Pltfm.current_platform().is_mac()

    def is_linux(self) -> bool:
        return 'linux' in self.value

    @staticmethod
    def linux() -> bool:
        return Pltfm.current_platform().is_linux()

    @staticmethod
    def current_platform() -> Pltfm:
        # sys.platform costs nothing to read, where the first call to
        # platform.system() on Windows asks WMI and takes 50 ms or more
        if sys.platform == 'win32':
            return Pltfm.WINDOWS
        elif sys.platform == 'darwin':
            return Pltfm.MAC
        elif sys.platform.startswith('linux'):
            return Pltfm.LINUX
        else:
            return Pltfm.UNKNOWN

def startfile(fn: str):
    if Pltfm.windows():
        os.startfile(fn)
    elif Pltfm.mac():
        opener = "open"
        subprocess.call([opener, fn])
    else:  # Linux??
        opener = "xdg-open"
        subprocess.call([opener, fn])

