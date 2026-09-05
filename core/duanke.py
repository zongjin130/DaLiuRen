"""基础断课：旺衰分析、吉凶判断。"""

from dataclasses import dataclass, field

from .ganzhi import (
    DI_ZHI, ZHI_WUXING, GAN_WUXING, GAN_JIGONG,
    WUXING_KE, WUXING_SHENG, LIU_CHONG, LIU_HE,
    get_zhi_index,
)
from .panju import PanJu


# 问事类型列表
QUESTION_TYPES = {
    "1": ("通用", "不指定具体事项，以日干为用神看整体运势"),
    "2": ("财运", "问求财、投资、生意等"),
    "3": ("事业", "问升职、调动、工作、考试等"),
    "4": ("感情", "问恋爱、婚姻、桃花等"),
    "5": ("健康", "问疾病、身体状况等"),
    "6": ("出行", "问旅行、出差、搬迁等"),
    "7": ("失物", "问丢失物品能否找回"),
    "8": ("诉讼", "问官司、纠纷、是非等"),
    "9": ("家宅", "问搬家、装修、风水等"),
}

# 月令五行旺衰
MONTH_WANG = {
    "寅": "木", "卯": "木", "辰": "土",
    "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土",
    "亥": "水", "子": "水", "丑": "土",
}

WUXING_STATUS_IN_MONTH = {
    "木": {"木": "旺", "火": "相", "水": "休", "金": "囚", "土": "死"},
    "火": {"火": "旺", "土": "相", "木": "休", "水": "囚", "金": "死"},
    "土": {"土": "旺", "金": "相", "火": "休", "木": "囚", "水": "死"},
    "金": {"金": "旺", "水": "相", "土": "休", "火": "囚", "木": "死"},
    "水": {"水": "旺", "木": "相", "金": "休", "土": "囚", "火": "死"},
}

# 天将吉凶
TIANGUIANG_JIXIONG = {
    "贵人": "吉", "腾蛇": "凶", "朱雀": "凶", "六合": "吉",
    "勾陈": "凶", "青龙": "吉", "天空": "凶", "白虎": "凶",
    "太常": "吉", "玄武": "凶", "太阴": "吉", "天后": "吉",
}

# 问事类型 → 六亲取用 + 相关天将 + 断语提示
QUESTION_YONGSHEN = {
    "通用": {
        "yongshen_type": "日干",
        "related_tiangiang": [],
        "prompt": "以日干为用神，看整体运势",
    },
    "财运": {
        "yongshen_type": "财",  # 日干所克之五行
        "related_tiangiang": ["青龙", "太常"],  # 青龙主财喜，太常主财帛
        "prompt": "财爻旺相则利求财，财爻衰败则不利",
    },
    "事业": {
        "yongshen_type": "官",  # 克日干之五行
        "related_tiangiang": ["贵人", "青龙"],  # 贵人主贵人相助
        "prompt": "官爻旺相则利升迁，官爻衰败则不利",
    },
    "感情": {
        "yongshen_type": "财官",  # 男看财（我克），女看官（克我）
        "related_tiangiang": ["天后", "六合"],  # 天后主女性，六合主婚姻
        "prompt": "天后六合旺相则感情顺遂",
    },
    "健康": {
        "yongshen_type": "日干",
        "related_tiangiang": ["白虎", "腾蛇"],  # 白虎主疾病凶险，腾蛇主惊恐
        "prompt": "日干旺相则身体尚可，白虎腾蛇临用则需注意",
    },
    "出行": {
        "yongshen_type": "日干",
        "related_tiangiang": ["青龙", "六合"],  # 青龙主出行吉利
        "prompt": "初传吉将旺相则出行顺利",
    },
    "失物": {
        "yongshen_type": "财",  # 失物多取财爻
        "related_tiangiang": ["玄武", "天空"],  # 玄武主盗窃遗失
        "prompt": "财爻旺相在课中可见则可找回",
    },
    "诉讼": {
        "yongshen_type": "官",
        "related_tiangiang": ["勾陈", "朱雀"],  # 勾陈主争斗，朱雀主口舌文书
        "prompt": "官爻旺相克我则不利，我旺克官则有利",
    },
    "家宅": {
        "yongshen_type": "父母",  # 生日干之五行
        "related_tiangiang": ["六合", "太阴"],  # 六合主家宅
        "prompt": "父母爻旺相则家宅安稳",
    },
}


