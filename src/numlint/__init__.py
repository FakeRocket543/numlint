"""numlint — Multilingual number & currency verification for translated text.

28 languages. Cross-lingual magnitude validation. Live financial checks.

Usage:
    from numlint import extract_numbers, verify_numbers, annotate_twd

    # Extract numbers from any language
    nums = extract_numbers("1,8 milliard de dollars et 3,5 millions")

    # Verify Chinese output against source numbers
    issues = verify_numbers(source_texts=["$1.8 billion"], zh_text="18億美元")

    # Annotate foreign currency with TWD equivalent
    text = annotate_twd("投資額達18億美元")
    # → "投資額達18億美元（約新台幣566億元）"
"""

from numlint.extract import extract_numbers, NumVal
from numlint.verify import verify_numbers
from numlint.currency import annotate_currency_twd as annotate_twd, convert_to_twd, convert_currency
from numlint.finance import verify_financial_claims
from numlint.measure import verify_measurements, annotate_metric
from numlint.domain import verify_domain, verify_semiconductor, verify_weather, verify_calendar, verify_air_quality

__version__ = "0.1.0"
__all__ = [
    "extract_numbers",
    "verify_numbers",
    "annotate_twd",
    "convert_to_twd",
    "verify_financial_claims",
    "NumVal",
    "verify_measurements",
    "annotate_metric",
    "verify_domain",
    "verify_semiconductor",
    "verify_weather",
    "verify_calendar",
    "verify_air_quality",
]
