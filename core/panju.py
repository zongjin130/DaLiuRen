"""课盘核心：天地盘、四课、三传、贵人、十二天将。"""

from dataclasses import dataclass, field
from .ganzhi import (
    DI_ZHI, TIAN_GAN, GAN_JIGONG, GAN_WUXING, ZHI_WUXING,
    GUIREN_GEJUE, GUIREN_SHUNNI, SHIER_TIANGUIANG,
    DAYTIME_HOURS, NIGHTTIME_HOURS,
    get_zhi_index, get_gan_index, is_ke, WUXING_KE, WUXING_SHENG,
    LIU_CHONG, LIU_HE, XING, YIMA, SANHE_NEXT,
    MENG, ZHONG as ZHONG_SET, JI,
)
from .calendar import GanZhiDateTime


@dataclass
class SiKe:
    """四课：每课有上神和下神"""
    # 第一课（干阳课）
    ke1_xia: str  # 下神（日干寄宫）
    ke1_shang: str  # 上神（天盘在日干寄宫位置的值）
    # 第二课（支阳课）
    ke2_xia: str
    ke2_shang: str
    # 第三课（干阴课）
    ke3_xia: str
    ke3_shang: str
    # 第四课（支阴课）
    ke4_xia: str
    ke4_shang: str


@dataclass
class SanChuan:
    """三传"""
    chu: str      # 初传
    zhong: str    # 中传
    mo: str       # 末传
    method: str   # 起法（九宗门中的哪一种）


@dataclass
class GuiRenTianJiang:
    """贵人和十二天将"""
    guiren_zhi: str      # 贵人所在地支
    guiren_dir: str      # 顺行/逆行
    tianjiang_map: dict = field(default_factory=dict)  # 地支 → 天将名


@dataclass
class PanJu:
    """完整课盘"""
    gzdt: GanZhiDateTime        # 干支时间
    tianpan: dict                # 天盘：地支 → 天盘值
    dipan: list                  # 地盘：固定顺序
    sike: SiKe                   # 四课
    sanchuan: SanChuan           # 三传
    guiren: GuiRenTianJiang     # 贵人天将
    true_solar_dt: object        # 真太阳时 datetime


def build_tianpan(yuejiang_zhi: str, shichen_zhi: str) -> dict:
    """布天盘：月将加占时。

    规则：将月将放在占时的位置上，然后顺时针依次排布。
    例如：月将=申，占时=午，则：
    - 地盘午位 → 天盘申
    - 地盘未位 → 天盘酉
    - 地盘申位 → 天盘戌
    - ...依次类推
    """
    yuejiang_idx = get_zhi_index(yuejiang_zhi)
    shichen_idx = get_zhi_index(shichen_zhi)

    # 偏移量：月将索引 - 占时索引
    offset = yuejiang_idx - shichen_idx

    tianpan = {}
    for i, zhi in enumerate(DI_ZHI):
        # 天盘位置 = (地盘索引 + 偏移) mod 12
        tianpan[zhi] = DI_ZHI[(i + offset) % 12]

    return tianpan


def build_sike(day_gan: str, day_zhi: str, tianpan: dict) -> SiKe:
    """取四课。

    第一课：日干寄宫为下神，天盘在该位为上神
    第二课：日支为下神，天盘在该位为上神
    第三课：第一课上神为下神，天盘在该位为上神
    第四课：第二课上神为下神，天盘在该位为上神
    """
    # 日干寄宫
    gan_jigong = GAN_JIGONG[day_gan]

    # 第一课
    ke1_xia = gan_jigong
    ke1_shang = tianpan[gan_jigong]

    # 第二课
    ke2_xia = day_zhi
    ke2_shang = tianpan[day_zhi]

    # 第三课
    ke3_xia = ke1_shang
    ke3_shang = tianpan[ke1_shang]

    # 第四课
    ke4_xia = ke2_shang
    ke4_shang = tianpan[ke2_shang]

    return SiKe(
        ke1_xia=ke1_xia, ke1_shang=ke1_shang,
        ke2_xia=ke2_xia, ke2_shang=ke2_shang,
        ke3_xia=ke3_xia, ke3_shang=ke3_shang,
        ke4_xia=ke4_xia, ke4_shang=ke4_shang,
    )


