"""Application screens (tkinter frames)."""
from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

from config import (
    BG,
    CARD,
    DAYS_OF_WEEK,
    PICKUP_STATUSES,
    PICKUP_WASTE_TYPES,
    MUTED,
    PRIMARY,
    REPORT_STATUSES,
    REPORT_TYPES,
    TEXT,
)
from photo_utils import save_photo
from print_reports import (
    print_announcement_slip,
    print_captain_summary,
    print_daily_task_sheet,
    print_report_list,
)
from validators import (
    validate_announcement,
    validate_pickup,
    validate_report,
    validate_resident,
    validate_schedule,
)
from widgets import draw_bar_chart, error_label, stat_card


class DashboardFrame(ttk.Frame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, style="Card.TFrame", padding=16)
        self.app = app
        self.stat_labels: dict[str, ttk.Label] = {}
        self._build()

    def _build(self) -> None:
        ttk.Label(self, text="Home", style="Section.TLabel").pack(anchor=tk.W)
        bar = tk.Frame(self, bg=CARD)
        bar.pack(fill=tk.X, pady=10)
        for key, label in [
            ("reports_pending", "Waiting"),
            ("reports_assigned", "Assigned"),
            ("reports_resolved", "Resolved"),
            ("pickups_pending", "Pending Pickups"),
        ]:
            self.stat_labels[key] = stat_card(bar, label)

        charts = tk.Frame(self, bg=CARD)
        charts.pack(fill=tk.BOTH, expand=True, pady=8)
        left = tk.Frame(charts, bg=CARD)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        right = tk.Frame(charts, bg=CARD)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(left, text="Complaint types (30 days)", style="Section.TLabel", background=CARD).pack(anchor=tk.W)
        self.type_chart = tk.Canvas(left, bg="#f8f9fa", height=220, highlightthickness=1, highlightbackground="#dee2e6")
        self.type_chart.pack(fill=tk.BOTH, expand=True)
        ttk.Label(right, text="Open issues by barangay", style="Section.TLabel", background=CARD).pack(anchor=tk.W)
        self.zone_chart = tk.Canvas(right, bg="#f8f9fa", height=220, highlightthickness=1, highlightbackground="#dee2e6")
        self.zone_chart.pack(fill=tk.BOTH, expand=True)

        actions = tk.Frame(self, bg=CARD)
        actions.pack(fill=tk.X, pady=8)
        ttk.Button(actions, text="Print crew task list", command=self._print_tasks).pack(side=tk.LEFT, padx=4)
        role = self.app.user.get("role", "")
        if role in ("Captain", "Admin", "Staff"):
            ttk.Button(actions, text="Print barangay summary", command=self._print_summary).pack(side=tk.LEFT, padx=4)

    def refresh(self) -> None:
        stats = self.app.db.get_dashboard_stats()
        self.stat_labels["reports_pending"].config(text=str(stats["reports_pending"]))
        self.stat_labels["reports_assigned"].config(text=str(stats["reports_assigned"]))
        self.stat_labels["reports_resolved"].config(text=str(stats["reports_resolved"]))
        self.stat_labels["pickups_pending"].config(text=str(stats["pickups_pending"]))
        types = [(r["report_type"], r["count"]) for r in self.app.db.get_report_type_counts(30)]
        zones = [(r["zone"], r["count"]) for r in self.app.db.get_zone_counts()]
        self.type_chart.after(100, lambda: draw_bar_chart(self.type_chart, types, "By Type"))
        self.zone_chart.after(100, lambda: draw_bar_chart(self.zone_chart, zones, "By Barangay"))

    def _print_tasks(self) -> None:
        print_daily_task_sheet(self.app.db)
        self.app.set_status("Task list opened — you can print from the browser.")

    def _print_summary(self) -> None:
        print_captain_summary(self.app.db)
        self.app.set_status("Summary opened — you can print from the browser.")


