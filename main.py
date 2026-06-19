import os
import sys
from datetime import datetime, date
from typing import Optional

from models import EQUIPMENT_TYPES
from rental_manager import (
    rent_equipment,
    return_equipment,
    add_equipment,
    delete_equipment,
    list_all_equipment,
    get_rental_by_id,
    get_active_rentals,
    get_overdue_rentals,
    get_rentals_by_equipment,
    get_equipment_schedule,
    check_rental_conflict,
)
from maintenance_manager import (
    get_maintenance_checklist,
    add_maintenance_record,
    get_maintenance_by_equipment,
    get_maintenance_stats,
    set_maintenance_interval,
)
from reports import (
    get_equipment_status_by_type,
    get_daily_status_report,
    get_monthly_revenue_report,
    export_monthly_report_to_csv,
    get_utilization_rate,
)


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    print("=" * 60)
    print("      工程机械租赁公司 - 设备调度与维护管理系统")
    print("=" * 60)
    print()


def print_menu(menu_items):
    for i, item in enumerate(menu_items, 1):
        print(f"  {i}. {item}")
    print(f"  0. 返回上级菜单")
    print()


def get_input(prompt, default=None):
    if default is not None:
        user_input = input(f"{prompt} (默认: {default}): ").strip()
        return user_input if user_input else str(default)
    return input(f"{prompt}: ").strip()


def get_date_input(prompt, default=None):
    while True:
        prompt_text = f"{prompt} (YYYY-MM-DD"
        if default:
            prompt_text += f"，默认: {default}"
        prompt_text += "): "
        user_input = input(prompt_text).strip()

        if not user_input and default:
            user_input = str(default)

        if not user_input:
            print("日期不能为空，请重新输入。")
            continue

        try:
            return datetime.strptime(user_input, "%Y-%m-%d").date()
        except ValueError:
            print("日期格式错误，请使用 YYYY-MM-DD 格式。")


def get_float_input(prompt, default=None, min_value=None):
    while True:
        user_input = get_input(prompt, default)
        try:
            value = float(user_input)
            if min_value is not None and value < min_value:
                print(f"数值不能小于 {min_value}，请重新输入。")
                continue
            return value
        except ValueError:
            print("请输入有效的数字。")


def get_int_input(prompt, default=None, min_value=None, max_value=None):
    while True:
        user_input = get_input(prompt, default)
        try:
            value = int(user_input)
            if min_value is not None and value < min_value:
                print(f"数值不能小于 {min_value}，请重新输入。")
                continue
            if max_value is not None and value > max_value:
                print(f"数值不能大于 {max_value}，请重新输入。")
                continue
            return value
        except ValueError:
            print("请输入有效的整数。")


def get_year_month_input() -> tuple:
    while True:
        today = date.today()
        year = get_int_input("请输入年份", str(today.year), min_value=2000, max_value=2100)
        month = get_int_input("请输入月份 (1-12)", str(today.month), min_value=1, max_value=12)
        return year, month


def show_maintenance_alert():
    checklist = get_maintenance_checklist()
    urgent_items = [item for item in checklist if item["urgency"] > 0]

    if not urgent_items:
        return

    print("!" * 60)
    print("  保养提醒清单")
    print("!" * 60)
    print(f"  共有 {len(urgent_items)} 台设备需要关注保养")
    print()

    for item in urgent_items:
        eq = item["equipment"]
        status_str = item["status"]
        if item["urgency"] == 2:
            status_str = f"【紧急】{status_str}"
        print(f"  - {eq.id} ({eq.type} {eq.model}) - {status_str}")
        print(f"    当前工时: {eq.total_hours:.1f}小时 | "
              f"下次保养: {eq.next_maintenance_hours:.1f}小时 | "
              f"{item['urgency_desc']}")
    print()


def show_main_menu():
    while True:
        clear_screen()
        print_header()

        today = date.today()
        print(f"当前日期: {today}")
        print()

        show_maintenance_alert()

        print("主菜单:")
        print_menu([
            "设备管理",
            "租赁管理",
            "保养管理",
            "统计报表",
        ])

        choice = get_input("请选择操作", "0")

        if choice == "1":
            show_equipment_menu()
        elif choice == "2":
            show_rental_menu()
        elif choice == "3":
            show_maintenance_menu()
        elif choice == "4":
            show_reports_menu()
        elif choice == "0":
            print("感谢使用，再见！")
            sys.exit(0)
        else:
            input("无效选择，请按回车键继续...")


def show_equipment_menu():
    while True:
        clear_screen()
        print_header()
        print("设备管理:")
        print_menu([
            "查看所有设备",
            "添加设备",
            "删除设备",
            "设置保养周期",
            "查看设备详情",
        ])

        choice = get_input("请选择操作", "0")

        if choice == "1":
            show_all_equipment()
        elif choice == "2":
            show_add_equipment()
        elif choice == "3":
            show_delete_equipment()
        elif choice == "4":
            show_set_maintenance_interval()
        elif choice == "5":
            show_equipment_detail()
        elif choice == "0":
            break
        else:
            input("无效选择，请按回车键继续...")


