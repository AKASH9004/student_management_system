"""Entry point:  python main.py"""
import sys


def main() -> None:
    try:
        from sms.ui.app import run
    except ImportError as exc:
        sys.exit(f"Tkinter is required to run the GUI ({exc}).\n"
                 "On Debian/Ubuntu install it with: sudo apt install python3-tk")
    run()


if __name__ == "__main__":
    main()