@dataclass
class DuanKeResult:
    """断课结果"""
    question_type: str      # 问事类型
    yongshen: str            # 用神（五行名）
    yongshen_wuxing: str     # 用神五行
    yongshen_status: str     # 用神旺衰状态
    chu_tianjiang: str
    chu_jixiong: str
    zhong_tianjiang: str
    zhong_jixiong: str
    mo_tianjiang: str
    mo_jixiong: str
    summary: str
    details: list


def get_wuxing_status(wuxing: str, month_zhi: str) -> str:
    """判断某五行在当月的旺衰状态。"""
    month_wx = MONTH_WANG.get(month_zhi, "土")
    return WUXING_STATUS_IN_MONTH.get(month_wx, {}).get(wuxing, "平")


def get_yongshen_by_type(day_gan: str, question_type: str) -> tuple:
    """根据问事类型确定用神。

    六亲取用：
    - 财：日干所克之五行（我克者为财）
    - 官：克日干之五行（克我者为官鬼）
    - 父母：生日干之五行（生我者为父母）
    - 子孙：日干所生之五行（我生者为子孙）
    - 比劫：与日干同五行

    Returns:
        (用神五行名, 用神类型描述)
    """
    day_wx = GAN_WUXING[day_gan]
    config = QUESTION_YONGSHEN.get(question_type, QUESTION_YONGSHEN["通用"])
    yongshen_type = config["yongshen_type"]

    if yongshen_type == "日干":
        return day_wx, "日干本身"
    elif yongshen_type == "财":
        # 我克者为财
        for wx, target in WUXING_KE.items():
            if wx == day_wx:
                return target, f"财爻（{day_wx}克{target}）"
        return day_wx, "财爻"
    elif yongshen_type == "官":
        # 克我者为官
        for wx, target in WUXING_KE.items():
            if target == day_wx:
                return wx, f"官爻（{wx}克{day_wx}）"
        return day_wx, "官爻"
    elif yongshen_type == "父母":
        # 生我者为父母
        for wx, target in WUXING_SHENG.items():
            if target == day_wx:
                return wx, f"父母爻（{wx}生{day_wx}）"
        return day_wx, "父母爻"
    elif yongshen_type == "子孙":
        # 我生者为子孙
        target = WUXING_SHENG.get(day_wx, day_wx)
        return target, f"子孙爻（{day_wx}生{target}）"
    elif yongshen_type == "财官":
        # 感情类：默认取财爻（男看财），同时参考官爻
        for wx, target in WUXING_KE.items():
            if wx == day_wx:
                return target, f"财爻/对象（{day_wx}克{target}）"
        return day_wx, "财爻"
    else:
        return day_wx, "日干本身"


def find_yongshen_in_sike(panju: PanJu, yongshen_wx: str) -> list:
    """在四课中寻找用神（五行匹配的上神或下神）。"""
    sike = panju.sike
    found = []
    classes = [
        ("第一课", sike.ke1_xia, sike.ke1_shang),
        ("第二课", sike.ke2_xia, sike.ke2_shang),
        ("第三课", sike.ke3_xia, sike.ke3_shang),
        ("第四课", sike.ke4_xia, sike.ke4_shang),
    ]
    for name, xia, shang in classes:
        if ZHI_WUXING[xia] == yongshen_wx:
            found.append(f"{name}下神{xia}（{ZHI_WUXING[xia]}）")
        if ZHI_WUXING[shang] == yongshen_wx:
            found.append(f"{name}上神{shang}（{ZHI_WUXING[shang]}）")
    return found