def show_all_equipment():
    clear_screen()
    print_header()
    print("设备列表:")
    print("-" * 80)

    equipment_list = list_all_equipment()

    if not equipment_list:
        print("暂无设备。")
    else:
        print(f"{'编号':<8} {'类型':<8} {'型号':<15} {'状态':<8} "
              f"{'小时费率':<10} {'累计工时':<12} {'距下次保养':<12}")
        print("-" * 80)

        for eq in equipment_list:
            maint_desc = f"{eq.hours_until_maintenance:.1f}小时"
            if eq.needs_maintenance:
                maint_desc = f"已超期 {abs(eq.hours_until_maintenance):.1f}h"
            elif eq.maintenance_soon:
                maint_desc = f"即将到期 {eq.hours_until_maintenance:.1f}h"

            status_str = eq.status
            if eq.status == "在租":
                status_str = "【在租"

            print(f"{eq.id:<8} {eq.type:<8} {eq.model:<15} {status_str:<8} "
                  f"¥{eq.hourly_rate:<9.0f} {eq.total_hours:<11.1f}h {maint_desc}")

    print("-" * 80)
    input("\n按回车键继续...")


def show_add_equipment():
    clear_screen()
    print_header()
    print("添加新设备")
    print("-" * 40)

    print("设备类型可选:")
    for i, eq_type in enumerate(EQUIPMENT_TYPES, 1):
        print(f"  {i}. {eq_type}")

    while True:
        type_choice = get_int_input("请选择设备类型 (1-5)", min_value=1)
        if 1 <= type_choice <= len(EQUIPMENT_TYPES):
            eq_type = EQUIPMENT_TYPES[type_choice - 1]
            break
        print("请输入有效的类型编号。")

    model = get_input("请输入设备型号")
    hourly_rate = get_float_input("请输入小时费率 (元/小时)", min_value=0)
    total_hours = get_float_input("请输入初始累计工时 (小时)", "0", min_value=0)

    confirm = get_input(f"\n确认添加该设备？(y/n)", "y")
    if confirm.lower() != "y":
        print("已取消添加。")
        input("\n按回车键继续...")
        return

    try:
        equipment = add_equipment(eq_type, model, hourly_rate, total_hours)
        print(f"\n设备添加成功！编号: {equipment.id}")
    except ValueError as e:
        print(f"\n添加失败: {e}")

    input("\n按回车键继续...")


def show_delete_equipment():
    clear_screen()
    print_header()
    print("删除设备")
    print("-" * 40)

    equipment_id = get_input("请输入要删除的设备编号")

    confirm = get_input(f"确认删除设备 {equipment_id}？(y/n)", "n")
    if confirm.lower() != "y":
        print("已取消删除。")
        input("\n按回车键继续...")
        return

    try:
        result = delete_equipment(equipment_id)
        if result:
            print(f"设备删除成功！")
        else:
            print(f"未找到设备 {equipment_id}")
    except ValueError as e:
        print(f"删除失败: {e}")

    input("\n按回车键继续...")


def show_set_maintenance_interval():
    clear_screen()
    print_header()
    print("设置保养周期")
    print("-" * 40)

    equipment_id = get_input("请输入设备编号")
    interval = get_int_input("请输入保养周期 (小时)", min_value=1)

    confirm = get_input(f"确认设置 {equipment_id} 的保养周期为 {interval} 小时？(y/n)", "y")
    if confirm.lower() != "y":
        print("已取消。")
        input("\n按回车键继续...")
        return

    try:
        equipment = set_maintenance_interval(equipment_id, interval)
        print(f"\n保养周期设置成功！")
        print(f"设备: {equipment.id} ({equipment.type} {equipment.model})")
        print(f"保养周期: {equipment.maintenance_interval_hours} 小时")
        print(f"下次保养: {equipment.next_maintenance_hours:.1f} 小时")
    except ValueError as e:
        print(f"\n设置失败: {e}")

    input("\n按回车键继续...")


def show_equipment_detail():
    clear_screen()
    print_header()
    print("设备详情")
    print("-" * 60)

    equipment_id = get_input("请输入设备编号")

    from storage import get_equipment_by_id
    equipment = get_equipment_by_id(equipment_id)

    if not equipment:
        print(f"未找到设备 {equipment_id}")
        input("\n按回车键继续...")
        return

    print(f"\n设备编号: {equipment.id}")
    print(f"设备类型: {equipment.type}")
    print(f"设备型号: {equipment.model}")
    print(f"当前状态: {equipment.status}")
    print(f"小时费率: ¥{equipment.hourly_rate:.2f}/小时")
    print(f"日租价格: ¥{equipment.hourly_rate * 8:.2f}/天")
    print(f"累计工时: {equipment.total_hours:.1f} 小时")
    print(f"上次保养工时: {equipment.last_maintenance_hours:.1f} 小时")
    print(f"保养周期: {equipment.maintenance_interval_hours} 小时")
    print(f"下次保养工时: {equipment.next_maintenance_hours:.1f} 小时")
    maint_status = "正常"
    if equipment.needs_maintenance:
        maint_status = "必须保养"
    elif equipment.maintenance_soon:
        maint_status = "即将到期"
    print(f"保养状态: {maint_status} (距下次保养还有 {equipment.hours_until_maintenance:.1f} 小时)")

    rentals = get_rentals_by_equipment(equipment_id)
    if rentals:
        print(f"\n租赁记录 ({len(rentals)} 条):")
        print("-" * 60)
        for r in rentals[:5]:
            status_str = r.status
            if r.is_overdue:
                status_str += " (超期)"
            print(f"  {r.id} | {r.customer_name} | {r.rental_date} ~ {r.actual_return_date or r.expected_return_date} | {status_str}")
        if len(rentals) > 5:
            print(f"  ... 共 {len(rentals)} 条记录")

    maint_records = get_maintenance_by_equipment(equipment_id)
    if maint_records:
        print(f"\n保养记录 ({len(maint_records)} 条):")
        print("-" * 60)
        for m in maint_records[:3]:
            print(f"  {m.maintenance_date} | {m.maintenance_type} | {m.maintenance_hours:.1f}小时 | ¥{m.cost:.2f}")
        if len(maint_records) > 3:
            print(f"  ... 共 {len(maint_records)} 条记录")

    input("\n按回车键继续...")


