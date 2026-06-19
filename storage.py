import json
import os
from datetime import date, datetime
from typing import List, Optional
from models import Equipment, RentalRecord, MaintenanceRecord


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EQUIPMENT_FILE = os.path.join(DATA_DIR, "equipment.json")
RENTALS_FILE = os.path.join(DATA_DIR, "rentals.json")
MAINTENANCE_FILE = os.path.join(DATA_DIR, "maintenance.json")


def _date_to_str(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def _str_to_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def _load_json(filepath: str) -> list:
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(filepath: str, data: list):
    _ensure_data_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_equipment() -> List[Equipment]:
    data = _load_json(EQUIPMENT_FILE)
    return [
        Equipment(
            id=item["id"],
            type=item["type"],
            model=item["model"],
            hourly_rate=item["hourly_rate"],
            total_hours=item.get("total_hours", 0.0),
            last_maintenance_hours=item.get("last_maintenance_hours", 0.0),
            status=item.get("status", "空闲"),
            maintenance_interval_hours=item.get("maintenance_interval_hours", 0),
        )
        for item in data
    ]


def save_equipment(equipment_list: List[Equipment]):
    data = [
        {
            "id": eq.id,
            "type": eq.type,
            "model": eq.model,
            "hourly_rate": eq.hourly_rate,
            "total_hours": eq.total_hours,
            "last_maintenance_hours": eq.last_maintenance_hours,
            "status": eq.status,
            "maintenance_interval_hours": eq.maintenance_interval_hours,
        }
        for eq in equipment_list
    ]
    _save_json(EQUIPMENT_FILE, data)


def load_rentals() -> List[RentalRecord]:
    data = _load_json(RENTALS_FILE)
    records = []
    for item in data:
        record = RentalRecord(
            id=item["id"],
            equipment_id=item["equipment_id"],
            customer_name=item["customer_name"],
            customer_phone=item["customer_phone"],
            rental_date=_str_to_date(item["rental_date"]),
            expected_return_date=_str_to_date(item["expected_return_date"]),
            start_hours=item.get("start_hours", 0.0),
            billing_method=item.get("billing_method", "按天"),
            daily_rate=item.get("daily_rate", 0.0),
            hourly_rate=item.get("hourly_rate", 0.0),
            total_cost=item.get("total_cost", 0.0),
            overdue_days=item.get("overdue_days", 0),
            overdue_fine=item.get("overdue_fine", 0.0),
            fine_rate=item.get("fine_rate", 0.5),
            status=item.get("status", "进行中"),
            notes=item.get("notes", ""),
        )
        if item.get("actual_return_date"):
            record.actual_return_date = _str_to_date(item["actual_return_date"])
        if item.get("end_hours") is not None:
            record.end_hours = item["end_hours"]
        records.append(record)
    return records


def save_rentals(rentals: List[RentalRecord]):
    data = []
    for r in rentals:
        item = {
            "id": r.id,
            "equipment_id": r.equipment_id,
            "customer_name": r.customer_name,
            "customer_phone": r.customer_phone,
            "rental_date": _date_to_str(r.rental_date),
            "expected_return_date": _date_to_str(r.expected_return_date),
            "actual_return_date": _date_to_str(r.actual_return_date) if r.actual_return_date else None,
            "start_hours": r.start_hours,
            "end_hours": r.end_hours,
            "billing_method": r.billing_method,
            "daily_rate": r.daily_rate,
            "hourly_rate": r.hourly_rate,
            "total_cost": r.total_cost,
            "overdue_days": r.overdue_days,
            "overdue_fine": r.overdue_fine,
            "fine_rate": r.fine_rate,
            "status": r.status,
            "notes": r.notes,
        }
        data.append(item)
    _save_json(RENTALS_FILE, data)


def load_maintenance() -> List[MaintenanceRecord]:
    data = _load_json(MAINTENANCE_FILE)
    return [
        MaintenanceRecord(
            id=item["id"],
            equipment_id=item["equipment_id"],
            maintenance_date=_str_to_date(item["maintenance_date"]),
            maintenance_type=item["maintenance_type"],
            maintenance_hours=item["maintenance_hours"],
            description=item.get("description", ""),
            cost=item.get("cost", 0.0),
            operator=item.get("operator", ""),
        )
        for item in data
    ]


def save_maintenance(records: List[MaintenanceRecord]):
    data = [
        {
            "id": r.id,
            "equipment_id": r.equipment_id,
            "maintenance_date": _date_to_str(r.maintenance_date),
            "maintenance_type": r.maintenance_type,
            "maintenance_hours": r.maintenance_hours,
            "description": r.description,
            "cost": r.cost,
            "operator": r.operator,
        }
        for r in records
    ]
    _save_json(MAINTENANCE_FILE, data)


def generate_id(prefix: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{timestamp}"


def get_equipment_by_id(equipment_id: str) -> Optional[Equipment]:
    equipment_list = load_equipment()
    for eq in equipment_list:
        if eq.id == equipment_id:
            return eq
    return None


def update_equipment(equipment: Equipment):
    equipment_list = load_equipment()
    for i, eq in enumerate(equipment_list):
        if eq.id == equipment.id:
            equipment_list[i] = equipment
            break
    save_equipment(equipment_list)