def find_yongshen_in_sanchuan(panju: PanJu, yongshen_wx: str) -> list:
    """在三传中寻找用神。"""
    sc = panju.sanchuan
    found = []
    for name, zhi in [("初传", sc.chu), ("中传", sc.zhong), ("末传", sc.mo)]:
        if ZHI_WUXING[zhi] == yongshen_wx:
            found.append(f"{name}{zhi}（{ZHI_WUXING[zhi]}）")
    return found


def analyze_sanchuan_trend(panju: PanJu) -> str:
    """分析三传趋势。"""
    sc = panju.sanchuan
    chu_wx = ZHI_WUXING[sc.chu]
    zhong_wx = ZHI_WUXING[sc.zhong]
    mo_wx = ZHI_WUXING[sc.mo]

    trends = []

    if WUXING_SHENG[chu_wx] == zhong_wx:
        trends.append("初传生中传，事有进展")
    elif WUXING_KE[chu_wx] == zhong_wx:
        trends.append("初传克中传，中途有阻")
    elif WUXING_SHENG[zhong_wx] == chu_wx:
        trends.append("中传生初传，得助")
    elif WUXING_KE[zhong_wx] == chu_wx:
        trends.append("中传克初传，事有反复")

    if WUXING_SHENG[zhong_wx] == mo_wx:
        trends.append("中传生末传，结局向好")
    elif WUXING_KE[zhong_wx] == mo_wx:
        trends.append("中传克末传，结局受阻")
    elif WUXING_SHENG[mo_wx] == zhong_wx:
        trends.append("末传生中传，终有回报")
    elif WUXING_KE[mo_wx] == zhong_wx:
        trends.append("末传克中传，虎头蛇尾")

    if not trends:
        trends.append("三传五行平和")

    return "；".join(trends)