def show_rental_menu():
    while True:
        clear_screen()
        print_header()
        print("租赁管理:")
        print_menu([
            "设备出租",
            "设备归还",
            "查看进行中租赁",
            "查看超期租赁",
            "查看租赁详情",
            "设备排期查询",
        ])

        choice = get_input("请选择操作", "0")

        if choice == "1":
            show_rent_equipment()
        elif choice == "2":
            show_return_equipment()
        elif choice == "3":
            show_active_rentals()
        elif choice == "4":
            show_overdue_rentals()
        elif choice == "5":
            show_rental_detail()
        elif choice == "6":
            show_equipment_schedule_view()
        elif choice == "0":
            break
        else:
            input("无效选择，请按回车键继续...")


def show_rent_equipment():
    from storage import get_equipment_by_id
    from rental_manager import calculate_rental_cost
    from datetime import timedelta

    clear_screen()
    print_header()
    print("设备出租")
    print("-" * 60)

    all_equipment = list_all_equipment()

    if not all_equipment:
        print("当前没有设备。")
        input("\n按回车键继续...")
        return

    print("设备列表:")
    for i, eq in enumerate(all_equipment, 1):
        daily_rate = eq.hourly_rate * 8
        status_tag = "【在租】" if eq.status == "在租" else ""
        print(f"  {i}. {eq.id} - {eq.type} {eq.model} {status_tag}")
        print(f"     ¥{eq.hourly_rate:.0f}/小时 (¥{daily_rate:.0f}/天) - 累计{ eq.total_hours:.0f}小时")

    print()
    while True:
        idx = get_int_input("请选择要出租的设备 (序号)", min_value=1, max_value=len(all_equipment))
        equipment = all_equipment[idx - 1]

        print(f"\n已选设备: {equipment.id} ({equipment.type} {equipment.model})")
        print(f"当前状态: {equipment.status}")

        schedule_end = date.today() + timedelta(days=60)
        schedule = get_equipment_schedule(equipment.id, date.today(), schedule_end)

        print(f"\n【排期预览】未来60天:")
        if not schedule:
            print("  暂无排期，设备全天空闲")
        else:
            for r in schedule:
                r_end = r.actual_return_date or r.expected_return_date
                status = "进行中" if r.status == "进行中" else "已完成"
                print(f"  {r.rental_date} ~ {r_end} - {r.customer_name} ({status})")

        confirm_eq = get_input("\n确认选择该设备？(y/n) 或输入 r 重新选择", "y")
        if confirm_eq.lower() == "r":
            continue
        if confirm_eq.lower() == "y":
            break
        print("已取消选择。")
        input("\n按回车键继续...")
        return

    customer_name = get_input("请输入客户名称")
    customer_phone = get_input("请输入客户联系方式")

    while True:
        print()
        rental_date = get_date_input("请输入起租日期", date.today())
        expected_return_date = get_date_input("请输入预计归还日期")

        if rental_date > expected_return_date:
            print("起租日期不能晚于预计归还日期，请重新输入。")
            continue

        conflicts = check_rental_conflict(equipment.id, rental_date, expected_return_date)
        if conflicts:
            print("\n⚠️  排期冲突！该时间段内已有以下租赁：")
            for c in conflicts:
                c_end = c.actual_return_date or c.expected_return_date
                print(f"  - {c.rental_date} ~ {c_end} ({c.customer_name})")
            retry = get_input("\n是否重新选择日期？(y/n)", "y")
            if retry.lower() == "y":
                continue
            else:
                print("已取消出租。")
                input("\n按回车键继续...")
                return
        break

    print("\n计费方式:")
    print("  1. 按天计费")
    print("  2. 按小时计费")
    billing_choice = get_input("请选择计费方式", "1")
    billing_method = "按天" if billing_choice == "1" else "按小时"

    notes = get_input("备注信息 (可选)", "")

    print("\n" + "=" * 60)
    print("租赁信息确认:")
    print(f"  设备: {equipment.id} ({equipment.type} {equipment.model})")
    print(f"  客户: {customer_name} ({customer_phone})")
    print(f"  起租日期: {rental_date}")
    print(f"  预计归还: {expected_return_date}")
    print(f"  租期: {(expected_return_date - rental_date).days + 1} 天")
    print(f"  计费方式: {billing_method}")

    total_cost, daily_rate, hourly_rate = calculate_rental_cost(
        equipment, rental_date, expected_return_date, billing_method
    )
    print(f"  日租价格: ¥{daily_rate:.2f}/天")
    print(f"  时租价格: ¥{hourly_rate:.2f}/小时")
    print(f"  预计租金: ¥{total_cost:.2f}")
    print("=" * 60)

    confirm = get_input("\n确认出租？(y/n)", "y")
    if confirm.lower() != "y":
        print("已取消出租。")
        input("\n按回车键继续...")
        return

    try:
        rental = rent_equipment(
            equipment.id,
            customer_name,
            customer_phone,
            rental_date,
            expected_return_date,
            billing_method,
            notes,
            check_conflict=True,
        )
        print(f"\n出租成功！租赁编号: {rental.id}")
    except ValueError as e:
        print(f"\n出租失败: {e}")

    input("\n按回车键继续...")


