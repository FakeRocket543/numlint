# numlint

Multilingual number & currency verification for translated text.

**28 languages. Cross-lingual magnitude validation. Live financial data checks.**

## Problem

When translating news across languages, numbers get mangled:
- "1.8 billion" → "1.8萬" (should be 18億)
- "$1.7 billion" → "1.7億先令" (wrong currency)
- "3.09 million" → "3100人" (magnitude lost)

LLMs can't reliably do arithmetic. `numlint` catches these errors with deterministic validation.

## Install

```bash
pip install numlint
```

## Usage

```python
from numlint import extract_numbers, verify_numbers, annotate_twd

# Extract numbers from any of 28 languages
nums = extract_numbers("1,8 milliard de dollars et 3,5 millions")
# → [NumVal(value=1.8e9, magnitude='B', currency='USD'), NumVal(value=3.5e6, magnitude='M')]

# Verify Chinese output against source
issues = verify_numbers(
    source_texts=["The deal is worth $1.8 billion"],
    zh_text="18萬美元"  # WRONG! should be 18億
)
# → [('warn', '源文有 $1.8 billion (B), 中文未找到對應 18億', '確認數字量級')]

# Annotate foreign currency with TWD equivalent
text = annotate_twd("投資額達18億美元")
# → "投資額達18億美元（約新台幣566億元）"
```

## Supported Languages (28)

EN, FR, DE, ES, PT, RU, JA, KO, AR, ID, TR, IT, NL, VI, SV, DA, TH, PL, RO, EL, HU, FI, HE, HI, BN, UR, MS, CZ

Including Indian number system (lakh/crore), CJK magnitudes (萬/億/兆/만/억), and Arabic numerals.

## Financial Verification

```python
from numlint import verify_financial_claims

issues = verify_financial_claims("道瓊指數收至42,100點。美元兌日圓升至159.3。")
# Checks against live Yahoo Finance / exchange rate APIs
```

Validates:
- Forex rates (±5% threshold)
- Stock indices: Dow, S&P, Nasdaq, Nikkei, Hang Seng, DAX, FTSE, KOSPI
- Oil prices (WTI/Brent)
- Individual stocks: TSMC, NVIDIA, Apple, Tesla, etc.

## License

AGPL-3.0 — Free for open-source use. Contact for commercial licensing.
