"""Windows Explorer right-click entry ("Convert with RadialConvert").

Works both from source (python + main.py) and from the packaged exe.
Per-user (HKCU): no admin rights needed.
"""
from __future__ import annotations

import sys
from pathlib import Path

KEY = r"Software\Classes\*\shell\RadialConvert"


def _command() -> tuple[str, str]:
    """(icon path, command line) for the current way of running the app."""
    if getattr(sys, "frozen", False):
        exe = sys.executable
        return exe, f'"{exe}" "%1"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")  # no console window
    runner = str(pythonw if pythonw.exists() else sys.executable)
    main_py = str(Path(__file__).with_name("main.py").resolve())
    return runner, f'"{runner}" "{main_py}" "%1"'


def register() -> str:
    if sys.platform != "win32":
        raise OSError("The right-click entry only works on Windows.")
    import winreg

    icon, command = _command()
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY) as k:
        winreg.SetValue(k, "", winreg.REG_SZ, "Convert with RadialConvert")
        winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, icon)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY + r"\command") as k:
        winreg.SetValue(k, "", winreg.REG_SZ, command)
    return "Added. On Windows 11 it appears under 'Show more options' (Shift+F10)."


def unregister() -> str:
    if sys.platform != "win32":
        raise OSError("The right-click entry only works on Windows.")
    import winreg

    for sub in (KEY + r"\command", KEY):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
        except FileNotFoundError:
            pass
    return "Removed."
