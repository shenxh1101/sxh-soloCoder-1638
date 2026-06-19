from datetime import date, timedelta
from typing import List, Optional, Tuple

from models import Equipment, RentalRecord
from storage import (
    load_equipment,
    save_equipment,
    load_rentals,
    save_rentals,
    generate_id,
    get_equipment_by_id,
    update_equipment,
)


DAILY_HOURS = 8


def calculate_rental_cost(
    equipment: Equipment,
    rental_date: date,
    expected_return_date: date,
    billing_method: str = "按天",
) -> Tuple[float, float, float]:
    if billing_method == "按天":
        days = (expected_return_date - rental_date).days
        if days <= 0:
            days = 1
        daily_rate = equipment.hourly_rate * DAILY_HOURS
        total_cost = daily_rate * days
        return total_cost, daily_rate, equipment.hourly_rate
    else:
        days = (expected_return_date - rental_date).days
        if days <= 0:
            days = 1
        estimated_hours = days * DAILY_HOURS
        total_cost = equipment.hourly_rate * estimated_hours
        daily_rate = equipment.hourly_rate * DAILY_HOURS
        return total_cost, daily_rate, equipment.hourly_rate


def calculate_overdue(
    rental: RentalRecord,
    actual_return_date: date,
) -> Tuple[int, float]:
    if actual_return_date <= rental.expected_return_date:
        return 0, 0.0
    overdue_days = (actual_return_date - rental.expected_return_date).days
    daily_rate = rental.daily_rate
    fine_amount = daily_rate * rental.fine_rate * overdue_days
    return overdue_days, fine_amount


def rent_equipment(
    equipment_id: str,
    customer_name: str,
    customer_phone: str,
    rental_date: date,
    expected_return_date: date,
    billing_method: str = "按天",
    notes: str = "",
) -> Optional[RentalRecord]:
    equipment = get_equipment_by_id(equipment_id)
    if not equipment:
        raise ValueError(f"设备 {equipment_id} 不存在")
    if equipment.status != "空闲":
        raise ValueError(f"设备 {equipment_id} 当前状态为 {equipment.status}，无法出租")

    if rental_date > expected_return_date:
        raise ValueError("起租日期不能晚于预计归还日期")

    total_cost, daily_rate, hourly_rate = calculate_rental_cost(
        equipment, rental_date, expected_return_date, billing_method
    )

    rental_id = generate_id("R")
    rental = RentalRecord(
        id=rental_id,
        equipment_id=equipment_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        rental_date=rental_date,
        expected_return_date=expected_return_date,
        start_hours=equipment.total_hours,
        billing_method=billing_method,
        daily_rate=daily_rate,
        hourly_rate=hourly_rate,
        total_cost=total_cost,
        status="进行中",
        notes=notes,
    )

    equipment.status = "在租"
    update_equipment(equipment)

    rentals = load_rentals()
    rentals.append(rental)
    save_rentals(rentals)

    return rental


def return_equipment(
    rental_id: str,
    return_date: date,
    end_hours: float,
) -> Optional[RentalRecord]:
    rentals = load_rentals()
    rental = None
    for r in rentals:
        if r.id == rental_id:
            rental = r
            break

    if not rental:
        raise ValueError(f"租赁记录 {rental_id} 不存在")
    if rental.status != "进行中":
        raise ValueError(f"租赁记录 {rental_id} 已归还")

    equipment = get_equipment_by_id(rental.equipment_id)
    if not equipment:
        raise ValueError(f"设备 {rental.equipment_id} 不存在")

    if end_hours < rental.start_hours:
        raise ValueError(f"归还工时不能小于起租工时（起租工时: {rental.start_hours}）")

    used_hours = end_hours - rental.start_hours

    overdue_days, overdue_fine = calculate_overdue(rental, return_date)

    if rental.billing_method == "按小时":
        rental.total_cost = rental.hourly_rate * used_hours

    rental.actual_return_date = return_date
    rental.end_hours = end_hours
    rental.overdue_days = overdue_days
    rental.overdue_fine = overdue_fine
    rental.total_cost += overdue_fine
    rental.status = "已完成"

    equipment.total_hours = end_hours
    equipment.status = "空闲"
    update_equipment(equipment)

    for i, r in enumerate(rentals):
        if r.id == rental_id:
            rentals[i] = rental
            break
    save_rentals(rentals)

    return rental


def get_active_rentals() -> List[RentalRecord]:
    rentals = load_rentals()
    return [r for r in rentals if r.status == "进行中"]


def get_rentals_by_equipment(equipment_id: str) -> List[RentalRecord]:
    rentals = load_rentals()
    return [r for r in rentals if r.equipment_id == equipment_id]


def get_overdue_rentals() -> List[RentalRecord]:
    active = get_active_rentals()
    return [r for r in active if r.is_overdue]


def get_rental_by_id(rental_id: str) -> Optional[RentalRecord]:
    rentals = load_rentals()
    for r in rentals:
        if r.id == rental_id:
            return r
    return None


def add_equipment(
    eq_type: str,
    model: str,
    hourly_rate: float,
    total_hours: float = 0.0,
    maintenance_interval_hours: int = 0,
) -> Equipment:
    from models import EQUIPMENT_TYPES
    if eq_type not in EQUIPMENT_TYPES:
        raise ValueError(f"设备类型必须是: {', '.join(EQUIPMENT_TYPES)}")

    equipment_list = load_equipment()
    type_count = sum(1 for eq in equipment_list if eq.type == eq_type)
    eq_id = f"{eq_type[0]}{type_count + 1:03d}"

    equipment = Equipment(
        id=eq_id,
        type=eq_type,
        model=model,
        hourly_rate=hourly_rate,
        total_hours=total_hours,
        last_maintenance_hours=total_hours,
        status="空闲",
        maintenance_interval_hours=maintenance_interval_hours,
    )

    equipment_list.append(equipment)
    save_equipment(equipment_list)
    return equipment


def delete_equipment(equipment_id: str) -> bool:
    active_rentals = get_active_rentals()
    for r in active_rentals:
        if r.equipment_id == equipment_id:
            raise ValueError("设备正在出租中，无法删除")

    equipment_list = load_equipment()
    new_list = [eq for eq in equipment_list if eq.id != equipment_id]
    if len(new_list) == len(equipment_list):
        return False
    save_equipment(new_list)
    return True


def list_all_equipment(status: Optional[str] = None) -> List[Equipment]:
    equipment_list = load_equipment()
    if status:
        return [eq for eq in equipment_list if eq.status == status]
    return equipment_list