def duanke(panju: PanJu, question_type: str = "通用") -> DuanKeResult:
    """基础断课。

    Args:
        panju: 课盘
        question_type: 问事类型（通用/财运/事业/感情/健康/出行/失物/诉讼/家宅）
    """
    day_gan = panju.gzdt.day_gan
    month_zhi = panju.gzdt.month_zhi

    # 根据问事类型确定用神
    yongshen_wx, yongshen_desc = get_yongshen_by_type(day_gan, question_type)
    yongshen_status = get_wuxing_status(yongshen_wx, month_zhi)

    # 在四课和三传中寻找用神
    sike_hits = find_yongshen_in_sike(panju, yongshen_wx)
    sanchuan_hits = find_yongshen_in_sanchuan(panju, yongshen_wx)

    # 三传天将
    chu_tj = panju.guiren.tianjiang_map.get(panju.sanchuan.chu, "无")
    zhong_tj = panju.guiren.tianjiang_map.get(panju.sanchuan.zhong, "无")
    mo_tj = panju.guiren.tianjiang_map.get(panju.sanchuan.mo, "无")

    chu_jx = TIANGUIANG_JIXIONG.get(chu_tj, "平")
    zhong_jx = TIANGUIANG_JIXIONG.get(zhong_tj, "平")
    mo_jx = TIANGUIANG_JIXIONG.get(mo_tj, "平")

    # 相关天将
    config = QUESTION_YONGSHEN.get(question_type, QUESTION_YONGSHEN["通用"])
    related_tj = config["related_tiangiang"]

    # === 分析详情 ===
    details = []

    # 1. 用神说明
    details.append(f"问事类型：{question_type}")
    details.append(f"用神：{yongshen_desc}，五行属{yongshen_wx}")

    # 2. 用神旺衰
    if yongshen_status == "旺":
        details.append(f"用神{yongshen_wx}在{month_zhi}月当令，旺相有力，根基稳固")
    elif yongshen_status == "相":
        details.append(f"用神{yongshen_wx}在{month_zhi}月得相气，有气可用")
    elif yongshen_status == "休":
        details.append(f"用神{yongshen_wx}在{month_zhi}月处休地，力量不足")
    elif yongshen_status == "囚":
        details.append(f"用神{yongshen_wx}在{month_zhi}月被囚，受制无力")
    elif yongshen_status == "死":
        details.append(f"用神{yongshen_wx}在{month_zhi}月处死地，极弱无气")

    # 3. 用神在四课中的位置
    if sike_hits:
        details.append(f"用神在四课中：{'、'.join(sike_hits)}")
    else:
        details.append("用神未现于四课，事未明")

    # 4. 用神在三传中的位置
    if sanchuan_hits:
        details.append(f"用神在三传中：{'、'.join(sanchuan_hits)}")
    else:
        details.append("用神未入三传，事之过程与用神无直接关联")

    # 5. 三传趋势
    trend = analyze_sanchuan_trend(panju)
    details.append(f"三传趋势：{trend}")

    # 6. 三传天将吉凶
    details.append(f"初传{panju.sanchuan.chu}乘{chu_tj}（{chu_jx}）")
    details.append(f"中传{panju.sanchuan.zhong}乘{zhong_tj}（{zhong_jx}）")
    details.append(f"末传{panju.sanchuan.mo}乘{mo_tj}（{mo_jx}）")

    # 7. 相关天将分析
    for tj in related_tj:
        for zhi in DI_ZHI:
            if panju.guiren.tianjiang_map.get(zhi) == tj:
                jx = TIANGUIANG_JIXIONG.get(tj, "平")
                details.append(f"{tj}（{jx}）在{zhi}位")
                break

    # 8. 贵人分析
    details.append(f"贵人在{panju.guiren.guiren_zhi}（{panju.guiren.guiren_dir}行）")

    # === 综合判断 ===
    ji_count = sum(1 for jx in [chu_jx, zhong_jx, mo_jx] if jx == "吉")
    xiong_count = sum(1 for jx in [chu_jx, zhong_jx, mo_jx] if jx == "凶")

    summary_parts = []

    # 用神旺衰
    if yongshen_status in ("旺", "相"):
        summary_parts.append("用神有力")
    else:
        summary_parts.append("用神无力")

    # 用神是否出现
    if sike_hits or sanchuan_hits:
        summary_parts.append("用神可见")
    else:
        summary_parts.append("用神不现")

    # 天将吉凶
    if ji_count > xiong_count:
        summary_parts.append("天将吉多凶少")
    elif ji_count < xiong_count:
        summary_parts.append("天将凶多吉少")
    else:
        summary_parts.append("天将吉凶参半")

    # 综合结论
    yongshen_ok = yongshen_status in ("旺", "相")
    yongshen_visible = bool(sike_hits or sanchuan_hits)
    tiangjiang_ok = ji_count >= xiong_count

    if yongshen_ok and yongshen_visible and tiangjiang_ok:
        conclusion = f"总体判断（{question_type}）：事可成，宜积极进取。"
    elif not yongshen_ok and xiong_count > ji_count:
        conclusion = f"总体判断（{question_type}）：事难成，宜谨慎守成。"
    elif not yongshen_visible:
        conclusion = f"总体判断（{question_type}）：用神不现，事尚不明，宜观望。"
    else:
        conclusion = f"总体判断（{question_type}）：事有波折，需审时度势。"

    summary = conclusion + "，".join(summary_parts)

    return DuanKeResult(
        question_type=question_type,
        yongshen=yongshen_wx,
        yongshen_wuxing=yongshen_wx,
        yongshen_status=yongshen_status,
        chu_tianjiang=chu_tj,
        chu_jixiong=chu_jx,
        zhong_tianjiang=zhong_tj,
        zhong_jixiong=zhong_jx,
        mo_tianjiang=mo_tj,
        mo_jixiong=mo_jx,
        summary=summary,
        details=details,
    )
