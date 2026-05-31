"""Open printable reports in the browser."""
from __future__ import annotations

import webbrowser
from datetime import datetime
from html import escape
from pathlib import Path

from config import APP_NAME, REPORTS_DIR
from database import Database

_STYLES = """
@media print { .no-print { display: none; } body { margin: 0.5in; } }
body { font-family: 'Segoe UI', Tahoma, sans-serif; color: #1b1b1b; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
h1 { color: #1b4332; } h2 { color: #2d6a4f; margin-top: 1.5rem; }
.meta { color: #666; margin-bottom: 1.5rem; }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; margin-top: 1rem; }
th, td { border: 1px solid #ccc; padding: 0.5rem; text-align: left; }
th { background: #1b4332; color: #fff; }
tr:nth-child(even) { background: #f8f9fa; }
.badge { padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
.pending { background: #fff3cd; } .assigned { background: #cce5ff; }
.resolved, .completed { background: #d4edda; }
button { background: #1b4332; color: white; border: none; padding: 0.55rem 1.1rem; border-radius: 6px; cursor: pointer; }
.summary { display: grid; grid-template-columns: repeat(3,1fr); gap: 1rem; margin: 1rem 0; }
.card { background: #e8f5e9; padding: 1rem; border-radius: 8px; text-align: center; }
.card strong { font-size: 1.4rem; display: block; color: #1b4332; }
.slip { border: 2px solid #1b4332; padding: 1.2rem; max-width: 400px; }
.empty { text-align: center; color: #888; }
"""


def _esc(text: str | None) -> str:
    return escape(text or "")


def _open(html: str, filename: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / filename
    path.write_text(html, encoding="utf-8")
    webbrowser.open(path.as_uri())
    return path


def _page(title: str, body: str) -> str:
    return (
        f"<!DOCTYPE html><html><head><meta charset='UTF-8'>"
        f"<title>{_esc(title)}</title><style>{_STYLES}</style></head>"
        f"<body>{body}</body></html>"
    )


def _print_btn() -> str:
    return '<motion class="no-print"><button onclick="window.print()">Print</button></motion>'.replace("motion", "div")


def _stat_card(value: int, label: str) -> str:
    return f'<motion class="card"><strong>{value}</strong>{label}</motion>'.replace("motion", "div")


def print_daily_task_sheet(db: Database) -> Path:
    reports = db.get_todays_assigned_reports()
    pickups = db.get_todays_assigned_pickups()
    when = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    r_rows = "".join(
        f"<tr><td>#{r['report_id']}</td><td>{_esc(r['report_type'])}</td>"
        f"<td>{_esc(r['resident_name'])}</td><td>{_esc(r['zone'])}</td>"
        f"<td>{_esc(r['location_description'])}</td><td>{_esc(r.get('crew_name') or '—')}</td></tr>"
        for r in reports
    ) or '<tr><td colspan="6" class="empty">No assigned reports for today.</td></tr>'

    p_rows = "".join(
        f"<tr><td>#{p['request_id']}</td><td>{_esc(p['waste_type'])}</td>"
        f"<td>{_esc(p['resident_name'])}</td><td>{_esc(p['zone'])}</td>"
        f"<td>{_esc(p['scheduled_date'])}</td><td>{_esc(p.get('crew_name') or '—')}</td></tr>"
        for p in pickups
    ) or '<tr><td colspan="6" class="empty">No assigned pickups for today.</td></tr>'

    body = f"""
<h1>{APP_NAME} — Crew task sheet</h1>
<p class="meta">Printed {when}</p>
{_print_btn()}
<h2>Waste reports</h2>
<table><tr><th>ID</th><th>Type</th><th>Resident</th><th>Barangay</th><th>Location</th><th>Crew</th></tr>{r_rows}</table>
<h2>Bulky pickups</h2>
<table><tr><th>ID</th><th>Type</th><th>Resident</th><th>Barangay</th><th>Date</th><th>Crew</th></tr>{p_rows}</table>
<p>Supervisor signature _______________ &nbsp; Date _______________</p>"""
    return _open(_page("Task sheet", body), f"tasks_{datetime.now():%Y%m%d_%H%M%S}.html")


def print_captain_summary(db: Database) -> Path:
    s = db.get_dashboard_stats()
    types = db.get_report_type_counts(30)
    barangays = db.get_zone_counts()
    when = datetime.now().strftime("%B %d, %Y")

    type_rows = "".join(
        f"<tr><td>{_esc(t['report_type'])}</td><td>{t['count']}</td></tr>" for t in types
    ) or '<tr><td colspan="2" class="empty">No complaints yet.</td></tr>'

    brgy_rows = "".join(
        f"<tr><td>{_esc(z['zone'])}</td><td>{z['count']}</td></tr>" for z in barangays
    ) or '<tr><td colspan="2" class="empty">No open issues.</td></tr>'

    cards = "".join(
        _stat_card(s[k], label)
        for k, label in [
            ("reports_pending", "Waiting"),
            ("reports_assigned", "Assigned"),
            ("reports_resolved", "Resolved"),
            ("pickups_pending", "Pickups waiting"),
            ("reports_total", "Total reports"),
            ("pickups_total", "Total pickups"),
        ]
    )
    summary = '<motion class="summary">' + cards + '</motion>'
    summary = summary.replace("motion", "div")
    body = f"""
<h1>{APP_NAME} — Barangay summary</h1>
<p class="meta">{when}</p>
{_print_btn()}
{summary}
<h2>Common complaints (last 30 days)</h2>
<table><tr><th>Type</th><th>Count</th></tr>{type_rows}</table>
<h2>Open issues by barangay</h2>
<table><tr><th>Barangay</th><th>Count</th></tr>{brgy_rows}</table>"""
    return _open(_page("Summary", body), f"summary_{datetime.now():%Y%m%d_%H%M%S}.html")


def print_announcement_slip(announcement: dict) -> Path:
    posted = (announcement.get("date_posted") or "")[:10]
    d = "div"
    body = f"""
<{d} class="slip">
  <h2>Barangay notice</h2>
  <p><strong>{_esc(announcement['title'])}</strong></p>
  <p>{_esc(announcement['message'])}</p>
  <p style="font-size:0.85rem;color:#666;">Posted {posted}</p>
</{d}>
{_print_btn()}"""
    return _open(_page("Notice", body), f"notice_{announcement['announcement_id']}.html")


def print_report_list(reports: list[dict], title: str = "Waste reports") -> Path:
    rows = "".join(
        f"<tr><td>#{r['report_id']}</td><td>{_esc(r.get('resident_name'))}</td>"
        f"<td>{_esc(r.get('zone'))}</td><td>{_esc(r['report_type'])}</td>"
        f"<td>{_esc(r['location_description'])}</td>"
        f"<td><span class=\"badge {r.get('status','').lower()}\">{_esc(r.get('status'))}</span></td>"
        f"<td>{_esc((r.get('date_submitted') or '')[:10])}</td></tr>"
        for r in reports
    ) or '<tr><td colspan="7" class="empty">No reports found.</td></tr>'
    body = f"""
<h1>{APP_NAME} — {_esc(title)}</h1>
<p class="meta">{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
{_print_btn()}
<table><tr><th>ID</th><th>Resident</th><th>Barangay</th><th>Type</th><th>Location</th><th>Status</th><th>Date</th></tr>
{rows}</table>"""
    return _open(_page(title, body), f"reports_{datetime.now():%Y%m%d_%H%M%S}.html")