def show_return_equipment():
    clear_screen()
    print_header()
    print("设备归还")
    print("-" * 50)

    active_rentals_list = get_active_rentals()

    if not active_rentals_list:
        print("当前没有进行中的租赁。")
        input("\n按回车键继续...")
        return

    print("进行中租赁列表:")
    for i, r in enumerate(active_rentals_list, 1):
        from storage import get_equipment_by_id
        eq = get_equipment_by_id(r.equipment_id)
        eq_info = f"{r.equipment_id} ({eq.type} {eq.model})" if eq else r.equipment_id
        overdue_str = " (超期)" if r.is_overdue else ""
        print(f"  {i}. {r.id} - {eq_info} - {r.customer_name}{overdue_str}")

    print()
    idx = get_int_input("请选择要归还的租赁 (序号)", min_value=1)
    if idx < 1 or idx > len(active_rentals_list):
        print("无效的序号。")
        input("\n按回车键继续...")
        return

    rental = active_rentals_list[idx - 1]

    from storage import get_equipment_by_id
    equipment = get_equipment_by_id(rental.equipment_id)

    print(f"\n租赁信息:")
    print(f"  租赁编号: {rental.id}")
    print(f"  设备: {rental.equipment_id} ({equipment.type} {equipment.model})")
    print(f"  客户: {rental.customer_name} ({rental.customer_phone})")
    print(f"  起租日期: {rental.rental_date}")
    print(f"  预计归还: {rental.expected_return_date}")
    print(f"  起租工时: {rental.start_hours:.1f} 小时")
    print(f"  计费方式: {rental.billing_method}")

    if rental.is_overdue:
        overdue_days = (date.today() - rental.expected_return_date).days
        print(f"  ⚠️  已超期 {overdue_days} 天")

    return_date = get_date_input("\n请输入实际归还日期", date.today())
    end_hours = get_float_input("请输入归还时的工时数 (小时)", min_value=rental.start_hours)

    from rental_manager import calculate_overdue
    overdue_days, overdue_fine = calculate_overdue(rental, return_date)

    used_hours = end_hours - rental.start_hours

    if rental.billing_method == "按小时":
        base_cost = rental.hourly_rate * used_hours
    else:
        base_cost = rental.total_cost - rental.overdue_fine

    total_cost = base_cost + overdue_fine

    print("\n" + "=" * 50)
    print("费用结算:")
    print(f"  使用工时: {used_hours:.1f} 小时")
    print(f"  基础租金: ¥{base_cost:.2f}")
    if overdue_days > 0:
        print(f"  超期天数: {overdue_days} 天")
        print(f"  超期罚款: ¥{overdue_fine:.2f}")
    print(f"  总计费用: ¥{total_cost:.2f}")
    print("=" * 50)

    confirm = get_input("\n确认归还并结算？(y/n)", "y")
    if confirm.lower() != "y":
        print("已取消归还。")
        input("\n按回车键继续...")
        return

    try:
        result = return_equipment(rental.id, return_date, end_hours)
        print(f"\n归还成功！总费用: ¥{result.total_cost:.2f}")
    except ValueError as e:
        print(f"\n归还失败: {e}")

    input("\n按回车键继续...")


def show_active_rentals():
    clear_screen()
    print_header()
    print("进行中租赁列表")
    print("-" * 80)

    rentals = get_active_rentals()

    if not rentals:
        print("当前没有进行中的租赁。")
    else:
        print(f"{'编号':<20} {'设备':<12} {'客户':<12} {'起租日期':<12} {'预计归还':<12} {'状态':<10}")
        print("-" * 80)

        for r in rentals:
            status = "正常"
            if r.is_overdue:
                overdue_days = (date.today() - r.expected_return_date).days
                status = f"超期{overdue_days}天"

            print(f"{r.id:<20} {r.equipment_id:<12} {r.customer_name:<12} "
                  f"{r.rental_date:<12} {r.expected_return_date:<12} {status:<10}")

    input("\n按回车键继续...")


def show_overdue_rentals():
    clear_screen()
    print_header()
    print("超期租赁列表")
    print("-" * 80)

    rentals = get_overdue_rentals()

    if not rentals:
        print("当前没有超期租赁。")
    else:
        print(f"{'编号':<20} {'设备':<12} {'客户':<12} {'联系方式':<15} {'预计归还':<12} {'超期天数':<10}")
        print("-" * 80)

        for r in rentals:
            overdue_days = (date.today() - r.expected_return_date).days
            print(f"{r.id:<20} {r.equipment_id:<12} {r.customer_name:<12} "
                  f"{r.customer_phone:<15} {r.expected_return_date:<12} {overdue_days:<10}天")

    input("\n按回车键继续...")