class ReportsFrame(ttk.Frame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, style="Card.TFrame", padding=12)
        self.app = app
        self.selected_id: int | None = None
        self.photo_path: str | None = None
        self._errs: dict[str, tk.Label] = {}
        self._build()

    def _build(self) -> None:
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5, bg=BG)
        paned.pack(fill=tk.BOTH, expand=True)

        form = ttk.Frame(paned, padding=10)
        paned.add(form, minsize=300, width=340)
        ttk.Label(form, text="Waste Report", style="Section.TLabel").pack(anchor=tk.W, pady=(0, 8))

        self.resident_var = tk.StringVar()
        ttk.Label(form, text="Resident *", background=CARD).pack(anchor=tk.W)
        rf = tk.Frame(form, bg=CARD)
        rf.pack(fill=tk.X)
        self.resident_combo = ttk.Combobox(rf, textvariable=self.resident_var, width=28, state="readonly")
        self.resident_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(rf, text="New", width=5, command=self._new_resident).pack(side=tk.LEFT, padx=4)
        self._errs["resident"] = error_label(form)
        self._errs["resident"].pack(fill=tk.X)

        self.type_var = tk.StringVar()
        ttk.Label(form, text="Report Type *", background=CARD).pack(anchor=tk.W)
        ttk.Combobox(form, textvariable=self.type_var, values=REPORT_TYPES, state="readonly").pack(fill=tk.X, pady=2)
        self._errs["report_type"] = error_label(form)
        self._errs["report_type"].pack(fill=tk.X)

        self.location_var = tk.StringVar()
        ttk.Label(form, text="Location *", background=CARD).pack(anchor=tk.W)
        ttk.Entry(form, textvariable=self.location_var).pack(fill=tk.X, pady=2)
        self._errs["location_description"] = error_label(form)
        self._errs["location_description"].pack(fill=tk.X)

        ttk.Label(form, text="Description *", background=CARD).pack(anchor=tk.W)
        self.desc = tk.Text(form, height=4, font=("Segoe UI", 9), wrap=tk.WORD)
        self.desc.pack(fill=tk.X, pady=2)
        self._errs["description"] = error_label(form)
        self._errs["description"].pack(fill=tk.X)

        pf = tk.Frame(form, bg=CARD)
        pf.pack(fill=tk.X, pady=4)
        ttk.Button(pf, text="Attach Photo", command=self._pick_photo).pack(side=tk.LEFT)
        self.photo_lbl = ttk.Label(pf, text="No photo", background=CARD)
        self.photo_lbl.pack(side=tk.LEFT, padx=8)

        self.crew_var = tk.StringVar()
        ttk.Label(form, text="Assign Crew", background=CARD).pack(anchor=tk.W, pady=(8, 0))
        self.crew_combo = ttk.Combobox(form, textvariable=self.crew_var, state="readonly")
        self.crew_combo.pack(fill=tk.X)

        self.notes_var = tk.StringVar()
        ttk.Label(form, text="Resolution Notes", background=CARD).pack(anchor=tk.W)
        ttk.Entry(form, textvariable=self.notes_var).pack(fill=tk.X, pady=2)

        bf = tk.Frame(form, bg=CARD)
        bf.pack(fill=tk.X, pady=10)
        self._readonly = self.app.user.get("role") == "Viewer"
        if not self._readonly:
            ttk.Button(bf, text="Save Report", command=self._save).pack(side=tk.LEFT, padx=2)
            ttk.Button(bf, text="Assign", command=self._assign).pack(side=tk.LEFT, padx=2)
            ttk.Button(bf, text="Resolve", command=self._resolve).pack(side=tk.LEFT, padx=2)
            ttk.Button(bf, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=2)
        ttk.Button(bf, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=2)

        right = ttk.Frame(paned, padding=8)
        paned.add(right, minsize=480)
        self._build_filters(right)
        self._build_table(right)

    def _build_filters(self, parent) -> None:
        f = tk.Frame(parent, bg=CARD)
        f.pack(fill=tk.X)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ttk.Label(f, text="Search", background=CARD).grid(row=0, column=0, padx=2)
        ttk.Entry(f, textvariable=self.search_var, width=18).grid(row=0, column=1, padx=2)
        self.status_f = tk.StringVar(value="All")
        ttk.Label(f, text="Status", background=CARD).grid(row=0, column=2, padx=2)
        status_cb = ttk.Combobox(
            f, textvariable=self.status_f, values=["All"] + REPORT_STATUSES, width=10, state="readonly"
        )
        status_cb.grid(row=0, column=3, padx=2)
        status_cb.bind("<<ComboboxSelected>>", lambda _: self.refresh())
        self.zone_f = tk.StringVar()
        ttk.Label(f, text="Barangay", background=CARD).grid(row=0, column=4, padx=2)
        barangay_entry = ttk.Entry(f, textvariable=self.zone_f, width=14)
        barangay_entry.grid(row=0, column=5, padx=2)
        barangay_entry.bind("<Return>", lambda _: self.refresh())
        ttk.Button(f, text="All", width=4, command=self._filter_all_barangays).grid(row=0, column=6, padx=2)
        self.date_from = tk.StringVar()
        self.date_to = tk.StringVar()
        ttk.Label(f, text="From", background=CARD).grid(row=1, column=0, pady=4)
        ttk.Entry(f, textvariable=self.date_from, width=12).grid(row=1, column=1)
        ttk.Label(f, text="To", background=CARD).grid(row=1, column=2)
        ttk.Entry(f, textvariable=self.date_to, width=12).grid(row=1, column=3)
        ttk.Button(f, text="Apply", command=self.refresh).grid(row=1, column=4, padx=4)
        ttk.Button(f, text="Print List", command=self._print).grid(row=1, column=5, padx=4)

    def _filter_all_barangays(self) -> None:
        self.zone_f.set("")
        self.refresh()

    def _build_table(self, parent) -> None:
        wrap = tk.Frame(parent, bg=CARD)
        wrap.pack(fill=tk.BOTH, expand=True, pady=8)
        cols = ("id", "resident", "zone", "type", "location", "status", "date")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", height=16)
        for c, t, w in [
            ("id", "ID", 45),
            ("resident", "Resident", 120),
            ("zone", "Barangay", 90),
            ("type", "Type", 110),
            ("location", "Location", 160),
            ("status", "Status", 80),
            ("date", "Date", 90),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Scrollbar(wrap, command=self.tree.yview).pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=self.tree.yview)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _resident_map(self) -> dict[str, int]:
        residents = self.app.db.search_residents()
        return {f"{r['full_name']} ({r['zone']})": r["resident_id"] for r in residents}

    def _crew_map(self) -> dict[str, int]:
        return {c["full_name"]: c["crew_id"] for c in self.app.db.get_crew()}

    def refresh(self) -> None:
        rmap = self._resident_map()
        self.resident_combo["values"] = list(rmap.keys())
        cmap = self._crew_map()
        self.crew_combo["values"] = [""] + list(cmap.keys())

        rows = self.app.db.search_reports(
            self.search_var.get(),
            self.status_f.get(),
            self.zone_f.get(),
            self.date_from.get(),
            self.date_to.get(),
        )
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert(
                "",
                tk.END,
                iid=str(r["report_id"]),
                values=(
                    r["report_id"],
                    r["resident_name"],
                    r["zone"],
                    r["report_type"],
                    r["location_description"][:40],
                    r["status"],
                    (r["date_submitted"] or "")[:10],
                ),
            )

    def _on_select(self, _=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        rid = int(sel[0])
        r = self.app.db.get_report(rid)
        if not r:
            return
        self.selected_id = rid
        self.type_var.set(r["report_type"])
        self.location_var.set(r["location_description"])
        self.desc.delete("1.0", tk.END)
        self.desc.insert(tk.END, r["description"])
        self.notes_var.set(r.get("resolution_notes") or "")
        key = f"{r['resident_name']} ({r['zone']})"
        if key in self._resident_map():
            self.resident_var.set(key)
        self.photo_path = r.get("photo_path")
        self.photo_lbl.config(text="Photo attached" if self.photo_path else "No photo")
        if r.get("crew_name"):
            self.crew_var.set(r["crew_name"])

    def _pick_photo(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.jpg *.jpeg *.png *.gif *.webp *.bmp")]
        )
        if path:
            try:
                self.photo_path = save_photo(path)
                self.photo_lbl.config(text="Photo saved")
            except (ValueError, FileNotFoundError) as e:
                messagebox.showerror("Photo Error", str(e))

    def _get_resident_id(self) -> int | None:
        return self._resident_map().get(self.resident_var.get())

    def _clear_errors(self) -> None:
        for lbl in self._errs.values():
            lbl.config(text="")

    def _save(self) -> None:
        result = validate_report(
            self.type_var.get(),
            self.location_var.get(),
            self.desc.get("1.0", tk.END),
            self._get_resident_id(),
        )
        self._clear_errors()
        if not result.ok:
            for k, v in result.errors.items():
                self._errs.get(k, error_label(self)).config(text=v)
            return
        data = result.data
        data["photo_path"] = self.photo_path
        data["resolution_notes"] = self.notes_var.get()
        try:
            if self.selected_id:
                self.app.db.update_report(self.selected_id, data)
                self.app.set_status(f"Report #{self.selected_id} updated.")
            else:
                self.selected_id = self.app.db.create_report(data)
                self.app.set_status(f"Report #{self.selected_id} created.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        self.refresh()
        self.app.refresh_dashboard()

    def _assign(self) -> None:
        if not self.selected_id:
            messagebox.showwarning("Select", "Select a report first.")
            return
        crew = self._crew_map().get(self.crew_var.get())
        if not crew:
            messagebox.showwarning("Crew", "Select a crew member.")
            return
        self.app.db.assign_report(self.selected_id, crew)
        self.app.set_status(f"Report #{self.selected_id} assigned.")
        self.refresh()
        self.app.refresh_dashboard()

    def _resolve(self) -> None:
        if not self.selected_id:
            messagebox.showwarning("Select", "Select a report first.")
            return
        self.app.db.resolve_report(self.selected_id, self.notes_var.get())
        self.app.set_status(f"Report #{self.selected_id} resolved.")
        self.refresh()
        self.app.refresh_dashboard()

    def _get_selected_report_id(self) -> int | None:
        if self.selected_id:
            return self.selected_id
        sel = self.tree.selection()
        if sel:
            try:
                return int(sel[0])
            except (ValueError, TypeError):
                pass
        return None

    def _delete(self) -> None:
        report_id = self._get_selected_report_id()
        if not report_id:
            messagebox.showwarning("Delete", "Please select a report from the list on the right.")
            return
        if not messagebox.askyesno("Delete", f"Delete report #{report_id}? This cannot be undone."):
            return
        try:
            if self.app.db.delete_report(report_id):
                self.app.set_status(f"Report #{report_id} deleted.")
                self._clear()
                self.refresh()
                self.app.refresh_dashboard()
            else:
                messagebox.showerror("Delete", f"Report #{report_id} was not found.")
        except Exception as e:
            messagebox.showerror("Delete Failed", f"Could not delete report:\n{e}")

    def _clear(self) -> None:
        self.selected_id = None
        self.photo_path = None
        self.resident_var.set("")
        self.type_var.set("")
        self.location_var.set("")
        self.crew_var.set("")
        self.notes_var.set("")
        self.desc.delete("1.0", tk.END)
        self.photo_lbl.config(text="No photo")
        for item in self.tree.selection():
            self.tree.selection_remove(item)
        self._clear_errors()

    def _new_resident(self) -> None:
        self.app.show_frame("residents")

    def _print(self) -> None:
        rows = self.app.db.search_reports(
            self.search_var.get(),
            self.status_f.get(),
            self.zone_f.get(),
            self.date_from.get(),
            self.date_to.get(),
        )
        print_report_list(rows)
        self.app.set_status("Report list opened for printing.")


class PickupsFrame(ttk.Frame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, style="Card.TFrame", padding=12)
        self.app = app
        self.selected_id: int | None = None
        self._build()

    def _build(self) -> None:
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5, bg=BG)
        paned.pack(fill=tk.BOTH, expand=True)
        form = ttk.Frame(paned, padding=10)
        paned.add(form, width=320)
        ttk.Label(form, text="Bulky Pickup Request", style="Section.TLabel").pack(anchor=tk.W)

        self.resident_var = tk.StringVar()
        ttk.Label(form, text="Resident *", background=CARD).pack(anchor=tk.W)
        self.resident_combo = ttk.Combobox(form, textvariable=self.resident_var, state="readonly")
        self.resident_combo.pack(fill=tk.X, pady=2)

        self.waste_var = tk.StringVar()
        ttk.Label(form, text="Waste Type *", background=CARD).pack(anchor=tk.W)
        ttk.Combobox(form, textvariable=self.waste_var, values=PICKUP_WASTE_TYPES, state="readonly").pack(fill=tk.X)

        self.date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Label(form, text="Scheduled Date *", background=CARD).pack(anchor=tk.W)
        ttk.Entry(form, textvariable=self.date_var).pack(fill=tk.X, pady=2)

        ttk.Label(form, text="Notes", background=CARD).pack(anchor=tk.W)
        self.notes = tk.Text(form, height=3, font=("Segoe UI", 9))
        self.notes.pack(fill=tk.X)

        self.crew_var = tk.StringVar()
        ttk.Label(form, text="Assign Crew", background=CARD).pack(anchor=tk.W, pady=(8, 0))
        self.crew_combo = ttk.Combobox(form, textvariable=self.crew_var, state="readonly")
        self.crew_combo.pack(fill=tk.X)

        bf = tk.Frame(form, bg=CARD)
        bf.pack(fill=tk.X, pady=10)
        if self.app.user.get("role") != "Viewer":
            ttk.Button(bf, text="Save", command=self._save).pack(side=tk.LEFT, padx=2)
            ttk.Button(bf, text="Assign", command=self._assign).pack(side=tk.LEFT, padx=2)
            ttk.Button(bf, text="Complete", command=self._complete).pack(side=tk.LEFT, padx=2)
        ttk.Button(bf, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=2)

        right = ttk.Frame(paned, padding=8)
        paned.add(right)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        sf = tk.Frame(right, bg=CARD)
        sf.pack(fill=tk.X)
        ttk.Entry(sf, textvariable=self.search_var, width=24).pack(side=tk.LEFT)
        self.status_f = tk.StringVar(value="All")
        pickup_status_cb = ttk.Combobox(
            sf, textvariable=self.status_f, values=["All"] + PICKUP_STATUSES, width=12, state="readonly"
        )
        pickup_status_cb.pack(side=tk.LEFT, padx=4)
        pickup_status_cb.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        wrap = tk.Frame(right, bg=CARD)
        wrap.pack(fill=tk.BOTH, expand=True, pady=8)
        cols = ("id", "resident", "zone", "type", "scheduled", "status")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings")
        for c, t, w in zip(cols, ["ID", "Resident", "Barangay", "Waste", "Scheduled", "Status"], [40, 120, 90, 120, 90, 80]):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Scrollbar(wrap, command=self.tree.yview).pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=self.tree.yview)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _resident_map(self) -> dict[str, int]:
        return {f"{r['full_name']} ({r['zone']})": r["resident_id"] for r in self.app.db.search_residents()}

    def refresh(self) -> None:
        self.resident_combo["values"] = list(self._resident_map().keys())
        self.crew_combo["values"] = [""] + [c["full_name"] for c in self.app.db.get_crew()]
        for i in self.tree.get_children():
            self.tree.delete(i)
        for p in self.app.db.search_pickups(self.search_var.get(), self.status_f.get()):
            self.tree.insert(
                "",
                tk.END,
                iid=str(p["request_id"]),
                values=(
                    p["request_id"],
                    p["resident_name"],
                    p["zone"],
                    p["waste_type"],
                    p["scheduled_date"],
                    p["status"],
                ),
            )

    def _on_select(self, _=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        rows = [p for p in self.app.db.search_pickups() if str(p["request_id"]) == sel[0]]
        if not rows:
            return
        p = rows[0]
        self.selected_id = p["request_id"]
        self.resident_var.set(f"{p['resident_name']} ({p['zone']})")
        self.waste_var.set(p["waste_type"])
        self.date_var.set(p["scheduled_date"])
        self.notes.delete("1.0", tk.END)
        self.notes.insert(tk.END, p.get("notes") or "")
        if p.get("crew_name"):
            self.crew_var.set(p["crew_name"])

    def _save(self) -> None:
        result = validate_pickup(
            self.waste_var.get(),
            self.date_var.get(),
            self._resident_map().get(self.resident_var.get()),
            self.notes.get("1.0", tk.END),
        )
        if not result.ok:
            messagebox.showwarning("Validation", "\n".join(result.errors.values()))
            return
        if self.selected_id:
            messagebox.showinfo("Info", "Edit pickup: create a new request if details changed.")
            return
        self.selected_id = self.app.db.create_pickup(result.data)
        self.app.set_status(f"Pickup request #{self.selected_id} created.")
        self.refresh()
        self.app.refresh_dashboard()

    def _assign(self) -> None:
        if not self.selected_id:
            return
        cmap = {c["full_name"]: c["crew_id"] for c in self.app.db.get_crew()}
        crew = cmap.get(self.crew_var.get())
        if crew:
            self.app.db.assign_pickup(self.selected_id, crew)
            self.refresh()

    def _complete(self) -> None:
        if self.selected_id:
            self.app.db.complete_pickup(self.selected_id)
            self.refresh()
            self.app.refresh_dashboard()

    def _clear(self) -> None:
        self.selected_id = None
        self.resident_var.set("")
        self.waste_var.set("")
        self.date_var.set(date.today().isoformat())
        self.notes.delete("1.0", tk.END)
        self.crew_var.set("")


class ResidentsFrame(ttk.Frame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, style="Card.TFrame", padding=12)
        self.app = app
        self.selected_id: int | None = None
        self._build()

    def _build(self) -> None:
        left = ttk.Frame(self, padding=8)
        left.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(left, text="Resident", style="Section.TLabel").pack(anchor=tk.W)
        self.name_var = tk.StringVar()
        self.zone_var = tk.StringVar()
        self.contact_var = tk.StringVar()
        for lbl, var in [("Full Name*", self.name_var), ("Contact", self.contact_var)]:
            ttk.Label(left, text=lbl, background=CARD).pack(anchor=tk.W)
            ttk.Entry(left, textvariable=var, width=30).pack(fill=tk.X, pady=2)
        ttk.Label(left, text="Barangay *", background=CARD).pack(anchor=tk.W)
        ttk.Entry(left, textvariable=self.zone_var, width=30).pack(fill=tk.X, pady=2)
        btn_row = tk.Frame(left, bg=CARD)
        btn_row.pack(fill=tk.X, pady=10)
        ttk.Button(btn_row, text="Save", command=self._save).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=2)

        right = ttk.Frame(self, padding=8)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(right, textvariable=self.search_var, width=30).pack(anchor=tk.W)
        wrap = tk.Frame(right, bg=CARD)
        wrap.pack(fill=tk.BOTH, expand=True, pady=8)
        cols = ("id", "name", "zone", "contact", "registered")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings")
        for c, t, w in zip(
            cols, ["ID", "Name", "Barangay", "Contact", "Registered"], [45, 140, 120, 100, 90]
        ):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Scrollbar(wrap, command=self.tree.yview).pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=self.tree.yview)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def refresh(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in self.app.db.search_residents(self.search_var.get()):
            self.tree.insert(
                "",
                tk.END,
                iid=str(r["resident_id"]),
                values=(
                    r["resident_id"],
                    r["full_name"],
                    r["zone"],
                    r["contact_number"],
                    (r["registered_at"] or "")[:10],
                ),
            )

    def _on_select(self, _=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        resident = self.app.db.get_resident(int(sel[0]))
        if not resident:
            return
        self.selected_id = resident["resident_id"]
        self.name_var.set(resident["full_name"])
        self.zone_var.set(resident["zone"])
        self.contact_var.set(resident.get("contact_number") or "")

    def _get_selected_id(self) -> int | None:
        if self.selected_id:
            return self.selected_id
        sel = self.tree.selection()
        if sel:
            try:
                return int(sel[0])
            except (ValueError, TypeError):
                pass
        return None

    def _save(self) -> None:
        from database import DatabaseError

        result = validate_resident(self.name_var.get(), self.zone_var.get(), self.contact_var.get())
        if not result.ok:
            messagebox.showwarning("Validation", "\n".join(result.errors.values()))
            return
        try:
            if self.selected_id:
                self.app.db.update_resident(self.selected_id, result.data)
                self.app.set_status(f"Resident #{self.selected_id} updated.")
            else:
                rid = self.app.db.create_resident(result.data)
                self.selected_id = rid
                self.app.set_status(f"Resident registered (ID {rid}).")
            self.refresh()
        except DatabaseError as e:
            messagebox.showerror("Error", str(e))

    def _delete(self) -> None:
        from database import DatabaseError

        resident_id = self._get_selected_id()
        if not resident_id:
            messagebox.showwarning("Delete", "Select a resident from the list first.")
            return
        if not messagebox.askyesno("Delete", f"Delete resident #{resident_id}? This cannot be undone."):
            return
        try:
            self.app.db.delete_resident(resident_id)
            self.app.set_status(f"Resident #{resident_id} deleted.")
            self._clear()
            self.refresh()
        except DatabaseError as e:
            messagebox.showerror("Cannot Delete", str(e))

    def _clear(self) -> None:
        self.selected_id = None
        self.name_var.set("")
        self.zone_var.set("")
        self.contact_var.set("")
        for item in self.tree.selection():
            self.tree.selection_remove(item)


class CrewFrame(ttk.Frame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, style="Card.TFrame", padding=12)
        self.app = app
        self.selected_id: int | None = None
        self._build()

    def _build(self) -> None:
        form = ttk.Frame(self, padding=8)
        form.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(form, text="Crew Member", style="Section.TLabel").pack(anchor=tk.W)
        self.name_var = tk.StringVar()
        self.contact_var = tk.StringVar()
        self.active_var = tk.BooleanVar(value=True)
        ttk.Label(form, text="Name", background=CARD).pack(anchor=tk.W)
        ttk.Entry(form, textvariable=self.name_var, width=28).pack(fill=tk.X)
        ttk.Label(form, text="Contact", background=CARD).pack(anchor=tk.W)
        ttk.Entry(form, textvariable=self.contact_var, width=28).pack(fill=tk.X)
        ttk.Checkbutton(form, text="Active", variable=self.active_var).pack(anchor=tk.W, pady=4)
        btn_row = tk.Frame(form, bg=CARD)
        btn_row.pack(fill=tk.X, pady=4)
        ttk.Button(btn_row, text="Save", command=self._save).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=2)

        wrap = tk.Frame(self, bg=CARD)
        wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=12)
        self.tree = ttk.Treeview(wrap, columns=("id", "name", "contact", "active"), show="headings")
        for c, t in zip(("id", "name", "contact", "active"), ["ID", "Name", "Contact", "Active"]):
            self.tree.heading(c, text=t)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def refresh(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for c in self.app.db.get_crew(active_only=False):
            self.tree.insert(
                "",
                tk.END,
                iid=str(c["crew_id"]),
                values=(c["crew_id"], c["full_name"], c["contact_number"], "Yes" if c["is_active"] else "No"),
            )

    def _on_select(self, _=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        rows = [c for c in self.app.db.get_crew(active_only=False) if str(c["crew_id"]) == sel[0]]
        if rows:
            c = rows[0]
            self.selected_id = c["crew_id"]
            self.name_var.set(c["full_name"])
            self.contact_var.set(c["contact_number"])
            self.active_var.set(bool(c["is_active"]))

    def _save(self) -> None:
        if not self.name_var.get().strip():
            messagebox.showwarning("Validation", "Name is required.")
            return
        data = {
            "full_name": self.name_var.get().strip(),
            "contact_number": self.contact_var.get().strip(),
            "is_active": self.active_var.get(),
        }
        crew_id = self.app.db.save_crew(data, self.selected_id)
        self.app.set_status(f"Crew member saved (ID {crew_id}).")
        self._clear()
        self.refresh()

    def _get_selected_id(self) -> int | None:
        if self.selected_id:
            return self.selected_id
        sel = self.tree.selection()
        if sel:
            try:
                return int(sel[0])
            except (ValueError, TypeError):
                pass
        return None

    def _delete(self) -> None:
        from database import DatabaseError

        crew_id = self._get_selected_id()
        if not crew_id:
            messagebox.showwarning("Delete", "Select a crew member from the list first.")
            return
        if not messagebox.askyesno(
            "Delete",
            f"Delete crew member #{crew_id}?\nAssigned reports and pickups will be unassigned.",
        ):
            return
        try:
            self.app.db.delete_crew(crew_id)
            self.app.set_status(f"Crew member #{crew_id} deleted.")
            self._clear()
            self.refresh()
            self.app.refresh_dashboard()
        except DatabaseError as e:
            messagebox.showerror("Delete Failed", str(e))

    def _clear(self) -> None:
        self.selected_id = None
        self.name_var.set("")
        self.contact_var.set("")
        self.active_var.set(True)
        for item in self.tree.selection():
            self.tree.selection_remove(item)


class AnnouncementsFrame(ttk.Frame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, style="Card.TFrame", padding=12)
        self.app = app
        self._build()

    def _build(self) -> None:
        form = ttk.Frame(self, padding=8)
        form.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(form, text="New Announcement", style="Section.TLabel").pack(anchor=tk.W)
        self.title_var = tk.StringVar()
        ttk.Label(form, text="Title", background=CARD).pack(anchor=tk.W)
        ttk.Entry(form, textvariable=self.title_var, width=32).pack(fill=tk.X)
        ttk.Label(form, text="Message", background=CARD).pack(anchor=tk.W)
        self.msg = tk.Text(form, height=6, width=32, font=("Segoe UI", 9), wrap=tk.WORD)
        self.msg.pack(fill=tk.X, pady=4)
        role = self.app.user.get("role", "")
        if role in ("Admin", "Staff"):
            ttk.Button(form, text="Post", command=self._post).pack(pady=4)

        right = ttk.Frame(self, padding=8)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.list = tk.Listbox(right, font=("Segoe UI", 10), height=18)
        self.list.pack(fill=tk.BOTH, expand=True, pady=4)
        ttk.Button(right, text="Print Selected Slip", command=self._print_slip).pack(anchor=tk.W)

    def refresh(self) -> None:
        self._announcements = self.app.db.get_announcements()
        self.list.delete(0, tk.END)
        for a in self._announcements:
            self.list.insert(tk.END, f"[{(a['date_posted'] or '')[:10]}] {a['title']}")

    def _post(self) -> None:
        result = validate_announcement(self.title_var.get(), self.msg.get("1.0", tk.END))
        if not result.ok:
            messagebox.showwarning("Validation", "\n".join(result.errors.values()))
            return
        self.app.db.create_announcement(result.data["title"], result.data["message"], self.app.user["user_id"])
        self.title_var.set("")
        self.msg.delete("1.0", tk.END)
        self.refresh()
        self.app.set_status("Announcement posted.")

    def _print_slip(self) -> None:
        idx = self.list.curselection()
        if not idx:
            messagebox.showinfo("Select", "Select an announcement to print.")
            return
        print_announcement_slip(self._announcements[idx[0]])
        self.app.set_status("Announcement slip opened for printing.")


class ScheduleFrame(ttk.Frame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, style="Card.TFrame", padding=12)
        self.app = app
        self.selected_id: int | None = None
        self.can_edit = self.app.user.get("role") in ("Admin", "Staff")
        self._build()

    def _build(self) -> None:
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5, bg=BG)
        paned.pack(fill=tk.BOTH, expand=True)

        form = ttk.Frame(paned, padding=10)
        paned.add(form, minsize=280, width=300)
        title = "Edit Collection Schedule" if self.can_edit else "Collection Schedule"
        ttk.Label(form, text=title, style="Section.TLabel").pack(anchor=tk.W, pady=(0, 8))

        self.zone_var = tk.StringVar()
        ttk.Label(form, text="Barangay *", background=CARD).pack(anchor=tk.W)
        self.barangay_entry = ttk.Entry(
            form, textvariable=self.zone_var, width=32, state="normal" if self.can_edit else "disabled"
        )
        self.barangay_entry.pack(fill=tk.X, pady=2)
        self.day_var = tk.StringVar()
        ttk.Label(form, text="Day *", background=CARD).pack(anchor=tk.W)
        self.day_combo = ttk.Combobox(
            form,
            textvariable=self.day_var,
            values=DAYS_OF_WEEK,
            state="readonly" if self.can_edit else "disabled",
            width=30,
        )
        self.day_combo.pack(fill=tk.X, pady=2)

        self.time_var = tk.StringVar()
        ttk.Label(form, text="Time Slot *", background=CARD).pack(anchor=tk.W)
        time_entry = ttk.Entry(form, textvariable=self.time_var, width=32)
        time_entry.pack(fill=tk.X, pady=2)
        if not self.can_edit:
            time_entry.config(state="disabled")

        ttk.Label(form, text="Notes", background=CARD).pack(anchor=tk.W)
        self.notes = tk.Text(form, height=3, width=32, font=("Segoe UI", 9), wrap=tk.WORD)
        self.notes.pack(fill=tk.X, pady=2)
        if not self.can_edit:
            self.notes.config(state="disabled")

        if self.can_edit:
            btn_row = tk.Frame(form, bg=CARD)
            btn_row.pack(fill=tk.X, pady=10)
            ttk.Button(btn_row, text="Save", command=self._save).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_row, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_row, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=2)
        right = ttk.Frame(paned, padding=8)
        paned.add(right, minsize=420)
        ttk.Label(right, text="All Schedules", style="Section.TLabel", background=CARD).pack(anchor=tk.W)
        wrap = tk.Frame(right, bg=CARD)
        wrap.pack(fill=tk.BOTH, expand=True, pady=8)
        cols = ("id", "zone", "day", "time", "notes")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", height=14)
        for c, t, w in zip(cols, ["ID", "Barangay", "Day", "Time Slot", "Notes"], [40, 120, 90, 130, 160]):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Scrollbar(wrap, command=self.tree.yview).pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=self.tree.yview)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        ttk.Label(
            right,
            text="Residents can check this schedule at the barangay hall or kiosk.",
            background=CARD,
            foreground=TEXT,
            font=("Segoe UI", 9),
        ).pack(anchor=tk.W)

    def refresh(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for s in self.app.db.get_schedule():
            self.tree.insert(
                "",
                tk.END,
                iid=str(s["schedule_id"]),
                values=(
                    s["schedule_id"],
                    s["zone"],
                    s["day_of_week"],
                    s["time_slot"],
                    s.get("notes", ""),
                ),
            )

    def _on_select(self, _=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        entry = self.app.db.get_schedule_entry(int(sel[0]))
        if not entry:
            return
        self.selected_id = entry["schedule_id"]
        self.zone_var.set(entry["zone"])
        self.day_var.set(entry["day_of_week"])
        self.time_var.set(entry["time_slot"])
        self.notes.config(state=tk.NORMAL)
        self.notes.delete("1.0", tk.END)
        self.notes.insert(tk.END, entry.get("notes") or "")
        if not self.can_edit:
            self.notes.config(state="disabled")

    def _get_selected_id(self) -> int | None:
        if self.selected_id:
            return self.selected_id
        sel = self.tree.selection()
        if sel:
            try:
                return int(sel[0])
            except (ValueError, TypeError):
                pass
        return None

    def _save(self) -> None:
        from database import DatabaseError

        if not self.can_edit:
            return
        result = validate_schedule(
            self.zone_var.get(),
            self.day_var.get(),
            self.time_var.get(),
            self.notes.get("1.0", tk.END),
        )
        if not result.ok:
            messagebox.showwarning("Validation", "\n".join(result.errors.values()))
            return
        try:
            sid = self.app.db.save_schedule(result.data, self.selected_id)
            action = "updated" if self.selected_id else "added"
            self.app.set_status(f"Schedule entry #{sid} {action}.")
            self._clear()
            self.refresh()
        except DatabaseError as e:
            messagebox.showerror("Error", str(e))

    def _delete(self) -> None:
        from database import DatabaseError

        if not self.can_edit:
            return
        schedule_id = self._get_selected_id()
        if not schedule_id:
            messagebox.showwarning("Delete", "Select a schedule entry from the list first.")
            return
        if not messagebox.askyesno("Delete", f"Delete schedule entry #{schedule_id}?"):
            return
        try:
            self.app.db.delete_schedule(schedule_id)
            self.app.set_status(f"Schedule entry #{schedule_id} deleted. IDs renumbered.")
            self._clear()
            self.refresh()
        except DatabaseError as e:
            messagebox.showerror("Delete Failed", str(e))

    def _clear(self) -> None:
        self.selected_id = None
        self.zone_var.set("")
        self.day_var.set("")
        self.time_var.set("")
        if self.can_edit:
            self.notes.config(state=tk.NORMAL)
        self.notes.delete("1.0", tk.END)
        if not self.can_edit:
            self.notes.config(state="disabled")
        for item in self.tree.selection():
            self.tree.selection_remove(item)


class KioskFrame(ttk.Frame):
    """Simplified interface for residents at the barangay hall kiosk."""

    def __init__(self, parent, app) -> None:
        super().__init__(parent, style="Card.TFrame", padding=20)
        self.app = app
        self.photo_path: str | None = None
        self._build()

    def _build(self) -> None:
        ttk.Label(self, text="Report a waste problem", font=("Segoe UI", 16, "bold")).pack(anchor=tk.W)
        ttk.Label(
            self,
            text="Staff will review your report at the desk.",
            font=("Segoe UI", 10),
            foreground=MUTED,
        ).pack(anchor=tk.W, pady=(0, 12))

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)

        report_tab = ttk.Frame(nb, padding=12)
        nb.add(report_tab, text="File a Report")
        self._build_report_tab(report_tab)

        pickup_tab = ttk.Frame(nb, padding=12)
        nb.add(pickup_tab, text="Request Bulky Pickup")
        self._build_pickup_tab(pickup_tab)

        info_tab = ttk.Frame(nb, padding=12)
        nb.add(info_tab, text="Schedule & Announcements")
        self._build_info_tab(info_tab)

    def _build_report_tab(self, parent) -> None:
        self.k_name = tk.StringVar()
        self.k_zone = tk.StringVar()
        self.k_contact = tk.StringVar()
        self.k_type = tk.StringVar()
        self.k_location = tk.StringVar()
        for lbl, var in [
            ("Your Full Name *", self.k_name),
            ("Contact Number", self.k_contact),
            ("Barangay *", self.k_zone),
        ]:
            ttk.Label(parent, text=lbl).pack(anchor=tk.W)
            ttk.Entry(parent, textvariable=var, width=42).pack(fill=tk.X, pady=2)
        ttk.Label(parent, text="Report Type *").pack(anchor=tk.W)
        ttk.Combobox(parent, textvariable=self.k_type, values=REPORT_TYPES, state="readonly", width=40).pack(fill=tk.X)
        ttk.Label(parent, text="Location (be specific) *").pack(anchor=tk.W)
        ttk.Entry(parent, textvariable=self.k_location, width=42).pack(fill=tk.X, pady=2)
        ttk.Label(parent, text="Description *").pack(anchor=tk.W)
        self.k_desc = tk.Text(parent, height=4, width=42, wrap=tk.WORD)
        self.k_desc.pack(fill=tk.X, pady=2)
        bf = tk.Frame(parent)
        bf.pack(fill=tk.X, pady=4)
        ttk.Button(bf, text="Attach Photo", command=self._kiosk_photo).pack(side=tk.LEFT)
        self.k_photo_lbl = ttk.Label(bf, text="No photo")
        self.k_photo_lbl.pack(side=tk.LEFT, padx=8)
        ttk.Button(parent, text="Submit Report", command=self._submit_report).pack(pady=10)

    def _build_pickup_tab(self, parent) -> None:
        self.p_name = tk.StringVar()
        self.p_zone = tk.StringVar()
        self.p_contact = tk.StringVar()
        self.p_waste = tk.StringVar()
        self.p_date = tk.StringVar(value=date.today().isoformat())
        for lbl, var in [
            ("Your Full Name *", self.p_name),
            ("Contact", self.p_contact),
            ("Barangay *", self.p_zone),
        ]:
            ttk.Label(parent, text=lbl).pack(anchor=tk.W)
            ttk.Entry(parent, textvariable=var, width=42).pack(fill=tk.X, pady=2)
        ttk.Label(parent, text="Waste Type *").pack(anchor=tk.W)
        ttk.Combobox(parent, textvariable=self.p_waste, values=PICKUP_WASTE_TYPES, state="readonly", width=40).pack(fill=tk.X)
        ttk.Label(parent, text="Preferred Pickup Date *").pack(anchor=tk.W)
        ttk.Entry(parent, textvariable=self.p_date, width=42).pack(fill=tk.X, pady=2)
        ttk.Button(parent, text="Submit Pickup Request", command=self._submit_pickup).pack(pady=10)

    def _build_info_tab(self, parent) -> None:
        ttk.Label(parent, text="Collection Schedule", font=("Segoe UI", 11, "bold")).pack(anchor=tk.W)
        self.sched_list = tk.Listbox(parent, height=8, font=("Segoe UI", 10))
        self.sched_list.pack(fill=tk.X, pady=4)
        ttk.Label(parent, text="Announcements", font=("Segoe UI", 11, "bold")).pack(anchor=tk.W, pady=(8, 0))
        self.ann_list = tk.Listbox(parent, height=8, font=("Segoe UI", 10))
        self.ann_list.pack(fill=tk.X, pady=4)

    def refresh(self) -> None:
        self.sched_list.delete(0, tk.END)
        for s in self.app.db.get_schedule():
            self.sched_list.insert(tk.END, f"{s['zone']}: {s['day_of_week']} — {s['time_slot']}")
        self.ann_list.delete(0, tk.END)
        for a in self.app.db.get_announcements(20):
            self.ann_list.insert(tk.END, f"{a['title']}: {a['message'][:60]}...")

    def _kiosk_photo(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.gif")])
        if path:
            try:
                self.photo_path = save_photo(path)
                self.k_photo_lbl.config(text="Photo attached")
            except Exception as e:
                messagebox.showerror("Photo", str(e))

    def _ensure_resident(self, name: str, zone: str, contact: str) -> int | None:
        vr = validate_resident(name, zone, contact)
        if not vr.ok:
            messagebox.showwarning("Validation", "\n".join(vr.errors.values()))
            return None
        residents = self.app.db.search_residents(name)
        for r in residents:
            if r["full_name"].lower() == name.lower() and r["zone"] == zone:
                return r["resident_id"]
        return self.app.db.create_resident(vr.data)

    def _submit_report(self) -> None:
        rid = self._ensure_resident(self.k_name.get(), self.k_zone.get(), self.k_contact.get())
        if not rid:
            return
        result = validate_report(
            self.k_type.get(), self.k_location.get(), self.k_desc.get("1.0", tk.END), rid
        )
        if not result.ok:
            messagebox.showwarning("Validation", "\n".join(result.errors.values()))
            return
        result.data["photo_path"] = self.photo_path
        report_id = self.app.db.create_report(result.data)
        messagebox.showinfo(
            "Thank you",
            f"Your report was saved.\n\nReference number: {report_id}\n\nPlease tell the staff at the desk.",
        )
        self.k_name.set("")
        self.k_contact.set("")
        self.k_location.set("")
        self.k_desc.delete("1.0", tk.END)
        self.photo_path = None
        self.k_photo_lbl.config(text="No photo")

    def _submit_pickup(self) -> None:
        rid = self._ensure_resident(self.p_name.get(), self.p_zone.get(), self.p_contact.get())
        if not rid:
            return
        result = validate_pickup(self.p_waste.get(), self.p_date.get(), rid, "")
        if not result.ok:
            messagebox.showwarning("Validation", "\n".join(result.errors.values()))
            return
        req_id = self.app.db.create_pickup(result.data)
        messagebox.showinfo(
            "Thank you",
            f"Your pickup request was saved.\n\nReference number: {req_id}",
        )
