"""Shared UI helpers."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from config import BG, CARD, DANGER, MUTED, PRIMARY, TEXT


def setup_styles() -> ttk.Style:
    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    elif "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"), foreground=PRIMARY, background=BG)
    style.configure("Section.TLabel", font=("Segoe UI", 12, "bold"), foreground=PRIMARY, background=CARD)
    style.configure("Card.TFrame", background=CARD)
    style.configure("Nav.TButton", font=("Segoe UI", 10))
    style.configure("Treeview", rowheight=26, font=("Segoe UI", 9))
    style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
    style.map("Treeview", background=[("selected", PRIMARY)], foreground=[("selected", "white")])
    return style


def stat_card(parent: tk.Widget, label: str, value: str = "0") -> ttk.Label:
    frame = tk.Frame(parent, bg=CARD, padx=12, pady=10, highlightbackground="#dee2e6", highlightthickness=1)
    frame.pack(side=tk.LEFT, padx=(0, 8), fill=tk.BOTH, expand=True)
    ttk.Label(frame, text=label, background=CARD, foreground=MUTED, font=("Segoe UI", 9)).pack(anchor=tk.W)
    val = ttk.Label(frame, text=value, background=CARD, foreground=PRIMARY, font=("Segoe UI", 16, "bold"))
    val.pack(anchor=tk.W)
    return val


def error_label(parent: tk.Widget) -> tk.Label:
    return tk.Label(parent, text="", fg=DANGER, bg=CARD, font=("Segoe UI", 8), anchor=tk.W)


def draw_bar_chart(canvas: tk.Canvas, data: list[tuple[str, int]], title: str = "") -> None:
    canvas.delete("all")
    w = int(canvas.winfo_width() or 400)
    h = int(canvas.winfo_height() or 200)
    if w < 50:
        w = 400
    if h < 50:
        h = 200
    if not data:
        canvas.create_text(w // 2, h // 2, text="No data yet", fill=MUTED, font=("Segoe UI", 10))
        return
    max_val = max(v for _, v in data) or 1
    margin_l, margin_b, margin_t = 80, 36, 28
    chart_w = w - margin_l - 20
    chart_h = h - margin_b - margin_t
    bar_w = max(20, chart_w // max(len(data), 1) - 10)
    canvas.create_text(w // 2, 12, text=title, fill=PRIMARY, font=("Segoe UI", 10, "bold"))
    for i, (label, val) in enumerate(data):
        x = margin_l + i * (bar_w + 12)
        bar_h = int((val / max_val) * chart_h)
        y0 = margin_t + chart_h
        y1 = y0 - bar_h
        canvas.create_rectangle(x, y1, x + bar_w, y0, fill=PRIMARY, outline="")
        canvas.create_text(x + bar_w // 2, y0 + 12, text=str(label)[:10], fill=TEXT, font=("Segoe UI", 7))
        canvas.create_text(x + bar_w // 2, y1 - 8, text=str(val), fill=TEXT, font=("Segoe UI", 8))