def show_rental_detail():
    clear_screen()
    print_header()
    print("租赁详情")
    print("-" * 60)

    rental_id = get_input("请输入租赁编号")

    rental = get_rental_by_id(rental_id)

    if not rental:
        print(f"未找到租赁记录 {rental_id}")
        input("\n按回车键继续...")
        return

    from storage import get_equipment_by_id
    equipment = get_equipment_by_id(rental.equipment_id)

    print(f"\n租赁编号: {rental.id}")
    print(f"设备: {rental.equipment_id}")
    if equipment:
        print(f"  类型: {equipment.type}")
        print(f"  型号: {equipment.model}")
    print(f"客户名称: {rental.customer_name}")
    print(f"联系方式: {rental.customer_phone}")
    print(f"起租日期: {rental.rental_date}")
    print(f"预计归还日期: {rental.expected_return_date}")
    if rental.actual_return_date:
        print(f"实际归还日期: {rental.actual_return_date}")
    print(f"起租工时: {rental.start_hours:.1f} 小时")
    if rental.end_hours is not None:
        print(f"归还工时: {rental.end_hours:.1f} 小时")
        print(f"使用工时: {rental.end_hours - rental.start_hours:.1f} 小时")
    print(f"计费方式: {rental.billing_method}")
    print(f"日租价格: ¥{rental.daily_rate:.2f}/天")
    print(f"时租价格: ¥{rental.hourly_rate:.2f}/小时")
    print(f"租金: ¥{rental.total_cost - rental.overdue_fine:.2f}")
    if rental.overdue_fine > 0:
        print(f"超期罚款: ¥{rental.overdue_fine:.2f}")
    print(f"总费用: ¥{rental.total_cost:.2f}")
    print(f"状态: {rental.status}")
    if rental.notes:
        print(f"备注: {rental.notes}")

    input("\n按回车键继续...")


def show_equipment_schedule_view():
    from datetime import timedelta
    from storage import get_equipment_by_id

    clear_screen()
    print_header()
    print("设备排期查询")
    print("-" * 70)

    all_equipment = list_all_equipment()

    if not all_equipment:
        print("当前没有设备。")
        input("\n按回车键继续...")
        return

    print("设备列表:")
    for i, eq in enumerate(all_equipment, 1):
        status_tag = "【在租】" if eq.status == "在租" else ""
        print(f"  {i}. {eq.id} - {eq.type} {eq.model} {status_tag}")

    print()
    idx = get_int_input("请选择要查询的设备 (序号)", min_value=1, max_value=len(all_equipment))
    equipment = all_equipment[idx - 1]

    print(f"\n查询时间段:")
    start_date = get_date_input("开始日期", date.today())

    default_end = start_date + timedelta(days=30)
    end_date = get_date_input("结束日期", default_end.strftime("%Y-%m-%d"))

    if start_date > end_date:
        print("开始日期不能晚于结束日期，已自动调换。")
        start_date, end_date = end_date, start_date

    schedule = get_equipment_schedule(equipment.id, start_date, end_date)

    print(f"\n设备排期: {equipment.id} ({equipment.type} {equipment.model})")
    print(f"查询区间: {start_date} ~ {end_date} (共{(end_date - start_date).days + 1}天)")
    print("-" * 70)

    if not schedule:
        print("  该时间段内无租赁记录，设备全天空闲。")
    else:
        total_rented_days = 0
        print(f"{'起始日期':<12} {'结束日期':<12} {'客户':<14} {'状态':<10} {'天数':<6}")
        print("-" * 70)
        for r in schedule:
            r_start = max(r.rental_date, start_date)
            r_end = r.actual_return_date or r.expected_return_date
            r_end = min(r_end, end_date)
            days = (r_end - r_start).days + 1
            total_rented_days += days
            status = "进行中" if r.status == "进行中" else "已完成"
            print(f"{r.rental_date:<12} {r_end:<12} {r.customer_name:<14} {status:<10} {days:<6}")

        total_days = (end_date - start_date).days + 1
        utilization = (total_rented_days / total_days * 100) if total_days > 0 else 0
        print("-" * 70)
        print(f"租赁天数: {total_rented_days} 天 / {total_days} 天 (利用率: {utilization:.1f}%)")

    input("\n按回车键继续...")


def show_maintenance_menu():
    while True:
        clear_screen()
        print_header()
        print("保养管理:")
        print_menu([
            "查看保养清单",
            "记录保养",
            "查看设备保养记录",
            "保养统计",
        ])

        choice = get_input("请选择操作", "0")

        if choice == "1":
            show_maintenance_checklist_view()
        elif choice == "2":
            show_add_maintenance()
        elif choice == "3":
            show_equipment_maintenance_records()
        elif choice == "4":
            show_maintenance_stats_view()
        elif choice == "0":
            break
        else:
            input("无效选择，请按回车键继续...")


