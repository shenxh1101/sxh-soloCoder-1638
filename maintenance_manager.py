from datetime import date
from typing import List, Optional

from models import Equipment, MaintenanceRecord
from storage import (
    load_equipment,
    load_maintenance,
    save_maintenance,
    generate_id,
    get_equipment_by_id,
    update_equipment,
)


def get_maintenance_by_equipment(equipment_id: str) -> List[MaintenanceRecord]:
    records = load_maintenance()
    return [r for r in records if r.equipment_id == equipment_id]


def add_maintenance_record(
    equipment_id: str,
    maintenance_date: date,
    maintenance_type: str,
    maintenance_hours: float,
    description: str = "",
    cost: float = 0.0,
    operator: str = "",
) -> MaintenanceRecord:
    equipment = get_equipment_by_id(equipment_id)
    if not equipment:
        raise ValueError(f"设备 {equipment_id} 不存在")

    if maintenance_hours < equipment.last_maintenance_hours:
        raise ValueError(
            f"保养工时不能小于上次保养工时 "
            f"（上次保养: {equipment.last_maintenance_hours}小时）"
        )
    if maintenance_hours > equipment.total_hours + 100:
        raise ValueError(
            f"保养工时不能远大于设备累计工时 "
            f"（累计工时: {equipment.total_hours}小时）"
        )

    record = MaintenanceRecord(
        id=generate_id("M"),
        equipment_id=equipment_id,
        maintenance_date=maintenance_date,
        maintenance_type=maintenance_type,
        maintenance_hours=maintenance_hours,
        description=description,
        cost=cost,
        operator=operator,
    )

    records = load_maintenance()
    records.append(record)
    save_maintenance(records)

    equipment.last_maintenance_hours = maintenance_hours
    update_equipment(equipment)

    return record


def get_maintenance_checklist() -> List[dict]:
    equipment_list = load_equipment()
    checklist = []

    for eq in equipment_list:
        status = "正常"
        urgency = 0
        if eq.needs_maintenance:
            status = "必须保养"
            urgency = 2
        elif eq.maintenance_soon:
            status = "即将到期"
            urgency = 1

        urgency_desc = ""
        if eq.needs_maintenance:
            urgency_desc = f"已超期 {abs(eq.hours_until_maintenance):.1f} 小时"
        elif eq.maintenance_soon:
            urgency_desc = f"还剩 {eq.hours_until_maintenance:.1f} 小时"

        checklist.append({
            "equipment": eq,
            "status": status,
            "urgency": urgency,
            "urgency_desc": urgency_desc,
            "next_maintenance_hours": eq.next_maintenance_hours,
            "hours_until_maintenance": eq.hours_until_maintenance,
            "maintenance_interval_hours": eq.maintenance_interval_hours,
        })

    checklist.sort(key=lambda x: (x["urgency"], x["hours_until_maintenance"]), reverse=True)
    return checklist


def get_equipment_that_need_maintenance() -> List[Equipment]:
    equipment_list = load_equipment()
    return [eq for eq in equipment_list if eq.needs_maintenance or eq.maintenance_soon]


def get_maintenance_stats() -> dict:
    equipment_list = load_equipment()
    total = len(equipment_list)
    need_maintenance = sum(1 for eq in equipment_list if eq.needs_maintenance)
    soon_maintenance = sum(1 for eq in equipment_list if eq.maintenance_soon and not eq.needs_maintenance)
    normal = total - need_maintenance - soon_maintenance

    return {
        "total": total,
        "need_maintenance": need_maintenance,
        "soon_maintenance": soon_maintenance,
        "normal": normal,
    }


def get_maintenance_record_by_id(record_id: str) -> Optional[MaintenanceRecord]:
    records = load_maintenance()
    for r in records:
        if r.id == record_id:
            return r
    return None


def set_maintenance_interval(equipment_id: str, interval_hours: int) -> Equipment:
    equipment = get_equipment_by_id(equipment_id)
    if not equipment:
        raise ValueError(f"设备 {equipment_id} 不存在")
    if interval_hours <= 0:
        raise ValueError("保养周期必须大于0小时")

    equipment.maintenance_interval_hours = interval_hours
    update_equipment(equipment)
    return equipment
