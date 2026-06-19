import os
from datetime import date, timedelta
from typing import List, Dict
from collections import defaultdict

from models import Equipment, RentalRecord, EQUIPMENT_TYPES
from storage import load_equipment, load_rentals, load_maintenance
from rental_manager import get_rentals_on_date


def get_unique_filename(filepath: str) -> str:
    if not os.path.exists(filepath):
        return filepath

    base, ext = os.path.splitext(filepath)
    counter = 2
    while True:
        new_path = f"{base}_{counter}{ext}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1



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

    rented_equipment_ids = set()
    new_rentals = []
    returns = []
    overdue = []
    rented_details = []

    for r in rentals:
        r_start = r.rental_date

        if r.status == "已完成" and r.actual_return_date:
            r_end = r.actual_return_date
            is_rented_on_date = r_start <= report_date < r_end
        else:
            r_end = r.expected_return_date
            is_rented_on_date = r_start <= report_date

        if is_rented_on_date:
            rented_equipment_ids.add(r.equipment_id)
            rented_details.append(r)

            if report_date > r.expected_return_date and r.status == "进行中":
                overdue.append(r)

        if r.rental_date == report_date:
            new_rentals.append(r)

        if r.actual_return_date == report_date and r.status == "已完成":
            returns.append(r)

    rented_count = len(rented_equipment_ids)
    total_equipment = len(equipment_list)
    idle_count = total_equipment - rented_count

    new_revenue = sum(
        r.total_cost - r.overdue_fine
        for r in returns
    )
    fine_revenue = sum(r.overdue_fine for r in returns)
    total_revenue = new_revenue + fine_revenue

    rented_by_type = defaultdict(int)
    for r in rented_details:
        eq = next((e for e in equipment_list if e.id == r.equipment_id), None)
        if eq:
            rented_by_type[eq.type] += 1

    idle_by_type = defaultdict(int)
    for eq in equipment_list:
        if eq.id not in rented_equipment_ids:
            idle_by_type[eq.type] += 1

    return {
        "report_date": report_date,
        "total_equipment": total_equipment,
        "rented_count": rented_count,
        "idle_count": idle_count,
        "new_rentals_count": len(new_rentals),
        "returns_count": len(returns),
        "overdue_count": len(overdue),
        "new_revenue": new_revenue,
        "fine_revenue": fine_revenue,
        "total_revenue": total_revenue,
        "rented_equipment_ids": rented_equipment_ids,
        "new_rentals": new_rentals,
        "returns": returns,
        "overdue_rentals": overdue,
        "rented_details": rented_details,
        "rented_by_type": dict(rented_by_type),
        "idle_by_type": dict(idle_by_type),
    }


def get_monthly_revenue_report(year: int, month: int) -> dict:
    rentals = load_rentals()
    equipment_list = load_equipment()

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

    total_rental_days = 0
    total_rental_hours = 0
    for r in completed_rentals:
        if r.end_hours is not None and r.start_hours is not None:
            total_rental_hours += r.end_hours - r.start_hours
        if r.actual_return_date:
            days = (r.actual_return_date - r.rental_date).days + 1
            total_rental_days += days

    equipment_revenue = defaultdict(lambda: {
        "id": "",
        "type": "",
        "model": "",
        "revenue": 0.0,
        "rental_count": 0,
    })
    for r in completed_rentals:
        eq = next((e for e in equipment_list if e.id == r.equipment_id), None)
        equipment_revenue[r.equipment_id]["id"] = r.equipment_id
        if eq:
            equipment_revenue[r.equipment_id]["type"] = eq.type
            equipment_revenue[r.equipment_id]["model"] = eq.model
        equipment_revenue[r.equipment_id]["revenue"] += r.total_cost
        equipment_revenue[r.equipment_id]["rental_count"] += 1

    customer_revenue = defaultdict(lambda: {
        "name": "",
        "phone": "",
        "total_amount": 0.0,
        "rental_count": 0,
        "fines": 0.0,
        "base_revenue": 0.0,
    })
    for r in completed_rentals:
        key = r.customer_name + "|" + r.customer_phone
        customer_revenue[key]["name"] = r.customer_name
        customer_revenue[key]["phone"] = r.customer_phone
        customer_revenue[key]["total_amount"] += r.total_cost
        customer_revenue[key]["rental_count"] += 1
        customer_revenue[key]["fines"] += r.overdue_fine
        customer_revenue[key]["base_revenue"] += r.total_cost - r.overdue_fine

    type_revenue = defaultdict(lambda: {
        "type": "",
        "revenue": 0.0,
        "rental_count": 0,
        "fines": 0.0,
    })
    for r in completed_rentals:
        eq = next((e for e in equipment_list if e.id == r.equipment_id), None)
        eq_type = eq.type if eq else "未知"
        type_revenue[eq_type]["type"] = eq_type
        type_revenue[eq_type]["revenue"] += r.total_cost
        type_revenue[eq_type]["rental_count"] += 1
        type_revenue[eq_type]["fines"] += r.overdue_fine

    billing_revenue = defaultdict(lambda: {
        "method": "",
        "revenue": 0.0,
        "rental_count": 0,
        "fines": 0.0,
    })
    for r in completed_rentals:
        method = r.billing_method
        billing_revenue[method]["method"] = method
        billing_revenue[method]["revenue"] += r.total_cost
        billing_revenue[method]["rental_count"] += 1
        billing_revenue[method]["fines"] += r.overdue_fine

    customer_list = sorted(
        customer_revenue.values(),
        key=lambda x: x["total_amount"],
        reverse=True
    )

    equipment_details = sorted(
        list(equipment_revenue.values()),
        key=lambda x: x["revenue"],
        reverse=True
    )

    type_list = sorted(
        list(type_revenue.values()),
        key=lambda x: x["revenue"],
        reverse=True
    )

    billing_list = sorted(
        list(billing_revenue.values()),
        key=lambda x: x["revenue"],
        reverse=True
    )

    fine_ratio = (total_fines / total_revenue * 100) if total_revenue > 0 else 0.0

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
        "fine_ratio": round(fine_ratio, 2),
        "total_rental_days": total_rental_days,
        "total_rental_hours": round(total_rental_hours, 1),
        "equipment_revenue": equipment_details,
        "customer_summary": customer_list,
        "type_summary": type_list,
        "billing_summary": billing_list,
        "rentals": completed_rentals,
    }


