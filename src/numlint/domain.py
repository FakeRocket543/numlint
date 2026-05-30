"""Domain-specific number validation: semiconductor, weather, calendar, air quality.

Validates that numbers in translated text fall within physically plausible ranges
and catches common conversion errors.
"""
import re
from datetime import datetime


# ── Semiconductor process nodes ──

_VALID_NODES_NM = {3, 4, 5, 7, 10, 12, 14, 16, 20, 22, 28, 32, 40, 45, 55, 65, 90, 130, 180, 250, 350}

def verify_semiconductor(zh_body: str) -> list[tuple[str, str, str]]:
    """Check semiconductor process references for plausibility."""
    issues = []
    
    # Pattern: Xnm / X奈米 / X納米
    for m in re.finditer(r'(\d+)\s*(?:nm|奈米|納米|纳米)', zh_body):
        val = int(m.group(1))
        if val not in _VALID_NODES_NM and val < 500:
            # Check if it's close to a valid node
            closest = min(_VALID_NODES_NM, key=lambda x: abs(x - val))
            if abs(val - closest) <= 2:
                issues.append(("warn", f"製程節點 {val}nm 可能應為 {closest}nm", "確認製程"))
            elif val > 0 and val < 2:
                issues.append(("warn", f"製程 {val}nm 尚未量產（目前最先進為 2-3nm）", "確認數字"))
    
    # Catch: nm 被翻成公尺/公里
    if re.search(r'\d+\s*(?:公尺|公里).*(?:製程|晶片|芯片|處理器|CPU|GPU)', zh_body):
        issues.append(("error", "製程單位疑似被翻成公尺/公里（應為奈米 nm）", "確認單位"))
    
    return issues


# ── Weather / Meteorology ──

_RANGES = {
    'temp_c': (-90, 60),       # °C on Earth
    'temp_f': (-130, 140),     # °F
    'pressure_hpa': (870, 1085),  # hPa (record low ~870, high ~1084)
    'rainfall_mm': (0, 1000),  # mm per event (record ~1825mm/day)
    'wind_kmh': (0, 410),      # km/h (record ~407)
    'wind_ms': (0, 115),       # m/s
    'humidity': (0, 100),      # %
}

def verify_weather(zh_body: str) -> list[tuple[str, str, str]]:
    """Validate weather numbers for physical plausibility."""
    issues = []
    
    # Temperature
    for m in re.finditer(r'(?:氣溫|溫度|高溫|低溫)[^\d]{0,10}?(-?\d+\.?\d*)\s*(?:度|°C|℃|攝氏)', zh_body):
        val = float(m.group(1))
        if val < -90 or val > 60:
            issues.append(("warn", f"溫度 {val}°C 超出地球紀錄範圍", "確認溫度"))
        elif val > 50:
            issues.append(("info", f"溫度 {val}°C 極端高溫，確認是否正確", ""))
    
    # Check if Fahrenheit leaked as Celsius
    for m in re.finditer(r'(?:氣溫|溫度|高溫)[^\d]{0,10}?(\d+)\s*度', zh_body):
        val = int(m.group(1))
        if 100 <= val <= 130:  # Likely °F not converted
            celsius = (val - 32) * 5 / 9
            issues.append(("warn", f"溫度 {val}度 疑似華氏未轉換（應為{celsius:.0f}°C）", "確認攝氏/華氏"))
    
    # Pressure
    for m in re.finditer(r'(\d+\.?\d*)\s*(?:hPa|百帕|毫巴)', zh_body):
        val = float(m.group(1))
        if val < 870 or val > 1085:
            issues.append(("warn", f"氣壓 {val}hPa 超出正常範圍 (870-1085)", "確認氣壓"))
    
    # Wind speed
    for m in re.finditer(r'風速[^\d]{0,5}?(\d+\.?\d*)\s*(?:公里|km)', zh_body):
        val = float(m.group(1))
        if val > 410:
            issues.append(("warn", f"風速 {val}km/h 超出地球紀錄 (≤407)", "確認風速"))
    
    # Rainfall
    for m in re.finditer(r'(?:降雨|雨量|降水)[^\d]{0,10}?(\d+\.?\d*)\s*(?:毫米|mm|公釐)', zh_body):
        val = float(m.group(1))
        if val > 1000:
            issues.append(("warn", f"降雨 {val}mm 極端值，確認時間範圍", ""))
    
    return issues


# ── Calendar / Era conversion ──

_CURRENT_YEAR = datetime.now().year

