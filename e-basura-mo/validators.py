"""Check form input before saving."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ValidationResult:
    ok: bool
    errors: dict[str, str]
    data: dict


def validate_resident(full_name: str, zone: str, contact: str) -> ValidationResult:
    errors: dict[str, str] = {}
    full_name = full_name.strip()
    zone = zone.strip()
    contact = contact.strip()

    if not full_name:
        errors["full_name"] = "Please enter the resident's full name."
    elif len(full_name) > 100:
        errors["full_name"] = "Name is too long (max 100 characters)."

    if not zone:
        errors["zone"] = "Please enter the barangay name."
    elif len(zone) > 120:
        errors["zone"] = "Barangay name is too long (max 120 characters)."

    if contact and not re.match(r"^[\d\s\-+()]{7,20}$", contact):
        errors["contact_number"] = "Please enter a valid phone number."

    return ValidationResult(
        ok=not errors,
        errors=errors,
        data={"full_name": full_name, "zone": zone, "contact_number": contact},
    )


def validate_report(
    report_type: str, location: str, description: str, resident_id: int | None,
) -> ValidationResult:
    errors: dict[str, str] = {}
    location = location.strip()
    description = description.strip()

    if not resident_id:
        errors["resident"] = "Please choose or register a resident first."
    if not report_type:
        errors["report_type"] = "Please choose a report type."
    if not location:
        errors["location_description"] = "Please describe where the problem is."
    elif len(location) > 200:
        errors["location_description"] = "Location is too long (max 200 characters)."
    if not description:
        errors["description"] = "Please describe the problem."
    elif len(description) > 1000:
        errors["description"] = "Description is too long (max 1000 characters)."

    return ValidationResult(
        ok=not errors,
        errors=errors,
        data={
            "resident_id": resident_id,
            "report_type": report_type,
            "location_description": location,
            "description": description,
        },
    )


def validate_pickup(
    waste_type: str, scheduled_date: str, resident_id: int | None, notes: str,
) -> ValidationResult:
    errors: dict[str, str] = {}
    notes = notes.strip()

    if not resident_id:
        errors["resident"] = "Please choose or register a resident first."
    if not waste_type:
        errors["waste_type"] = "Please choose a waste type."
    if not scheduled_date.strip():
        errors["scheduled_date"] = "Please enter a pickup date."
    else:
        try:
            datetime.strptime(scheduled_date.strip(), "%Y-%m-%d")
        except ValueError:
            errors["scheduled_date"] = "Use date format: YYYY-MM-DD (example: 2026-05-16)."

    if len(notes) > 500:
        errors["notes"] = "Notes are too long (max 500 characters)."

    return ValidationResult(
        ok=not errors,
        errors=errors,
        data={
            "resident_id": resident_id,
            "waste_type": waste_type,
            "scheduled_date": scheduled_date.strip(),
            "notes": notes,
        },
    )


def validate_schedule(zone: str, day: str, time_slot: str, notes: str) -> ValidationResult:
    errors: dict[str, str] = {}
    zone, day, time_slot, notes = zone.strip(), day.strip(), time_slot.strip(), notes.strip()

    if not zone:
        errors["zone"] = "Please enter the barangay name."
    elif len(zone) > 120:
        errors["zone"] = "Barangay name is too long."
    if not day:
        errors["day_of_week"] = "Please choose a day."
    if not time_slot:
        errors["time_slot"] = "Please enter the collection time."
    elif len(time_slot) > 80:
        errors["time_slot"] = "Time slot is too long."
    if len(notes) > 200:
        errors["notes"] = "Notes are too long."

    return ValidationResult(
        ok=not errors,
        errors=errors,
        data={"zone": zone, "day_of_week": day, "time_slot": time_slot, "notes": notes},
    )


def validate_announcement(title: str, message: str) -> ValidationResult:
    title, message = title.strip(), message.strip()
    errors: dict[str, str] = {}
    if not title:
        errors["title"] = "Please enter a title."
    if not message:
        errors["message"] = "Please enter the announcement message."
    return ValidationResult(ok=not errors, errors=errors, data={"title": title, "message": message})