def _get_ke_candidates(sike: SiKe) -> tuple:
    """找出四课中所有的克关系。

    Returns:
        (下克上列表, 上克下列表)
        每个元素为 (课号, 下神, 上神)
    """
    xia_ke_shang = []  # 下克上
    shang_ke_xia = []  # 上克下

    classes = [
        (1, sike.ke1_xia, sike.ke1_shang),
        (2, sike.ke2_xia, sike.ke2_shang),
        (3, sike.ke3_xia, sike.ke3_shang),
        (4, sike.ke4_xia, sike.ke4_shang),
    ]

    for idx, xia, shang in classes:
        xia_wx = ZHI_WUXING[xia]
        shang_wx = ZHI_WUXING[shang]
        if WUXING_KE[xia_wx] == shang_wx:
            xia_ke_shang.append((idx, xia, shang))
        if WUXING_KE[shang_wx] == xia_wx:
            shang_ke_xia.append((idx, xia, shang))

    return xia_ke_shang, shang_ke_xia


def _check_same_yinyang(z1: str, z2: str) -> bool:
    """检查两个天干/地支是否同阴阳"""
    if z1 in TIAN_GAN:
        idx1 = TIAN_GAN.index(z1)
    else:
        idx1 = DI_ZHI.index(z1)
    if z2 in TIAN_GAN:
        idx2 = TIAN_GAN.index(z2)
    else:
        idx2 = DI_ZHI.index(z2)
    return idx1 % 2 == idx2 % 2


def _shehai_count(xia: str, shang: str, ke_dir: str) -> int:
    """涉害法：从下神地盘本位出发，沿地盘顺行到上神位置，数被克方所克的地支个数。

    ke_dir: 'xia_ke_shang' 或 'shang_ke_xia'。
    下克上时以克方(下神)的五行计数，上克下时以克方(上神)的五行计数。
    """
    xia_idx = get_zhi_index(xia)
    shang_idx = get_zhi_index(shang)
    if ke_dir == 'xia_ke_shang':
        ke_wx = ZHI_WUXING[xia]
    else:
        ke_wx = ZHI_WUXING[shang]

    count = 0
    current_idx = xia_idx
    while current_idx != shang_idx:
        current_zhi = DI_ZHI[current_idx]
        current_wx = ZHI_WUXING[current_zhi]
        if WUXING_KE.get(ke_wx) == current_wx:
            count += 1
        current_idx = (current_idx + 1) % 12

    return count


def _mengzhongji_rank(zhi: str) -> int:
    """孟仲季优先级：孟(0) > 仲(1) > 季(2)"""
    if zhi in MENG:
        return 0
    if zhi in ZHONG_SET:
        return 1
    return 2


