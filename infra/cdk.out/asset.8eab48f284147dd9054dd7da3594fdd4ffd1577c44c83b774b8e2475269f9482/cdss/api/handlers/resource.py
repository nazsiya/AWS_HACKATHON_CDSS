"""
Resource agent handler – OTs, equipment, specialists from Aurora.

GET /api/v1/resources: load by type (ot, equipment, staff) and return
{ ots, equipment, specialists, capacity, inventory, conflicts }.
Enrich from MCP get_hospital_data when available; detect OT/slot conflicts (Phase 5).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select

from cdss.api.handlers.common import json_response
from cdss.db.models import Resource, ScheduleSlot, Surgery
from cdss.db.session import get_session

logger = logging.getLogger(__name__)


def _serialize_datetime(d: datetime | None) -> str | None:
    if d is None:
        return None
    return d.isoformat()


def _resource_to_ot(r: Resource) -> dict:
    """Map Resource (type=ot) to frontend OT shape."""
    avail = r.availability or {}
    return {
        "id": r.id,
        "name": r.name,
        "status": r.status,
        "nextFree": avail.get("nextFree"),
        "lastUpdated": _serialize_datetime(r.last_updated),
    }


def _resource_to_equipment(r: Resource) -> dict:
    """Map Resource (type=equipment) to frontend equipment shape."""
    avail = r.availability or {}
    return {
        "id": r.id,
        "name": r.name,
        "status": r.status,
        "location": avail.get("location", "—"),
        "lastUpdated": _serialize_datetime(r.last_updated),
    }


def _resource_to_specialist(r: Resource) -> dict:
    """Map Resource (type=staff) to frontend specialist shape."""
    avail = r.availability or {}
    return {
        "id": r.id,
        "name": r.name,
        "specialty": avail.get("specialty", "—"),
        "status": r.status,
        "lastUpdated": _serialize_datetime(r.last_updated),
    }


def _resource_to_inventory_item(r: Resource, resource_type: str) -> dict:
    """Single row for Resources.jsx inventory table: id, name, specialty, status, assignedTo, area."""
    avail = r.availability or {}
    if resource_type == "ot":
        specialty = "Operation Theater"
        assigned_to = avail.get("assignedTo", "—")
        area = avail.get("area") or r.id or "—"
    elif resource_type == "equipment":
        specialty = "Equipment"
        assigned_to = avail.get("assignedTo", "—")
        area = avail.get("location", "—")
    else:
        specialty = avail.get("specialty", "—")
        assigned_to = avail.get("assignedTo", "—")
        area = avail.get("area", "—")
    return {
        "id": r.id,
        "name": r.name,
        "specialty": specialty,
        "status": r.status,
        "assignedTo": assigned_to,
        "area": area,
    }


def _detect_ot_conflicts(session) -> list:
    """
    Detect OT conflicts: same ot_id, same slot_date, same slot_time (double booking).
    Returns list of { ot_id, date, time, surgery_ids, message }.
    """
    stmt = (
        select(ScheduleSlot)
        .where(ScheduleSlot.ot_id.isnot(None), ScheduleSlot.slot_date.isnot(None))
        .order_by(ScheduleSlot.ot_id, ScheduleSlot.slot_date, ScheduleSlot.slot_time)
    )
    slots = list(session.scalars(stmt).all())
    groups: dict[tuple[str, str, str], list] = defaultdict(list)
    for s in slots:
        k = (s.ot_id or "", str(s.slot_date) if s.slot_date else "", s.slot_time or "")
        if k[0] and k[1]:
            groups[k].append(s)
    conflicts = []
    for (ot_id, date_str, time_str), group in groups.items():
        if len(group) < 2:
            continue
        surgery_ids = [s.surgery_id for s in group if s.surgery_id]
        conflicts.append({
            "ot_id": ot_id,
            "date": date_str,
            "time": time_str,
            "surgery_ids": surgery_ids,
            "message": f"OT {ot_id} double-booked on {date_str} at {time_str}",
        })
    return conflicts


def _list_resources() -> dict:
    """Return ots, equipment, specialists; enrich from MCP in response; detect conflicts; capacity and inventory."""
    with get_session() as session:
        stmt = select(Resource).order_by(Resource.type, Resource.id)
        rows = list(session.scalars(stmt).all())

        ots = []
        equipment = []
        specialists = []
        inventory = []
        for r in rows:
            if r.type == "ot":
                ots.append(_resource_to_ot(r))
                inventory.append(_resource_to_inventory_item(r, "ot"))
            elif r.type == "equipment":
                equipment.append(_resource_to_equipment(r))
                inventory.append(_resource_to_inventory_item(r, "equipment"))
            elif r.type == "staff":
                specialists.append(_resource_to_specialist(r))
                inventory.append(_resource_to_inventory_item(r, "staff"))

        # Enrich response from MCP (no DB write): merge MCP OT/equipment into response
        try:
            from cdss.mcp.adapter import get_hospital_data

            for data_type, key in [("ot_status", "ots"), ("equipment", "equipment")]:
                data = get_hospital_data(data_type)
                if data.get("error"):
                    continue
                items = data.get(key, data.get("ots", data.get("equipment", [])))
                if not isinstance(items, list):
                    continue
                existing_ids = {x["id"] for x in (ots if data_type == "ot_status" else equipment)}
                for item in items:
                    rid = (item.get("id") or item.get("name") or "").strip()
                    if not rid or rid in existing_ids:
                        continue
                    name = (item.get("name") or rid).strip()
                    status = (item.get("status") or "available").strip().lower()
                    if data_type == "ot_status":
                        ots.append({
                            "id": rid,
                            "name": name,
                            "status": status,
                            "nextFree": item.get("nextFree"),
                            "lastUpdated": None,
                        })
                        inventory.append({
                            "id": rid,
                            "name": name,
                            "specialty": "Operation Theater",
                            "status": status,
                            "assignedTo": "—",
                            "area": item.get("area", "—"),
                        })
                    else:
                        equipment.append({
                            "id": rid,
                            "name": name,
                            "status": status,
                            "location": item.get("location", "—"),
                            "lastUpdated": None,
                        })
                        inventory.append({
                            "id": rid,
                            "name": name,
                            "specialty": "Equipment",
                            "status": status,
                            "assignedTo": "—",
                            "area": item.get("location", "—"),
                        })
                    existing_ids.add(rid)
        except Exception as e:
            logger.debug("MCP enrich skip: %s", e)

        capacity = {"staff": len(specialists), "assets": len(ots) + len(equipment)}
        conflicts = _detect_ot_conflicts(session)

        return json_response(
            200,
            {
                "ots": ots,
                "equipment": equipment,
                "specialists": specialists,
                "capacity": capacity,
                "inventory": inventory,
                "conflicts": conflicts,
            },
        )


def handler(event: dict, context: object) -> dict:
    """Handle GET /api/v1/resources."""
    try:
        if (event.get("httpMethod") or "GET").upper() != "GET":
            return json_response(405, {"error": "Method not allowed"})

        proxy = (event.get("pathParameters") or {}).get("proxy") or ""
        parts = [p for p in proxy.split("/") if p]
        if len(parts) < 2 or parts[0].lower() != "v1" or parts[1].lower() != "resources":
            return json_response(404, {"error": "Not found"})

        return _list_resources()
    except Exception as e:
        logger.error(
            "Resource handler error",
            extra={"error": str(e), "handler": "resource"},
            exc_info=True,
        )
        return json_response(500, {"error": "Internal server error"})
