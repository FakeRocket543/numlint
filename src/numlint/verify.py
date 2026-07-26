"""Cross-lingual number verification: source texts vs translated output."""
import re

from numlint.extract import NumVal, extract_numbers, extract_zh_numbers


def verify_numbers(source_texts: list[str], target_text: str, target_lang: str = "zh") -> list[tuple[str, str, str]]:
    """Cross-validate numbers between multilingual sources and target-language output.

    Returns list of (severity, issue, suggestion).
    """
    issues = []
    src_combined = " ".join(source_texts)
    
    src_nums = extract_numbers(src_combined)
    zh_nums = extract_zh_numbers(target_text) if target_lang == "zh" else extract_numbers(target_text)
    
    # 1. Check magnitude mismatches (most critical)
    for sn in src_nums:
        if sn.value < 1000:  # skip small numbers
            continue
        if sn.magnitude in ('B', 'T', 'M'):
            # Find corresponding Chinese number (within 20% tolerance)
            found = False
            for zn in zh_nums:
                ratio = zn.value / sn.value if sn.value else 0
                if 0.8 <= ratio <= 1.2:
                    found = True
                    break
            if not found and sn.value >= 1e6:
                # Format expected value in Chinese
                if sn.value >= 1e12:
                    expected = f"{sn.value/1e12:.1f}兆"
                elif sn.value >= 1e8:
                    expected = f"{sn.value/1e8:.0f}億"
                elif sn.value >= 1e4:
                    expected = f"{sn.value/1e4:.0f}萬"
                else:
                    expected = f"{sn.value:.0f}"
                issues.append(("warn", f"source has {sn.raw} ({sn.magnitude}), target missing equivalent {expected}", "check magnitude"))
    
    # 2. Check format anomalies in Chinese
    bad_formats = re.findall(r'(\d+,\d{1,2}[萬億兆])', target_text)
    for bf in bad_formats:
        issues.append(("warn", f"abnormal number format: {bf}", "check for translation error"))
    
    # 3. Check 萬/億 confusion (e.g., "1.23萬人" should be "1.23億")
    for zn in zh_nums:
        # If Chinese says X萬 but source has X*10000 scale number → likely 億 not 萬
        if zn.magnitude == 'M' and zn.value < 1e6:  # X萬 with small X
            for sn in src_nums:
                if sn.value >= 1e8 and abs(sn.value / 1e8 - zn.value / 1e4) < 0.5:
                    issues.append(("auto-fix", f"magnitude error: {zn.raw} should be {sn.value/1e8:.2f}×10⁸", f"→ {sn.value/1e8:.2f}×10⁸"))
    
    # 3b. Magnitude inflation: Chinese has 萬/億 but source has small number
    # e.g., source: 140人, Chinese: 14萬人 → likely error (140 ≠ 140000)
    # Use permissive extraction (catch bare numbers without magnitude/currency)
    _raw_src_nums = [int(m.group()) for m in re.finditer(r"\d+", src_combined) if 2 <= len(m.group()) <= 5]
    _all_src = src_nums + [NumVal(raw=str(v), value=float(v), unit="", currency="", magnitude="") for v in _raw_src_nums if v >= 10]
    for zn in zh_nums:
        if zn.magnitude in ("M", "B", "K") and zn.value >= 1e4:
            zh_face = zn.value / {"K": 1e4, "M": 1e6, "B": 1e8, "T": 1e12}.get(zn.magnitude, 1e4)
            for sn in _all_src:
                if sn.magnitude == "" and 10 <= sn.value < 1e4:
                    ratio = sn.value / zn.value if zn.value else 0
                    if 0.8 <= ratio <= 1.2:
                        pass
                    elif abs(sn.value - zh_face) < zh_face * 0.3 or sn.value > 1 and abs(sn.value / 10 - zh_face) < zh_face * 0.3:
                        issues.append(("warn", f"magnitude inflation: source ~{sn.value:.0f}, target {zn.raw} (~{zn.value:.0f})", f"should be {sn.value:.0f}"))

    # 4. Currency mismatch check
    src_currencies = {sn.currency for sn in src_nums if sn.currency}
    zh_currencies = {zn.currency for zn in zh_nums if zn.currency}
    # If source mentions USD but Chinese says different currency → warn
    if src_currencies and zh_currencies:
        unexpected = zh_currencies - src_currencies - {'TWD'}  # TWD added as conversion is OK
        if unexpected:
            issues.append(("warn", f"currency mismatch: source {src_currencies}, target {zh_currencies}", "check currency"))
    
    # 5. Bare large number warning (>8 digits without 億/萬/兆 suffix)
    if target_lang == "zh":
        bare_large_re = re.compile(r'(\d{8,})')
        for m in bare_large_re.finditer(target_text):
            num_str = m.group(1)
            end_pos = m.end()
            after = target_text[end_pos:end_pos+2]
            if any(mag in after for mag in ('兆', '億', '萬')):
                continue
            # Skip date-like patterns
            if re.match(r'20[012]\d', num_str[:4]):
                continue
            try:
                val = int(num_str)
            except ValueError:
                continue
            if val >= 1e12:
                suggested = f"{val/1e12:.2f}兆"
            elif val >= 1e8:
                suggested = f"{val/1e8:.0f}億"
            elif val >= 1e4:
                suggested = f"{val/1e4:.0f}萬"
            else:
                continue
            issues.append(("warn", f"bare large number: {num_str} (should be {suggested})", f"→ {suggested}"))

    return issues


if __name__ == "__main__":
    # Test
    src = ["Japan population fell to 123 million, down 3.09 million from 2020",
           "Le Japon perd 3,1 millions d'habitants en 5 ans"]
    zh = "日本人口降至1.23萬人，較2020年減少3100人。"
    
    issues = verify_numbers(src, zh)
    for sev, issue, fix in issues:
        print(f"  [{sev}] {issue} | {fix}")


