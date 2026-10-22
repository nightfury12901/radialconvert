"""Add / remove the Explorer right-click entry when running from source.

    python register_context_menu.py          # add (current user only, no admin needed)
    python register_context_menu.py --remove # remove
"""
import sys

import shell_integration

if __name__ == "__main__":
    try:
        print(shell_integration.unregister() if "--remove" in sys.argv else shell_integration.register())
    except OSError as exc:
        sys.exit(str(exc))