def show_maintenance_checklist_view():
    clear_screen()
    print_header()
    print("保养清单")
    print("-" * 90)

    checklist = get_maintenance_checklist()

    if not checklist:
        print("暂无设备。")
    else:
        print(f"{'编号':<8} {'类型':<8} {'型号':<15} {'状态':<10} "
              f"{'累计工时':<12} {'下次保养':<12} {'距保养':<15} {'状态':<8}")
        print("-" * 90)

        for item in checklist:
            eq = item["equipment"]
            status = item["status"]
            urgency_desc = item["urgency_desc"] or "-"

            status_color = ""
            if item["urgency"] == 2:
                status = "【紧急】" + status
            elif item["urgency"] == 1:
                status = "【提醒】" + status

            print(f"{eq.id:<8} {eq.type:<8} {eq.model:<15} {eq.status:<10} "
                  f"{eq.total_hours:<11.1f}h {eq.next_maintenance_hours:<11.1f}h {urgency_desc:<15} {item['status']:<8}")

    input("\n按回车键继续...")


def show_add_maintenance():
    clear_screen()
    print_header()
    print("记录保养")
    print("-" * 50)

    equipment_id = get_input("请输入设备编号")

    from storage import get_equipment_by_id
    equipment = get_equipment_by_id(equipment_id)
    if not equipment:
        print(f"未找到设备 {equipment_id}")
        input("\n按回车键继续...")
        return

    print(f"\n设备信息:")
    print(f"  编号: {equipment.id}")
    print(f"  类型: {equipment.type} {equipment.model}")
    print(f"  累计工时: {equipment.total_hours:.1f} 小时")
    print(f"  上次保养工时: {equipment.last_maintenance_hours:.1f} 小时")
    print(f"  距下次保养: {equipment.hours_until_maintenance:.1f} 小时")

    maintenance_date = get_date_input("\n请输入保养日期", date.today())

    print("\n保养类型:")
    print("  1. 例行保养")
    print("  2. 定期保养")
    print("  3. 大修")
    print("  4. 故障维修")
    print("  5. 其他")
    type_choice = get_input("请选择保养类型", "2")
    type_map = {"1": "例行保养", "2": "定期保养", "3": "大修", "4": "故障维修", "5": "其他"}
    maintenance_type = type_map.get(type_choice, "其他")

    maintenance_hours = get_float_input(
        "请输入保养时的工时数 (小时)",
        default=equipment.total_hours,
        min_value=equipment.last_maintenance_hours
    )

    description = get_input("保养描述 (可选)", "")
    cost = get_float_input("保养费用 (元)", "0", min_value=0)
    operator = get_input("操作人员 (可选)", "")

    print("\n" + "=" * 50)
    print("保养信息确认:")
    print(f"  设备: {equipment.id} ({equipment.type} {equipment.model})")
    print(f"  保养日期: {maintenance_date}")
    print(f"  保养类型: {maintenance_type}")
    print(f"  保养工时: {maintenance_hours:.1f} 小时")
    print(f"  保养费用: ¥{cost:.2f}")
    print("=" * 50)

    confirm = get_input("\n确认记录保养？(y/n)", "y")
    if confirm.lower() != "y":
        print("已取消。")
        input("\n按回车键继续...")
        return

    try:
        record = add_maintenance_record(
            equipment_id,
            maintenance_date,
            maintenance_type,
            maintenance_hours,
            description,
            cost,
            operator,
        )
        print(f"\n保养记录添加成功！编号: {record.id}")
    except ValueError as e:
        print(f"\n添加失败: {e}")

    input("\n按回车键继续...")


def show_equipment_maintenance_records():
    clear_screen()
    print_header()
    print("设备保养记录")
    print("-" * 70)

    equipment_id = get_input("请输入设备编号")

    from storage import get_equipment_by_id
    equipment = get_equipment_by_id(equipment_id)
    if not equipment:
        print(f"未找到设备 {equipment_id}")
        input("\n按回车键继续...")
        return

    records = get_maintenance_by_equipment(equipment_id)

    print(f"\n设备: {equipment.id} ({equipment.type} {equipment.model})")
    print(f"累计工时: {equipment.total_hours:.1f} 小时")
    print(f"上次保养: {equipment.last_maintenance_hours:.1f} 小时")
    print()

    if not records:
        print("暂无保养记录。")
    else:
        print(f"{'日期':<12} {'类型':<10} {'工时':<12} {'费用':<10} {'操作人员':<12} {'描述'}")
        print("-" * 70)

        for r in sorted(records, key=lambda x: x.maintenance_date, reverse=True):
            print(f"{r.maintenance_date:<12} {r.maintenance_type:<10} "
                  f"{r.maintenance_hours:<11.1f}h ¥{r.cost:<9.2f} {r.operator:<12} {r.description}")

    input("\n按回车键继续...")


def show_maintenance_stats_view():
    clear_screen()
    print_header()
    print("保养统计")
    print("-" * 50)

    stats = get_maintenance_stats()

    print(f"设备总数: {stats['total']} 台")
    print(f"必须保养: {stats['need_maintenance']} 台")
    print(f"即将到期: {stats['soon_maintenance']} 台")
    print(f"状态正常: {stats['normal']} 台")
    print()

    if stats["need_maintenance"] > 0:
        print("⚠️  有设备必须立即保养！")
    elif stats["soon_maintenance"] > 0:
        print("ℹ️  有设备即将到期保养。")
    else:
        print("✅ 所有设备保养状态正常。")

    input("\n按回车键继续...")