def build_sanchuan(sike: SiKe, day_gan: str, day_zhi: str, tianpan: dict) -> SanChuan:
    """取三传：九宗门法。

    按优先级：
    1. 贼克法（下克上或上克下，且只有一个克）
    2. 比用法（多个克，取与日干同阴阳者）
    3. 涉害法（比用法无法区分时，取涉害深者）
    4. 遥克法（四课无克，看上神是否克日干或被日干克）
    5. 昴星法（无克无遥克）
    6. 别责法（无克无遥克，非八专）
    7. 八专法（日干支同位）
    8. 伏吟法（天地盘重合）
    9. 返吟法（天地盘对冲）
    """
    is_yang = get_gan_index(day_gan) % 2 == 0
    jigong = GAN_JIGONG[day_gan]

    # === 检测伏吟/返吟 ===
    is_fuyin = all(tianpan[z] == z for z in DI_ZHI)
    is_fanyin = all(tianpan[z] == LIU_CHONG[z] for z in DI_ZHI)

    # === 伏吟法 ===
    if is_fuyin:
        xia_ke_shang, shang_ke_xia = _get_ke_candidates(sike)
        candidates = xia_ke_shang if xia_ke_shang else shang_ke_xia
        if candidates:
            # 伏吟有克：按贼克法取初传，中传取刑，末传取冲
            _, xia, shang = candidates[0]
            chu = shang
            zhong = XING[chu]
            mo = LIU_CHONG[chu]
            return SanChuan(chu=chu, zhong=zhong, mo=mo, method="伏吟法（有克）")
        else:
            # 伏吟无克
            if is_yang:
                chu = tianpan[jigong]
            else:
                chu = tianpan[day_zhi]
            zhong = XING[chu]
            mo = LIU_CHONG[chu]
            return SanChuan(chu=chu, zhong=zhong, mo=mo, method="伏吟法")

    # === 返吟法 ===
    if is_fanyin:
        xia_ke_shang, shang_ke_xia = _get_ke_candidates(sike)
        candidates = xia_ke_shang if xia_ke_shang else shang_ke_xia
        if candidates:
            # 返吟有克：按贼克法取初传，中末传天盘递推
            _, xia, shang = candidates[0]
            chu = shang
            zhong = tianpan[chu]
            mo = tianpan[zhong]
            return SanChuan(chu=chu, zhong=zhong, mo=mo, method="返吟法（有克）")
        else:
            # 返吟无克：取驿马
            if is_yang:
                chu = tianpan[YIMA[day_zhi]]
            else:
                chu = tianpan[YIMA[jigong]]
            zhong = tianpan[chu]
            mo = tianpan[zhong]
            return SanChuan(chu=chu, zhong=zhong, mo=mo, method="返吟法")

    # === 常规九宗门 ===
    xia_ke_shang, shang_ke_xia = _get_ke_candidates(sike)

    # 优先下克上，其次上克下
    candidates = xia_ke_shang if xia_ke_shang else shang_ke_xia
    ke_dir = 'xia_ke_shang' if xia_ke_shang else 'shang_ke_xia'

    # === 1. 贼克法 ===
    if len(candidates) == 1:
        _, xia, shang = candidates[0]
        chu = shang
        zhong = tianpan[chu]
        mo = tianpan[zhong]
        return SanChuan(chu=chu, zhong=zhong, mo=mo, method="贼克法")

    # === 2. 比用法 + 3. 涉害法 ===
    if len(candidates) > 1:
        same_yinyang = []
        diff_yinyang = []
        for idx, xia, shang in candidates:
            if _check_same_yinyang(shang, day_gan):
                same_yinyang.append((idx, xia, shang))
            else:
                diff_yinyang.append((idx, xia, shang))

        if len(same_yinyang) == 1:
            _, xia, shang = same_yinyang[0]
            chu = shang
            zhong = tianpan[chu]
            mo = tianpan[zhong]
            return SanChuan(chu=chu, zhong=zhong, mo=mo, method="比用法")

        if len(same_yinyang) > 1:
            # 涉害法：取涉害深者，同数取孟仲季
            counts = []
            for idx, xia, shang in same_yinyang:
                c = _shehai_count(xia, shang, ke_dir)
                counts.append((c, idx, xia, shang))

            max_count = max(c[0] for c in counts)
            best_candidates = [c for c in counts if c[0] == max_count]

            if len(best_candidates) == 1:
                _, idx, xia, shang = best_candidates[0]
            else:
                # 同数取孟仲季
                best_candidates.sort(key=lambda c: _mengzhongji_rank(c[2]))
                _, idx, xia, shang = best_candidates[0]

            chu = shang
            zhong = tianpan[chu]
            mo = tianpan[zhong]
            return SanChuan(chu=chu, zhong=zhong, mo=mo, method="涉害法")

        if len(diff_yinyang) == 1:
            _, xia, shang = diff_yinyang[0]
            chu = shang
            zhong = tianpan[chu]
            mo = tianpan[zhong]
            return SanChuan(chu=chu, zhong=zhong, mo=mo, method="比用法")

    # === 4. 遥克法 ===
    day_gan_wx = GAN_WUXING[day_gan]
    yao_ke_candidates = []
    for idx, xia, shang in [
        (1, sike.ke1_xia, sike.ke1_shang),
        (2, sike.ke2_xia, sike.ke2_shang),
        (3, sike.ke3_xia, sike.ke3_shang),
        (4, sike.ke4_xia, sike.ke4_shang),
    ]:
        shang_wx = ZHI_WUXING[shang]
        if WUXING_KE.get(shang_wx) == day_gan_wx:
            yao_ke_candidates.append(("克日干", idx, xia, shang))
        elif WUXING_KE.get(day_gan_wx) == shang_wx:
            yao_ke_candidates.append(("日干克", idx, xia, shang))

    if yao_ke_candidates:
        ke_ri = [c for c in yao_ke_candidates if c[0] == "克日干"]
        ri_ke = [c for c in yao_ke_candidates if c[0] == "日干克"]

        target = ke_ri if ke_ri else ri_ke
        if len(target) == 1:
            _, idx, xia, shang = target[0]
            chu = shang
            zhong = tianpan[chu]
            mo = tianpan[zhong]
            method = "遥克法（蒿矢）" if ke_ri else "遥克法（弹射）"
            return SanChuan(chu=chu, zhong=zhong, mo=mo, method=method)

        if len(target) > 1:
            same = [c for c in target if _check_same_yinyang(c[3], day_gan)]
            if len(same) == 1:
                _, idx, xia, shang = same[0]
                chu = shang
                zhong = tianpan[chu]
                mo = tianpan[zhong]
                return SanChuan(chu=chu, zhong=zhong, mo=mo, method="遥克法")

    # === 5. 八专法 ===
    # 日干支同位 + 无克 + 无遥克
    # 八专日：甲寅, 丁未, 己未, 庚申, 壬亥, 癸丑
    is_bazhuan = (jigong == day_zhi)

    if is_bazhuan:
        if is_yang:
            chu = tianpan[jigong]
            zhong_idx = (get_zhi_index(chu) + 3) % 12
            mo_idx = (get_zhi_index(chu) - 3) % 12
        else:
            chu = tianpan[jigong]
            zhong_idx = (get_zhi_index(chu) - 3) % 12
            mo_idx = (get_zhi_index(chu) + 3) % 12
        zhong = DI_ZHI[zhong_idx]
        mo = DI_ZHI[mo_idx]
        return SanChuan(chu=chu, zhong=zhong, mo=mo, method="八专法")

    # 四课不备检测：上神有重复 → 别责法，无重复 → 昴星法
    shangs = [sike.ke1_shang, sike.ke2_shang, sike.ke3_shang, sike.ke4_shang]
    is_bubei = len(set(shangs)) < 4

    # === 6. 别责法 ===
    # 四课不备（上神有重复）+ 无克 + 无遥克 + 非八专
    if is_bubei:
        if is_yang:
            he_zhi = LIU_HE[jigong]
            chu = tianpan[he_zhi]
            zhong = he_zhi
            mo = he_zhi
        else:
            next_zhi = SANHE_NEXT[day_zhi]
            chu = tianpan[next_zhi]
            zhong = next_zhi
            mo = next_zhi
        return SanChuan(chu=chu, zhong=zhong, mo=mo, method="别责法")

    # === 7. 昴星法 ===
    # 四课完备（上神无重复）+ 无克 + 无遥克 + 非八专
    you_zhi = "酉"
    if is_yang:
        chu = tianpan[you_zhi]
        zhong = tianpan[day_zhi]
        mo = tianpan[jigong]
        method = "昴星法（虎视）"
    else:
        chu = tianpan[tianpan[you_zhi]]
        zhong = tianpan[jigong]
        mo = tianpan[day_zhi]
        method = "昴星法（冬蛇掩目）"
    return SanChuan(chu=chu, zhong=zhong, mo=mo, method=method)

    # === 7. 别责法 ===
    # 无克无遥克，非八专，非昴星（理论上不会到达此处，作为兜底）
    # 实际上别责法的条件是：四课无克、无遥克、非八专
    # 但昴星法已覆盖此情况，别责法仅在特定流派中独立使用


