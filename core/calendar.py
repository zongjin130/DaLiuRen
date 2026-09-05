"""历法计算：真太阳时、节气、月将、干支。"""

import math
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import cnlunar
from .ganzhi import TIAN_GAN, DI_ZHI


# 节气 → 月将映射（中气换将）
JIEQI_TO_YUEJIANG = {
    "雨水": ("亥", "亥将"), "春分": ("戌", "戌将"),
    "谷雨": ("酉", "酉将"), "小满": ("申", "申将"),
    "夏至": ("未", "未将"), "大暑": ("午", "午将"),
    "处暑": ("巳", "巳将"), "秋分": ("辰", "辰将"),
    "霜降": ("卯", "卯将"), "小雪": ("寅", "寅将"),
    "冬至": ("丑", "丑将"), "大寒": ("子", "子将"),
}



@dataclass
class GanZhiDateTime:
    year_gan: str
    year_zhi: str
    month_gan: str
    month_zhi: str
    day_gan: str
    day_zhi: str
    hour_gan: str
    hour_zhi: str
    year_ganzhi: str
    month_ganzhi: str
    day_ganzhi: str
    hour_ganzhi: str
    lunar_month: int
    lunar_day: int
    yuejiang: str       # 月将地支
    yuejiang_name: str  # 月将名
    jieqi: str          # 当前中气


@dataclass
class TrueSolarTime:
    dt: datetime
    hour_zhi: str
    hour_zhi_index: int


def get_true_solar_time(local_dt: datetime, longitude: float) -> TrueSolarTime:
    """将本地时间换算为真太阳时，并确定时辰。"""
    day_of_year = local_dt.timetuple().tm_yday
    B = 2 * math.pi * (day_of_year - 81) / 365
    eot = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)

    lng_correction = (longitude - 120) * 4
    total_correction = timedelta(minutes=lng_correction + eot)
    true_solar_dt = local_dt + total_correction

    hour = true_solar_dt.hour
    minute = true_solar_dt.minute
    total_minutes = hour * 60 + minute

    zhi_index = ((total_minutes + 60) // 120) % 12
    hour_zhi = DI_ZHI[zhi_index]

    return TrueSolarTime(dt=true_solar_dt, hour_zhi=hour_zhi, hour_zhi_index=zhi_index)


def get_yuejiang(dt: datetime) -> tuple:
    """根据日期确定当前月将。直接使用 cnlunar 的节气名称。

    Returns:
        (月将地支, 月将名, 当前中气名)
    """
    dt_naive = dt.replace(tzinfo=None)
    lunar = cnlunar.Lunar(dt_naive)

    # thisYearSolarTermsDic: {节气名: (month, day), ...}
    terms_dict = lunar.thisYearSolarTermsDic

    # 找到当前日期之前最近的中气
    current_zhongqi = None
    current_zhongqi_date = None

    for name, (month, day) in terms_dict.items():
        if name not in JIEQI_TO_YUEJIANG:
            continue

        term_date = datetime(dt.year, month, day)
        if term_date <= dt_naive:
            if current_zhongqi_date is None or term_date > current_zhongqi_date:
                current_zhongqi = name
                current_zhongqi_date = term_date

    if current_zhongqi and current_zhongqi in JIEQI_TO_YUEJIANG:
        zhi, name = JIEQI_TO_YUEJIANG[current_zhongqi]
        return zhi, name, current_zhongqi

    # 默认：冬至后用丑将
    return "丑", "丑将", "冬至"


def get_ganzhi_for_datetime(dt: datetime, longitude: float) -> GanZhiDateTime:
    """获取指定时间的干支信息。"""
    # 先换算真太阳时
    tst = get_true_solar_time(dt, longitude)

    # 使用 cnlunar 获取干支（用真太阳时的日期）
    # cnlunar 需要 naive datetime
    tst_naive = tst.dt.replace(tzinfo=None)
    lunar = cnlunar.Lunar(tst_naive)

    year_gan = TIAN_GAN[lunar.yearHeavenNum]
    year_zhi = DI_ZHI[lunar.yearEarthNum]
    month_gan = TIAN_GAN[lunar.monthHeavenNum]
    month_zhi = DI_ZHI[lunar.monthEarthNum]
    day_gan = TIAN_GAN[lunar.dayHeavenNum]
    day_zhi = DI_ZHI[lunar.dayEarthNum]

    # cnlunar 的 twohourNum 给出时辰地支索引
    # 23:xx 时 twohourNum=12，需要 mod 12 防止越界
    hour_zhi = DI_ZHI[lunar.twohourNum % 12]
    # 时干需要根据日干和时辰推算（五鼠遁日起时法）
    hour_gan = _calc_hour_gan(day_gan, hour_zhi)

    lunar_month = lunar.lunarMonth
    lunar_day = lunar.lunarDay
    # 子时（23:00-23:59）农历日期需加一天
    if lunar.twohourNum == 12:
        lunar_day += 1
        # 简单处理：不考虑月末换月（cnlunar 内部已有类似逻辑）

    # 确定月将
    yuejiang_zhi, yuejiang_name, jieqi = get_yuejiang(tst.dt)

    return GanZhiDateTime(
        year_gan=year_gan, year_zhi=year_zhi,
        month_gan=month_gan, month_zhi=month_zhi,
        day_gan=day_gan, day_zhi=day_zhi,
        hour_gan=hour_gan, hour_zhi=hour_zhi,
        year_ganzhi=f"{year_gan}{year_zhi}",
        month_ganzhi=f"{month_gan}{month_zhi}",
        day_ganzhi=f"{day_gan}{day_zhi}",
        hour_ganzhi=f"{hour_gan}{hour_zhi}",
        lunar_month=lunar_month, lunar_day=lunar_day,
        yuejiang=yuejiang_zhi, yuejiang_name=yuejiang_name,
        jieqi=jieqi,
    )


def _calc_hour_gan(day_gan: str, hour_zhi: str) -> str:
    """五鼠遁日起时法：根据日干推算时干。

    甲己还加甲，乙庚丙作初，丙辛从戊起，丁壬庚子居，戊癸何方发，壬子是真途。
    """
    day_gan_idx = TIAN_GAN.index(day_gan)
    hour_zhi_idx = DI_ZHI.index(hour_zhi)

    # 日干对应的子时天干
    # 甲(0)/己(5) → 甲(0), 乙(1)/庚(6) → 丙(2), 丙(2)/辛(7) → 戊(4), 丁(3)/壬(8) → 庚(6), 戊(4)/癸(9) → 壬(8)
    base = [0, 2, 4, 6, 8, 0, 2, 4, 6, 8]
    start_gan = base[day_gan_idx]

    hour_gan_idx = (start_gan + hour_zhi_idx) % 10
    return TIAN_GAN[hour_gan_idx]
