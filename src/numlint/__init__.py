"""numlint — Multilingual number & currency verification for translated text.

28 languages. Cross-lingual magnitude validation. Live financial checks.

Usage:
    from numlint import extract_numbers, verify_numbers, annotate_twd

    # Extract numbers from any language
    nums = extract_numbers("1,8 milliard de dollars et 3,5 millions")

    # Verify target-language output against source numbers
    issues = verify_numbers(source_texts=["$1.8 billion"], target_text="18億美元")

    # Annotate foreign currency with TWD equivalent
    text = annotate_twd("投資額達18億美元")
    # → "投資額達18億美元（約新台幣566億元）"
"""

from numlint.currency import annotate_currency_twd as annotate_twd
from numlint.currency import convert_currency, convert_to_twd
from numlint.domain import verify_air_quality, verify_calendar, verify_domain, verify_semiconductor, verify_weather
from numlint.extract import NumVal, extract_numbers
from numlint.finance import verify_financial_claims
from numlint.measure import annotate_metric, verify_measurements
from numlint.verify import verify_numbers

__version__ = "0.1.0"
__all__ = [
    "NumVal",
    "annotate_metric",
    "annotate_twd",
    "convert_currency",
    "convert_to_twd",
    "extract_numbers",
    "verify_air_quality",
    "verify_calendar",
    "verify_domain",
    "verify_financial_claims",
    "verify_measurements",
    "verify_numbers",
    "verify_semiconductor",
    "verify_weather",
]
