"""Start E-Basura Mo."""
import sys
import traceback


def main() -> None:
    try:
        from app import EBasuraApp

        EBasuraApp(kiosk="--kiosk" in sys.argv).run()
    except Exception:
        err = traceback.format_exc()
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "E-Basura Mo could not start",
                f"Something went wrong while opening the app.\n\n{err}",
            )
            root.destroy()
        except Exception:
            print("E-Basura Mo could not start:\n")
            print(err)
            input("Press Enter to close...")
        sys.exit(1)


if __name__ == "__main__":
    main()
