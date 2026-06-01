# numlint

Multilingual number & currency verification for translated text.

Catches magnitude errors, unit conversion mistakes, and financial data discrepancies that slip through LLM-based or human translation. Deterministic — no AI, no hallucination.

## Why this exists

LLMs and human translators routinely make number errors that are invisible to proofreaders:

- "1.8 billion" → "1.8萬" (off by 5 orders of magnitude)
- "500 miles" → "500公里" (not converted, should be 805km)
- "$45 billion" → "45億美元" (should be 450億)
- "104°F" → "104度" (Fahrenheit not converted to Celsius)

These errors are **catastrophic in news, finance, and legal documents** but trivially detectable with arithmetic. numlint does that arithmetic across 28 languages.

## Features

| Module | What it does |
|--------|-------------|
| `extract` | Extracts numbers + magnitudes from 28 languages (EN/FR/DE/ES/PT/RU/JA/KO/AR/ID/TR/IT/NL/VI/SV/DA/TH/PL/RO/EL/HU/FI/HE/HI/BN/UR/MS/CZ) |
| `verify` | Cross-validates source numbers vs target translation |
| `currency` | Live exchange rate lookup + target currency annotation |
| `finance` | Validates stock/forex/oil prices against market data |
| `measure` | Imperial↔metric conversion verification |
| `domain` | Domain-specific checks: semiconductor, weather, calendar, air quality |

## Installation

```bash
pip install numlint
```

Or from source:
```bash
git clone https://github.com/FakeRocket543/numlint.git
cd numlint
pip install -e .
```

## Quick Start

```python
from numlint import verify_numbers, extract_numbers, convert_currency

# Verify translation accuracy (any source language → any target)
issues = verify_numbers(
    source_texts=["The deal was worth $1.8 billion"],
    target_text="這筆交易價值18億美元",
    target_lang="zh"
)
# [] — correct (1.8B = 18億)

issues = verify_numbers(
    source_texts=["Le budget est de 3,5 milliards d'euros"],
    target_text="The budget is 3.5 million euros"
)
# [('warn', 'source has 3,5 milliards (B), target missing equivalent...', ...)]
# Caught: milliards (billion) mistranslated as million

# Extract numbers from any of 28 languages
from numlint import extract_numbers

# French
extract_numbers("Le budget est de 3,5 milliards d'euros")
# [NumVal(value=3_500_000_000, currency='EUR', magnitude='B')]

# German
extract_numbers("Die Investition beträgt 2,7 Milliarden Dollar")
# [NumVal(value=2_700_000_000, currency='USD', magnitude='B')]

# Russian
extract_numbers("Бюджет составляет 450 млрд рублей")
# [NumVal(value=450_000_000_000, currency='RUB', magnitude='B')]

# Japanese
extract_numbers("予算は1兆8000億円")
# [NumVal(value=1_800_000_000_000, currency='JPY', magnitude='T')]

# Korean
extract_numbers("투자액 464만 달러")
# [NumVal(value=4_640_000, currency='USD', magnitude='M')]

# Hindi/Indian English
extract_numbers("The project costs 1.5 lakh crore rupees")
# [NumVal(value=15_000_000_000_000, currency='INR', magnitude='T')]

# Arabic
extract_numbers("الميزانية 500 مليون دولار")
# [NumVal(value=500_000_000, currency='USD', magnitude='M')]

# Convert between any currencies (live rates)
convert_currency(100, "USD", "JPY")   # → ~15,900
convert_currency(100, "EUR", "GBP")   # → ~86
convert_currency(1.8e9, "USD", "TWD") # → ~56,600,000,000
```

## Modules

### `verify_numbers(source_texts, target_text, target_lang="zh")`

Cross-validates numbers between multilingual sources and target output. Returns list of `(severity, issue, suggestion)` tuples.

Checks:
- Magnitude mismatches (billion → 萬 instead of 億)
- Number format anomalies (1,50億 — comma in wrong place)
- Currency mismatches (source USD, target says EUR)

