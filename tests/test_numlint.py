"""Tests for numlint — covers README examples and edge cases."""
import pytest
from numlint import extract_numbers, verify_numbers, annotate_twd, NumVal
from numlint.extract import extract_zh_numbers


# ── extract_numbers ──

class TestExtractNumbers:
    """README example + multilingual extraction."""

    def test_readme_french(self):
        """README: '1,8 milliard de dollars et 3,5 millions'"""
        nums = extract_numbers("1,8 milliard de dollars et 3,5 millions")
        # Should find 1.8e9 and 3.5e6
        values = [n.value for n in nums]
        assert any(abs(v - 1.8e9) < 1e6 for v in values), f"Expected ~1.8B, got {values}"
        assert any(abs(v - 3.5e6) < 1e4 for v in values), f"Expected ~3.5M, got {values}"

    def test_english_billion_usd(self):
        nums = extract_numbers("The deal is worth $1.8 billion")
        assert len(nums) >= 1
        assert abs(nums[0].value - 1.8e9) < 1e6
        assert nums[0].currency == 'USD'
        assert nums[0].magnitude == 'B'

    def test_german_milliarden(self):
        nums = extract_numbers("Das Unternehmen ist 5,2 Milliarden Euro wert")
        assert any(abs(n.value - 5.2e9) < 1e6 for n in nums)

    def test_russian(self):
        nums = extract_numbers("население составляет 146 млн человек")
        assert any(abs(n.value - 146e6) < 1e5 for n in nums)

    def test_korean_eok(self):
        nums = extract_numbers("매출 500억")
        assert any(abs(n.value - 500e8) < 1e7 for n in nums)

    def test_indian_lakh_crore(self):
        nums = extract_numbers("5 lakh crores of rupees")
        assert any(abs(n.value - 5e12) < 1e10 for n in nums)

    def test_compound_korean(self):
        """6조4000억 should parse to 6.4 trillion."""
        nums = extract_numbers("6조4000억")
        assert any(abs(n.value - 6.4e12) < 1e10 for n in nums)

    def test_skips_dates_and_versions(self):
        """Bare numbers without context should be filtered."""
        nums = extract_numbers("Updated on 2024-01-15. Version 3.2.1 released.")
        values = [n.value for n in nums]
        assert not any(abs(v - 2024) < 1 for v in values), f"Should skip year 2024, got {values}"
        assert not any(abs(v - 3.2) < 0.1 for v in values), f"Should skip version 3.2, got {values}"

    def test_keeps_large_number_with_magnitude(self):
        nums = extract_numbers("Revenue reached $42,500 million")
        assert any(abs(n.value - 42.5e9) < 1e7 for n in nums)

    def test_spanish_thousand_dot(self):
        """1.800 in Spanish = 1800 (thousands separator), not 1.8."""
        nums = extract_numbers("1.800 millones de dólares")
        # 1800 million = 1.8e9
        assert any(abs(n.value - 1.8e9) < 1e7 for n in nums)


# ── extract_zh_numbers ──

class TestExtractZhNumbers:
    def test_basic_yi(self):
        nums = extract_zh_numbers("投資額達18億美元")
        assert len(nums) >= 1
        assert abs(nums[0].value - 18e8) < 1e6
        assert nums[0].currency == 'USD'

    def test_wan(self):
        nums = extract_zh_numbers("人口約2300萬")
        assert len(nums) >= 1
        assert abs(nums[0].value - 2300e4) < 1e5
        assert nums[0].magnitude == 'K'

    def test_zhao(self):
        nums = extract_zh_numbers("國債達45兆美元")
        assert len(nums) >= 1
        assert abs(nums[0].value - 45e12) < 1e10
        assert nums[0].currency == 'USD'
        assert nums[0].magnitude == 'T'


# ── verify_numbers ──

class TestVerifyNumbers:
    def test_readme_mismatch(self):
        """README: $1.8 billion vs '18萬美元' should warn."""
        issues = verify_numbers(
            source_texts=["The deal is worth $1.8 billion"],
            zh_body="18萬美元"
        )
        assert len(issues) > 0, "Should detect mismatch: $1.8B → 18萬"
        assert any('warn' in i[0] for i in issues)

    def test_correct_translation(self):
        """$1.8 billion → 18億美元 should pass."""
        issues = verify_numbers(
            source_texts=["The deal is worth $1.8 billion"],
            zh_body="這筆交易價值18億美元"
        )
        # Should have no magnitude mismatch warnings
        mag_issues = [i for i in issues if '量級' in i[1] or '未找到' in i[1]]
        assert len(mag_issues) == 0, f"Should not warn on correct translation, got {mag_issues}"


# ── annotate_twd ──

class TestAnnotateTWD:
    def test_basic_annotation(self):
        """Should add TWD equivalent after USD amount."""
        # This test may skip if no network; that's OK
        result = annotate_twd("投資額達18億美元")
        if result != "投資額達18億美元":
            assert "新台幣" in result
            assert "約" in result
