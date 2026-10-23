"""Add / remove a "Convert with RadialConvert" entry in the Windows Explorer right-click menu.

    python register_context_menu.py          # add (current user only, no admin needed)
    python register_context_menu.py --remove # remove
"""
import sys
from pathlib import Path

if sys.platform != "win32":
    sys.exit("This script only works on Windows.")

import winreg

KEY = r"Software\Classes\*\shell\RadialConvert"


def add():
    pythonw = Path(sys.executable).with_name("pythonw.exe")  # no console window
    runner = str(pythonw if pythonw.exists() else sys.executable)
    main_py = str(Path(__file__).with_name("main.py").resolve())
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY) as k:
        winreg.SetValue(k, "", winreg.REG_SZ, "Convert with RadialConvert")
        winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, runner)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY + r"\command") as k:
        winreg.SetValue(k, "", winreg.REG_SZ, f'"{runner}" "{main_py}" "%1"')
    print("Added. On Windows 11 it appears under 'Show more options' (Shift+F10).")


#hi
def remove():
    for sub in (KEY + r"\command", KEY):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
        except FileNotFoundError:
            pass
    print("Removed.")


if __name__ == "__main__":
    remove() if "--remove" in sys.argv else add()

