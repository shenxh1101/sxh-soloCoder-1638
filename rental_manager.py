from datetime import date, timedelta
from typing import List, Optional, Tuple
from collections import defaultdict

from models import Equipment, RentalRecord
from storage import (
    load_equipment,
    save_equipment,
    load_rentals,
    save_rentals,
    generate_id,
    get_equipment_by_id,
    update_equipment,
    get_next_equipment_number,
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
    check_conflict: bool = True,
) -> Optional[RentalRecord]:
    equipment = get_equipment_by_id(equipment_id)
    if not equipment:
        raise ValueError(f"设备 {equipment_id} 不存在")

    if rental_date > expected_return_date:
        raise ValueError("起租日期不能晚于预计归还日期")

    if check_conflict:
        conflicts = check_rental_conflict(equipment_id, rental_date, expected_return_date)
        if conflicts:
            conflict_details = []
            for c in conflicts:
                c_end = c.actual_return_date or c.expected_return_date
                conflict_details.append(
                    f"{c.id} ({c.customer_name}): {c.rental_date} ~ {c_end}"
                )
            raise ValueError(
                f"排期冲突！该设备在所选时间段内已有租赁：\n" + "\n".join(conflict_details)
            )

    if rental_date <= date.today() <= expected_return_date:
        if equipment.status != "空闲":
            raise ValueError(f"设备 {equipment_id} 当前状态为 {equipment.status}，无法出租")
        equipment.status = "在租"

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

    update_equipment(equipment)

    rentals = load_rentals()
    rentals.append(rental)
    save_rentals(rentals)

    return rental


def calculate_return_settlement(
    rental_id: str,
    return_date: date,
    end_hours: float,
) -> dict:
    rental = get_rental_by_id(rental_id)
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
    actual_days = (return_date - rental.rental_date).days + 1
    expected_days = (rental.expected_return_date - rental.rental_date).days + 1

    overdue_days, overdue_fine = calculate_overdue(rental, return_date)

    original_rental_cost = rental.total_cost - rental.overdue_fine

    if rental.billing_method == "按小时":
        actual_rental_cost = rental.hourly_rate * used_hours
        billing_detail = "按小时计费"
        base_usage = f"{used_hours:.1f} 小时"
    else:
        actual_rental_cost = original_rental_cost
        billing_detail = "按天计费"
        base_usage = f"{expected_days} 天"

    total_receivable = actual_rental_cost + overdue_fine

    return {
        "rental": rental,
        "equipment": equipment,
        "billing_method": rental.billing_method,
        "billing_detail": billing_detail,
        "start_hours": rental.start_hours,
        "end_hours": end_hours,
        "used_hours": used_hours,
        "rental_date": rental.rental_date,
        "expected_return_date": rental.expected_return_date,
        "actual_return_date": return_date,
        "expected_days": expected_days,
        "actual_days": actual_days,
        "overdue_days": overdue_days,
        "original_rental_cost": original_rental_cost,
        "actual_rental_cost": actual_rental_cost,
        "overdue_fine": overdue_fine,
        "total_receivable": total_receivable,
        "daily_rate": rental.daily_rate,
        "hourly_rate": rental.hourly_rate,
        "base_usage": base_usage,
    }


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
    next_num = get_next_equipment_number(eq_type)
    eq_id = f"{eq_type[0]}{next_num:03d}"

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


def get_equipment_schedule(equipment_id: str, start_date: date = None, end_date: date = None) -> List[RentalRecord]:
    from datetime import timedelta
    if start_date is None:
        start_date = date.today()
    if end_date is None:
        end_date = start_date + timedelta(days=30)

    rentals = get_rentals_by_equipment(equipment_id)
    schedule = []

    for r in rentals:
        r_start = r.rental_date
        r_end = r.actual_return_date or r.expected_return_date

        if r_end >= start_date and r_start <= end_date:
            schedule.append(r)

    schedule.sort(key=lambda x: x.rental_date)
    return schedule


def check_rental_conflict(
    equipment_id: str,
    rental_date: date,
    expected_return_date: date,
    exclude_rental_id: str = None,
) -> List[RentalRecord]:
    rentals = get_rentals_by_equipment(equipment_id)
    conflicts = []

    for r in rentals:
        if exclude_rental_id and r.id == exclude_rental_id:
            continue

        if r.status == "已完成" and r.actual_return_date:
            r_end = r.actual_return_date
        else:
            r_end = r.expected_return_date

        if rental_date <= r_end and expected_return_date >= r.rental_date:
            conflicts.append(r)

    return conflicts


def get_equipment_status_on_date(equipment_id: str, target_date: date) -> str:
    rentals = get_rentals_by_equipment(equipment_id)

    for r in rentals:
        r_start = r.rental_date
        if r.status == "已完成" and r.actual_return_date:
            r_end = r.actual_return_date
        else:
            r_end = r.expected_return_date

        if r_start <= target_date <= r_end:
            if r.status == "已完成":
                return "已归还"
            else:
                return "在租"

    return "空闲"