def build_guiren(day_gan: str, hour_zhi: str) -> GuiRenTianJiang:
    """起贵人并布十二天将。

    根据日干和时辰确定贵人位置，然后根据阴阳日顺逆排布十二天将。
    """
    # 确定昼占还是夜占
    is_daytime = hour_zhi in DAYTIME_HOURS

    # 从贵人歌诀取贵人位置
    guiren_positions = GUIREN_GEJUE.get(day_gan, ["丑", "未"])
    guiren_zhi = guiren_positions[0] if is_daytime else guiren_positions[1]

    # 确定顺逆
    direction = GUIREN_SHUNNI.get(day_gan, "顺")

    # 布十二天将
    guiren_idx = get_zhi_index(guiren_zhi)
    tianjiang_map = {}

    for i, tianjiang in enumerate(SHIER_TIANGUIANG):
        if direction == "顺":
            zhi_idx = (guiren_idx + i) % 12
        else:
            zhi_idx = (guiren_idx - i) % 12
        tianjiang_map[DI_ZHI[zhi_idx]] = tianjiang

    return GuiRenTianJiang(
        guiren_zhi=guiren_zhi,
        guiren_dir=direction,
        tianjiang_map=tianjiang_map,
    )


def build_panju(gzdt: GanZhiDateTime, true_solar_dt: object) -> PanJu:
    """构建完整课盘。"""
    # 1. 布天盘
    tianpan = build_tianpan(gzdt.yuejiang, gzdt.hour_zhi)

    # 地盘（固定）
    dipan = list(DI_ZHI)

    # 2. 取四课
    sike = build_sike(gzdt.day_gan, gzdt.day_zhi, tianpan)

    # 3. 取三传
    sanchuan = build_sanchuan(sike, gzdt.day_gan, gzdt.day_zhi, tianpan)

    # 4. 起贵人
    guiren = build_guiren(gzdt.day_gan, gzdt.hour_zhi)

    return PanJu(
        gzdt=gzdt,
        tianpan=tianpan,
        dipan=dipan,
        sike=sike,
        sanchuan=sanchuan,
        guiren=guiren,
        true_solar_dt=true_solar_dt,
    )
