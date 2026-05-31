"""Measurement unit extraction, verification and annotation.

Detects unit mismatches (miles written as km without conversion)
and annotates with metric equivalents.
"""
import re

# ── Conversion constants ──
_CONVERSIONS = {
    # Distance
    ('mile', 'km'): 1.60934,
    ('miles', 'km'): 1.60934,
    ('mi', 'km'): 1.60934,
    ('yard', 'm'): 0.9144,
    ('yards', 'm'): 0.9144,
    ('foot', 'm'): 0.3048,
    ('feet', 'm'): 0.3048,
    ('ft', 'm'): 0.3048,
    ('inch', 'cm'): 2.54,
    ('inches', 'cm'): 2.54,
    ('nautical mile', 'km'): 1.852,
    ('nm', 'km'): 1.852,
    # Weight
    ('pound', 'kg'): 0.453592,
    ('pounds', 'kg'): 0.453592,
    ('lbs', 'kg'): 0.453592,
    ('lb', 'kg'): 0.453592,
    ('ounce', 'g'): 28.3495,
    ('oz', 'g'): 28.3495,
    ('ton', '公噸'): 0.907185,  # short ton
    ('tons', '公噸'): 0.907185,
    ('tonne', '公噸'): 1.0,
    ('tonnes', '公噸'): 1.0,
    # Area
    ('acre', '公頃'): 0.404686,
    ('acres', '公頃'): 0.404686,
    ('sq ft', '平方公尺'): 0.092903,
    ('square feet', '平方公尺'): 0.092903,
    ('sq mi', '平方公里'): 2.58999,
    ('square miles', '平方公里'): 2.58999,
    # Volume
    ('gallon', '公升'): 3.78541,
    ('gallons', '公升'): 3.78541,
    ('barrel', '公升'): 158.987,
    ('barrels', '公升'): 158.987,
    ('bbl', '公升'): 158.987,
    # Speed
    ('mph', 'km/h'): 1.60934,
    ('knot', 'km/h'): 1.852,
    ('knots', 'km/h'): 1.852,
}

# ── Multilingual unit patterns (source text) ──
_UNIT_PATTERNS_SRC = re.compile(
    r'(\d+[,.]?\d*)\s*'
    r'(miles?|mi|km|feet|foot|ft|yards?|inch(?:es)?|'
    r'pounds?|lbs?|lb|ounces?|oz|tonn?e?s?|'
    r'acres?|sq(?:uare)?\s*(?:ft|feet|mi(?:les)?)|'
    r'gallons?|barrels?|bbl|'
    r'mph|knots?|'
    r'°[FC]|degrees?\s*[FC](?:ahrenheit|elsius)?)',
    re.IGNORECASE
)

# ── Chinese unit patterns (output text) ──
_ZH_UNIT_MAP = {
    '公里': 'km', '英里': 'mile', '海里': 'nm',
    '公尺': 'm', '英尺': 'foot', '碼': 'yard',
    '公分': 'cm', '英寸': 'inch',
    '公斤': 'kg', '磅': 'pound', '公噸': 'tonne', '噸': 'ton',
    '英畝': 'acre', '公頃': 'hectare',
    '平方公里': 'sq km', '平方英里': 'sq mi',
    '加侖': 'gallon', '公升': 'liter', '桶': 'barrel',
    '攝氏': '°C', '華氏': '°F',
    '時速': 'speed',
}

_ZH_UNIT_PATTERN = re.compile(
    r'(\d+[,.]?\d*)\s*(公里|英里|海里|公尺|英尺|碼|公分|英寸|'
    r'公斤|磅|公噸|噸|英畝|公頃|平方公里|平方英里|'
    r'加侖|公升|桶|攝氏|華氏|km/h|mph)'
)


def _normalize_unit(raw: str) -> str:
    """Normalize unit string to canonical form."""
    raw = raw.lower().strip()
    if raw in ('mile', 'miles', 'mi'): return 'mile'
    if raw in ('km', 'kilometer', 'kilometers', '公里'): return 'km'
    if raw in ('foot', 'feet', 'ft'): return 'foot'
    if raw in ('pound', 'pounds', 'lbs', 'lb'): return 'pound'
    if raw in ('ton', 'tons'): return 'ton'
    if raw in ('tonne', 'tonnes'): return 'tonne'
    if raw in ('acre', 'acres'): return 'acre'
    if raw in ('gallon', 'gallons'): return 'gallon'
    if raw in ('barrel', 'barrels', 'bbl'): return 'barrel'
    if '°f' in raw or 'fahrenheit' in raw: return '°F'
    if '°c' in raw or 'celsius' in raw: return '°C'
    if raw == 'mph': return 'mph'
    if raw in ('knot', 'knots'): return 'knot'
    return raw


