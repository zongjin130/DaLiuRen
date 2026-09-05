"""IP定位模块：通过网络获取用户经纬度和城市信息。"""

import requests
from dataclasses import dataclass


@dataclass
class Location:
    city: str
    longitude: float
    latitude: float


def get_location(timeout: int = 5) -> Location:
    """通过IP获取当前位置（经纬度和城市名）。

    优先使用 ip-api.com，失败则使用默认值（北京）。
    """
    try:
        resp = requests.get(
            "http://ip-api.com/json/?lang=zh-CN&fields=status,country,regionName,city,lat,lon",
            timeout=timeout,
        )
        data = resp.json()
        if data.get("status") == "success":
            city = f"{data.get('regionName', '')}{data.get('city', '')}"
            return Location(
                city=city or "未知城市",
                longitude=float(data["lon"]),
                latitude=float(data["lat"]),
            )
    except Exception:
        pass

    # 默认北京
    return Location(city="北京", longitude=116.4, latitude=39.9)
