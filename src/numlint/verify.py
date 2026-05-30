"""Cross-lingual number verification: source texts vs Chinese output."""
import re
from numlint.extract import extract_numbers, extract_zh_numbers, NumVal, _ZH_MAG


def verify_numbers(source_texts: list[str], zh_body: str) -> list[tuple[str, str, str]]:
    """Cross-validate numbers between multilingual sources and Chinese output.
    
    Returns list of (severity, issue, suggestion).
    """
    issues = []
    src_combined = " ".join(source_texts)
    
    src_nums = extract_numbers(src_combined)
    zh_nums = extract_zh_numbers(zh_body)
    
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
                issues.append(("warn", f"源文有 {sn.raw} ({sn.magnitude}), 中文未找到對應 {expected}", "確認數字量級"))
    
    # 2. Check format anomalies in Chinese
    bad_formats = re.findall(r'(\d+,\d{1,2}[萬億兆])', zh_body)
    for bf in bad_formats:
        issues.append(("warn", f"數字格式異常: {bf}", "確認是否為翻譯錯誤"))
    
    # 3. Check 萬/億 confusion (e.g., "1.23萬人" should be "1.23億")
    for zn in zh_nums:
        # If Chinese says X萬 but source has X*10000 scale number → likely 億 not 萬
        if zn.magnitude == 'M' and zn.value < 1e6:  # X萬 with small X
            for sn in src_nums:
                if sn.value >= 1e8 and abs(sn.value / 1e8 - zn.value / 1e4) < 0.5:
                    issues.append(("auto-fix", f"量級錯誤: {zn.raw} 應為 {sn.value/1e8:.2f}億", f"→ {sn.value/1e8:.2f}億"))
    
    # 4. Currency mismatch check
    src_currencies = {sn.currency for sn in src_nums if sn.currency}
    zh_currencies = {zn.currency for zn in zh_nums if zn.currency}
    # If source mentions USD but Chinese says different currency → warn
    if src_currencies and zh_currencies:
        unexpected = zh_currencies - src_currencies - {'TWD'}  # TWD added as conversion is OK
        if unexpected:
            issues.append(("warn", f"幣值不一致: 源文{src_currencies}, 中文{zh_currencies}", "確認幣別"))
    
    return issues


if __name__ == "__main__":
    # Test
    src = ["Japan population fell to 123 million, down 3.09 million from 2020",
           "Le Japon perd 3,1 millions d'habitants en 5 ans"]
    zh = "日本人口降至1.23萬人，較2020年減少3100人。"
    
    issues = lint_numbers_v2(src, zh)
    for sev, issue, fix in issues:
        print(f"  [{sev}] {issue} | {fix}")


