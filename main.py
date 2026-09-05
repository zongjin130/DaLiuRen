"""大六壬卜卦 — 命令行入口。"""

import sys
import os

# Windows 终端 UTF-8 支持
os.system("chcp 65001 >nul 2>&1")
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from datetime import datetime, timezone, timedelta

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box

from core.location import get_location
from core.calendar import get_ganzhi_for_datetime, get_true_solar_time
from core.panju import build_panju, PanJu
from core.duanke import duanke, DuanKeResult, QUESTION_TYPES
from core.ganzhi import DI_ZHI, SHIER_TIANGUIANG

console = Console()


def format_tianpan(tianpan: dict) -> str:
    """格式化天地盘显示。"""
    layout = [
        ("巳", "午", "未", "申"),
        ("辰", None, None, "酉"),
        ("卯", None, None, "戌"),
        ("寅", "丑", "子", "亥"),
    ]

    lines = []
    for row in layout:
        parts = []
        for pos in row:
            if pos is None:
                parts.append("  ")
            else:
                tian_val = tianpan[pos]
                parts.append(f"{tian_val}")
        lines.append("  ".join(parts))

    return "\n".join(lines)


def format_dipan() -> str:
    """格式化地盘显示。"""
    layout = [
        ("巳", "午", "未", "申"),
        ("辰", None, None, "酉"),
        ("卯", None, None, "戌"),
        ("寅", "丑", "子", "亥"),
    ]

    lines = []
    for row in layout:
        parts = []
        for pos in row:
            if pos is None:
                parts.append("  ")
            else:
                parts.append(f"{pos}")
        lines.append("  ".join(parts))

    return "\n".join(lines)


def print_panju(panju: PanJu, result: DuanKeResult, location):
    """输出完整课盘。"""
    gzdt = panju.gzdt
    tst = panju.true_solar_dt

    # === 标题 ===
    console.print()
    console.print(Panel.fit(
        "[bold yellow]大 六 壬 起 课[/]",
        border_style="yellow",
        padding=(0, 2),
    ))

    # === 基本信息 ===
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column(width=12)
    info_table.add_column()

    info_table.add_row("[cyan]占时[/]", f"{gzdt.year_ganzhi}年 {gzdt.month_ganzhi}月 {gzdt.day_ganzhi}日 {gzdt.hour_ganzhi}时")
    info_table.add_row("[cyan]农历[/]", f"{gzdt.lunar_month}月{gzdt.lunar_day}日")
    info_table.add_row("[cyan]地点[/]", f"{location.city}（东经{location.longitude}°）")
    info_table.add_row("[cyan]真太阳时[/]", f"{tst.strftime('%H:%M')}")
    info_table.add_row("[cyan]月将[/]", f"{gzdt.yuejiang_name}（{gzdt.jieqi}后）")
    info_table.add_row("[cyan]问事[/]", f"[bold]{result.question_type}[/]")

    console.print(Panel(info_table, title="[bold]基本信息[/]", border_style="blue"))

    # === 天地盘 ===
    tianpan_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    for _ in range(4):
        tianpan_table.add_column(width=3, justify="center")

    dipan_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    for _ in range(4):
        dipan_table.add_column(width=3, justify="center")

    layout = [
        ("巳", "午", "未", "申"),
        ("辰", None, None, "酉"),
        ("卯", None, None, "戌"),
        ("寅", "丑", "子", "亥"),
    ]

    for row in layout:
        tian_row = []
        di_row = []
        for pos in row:
            if pos is None:
                tian_row.append("")
                di_row.append("")
            else:
                tian_row.append(f"[bold]{panju.tianpan[pos]}[/]")
                di_row.append(f"[dim]{pos}[/]")
        tianpan_table.add_row(*tian_row)
        dipan_table.add_row(*di_row)

    pan_columns = Columns([
        Panel(tianpan_table, title="[bold yellow]天盘[/]", border_style="yellow"),
        Panel(dipan_table, title="[bold cyan]地盘[/]", border_style="cyan"),
    ], padding=2)

    console.print(pan_columns)

    # === 四课 ===
    sike_table = Table(show_header=True, box=box.ROUNDED, border_style="green")
    sike_table.add_column("", justify="center", width=8)
    sike_table.add_column("第一课\n（干阳）", justify="center", width=8)
    sike_table.add_column("第二课\n（支阳）", justify="center", width=8)
    sike_table.add_column("第三课\n（干阴）", justify="center", width=8)
    sike_table.add_column("第四课\n（支阴）", justify="center", width=8)

    sike = panju.sike
    sike_table.add_row(
        "[bold]上神[/]",
        f"[bold]{sike.ke1_shang}[/]",
        f"[bold]{sike.ke2_shang}[/]",
        f"[bold]{sike.ke3_shang}[/]",
        f"[bold]{sike.ke4_shang}[/]",
    )
    sike_table.add_row(
        "[dim]下神[/]",
        f"[dim]{sike.ke1_xia}[/]",
        f"[dim]{sike.ke2_xia}[/]",
        f"[dim]{sike.ke3_xia}[/]",
        f"[dim]{sike.ke4_xia}[/]",
    )

    console.print(Panel(sike_table, title="[bold]四课[/]", border_style="green"))

    # === 三传 ===
    sc = panju.sanchuan
    chu_tj = panju.guiren.tianjiang_map.get(sc.chu, "—")
    zhong_tj = panju.guiren.tianjiang_map.get(sc.zhong, "—")
    mo_tj = panju.guiren.tianjiang_map.get(sc.mo, "—")

    sc_table = Table(show_header=True, box=box.ROUNDED, border_style="magenta")
    sc_table.add_column("", justify="center", width=8)
    sc_table.add_column("初传", justify="center", width=8)
    sc_table.add_column("中传", justify="center", width=8)
    sc_table.add_column("末传", justify="center", width=8)

    sc_table.add_row("[bold]地支[/]", f"[bold]{sc.chu}[/]", f"[bold]{sc.zhong}[/]", f"[bold]{sc.mo}[/]")
    sc_table.add_row("[cyan]天将[/]", chu_tj, zhong_tj, mo_tj)
    sc_table.add_row("[dim]起法[/]", f"[dim]{sc.method}[/]", "", "")

    console.print(Panel(sc_table, title="[bold]三传[/]", border_style="magenta"))

    # === 十二天将 ===
    tj_table = Table(show_header=True, box=box.SIMPLE_HEAVY, border_style="cyan")
    tj_table.add_column("地支", justify="center", width=4)
    for zhi in DI_ZHI:
        tj_table.add_column(zhi, justify="center", width=5)

    tj_row_name = ["天将"]
    tj_row_jx = ["吉凶"]
    for zhi in DI_ZHI:
        tj = panju.guiren.tianjiang_map.get(zhi, "—")
        tj_row_name.append(tj)
        from core.duanke import TIANGUIANG_JIXIONG
        jx = TIANGUIANG_JIXIONG.get(tj, "—")
        if jx == "吉":
            tj_row_jx.append(f"[green]{jx}[/]")
        elif jx == "凶":
            tj_row_jx.append(f"[red]{jx}[/]")
        else:
            tj_row_jx.append(jx)

    tj_table.add_row(*tj_row_name)
    tj_table.add_row(*tj_row_jx)

    console.print(Panel(tj_table, title=f"[bold]十二天将[/]（贵人在{panju.guiren.guiren_zhi}，{panju.guiren.guiren_dir}行）", border_style="cyan"))

    # === 断语 ===
    details_text = "\n".join(f"  • {d}" for d in result.details)

    summary_panel = Panel(
        f"[bold]{result.summary}[/]\n\n{details_text}",
        title="[bold red]基础断语[/]",
        border_style="red",
        padding=(1, 2),
    )

    console.print(summary_panel)
    console.print()