### `extract_numbers(text) → list[NumVal]`

Extracts all significant numbers from text in any of 28 supported languages. Handles:

- Western magnitudes: billion, million, milliard, Milliarden, milhões...
- CJK magnitudes: 兆/億/萬 (ZH), 조/억/만 (KO), 兆/億/万 (JA)
- Indian system: lakh, crore, lakh crore
- Arabic/Thai/Hebrew/Bengali/Urdu numeral words
- European comma decimals (3,5 = 3.5)
- Spanish/Portuguese thousand dots (1.800 = 1800)

### `verify_measurements(source_texts, zh_body)`

Catches unconverted imperial→metric units:
- 500 miles written as 500公里 (should be 805)
- 104°F written as 104度 (should be 40°C)

### `verify_financial_claims(zh_body)`

Live validation against market data:
- Stock index levels (道瓊/日經/恒生)
- Forex rates (美元兌日圓)
- Oil prices (WTI/Brent)

Uses Yahoo Finance → Twelve Data → Google Finance (fallback chain).

### `verify_domain(source_texts, zh_body)`

Domain-specific plausibility:
- **Semiconductor**: validates process nodes (3nm, 5nm...), catches nm→公尺 mistranslation
- **Weather**: temperature range checks, °F→°C conversion detection
- **Calendar**: Buddhist Era (พ.ศ.), Islamic calendar (هـ), 民國/令和 conversion
- **Air quality**: PM2.5/AQI range validation

### `convert_currency(value, from_currency, to_currency="TWD")`

Live exchange rate conversion. 166 currencies supported. Rates cached 6 hours.

## Supported Languages (Number Extraction)

English, French, German, Spanish, Portuguese, Russian, Japanese, Korean, Arabic, Indonesian, Turkish, Italian, Dutch, Vietnamese, Swedish, Danish, Thai, Polish, Romanian, Greek, Hungarian, Finnish, Hebrew, Hindi, Bengali, Urdu, Malay, Czech

## Configuration

numlint uses no config files. Behavior is controlled by function parameters:

```python
# Verify against any target language (not just Chinese)
issues = verify_numbers(sources, target, target_lang="zh")  # Chinese
issues = verify_numbers(sources, target, target_lang="en")  # English target

# Convert to any currency
convert_currency(100, "USD", "EUR")  # USD → EUR
convert_currency(100, "USD", "JPY")  # USD → JPY
```

## Troubleshooting

### "source has X, target missing equivalent Y"

The source text contains a significant number that doesn't appear (within ±20% tolerance) in the target text. Common causes:
- LLM omitted the number entirely
- Magnitude was wrong (billion → 萬 instead of 億)
- Number was paraphrased in a way numlint can't parse

**Fix**: Check the target text manually. If the number is there but in a different format, you may need to expand `_ZH_MAG` patterns in `extract.py`.

### False positives on dates/versions

numlint skips bare numbers without currency/magnitude context. If you get false positives on years or version numbers, they likely have an adjacent magnitude word being mismatched.

### Exchange rates stale

Rates are cached 6 hours. If you need fresh rates:
```python
from numlint.currency import _RATE_CACHE
_RATE_CACHE.clear()
```

### Adding a new language

Edit `src/numlint/extract.py`:
1. Add magnitude words to `_MAG_PATTERNS` dict
2. Add currency names to `_CURRENCY_MAP` if needed
3. Add a test case to `tests/test_basic.py`

## Development

```bash
git clone https://github.com/FakeRocket543/numlint.git
cd numlint
pip install -e ".[dev]"
pytest tests/ -v
```

## License

AGPL-3.0. If you use numlint in a web service, you must open-source your modifications.

## Contributing

Issues and PRs welcome. Particularly useful contributions:

- New language magnitude patterns (with test cases)
- Edge case fixes (number formats that parse incorrectly)
- Domain-specific validators (e.g., sports statistics, medical dosages)
- Performance improvements for large-scale batch verification

Please include test cases for any new extraction patterns.