def export_monthly_report_to_csv(
    year: int,
    month: int,
    filepath: str,
    auto_increment: bool = True,
) -> str:
    if auto_increment:
        filepath = get_unique_filename(filepath)

    report = get_monthly_revenue_report(year, month)

    lines = []

    lines.append("月度租赁收入报表")
    lines.append(f"统计周期,{report['month_start']},至,{report['month_end']}")
    lines.append("")

    lines.append("一、收入总览")
    lines.append("项目,金额(元),占比/说明")
    lines.append(f"租金收入,{report['base_revenue']:.2f},{100 - report['fine_ratio']:.2f}%")
    lines.append(f"超期罚款,{report['total_fines']:.2f},{report['fine_ratio']:.2f}%")
    lines.append(f"总收入,{report['total_revenue']:.2f},100.00%")
    lines.append(f"完成租赁单数,{report['total_rentals']},")
    lines.append(f"进行中租赁单数,{report['active_rentals']},")
    lines.append(f"累计租赁天数,{report['total_rental_days']},")
    lines.append(f"累计租赁工时,{report['total_rental_hours']},")
    lines.append("")

    lines.append("二、按设备类型汇总")
    lines.append("设备类型,租赁单数,租金收入(元),超期罚款(元),总收入(元),占比(%)")
    for item in report["type_summary"]:
        ratio = (item["revenue"] / report["total_revenue"] * 100) if report["total_revenue"] > 0 else 0
        lines.append(
            f"{item['type']},{item['rental_count']},"
            f"{item['revenue'] - item['fines']:.2f},{item['fines']:.2f},"
            f"{item['revenue']:.2f},{ratio:.2f}"
        )
    lines.append("")

    lines.append("三、按计费方式汇总")
    lines.append("计费方式,租赁单数,租金收入(元),超期罚款(元),总收入(元),占比(%)")
    for item in report["billing_summary"]:
        ratio = (item["revenue"] / report["total_revenue"] * 100) if report["total_revenue"] > 0 else 0
        lines.append(
            f"{item['method']},{item['rental_count']},"
            f"{item['revenue'] - item['fines']:.2f},{item['fines']:.2f},"
            f"{item['revenue']:.2f},{ratio:.2f}"
        )
    lines.append("")

    lines.append("四、按客户汇总")
    lines.append("排名,客户名称,联系方式,租赁单数,租金收入(元),超期罚款(元),总金额(元),占比(%)")
    for i, cust in enumerate(report["customer_summary"], 1):
        ratio = (cust["total_amount"] / report["total_revenue"] * 100) if report["total_revenue"] > 0 else 0
        lines.append(
            f"{i},{cust['name']},{cust['phone']},{cust['rental_count']},"
            f"{cust['base_revenue']:.2f},{cust['fines']:.2f},"
            f"{cust['total_amount']:.2f},{ratio:.2f}"
        )
    lines.append("")

    lines.append("五、按设备汇总")
    lines.append("设备编号,设备类型,设备型号,租赁单数,收入金额(元),占比(%)")
    for eq in report["equipment_revenue"]:
        ratio = (eq["revenue"] / report["total_revenue"] * 100) if report["total_revenue"] > 0 else 0
        lines.append(
            f"{eq['id']},{eq['type']},{eq['model']},{eq['rental_count']},"
            f"{eq['revenue']:.2f},{ratio:.2f}"
        )
    lines.append("")

    lines.append("六、租赁明细")
    lines.append(
        "租赁编号,设备编号,设备类型,客户名称,客户电话,"
        "起租日期,归还日期,计费方式,租赁天数,使用工时(小时),"
        "租金(元),超期罚款(元),总金额(元)"
    )
    for r in report["rentals"]:
        eq = next((e for e in load_equipment() if e.id == r.equipment_id), None)
        eq_type = eq.type if eq else ""
        days = (r.actual_return_date - r.rental_date).days + 1 if r.actual_return_date else 0
        hours = (r.end_hours - r.start_hours) if (r.end_hours and r.start_hours) else 0
        base_cost = r.total_cost - r.overdue_fine
        lines.append(
            f"{r.id},{r.equipment_id},{eq_type},{r.customer_name},{r.customer_phone},"
            f"{r.rental_date},{r.actual_return_date},{r.billing_method},{days},{hours:.1f},"
            f"{base_cost:.2f},{r.overdue_fine:.2f},{r.total_cost:.2f}"
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
            result[eq_type] = {"rate": 0.0, "total": 0, "rented_days": 0, "total_days": 0}
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