def select_question_type() -> str:
    """让用户选择问事类型。"""
    console.print()
    console.print(Panel.fit("[bold]请问卜何事？[/]", border_style="cyan", padding=(0, 2)))

    menu_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    menu_table.add_column(width=4, justify="center")
    menu_table.add_column(width=8)
    menu_table.add_column()

    for key, (name, desc) in QUESTION_TYPES.items():
        menu_table.add_row(f"[bold]{key}[/]", f"[cyan]{name}[/]", desc)

    console.print(menu_table)
    console.print()

    while True:
        choice = input("请输入编号（1-9，直接回车默认1通用）：").strip()
        if choice == "":
            choice = "1"
        if choice in QUESTION_TYPES:
            name, _ = QUESTION_TYPES[choice]
            console.print(f"[green]✓[/] 已选择：{name}")
            return name
        console.print("[red]无效输入，请重新选择[/]")


def main():
    console.print("[bold yellow]正在获取位置信息...[/]")

    # 获取位置
    location = get_location()
    console.print(f"[green]✓[/] 位置：{location.city}（东经{location.longitude}°）")

    # 获取当前时间（北京时间 UTC+8）
    tz_cn = timezone(timedelta(hours=8))
    now = datetime.now(tz_cn)
    console.print(f"[green]✓[/] 当前时间：{now.strftime('%Y-%m-%d %H:%M')}")

    # 获取干支信息
    gzdt = get_ganzhi_for_datetime(now, location.longitude)

    # 获取真太阳时
    tst = get_true_solar_time(now, location.longitude)

    console.print(f"[green]✓[/] 真太阳时：{tst.dt.strftime('%H:%M')}（{gzdt.hour_ganzhi}时）")

    # 选择问事类型
    question_type = select_question_type()

    # 构建课盘
    panju = build_panju(gzdt, tst.dt)

    # 断课（传入问事类型）
    result = duanke(panju, question_type=question_type)

    # 输出
    print_panju(panju, result, location)


if __name__ == "__main__":
    main()
