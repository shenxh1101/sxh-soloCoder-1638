from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional


EQUIPMENT_TYPES = ["挖掘机", "装载机", "起重机", "压路机", "推土机"]

DEFAULT_MAINTENANCE_HOURS = {
    "挖掘机": 500,
    "装载机": 400,
    "起重机": 600,
    "压路机": 350,
    "推土机": 450,
}


@dataclass
class Equipment:
    id: str
    type: str
    model: str
    hourly_rate: float
    total_hours: float = 0.0
    last_maintenance_hours: float = 0.0
    status: str = "空闲"
    maintenance_interval_hours: int = 0

    def __post_init__(self):
        if self.maintenance_interval_hours == 0:
            self.maintenance_interval_hours = DEFAULT_MAINTENANCE_HOURS.get(self.type, 500)

    @property
    def next_maintenance_hours(self) -> float:
        return self.last_maintenance_hours + self.maintenance_interval_hours

    @property
    def hours_until_maintenance(self) -> float:
        return self.next_maintenance_hours - self.total_hours

    @property
    def needs_maintenance(self) -> bool:
        return self.hours_until_maintenance <= 0

    @property
    def maintenance_soon(self) -> bool:
        return self.hours_until_maintenance <= self.maintenance_interval_hours * 0.1


@dataclass
class RentalRecord:
    id: str
    equipment_id: str
    customer_name: str
    customer_phone: str
    rental_date: date
    expected_return_date: date
    actual_return_date: Optional[date] = None
    start_hours: float = 0.0
    end_hours: Optional[float] = None
    billing_method: str = "按天"
    daily_rate: float = 0.0
    hourly_rate: float = 0.0
    total_cost: float = 0.0
    overdue_days: int = 0
    overdue_fine: float = 0.0
    fine_rate: float = 0.5
    status: str = "进行中"
    notes: str = ""

    @property
    def is_overdue(self) -> bool:
        if self.status == "进行中":
            return date.today() > self.expected_return_date
        if self.actual_return_date:
            return self.actual_return_date > self.expected_return_date
        return False


@dataclass
class MaintenanceRecord:
    id: str
    equipment_id: str
    maintenance_date: date
    maintenance_type: str
    maintenance_hours: float
    description: str = ""
    cost: float = 0.0
    operator: str = ""