def get_rentals_on_date(target_date: date) -> dict:
    rentals = load_rentals()

    rented_equipment = []
    new_rentals = []
    returns = []
    overdue = []

    for r in rentals:
        r_start = r.rental_date

        if r.status == "已完成" and r.actual_return_date:
            r_end = r.actual_return_date
            is_active_on_date = r_start <= target_date <= r_end
            is_return_on_date = r_end == target_date
        else:
            r_end = r.expected_return_date
            is_active_on_date = r_start <= target_date
            is_return_on_date = False

        if is_active_on_date and r.status == "进行中":
            rented_equipment.append(r)

            if target_date > r.expected_return_date:
                overdue.append(r)

        if r.rental_date == target_date:
            new_rentals.append(r)

        if is_return_on_date and r.status == "已完成":
            returns.append(r)

    return {
        "target_date": target_date,
        "rented_equipment": rented_equipment,
        "new_rentals": new_rentals,
        "returns": returns,
        "overdue": overdue,
    }


def search_customer(keyword: str) -> List[dict]:
    rentals = load_rentals()
    keyword = keyword.strip().lower()

    if not keyword:
        return []

    customer_rentals = defaultdict(list)

    for r in rentals:
        name_match = keyword in r.customer_name.lower()
        phone_match = keyword in r.customer_phone.lower()
        if name_match or phone_match:
            key = r.customer_name + "|" + r.customer_phone
            customer_rentals[key].append(r)

    result = []
    for key, rent_list in customer_rentals.items():
        name, phone = key.split("|", 1)
        completed = [r for r in rent_list if r.status == "已完成"]
        active = [r for r in rent_list if r.status == "进行中"]
        overdue = [r for r in active if r.is_overdue]
        total_spent = sum(r.total_cost for r in completed)
        overdue_count = sum(1 for r in rent_list if r.status == "已完成" and r.overdue_fine > 0)
        overdue_count += len(overdue)

        result.append({
            "name": name,
            "phone": phone,
            "total_rentals": len(rent_list),
            "completed_count": len(completed),
            "active_count": len(active),
            "overdue_count": overdue_count,
            "total_spent": total_spent,
            "rentals": sorted(rent_list, key=lambda x: x.rental_date, reverse=True),
            "active_rentals": active,
        })

    result.sort(key=lambda x: x["total_spent"], reverse=True)
    return result


def get_customer_profile(customer_name: str, customer_phone: str) -> Optional[dict]:
    rentals = load_rentals()

    customer_rentals = [
        r for r in rentals
        if r.customer_name == customer_name and r.customer_phone == customer_phone
    ]

    if not customer_rentals:
        return None

    completed = [r for r in customer_rentals if r.status == "已完成"]
    active = [r for r in customer_rentals if r.status == "进行中"]
    overdue = [r for r in active if r.is_overdue]
    total_spent = sum(r.total_cost for r in completed)
    overdue_count = sum(1 for r in completed if r.overdue_fine > 0)
    overdue_count += len(overdue)
    total_hours = sum(
        (r.end_hours - r.start_hours)
        for r in completed
        if r.end_hours is not None and r.start_hours is not None
    )

    first_rental = min(customer_rentals, key=lambda x: x.rental_date)
    last_rental = max(customer_rentals, key=lambda x: x.rental_date)

    return {
        "name": customer_name,
        "phone": customer_phone,
        "total_rentals": len(customer_rentals),
        "completed_count": len(completed),
        "active_count": len(active),
        "overdue_count": overdue_count,
        "total_spent": round(total_spent, 2),
        "total_hours": round(total_hours, 1),
        "first_rental_date": first_rental.rental_date,
        "last_rental_date": last_rental.rental_date if last_rental.status == "已完成" else None,
        "rentals": sorted(customer_rentals, key=lambda x: x.rental_date, reverse=True),
        "active_rentals": active,
        "overdue_rentals": overdue,
    }


def get_equipment_schedule_multi(
    start_date: date,
    end_date: date,
    eq_type: str = None,
) -> List[dict]:
    equipment_list = load_equipment()

    if eq_type:
        equipment_list = [eq for eq in equipment_list if eq.type == eq_type]

    result = []
    for eq in equipment_list:
        schedule = get_equipment_schedule(eq.id, start_date, end_date)

        total_days = (end_date - start_date).days + 1
        rented_days = 0

        for r in schedule:
            r_start = max(r.rental_date, start_date)
            r_end = r.actual_return_date or r.expected_return_date
            r_end = min(r_end, end_date)
            days = (r_end - r_start).days + 1
            if days > 0:
                rented_days += days

        idle_days = total_days - rented_days
        utilization = (rented_days / total_days * 100) if total_days > 0 else 0

        result.append({
            "equipment": eq,
            "schedule": schedule,
            "total_days": total_days,
            "rented_days": rented_days,
            "idle_days": idle_days,
            "utilization": round(utilization, 2),
            "is_idle": len(schedule) == 0,
        })

    result.sort(key=lambda x: x["equipment"].type)
    return result