# Era offsets (era_year + offset = western_year)
_ERA_OFFSETS = {
    '民國': 1911,    # 民國115年 = 2026
    '令和': 2018,    # 令和8年 = 2026
    '佛曆': -543,   # 佛曆2569 = 2026
    '伊斯蘭曆': 579, # Approximate (Islamic calendar is lunar)
}

def verify_calendar(source_texts: list[str], zh_body: str) -> list[tuple[str, str, str]]:
    """Cross-check year references between source and Chinese output."""
    issues = []
    
    # Check: 民國 year mentioned
    for m in re.finditer(r'民國\s*(\d+)\s*年', zh_body):
        minguo = int(m.group(1))
        western = minguo + 1911
        if abs(western - _CURRENT_YEAR) > 5:
            issues.append(("warn", f"民國{minguo}年 = 西元{western}年，確認是否正確", ""))
    
    # Check: source has Buddhist era (Thai news)
    src_combined = " ".join(source_texts)
    for m in re.finditer(r'พ\.ศ\.\s*(\d{4})|B\.E\.\s*(\d{4})', src_combined):
        be_year = int(m.group(1) or m.group(2))
        western = be_year - 543
        # Check if zh mentions the wrong year
        if str(be_year) in zh_body:
            issues.append(("warn", f"佛曆 {be_year} 未轉換為西元 {western}", "確認年份"))
    
    # Check: source has Islamic calendar (Hijri)
    for m in re.finditer(r'(\d{4})\s*(?:هـ|AH|Hijri)', src_combined):
        hijri = int(m.group(1))
        # Approximate conversion
        western_approx = hijri + 579
        if str(hijri) in zh_body and western_approx > 2000:
            issues.append(("warn", f"伊斯蘭曆 {hijri} 未轉換為約西元 {western_approx}", "確認年份"))
    
    # Check: Japanese era
    for m in re.finditer(r'令和\s*(\d+)\s*年', zh_body):
        reiwa = int(m.group(1))
        western = reiwa + 2018
        if abs(western - _CURRENT_YEAR) > 2:
            issues.append(("warn", f"令和{reiwa}年 = 西元{western}年，確認年份", ""))
    
    return issues


# ── Air Quality ──

def verify_air_quality(zh_body: str) -> list[tuple[str, str, str]]:
    """Validate air quality numbers."""
    issues = []
    
    # PM2.5: normal 0-500 μg/m³
    for m in re.finditer(r'PM\s*2\.?5[^\d]{0,10}?(\d+\.?\d*)\s*(?:μg|微克)?', zh_body):
        val = float(m.group(1))
        if val > 500:
            issues.append(("warn", f"PM2.5 = {val}，超出 AQI 量表上限 (0-500)", "確認數值"))
    
    # AQI: 0-500
    for m in re.finditer(r'AQI[^\d]{0,5}?(\d+)', zh_body):
        val = int(m.group(1))
        if val > 500:
            issues.append(("warn", f"AQI = {val}，超出標準量表 (0-500)", "確認數值"))
    
    return issues


# ── Combined verification ──

def verify_domain(source_texts: list[str], zh_body: str) -> list[tuple[str, str, str]]:
    """Run all domain-specific checks."""
    issues = []
    issues.extend(verify_semiconductor(zh_body))
    issues.extend(verify_weather(zh_body))
    issues.extend(verify_calendar(source_texts, zh_body))
    issues.extend(verify_air_quality(zh_body))
    return issues


if __name__ == "__main__":
    print("═══ Domain verification tests ═══\n")
    
    # Semiconductor
    issues = verify_semiconductor("台積電宣布量產2奈米製程")
    print(f"Semi (2nm 未量產): {'✅' if issues else '❌'} {issues[0][1] if issues else ''}")
    
    issues = verify_semiconductor("新處理器採用5奈米製程")
    print(f"Semi (5nm OK): {'✅ clean' if not issues else '❌'}")
    
    # Weather
    issues = verify_weather("鳳凰城氣溫達到104度")
    print(f"Weather (104度=°F): {'✅' if issues else '❌'} {issues[0][1][:40] if issues else ''}")
    
    issues = verify_weather("今日高溫38度")
    print(f"Weather (38°C OK): {'✅ clean' if not issues else '❌'}")
    
    # Calendar
    issues = verify_calendar(["พ.ศ. 2569"], "事件發生在2569年")
    print(f"Calendar (佛曆未轉): {'✅' if issues else '❌'} {issues[0][1][:40] if issues else ''}")
    
    # Air quality
    issues = verify_air_quality("該地區 PM2.5 達到 800 微克")
    print(f"AQI (PM2.5=800): {'✅' if issues else '❌'} {issues[0][1][:40] if issues else ''}")
