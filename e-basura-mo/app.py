"""E-Basura Mo — main window, login, and navigation."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from config import APP_NAME, APP_TAGLINE, BG, CARD, MUTED, PRIMARY, TEXT
from database import Database
from frames import (
    AnnouncementsFrame,
    CrewFrame,
    DashboardFrame,
    KioskFrame,
    PickupsFrame,
    ReportsFrame,
    ResidentsFrame,
    ScheduleFrame,
)
from widgets import setup_styles

FRAME_CLASSES = {
    "dashboard": DashboardFrame,
    "reports": ReportsFrame,
    "pickups": PickupsFrame,
    "residents": ResidentsFrame,
    "crew": CrewFrame,
    "announcements": AnnouncementsFrame,
    "schedule": ScheduleFrame,
}


class EBasuraApp:
    def __init__(self, kiosk: bool = False) -> None:
        self.db = Database()
        self.user: dict = {}
        self.frames: dict[str, ttk.Frame] = {}

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("1200x760")
        self.root.minsize(1000, 640)
        self.root.configure(bg=BG)
        setup_styles()

        if kiosk:
            self._show_kiosk()
        else:
            self._show_login()

        self.status = tk.Label(
            self.root, text="Ready.", anchor=tk.W, bg="#e9ecef", fg=TEXT,
            padx=12, pady=6, font=("Segoe UI", 9),
        )
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def _show_login(self) -> None:
        self.login_frame = tk.Frame(self.root, bg=BG)
        self.login_frame.pack(fill=tk.BOTH, expand=True)

        card = tk.Frame(
            self.login_frame, bg=CARD, padx=40, pady=36,
            highlightbackground="#dee2e6", highlightthickness=1,
        )
        card.place(relx=0.5, rely=0.45, anchor=tk.CENTER)

        ttk.Label(
            card, text=APP_NAME, font=("Segoe UI", 22, "bold"),
            foreground=PRIMARY, background=CARD,
        ).pack()
        ttk.Label(
            card, text=APP_TAGLINE, font=("Segoe UI", 10),
            foreground=MUTED, background=CARD, wraplength=320,
        ).pack(pady=(6, 20))

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        ttk.Label(card, text="Username", background=CARD).pack(anchor=tk.W)
        ttk.Entry(card, textvariable=self.username_var, width=32).pack(fill=tk.X, pady=(2, 10))
        ttk.Label(card, text="Password", background=CARD).pack(anchor=tk.W)
        ttk.Entry(card, textvariable=self.password_var, width=32, show="•").pack(fill=tk.X, pady=(2, 16))
        ttk.Button(card, text="Sign in", command=self._login).pack(fill=tk.X, pady=4)
        ttk.Button(
            card, text="Resident kiosk (no login)", command=self._open_kiosk_from_login,
        ).pack(fill=tk.X, pady=8)

        tk.Label(
            card,
            text=" Basura Mo Itapon Mo! ",
            bg=CARD, fg="#888", font=("Segoe UI", 8), wraplength=300,
        ).pack(pady=(12, 0))
        self.root.bind("<Return>", lambda _: self._login())

    def _login(self) -> None:
        user = self.db.authenticate(self.username_var.get(), self.password_var.get())
        if not user:
            messagebox.showerror("Could not sign in", "Wrong username or password. Please try again.")
            return
        self.user = user
        self.login_frame.destroy()
        self._build_main()

    def _open_kiosk_from_login(self) -> None:
        self.login_frame.destroy()
        self._show_kiosk()

    def _show_kiosk(self) -> None:
        self.user = {"full_name": "Kiosk", "role": "Kiosk", "user_id": 0}
        top = tk.Frame(self.root, bg=PRIMARY, padx=16, pady=10)
        top.pack(fill=tk.X)
        tk.Label(
            top, text=f"{APP_NAME} — Resident desk", fg="white", bg=PRIMARY,
            font=("Segoe UI", 14, "bold"),
        ).pack(side=tk.LEFT)
        ttk.Button(top, text="Staff sign in", command=self._kiosk_to_login).pack(side=tk.RIGHT)

        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        self.kiosk = KioskFrame(container, self)
        self.kiosk.pack(fill=tk.BOTH, expand=True)
        self.kiosk.refresh()

    def _kiosk_to_login(self) -> None:
        if messagebox.askyesno("Staff sign in", "Close the kiosk and open staff login?"):
            self.root.destroy()
            EBasuraApp(kiosk=False).run()

    def _nav_for_role(self, role: str) -> list[tuple[str, str]]:
        items = [("dashboard", "Home")]
        if role == "Captain":
            items += [("schedule", "Collection schedule"), ("announcements", "Announcements")]
        elif role == "Viewer":
            items += [("reports", "Waste reports"), ("schedule", "Collection schedule")]
        else:
            items += [
                ("reports", "Waste reports"),
                ("pickups", "Pickup requests"),
                ("residents", "Residents"),
                ("crew", "Collection crew"),
                ("announcements", "Announcements"),
                ("schedule", "Collection schedule"),
            ]
        return items

    def _build_main(self) -> None:
        role = self.user.get("role", "Staff")
        top = tk.Frame(self.root, bg=PRIMARY, padx=12, pady=8)
        top.pack(fill=tk.X)
        tk.Label(
            top, text=APP_NAME, fg="white", bg=PRIMARY, font=("Segoe UI", 14, "bold"),
        ).pack(side=tk.LEFT)
        tk.Label(
            top,
            text=f"  {self.user.get('full_name', '')} · {role}",
            fg="#d8f3dc", bg=PRIMARY, font=("Segoe UI", 10),
        ).pack(side=tk.LEFT, padx=8)
        ttk.Button(top, text="Sign out", command=self._logout).pack(side=tk.RIGHT)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)

        nav = tk.Frame(body, bg="#d8f3dc", width=180)
        nav.pack(side=tk.LEFT, fill=tk.Y)
        nav.pack_propagate(False)

        container = ttk.Frame(body)
        container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        nav_items = self._nav_for_role(role)
        for key, label in nav_items:
            ttk.Button(
                nav, text=label, style="Nav.TButton",
                command=lambda k=key: self.show_frame(k),
            ).pack(fill=tk.X, padx=8, pady=4)

        if role in ("Admin", "Staff"):
            ttk.Separator(nav).pack(fill=tk.X, pady=8, padx=8)
            ttk.Button(nav, text="Open resident kiosk", command=self._launch_kiosk_window).pack(
                fill=tk.X, padx=8, pady=4,
            )

        for key, _ in nav_items:
            self.frames[key] = FRAME_CLASSES[key](container, self)
            self.frames[key].grid(row=0, column=0, sticky="nsew")

        self.show_frame("dashboard")

    def show_frame(self, name: str) -> None:
        frame = self.frames.get(name)
        if frame:
            frame.tkraise()
            if hasattr(frame, "refresh"):
                frame.refresh()

    def refresh_dashboard(self) -> None:
        dash = self.frames.get("dashboard")
        if dash and hasattr(dash, "refresh"):
            dash.refresh()

    def set_status(self, msg: str) -> None:
        if not msg.endswith("."):
            msg += "."
        self.status.config(text=msg)

    def _logout(self) -> None:
        if messagebox.askyesno("Sign out", "Sign out of E-Basura Mo?"):
            self.root.destroy()
            EBasuraApp().run()

    def _launch_kiosk_window(self) -> None:
        win = tk.Toplevel(self.root)
        win.title(f"{APP_NAME} — Resident desk")
        win.geometry("700x600")
        kiosk = KioskFrame(win, self)
        kiosk.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        kiosk.refresh()

    def run(self) -> None:
        self.root.mainloop()