def verify_measurements(source_texts: list[str], zh_body: str) -> list[tuple[str, str, str]]:
    """Verify measurement units between source and Chinese output.
    
    Catches: miles written as 公里 without conversion, °F written as °C, etc.
    """
    issues = []
    src_combined = " ".join(source_texts)
    
    # Extract source measurements
    src_measurements = []
    for m in _UNIT_PATTERNS_SRC.finditer(src_combined):
        val = float(m.group(1).replace(',', ''))
        unit = _normalize_unit(m.group(2))
        src_measurements.append((val, unit, m.group(0)))
    
    # Extract Chinese measurements
    zh_measurements = []
    for m in _ZH_UNIT_PATTERN.finditer(zh_body):
        val = float(m.group(1).replace(',', ''))
        zh_unit = m.group(2)
        canon = _ZH_UNIT_MAP.get(zh_unit, zh_unit)
        zh_measurements.append((val, canon, m.group(0)))
    
    # Cross-check: source imperial + zh metric with same number → not converted
    _IMPERIAL_METRIC_PAIRS = {
        ('mile', 'km'): 1.60934,
        ('foot', 'm'): 0.3048,
        ('pound', 'kg'): 0.453592,
        ('acre', 'hectare'): 0.404686,
        ('gallon', 'liter'): 3.78541,
        ('mph', 'km/h'): 1.60934,
        ('°F', '°C'): None,  # special formula
    }
    
    for s_val, s_unit, s_raw in src_measurements:
        for z_val, z_unit, z_raw in zh_measurements:
            for (imp, met), factor in _IMPERIAL_METRIC_PAIRS.items():
                if s_unit == imp and z_unit == met:
                    if factor:
                        expected = s_val * factor
                    else:  # temperature
                        expected = (s_val - 32) * 5 / 9
                    # If zh value ≈ source value (not converted)
                    if abs(z_val - s_val) / max(s_val, 1) < 0.1:
                        issues.append(("warn", f"not converted: {s_raw} → {z_raw}, expected ≈{expected:.0f}{z_raw[-2:]}", "check unit conversion"))
                    # If zh value is way off from expected
                    elif abs(z_val - expected) / max(expected, 1) > 0.2:
                        issues.append(("warn", f"conversion deviation: {s_raw}→{z_raw}, expected ≈{expected:.0f}", "check conversion"))
    
    # Check: temperature without unit label
    temp_no_unit = re.findall(r'(\d+)度(?!C|F|攝|華)', zh_body)
    for t in temp_no_unit:
        val = int(t)
        if val > 45:  # likely °F not converted
            for s_val, s_unit, _ in src_measurements:
                if s_unit == '°F' and abs(s_val - val) < 3:
                    expected_c = (val - 32) * 5 / 9
                    issues.append(("warn", f"temperature likely °F not converted: {val}° possibly {expected_c:.0f}°C", "check °C/°F"))
    
    return issues


def annotate_metric(zh_body: str) -> str:
    """Add metric equivalents for imperial units in Chinese text.
    
    Example: 500英里 → 500英里（約805公里）
    """
    def _add_equiv(m):
        val = float(m.group(1).replace(',', ''))
        unit = m.group(2)
        
        equiv = None
        if unit == '英里':
            equiv = f"{val * 1.60934:.0f}公里"
        elif unit == '英尺':
            equiv = f"{val * 0.3048:.1f}公尺"
        elif unit == '英畝':
            equiv = f"{val * 0.404686:.1f}公頃"
        elif unit == '磅':
            equiv = f"{val * 0.453592:.1f}公斤"
        elif unit == '加侖':
            equiv = f"{val * 3.78541:.1f}公升"
        elif unit == '華氏':
            equiv = f"攝氏{(val - 32) * 5/9:.0f}度"
        
        if equiv:
            return f"{m.group(0)}（約{equiv}）"
        return m.group(0)
    
    # Only annotate imperial → metric (not the other way)
    pattern = re.compile(r'(\d+[,.]?\d*)\s*(英里|英尺|英畝|磅|加侖|華氏)(?!（約)')
    return pattern.sub(_add_equiv, zh_body)


if __name__ == "__main__":
    # Self-test
    print("═══ 度量衡驗證測試 ═══\n")
    
    # Test: miles not converted
    issues = verify_measurements(
        ["The hurricane is 500 miles from the coast"],
        "颶風距離海岸500公里"
    )
    print(f"Test 1 (500 miles → 500公里 not converted): {'✅ caught' if issues else '❌ missed'}")
    if issues: print(f"  → {issues[0][1]}")
    
    # Test: correct conversion
    issues2 = verify_measurements(
        ["The hurricane is 500 miles from the coast"],
        "颶風距離海岸805公里"
    )
    print(f"Test 2 (500 miles → 805公里 正確): {'✅ clean' if not issues2 else '❌ FP'}")
    
    # Test: °F not converted
    issues3 = verify_measurements(
        ["Temperatures reached 104°F in Phoenix"],
        "鳳凰城氣溫達到104度"
    )
    print(f"Test 3 (104°F → 104度 未標): {'✅ caught' if issues3 else '❌ missed'}")
    if issues3: print(f"  → {issues3[0][1]}")
    
    # Test: annotation
    text = "該地區面積達500英里，氣溫高達華氏98度"
    result = annotate_metric(text)
    print(f"\nTest 4 (標註):")
    print(f"  In:  {text}")
    print(f"  Out: {result}")