def show_reports_menu():
    while True:
        clear_screen()
        print_header()
        print("统计报表:")
        print_menu([
            "设备状态统计",
            "每日设备状态报表",
            "月度租赁收入报表",
            "导出月度报表",
            "设备利用率统计",
        ])

        choice = get_input("请选择操作", "0")

        if choice == "1":
            show_equipment_status_by_type()
        elif choice == "2":
            show_daily_report()
        elif choice == "3":
            show_monthly_report()
        elif choice == "4":
            show_export_monthly_report()
        elif choice == "5":
            show_utilization_report()
        elif choice == "0":
            break
        else:
            input("无效选择，请按回车键继续...")


def show_equipment_status_by_type():
    clear_screen()
    print_header()
    print("设备状态统计（按类型）")
    print("-" * 60)

    status_data = get_equipment_status_by_type()

    print(f"{'类型':<10} {'总数':<8} {'在租':<8} {'空闲':<8} {'利用率'}")
    print("-" * 60)

    total_all = 0
    rented_all = 0

    for eq_type in EQUIPMENT_TYPES:
        data = status_data.get(eq_type, {"total": 0, "rented": 0, "idle": 0})
        rate = (data["rented"] / data["total"] * 100) if data["total"] > 0 else 0
        print(f"{eq_type:<10} {data['total']:<8} {data['rented']:<8} {data['idle']:<8} {rate:.1f}%")
        total_all += data["total"]
        rented_all += data["rented"]

    print("-" * 60)
    overall_rate = (rented_all / total_all * 100) if total_all > 0 else 0
    print(f"{'合计':<10} {total_all:<8} {rented_all:<8} {total_all - rented_all:<8} {overall_rate:.1f}%")

    input("\n按回车键继续...")


def show_daily_report():
    clear_screen()
    print_header()
    print("每日设备状态报表（支持历史回看）")
    print("-" * 70)

    report_date = get_date_input("请输入报表日期", date.today())

    report = get_daily_status_report(report_date)

    print(f"\n报表日期: {report['report_date']}"
          f"{'（今天）' if report_date == date.today() else ''}")
    print()
    print(f"设备总数: {report['total_equipment']} 台")
    print(f"在租设备: {report['rented_count']} 台")
    print(f"空闲设备: {report['idle_count']} 台")
    print()
    print(f"当日新租: {report['new_rentals_count']} 单")
    print(f"当日归还: {report['returns_count']} 单")
    print(f"超期租赁: {report['overdue_count']} 单")
    print()
    print(f"当日租金收入: ¥{report['new_revenue']:.2f}")
    print(f"当日超期罚款: ¥{report['fine_revenue']:.2f}")
    print(f"当日总收入: ¥{report['total_revenue']:.2f}")

    rented_by_type = report.get('rented_by_type', {})
    if rented_by_type:
        print("\n【在租设备按类型分布】")
        for eq_type in EQUIPMENT_TYPES:
            count = rented_by_type.get(eq_type, 0)
            if count > 0:
                print(f"  {eq_type}: {count} 台")

    if report['rented_details']:
        print(f"\n【当日在租设备明细】（共{len(report['rented_details'])}条记录）")
        print("-" * 70)
        seen = set()
        for r in report['rented_details']:
            if r.equipment_id not in seen:
                seen.add(r.equipment_id)
                overdue_str = ""
                if report_date > r.expected_return_date and r.status == "进行中":
                    overdue_days = (report_date - r.expected_return_date).days
                    overdue_str = f"【超期{overdue_days}天】"
                print(f"  {r.equipment_id} - {r.customer_name} {overdue_str}")

    if report['new_rentals']:
        print(f"\n【当日新租】（共{len(report['new_rentals'])}单）")
        for r in report['new_rentals']:
            print(f"  {r.id} - {r.equipment_id} - {r.customer_name}")

    if report['returns']:
        print(f"\n【当日归还】（共{len(report['returns'])}单）")
        for r in report['returns']:
            print(f"  {r.id} - {r.equipment_id} - {r.customer_name} - ¥{r.total_cost:.2f}")

    if report['overdue_rentals']:
        print(f"\n【超期租赁明细】（共{len(report['overdue_rentals'])}单）")
        for r in report['overdue_rentals']:
            overdue_days = (report_date - r.expected_return_date).days
            print(f"  {r.id} | {r.equipment_id} | {r.customer_name} | 超期{overdue_days}天")

    input("\n按回车键继续...")


