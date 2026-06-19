from datetime import date, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict

from models import Equipment, RentalRecord, EQUIPMENT_TYPES
from storage import load_equipment, load_rentals, load_maintenance
from rental_manager import get_active_rentals


def get_equipment_status_by_type() -> Dict[str, Dict[str, int]]:
    equipment_list = load_equipment()
    result = {}

    for eq_type in EQUIPMENT_TYPES:
        type_equipment = [eq for eq in equipment_list if eq.type == eq_type]
        total = len(type_equipment)
        rented = sum(1 for eq in type_equipment if eq.status == "在租")
        idle = total - rented
        result[eq_type] = {
            "total": total,
            "rented": rented,
            "idle": idle,
        }

    return result


def get_daily_status_report(report_date: date = None) -> dict:
    if report_date is None:
        report_date = date.today()

    equipment_list = load_equipment()
    rentals = load_rentals()

    active_rentals = [
        r for r in rentals
        if r.status == "进行中"
        or (r.actual_return_date and r.actual_return_date >= report_date and r.rental_date <= report_date)
    ]

    total_equipment = len(equipment_list)
    rented_count = sum(1 for eq in equipment_list if eq.status == "在租")
    idle_count = total_equipment - rented_count

    new_rentals_today = [
        r for r in rentals
        if r.rental_date == report_date
    ]
    returns_today = [
        r for r in rentals
        if r.actual_return_date == report_date
    ]

    overdue_rentals = [
        r for r in rentals
        if r.status == "进行中" and r.is_overdue
    ]

    total_revenue_today = sum(
        r.total_cost for r in returns_today
    )

    return {
        "report_date": report_date,
        "total_equipment": total_equipment,
        "rented_count": rented_count,
        "idle_count": idle_count,
        "new_rentals_count": len(new_rentals_today),
        "returns_count": len(returns_today),
        "overdue_count": len(overdue_rentals),
        "total_revenue_today": total_revenue_today,
        "new_rentals": new_rentals_today,
        "returns": returns_today,
        "overdue_rentals": overdue_rentals,
    }


def get_monthly_revenue_report(year: int, month: int) -> dict:
    rentals = load_rentals()

    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(year, month + 1, 1) - timedelta(days=1)

    completed_rentals = [
        r for r in rentals
        if r.status == "已完成"
        and r.actual_return_date
        and month_start <= r.actual_return_date <= month_end
    ]

    active_rentals = [
        r for r in rentals
        if r.status == "进行中"
        and r.rental_date <= month_end
    ]

    total_revenue = sum(r.total_cost for r in completed_rentals)
    total_fines = sum(r.overdue_fine for r in completed_rentals)
    base_revenue = total_revenue - total_fines

    equipment_revenue = defaultdict(float)
    for r in completed_rentals:
        equipment_revenue[r.equipment_id] += r.total_cost

    customer_revenue = defaultdict(lambda: {
        "name": "",
        "phone": "",
        "total_amount": 0.0,
        "rental_count": 0,
        "fines": 0.0,
    })

    for r in completed_rentals:
        key = r.customer_name + "_" + r.customer_phone
        customer_revenue[key]["name"] = r.customer_name
        customer_revenue[key]["phone"] = r.customer_phone
        customer_revenue[key]["total_amount"] += r.total_cost
        customer_revenue[key]["rental_count"] += 1
        customer_revenue[key]["fines"] += r.overdue_fine

    customer_list = sorted(
        customer_revenue.values(),
        key=lambda x: x["total_amount"],
        reverse=True
    )

    equipment_list = load_equipment()
    equipment_details = []
    for eq_id, revenue in equipment_revenue.items():
        eq = next((e for e in equipment_list if e.id == eq_id), None)
        if eq:
            equipment_details.append({
                "id": eq_id,
                "type": eq.type,
                "model": eq.model,
                "revenue": revenue,
            })

    equipment_details.sort(key=lambda x: x["revenue"], reverse=True)

    return {
        "year": year,
        "month": month,
        "month_start": month_start,
        "month_end": month_end,
        "total_rentals": len(completed_rentals),
        "active_rentals": len(active_rentals),
        "total_revenue": total_revenue,
        "base_revenue": base_revenue,
        "total_fines": total_fines,
        "equipment_revenue": equipment_details,
        "customer_summary": customer_list,
        "rentals": completed_rentals,
    }


def export_monthly_report_to_csv(year: int, month: int, filepath: str) -> str:
    report = get_monthly_revenue_report(year, month)

    lines = []
    lines.append(f"月度租赁收入报表 - {year}年{month}月")
    lines.append("=" * 50)
    lines.append(f"统计周期: {report['month_start']} 至 {report['month_end']}")
    lines.append(f"完成租赁数: {report['total_rentals']}")
    lines.append(f"进行中租赁数: {report['active_rentals']}")
    lines.append(f"租金收入: ¥{report['base_revenue']:.2f}")
    lines.append(f"超期罚款: ¥{report['total_fines']:.2f}")
    lines.append(f"总收入: ¥{report['total_revenue']:.2f}")
    lines.append("")

    lines.append("一、按客户汇总")
    lines.append("-" * 50)
    lines.append("排名,客户名称,联系方式,租赁次数,租金收入,超期罚款,总金额")
    for i, cust in enumerate(report["customer_summary"], 1):
        base = cust["total_amount"] - cust["fines"]
        lines.append(
            f"{i},{cust['name']},{cust['phone']},{cust['rental_count']},"
            f"¥{base:.2f},¥{cust['fines']:.2f},¥{cust['total_amount']:.2f}"
        )
    lines.append("")

    lines.append("二、按设备汇总")
    lines.append("-" * 50)
    lines.append("设备编号,设备类型,型号,收入金额")
    for eq in report["equipment_revenue"]:
        lines.append(
            f"{eq['id']},{eq['type']},{eq['model']},¥{eq['revenue']:.2f}"
        )
    lines.append("")

    lines.append("三、租赁明细")
    lines.append("-" * 50)
    lines.append("租赁编号,设备编号,客户名称,起租日期,归还日期,计费方式,总金额,超期罚款")
    for r in report["rentals"]:
        lines.append(
            f"{r.id},{r.equipment_id},{r.customer_name},"
            f"{r.rental_date},{r.actual_return_date},{r.billing_method},"
            f"¥{r.total_cost - r.overdue_fine:.2f},¥{r.overdue_fine:.2f}"
        )

    with open(filepath, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))

    return filepath


def get_utilization_rate(days: int = 30) -> Dict[str, dict]:
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    equipment_list = load_equipment()
    rentals = load_rentals()

    result = {}

    for eq_type in EQUIPMENT_TYPES:
        type_equipment = [eq for eq in equipment_list if eq.type == eq_type]
        if not type_equipment:
            result[eq_type] = {"rate": 0.0, "total": 0, "rented_days": 0}
            continue

        total_equipment_days = len(type_equipment) * days
        rented_days = 0

        for eq in type_equipment:
            eq_rentals = [
                r for r in rentals
                if r.equipment_id == eq.id
                and r.actual_return_date
                and r.actual_return_date >= start_date
                and r.rental_date <= end_date
            ]
            for r in eq_rentals:
                rental_start = max(r.rental_date, start_date)
                rental_end = min(r.actual_return_date, end_date)
                days_rented = (rental_end - rental_start).days + 1
                rented_days += days_rented

        rate = (rented_days / total_equipment_days * 100) if total_equipment_days > 0 else 0

        result[eq_type] = {
            "rate": round(rate, 2),
            "total": len(type_equipment),
            "rented_days": rented_days,
            "total_days": total_equipment_days,
        }

    return result