def show_monthly_report():
    clear_screen()
    print_header()
    print("月度租赁收入报表")
    print("-" * 70)

    year, month = get_year_month_input()

    report = get_monthly_revenue_report(year, month)

    print(f"\n统计周期: {report['month_start']} 至 {report['month_end']}")
    print()
    print("【收入总览】")
    print(f"  完成租赁: {report['total_rentals']} 单")
    print(f"  进行中: {report['active_rentals']} 单")
    print(f"  累计租赁天数: {report['total_rental_days']} 天")
    print(f"  累计租赁工时: {report['total_rental_hours']} 小时")
    print()
    print(f"  租金收入: ¥{report['base_revenue']:.2f}  ({100 - report['fine_ratio']:.2f}%)")
    print(f"  超期罚款: ¥{report['total_fines']:.2f}  ({report['fine_ratio']:.2f}%)")
    print(f"  总收入:   ¥{report['total_revenue']:.2f}  (100.00%)")

    if report['type_summary']:
        print(f"\n【按设备类型汇总】")
        print("-" * 70)
        print(f"{'设备类型':<10} {'单数':<6} {'租金收入':<12} {'超期罚款':<12} {'总收入':<12} {'占比':<8}")
        print("-" * 70)
        for item in report['type_summary']:
            ratio = (item['revenue'] / report['total_revenue'] * 100) if report['total_revenue'] > 0 else 0
            base_rev = item['revenue'] - item['fines']
            print(f"{item['type']:<10} {item['rental_count']:<6} "
                  f"¥{base_rev:<11.2f} ¥{item['fines']:<11.2f} "
                  f"¥{item['revenue']:<11.2f} {ratio:<7.2f}%")

    if report['billing_summary']:
        print(f"\n【按计费方式汇总】")
        print("-" * 70)
        print(f"{'计费方式':<10} {'单数':<6} {'租金收入':<12} {'超期罚款':<12} {'总收入':<12} {'占比':<8}")
        print("-" * 70)
        for item in report['billing_summary']:
            ratio = (item['revenue'] / report['total_revenue'] * 100) if report['total_revenue'] > 0 else 0
            base_rev = item['revenue'] - item['fines']
            print(f"{item['method']:<10} {item['rental_count']:<6} "
                  f"¥{base_rev:<11.2f} ¥{item['fines']:<11.2f} "
                  f"¥{item['revenue']:<11.2f} {ratio:<7.2f}%")

    if report['customer_summary']:
        print(f"\n【按客户汇总 (前10名)】")
        print("-" * 70)
        print(f"{'排名':<4} {'客户名称':<14} {'单数':<5} {'总金额':<12} {'占比':<8}")
        print("-" * 70)
        for i, cust in enumerate(report['customer_summary'][:10], 1):
            ratio = (cust['total_amount'] / report['total_revenue'] * 100) if report['total_revenue'] > 0 else 0
            print(f"{i:<4} {cust['name']:<14} {cust['rental_count']:<5} "
                  f"¥{cust['total_amount']:<11.2f} {ratio:<7.2f}%")

    if report['equipment_revenue']:
        print(f"\n【按设备汇总 (前10名)】")
        print("-" * 70)
        print(f"{'排名':<4} {'设备编号':<10} {'型号':<14} {'单数':<5} {'收入':<12} {'占比':<8}")
        print("-" * 70)
        for i, eq in enumerate(report['equipment_revenue'][:10], 1):
            ratio = (eq['revenue'] / report['total_revenue'] * 100) if report['total_revenue'] > 0 else 0
            print(f"{i:<4} {eq['id']:<10} {eq['model']:<14} {eq['rental_count']:<5} "
                  f"¥{eq['revenue']:<11.2f} {ratio:<7.2f}%")

    input("\n按回车键继续...")


def show_export_monthly_report():
    clear_screen()
    print_header()
    print("导出月度报表")
    print("-" * 60)

    year, month = get_year_month_input()

    default_filename = f"月度报表_{year}_{month:02d}.csv"
    filename = get_input("请输入文件名", default_filename)

    if not filename.endswith('.csv'):
        filename += '.csv'

    try:
        filepath = export_monthly_report_to_csv(year, month, filename)
        print(f"\n报表导出成功！文件: {filepath}")
        print("该 CSV 包含6个工作表：收入总览、按设备类型、按计费方式、按客户、按设备、租赁明细")
    except Exception as e:
        print(f"\n导出失败: {e}")

    input("\n按回车键继续...")


def show_utilization_report():
    clear_screen()
    print_header()
    print("设备利用率统计")
    print("-" * 60)

    days = get_int_input("请输入统计天数", "30", min_value=1)

    utilization = get_utilization_rate(days)

    print(f"\n统计周期: 最近 {days} 天")
    print()
    print(f"{'类型':<10} {'设备数':<10} {'出租天数':<12} {'利用率'}")
    print("-" * 60)

    total_rented_days = 0
    total_days = 0

    for eq_type in EQUIPMENT_TYPES:
        data = utilization.get(eq_type, {"rate": 0, "total": 0, "rented_days": 0, "total_days": 0})
        print(f"{eq_type:<10} {data['total']:<10} {data['rented_days']:<12} {data['rate']:.2f}%")
        total_rented_days += data['rented_days']
        total_days += data['total_days']

    print("-" * 60)
    overall_rate = (total_rented_days / total_days * 100) if total_days > 0 else 0
    print(f"整体利用率: {overall_rate:.2f}%")

    input("\n按回车键继续...")


def init_sample_data():
    from storage import load_equipment
    from storage import reset_equipment_counter

    equipment_list = load_equipment()
    if equipment_list:
        return

    for eq_type in EQUIPMENT_TYPES:
        reset_equipment_counter(eq_type)

    samples = [
        ("挖掘机", "卡特320", 200, 1250.5),
        ("挖掘机", "小松PC200", 180, 850.0),
        ("装载机", "柳工856", 150, 2100.0),
        ("装载机", "徐工LW500", 140, 350.0),
        ("起重机", "三一25吨", 300, 680.0),
        ("压路机", "徐工XS263", 120, 420.0),
        ("推土机", "山推SD22", 250, 1580.0),
    ]

    for eq_type, model, rate, hours in samples:
        add_equipment(eq_type, model, rate, total_hours=hours)


def main():
    init_sample_data()
    show_main_menu()


if __name__ == "__main__":
    main()
