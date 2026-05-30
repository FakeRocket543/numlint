"""Currency conversion and TWD annotation."""
import re
import time
import httpx
from numlint.extract import _CURRENCY_MAP, _ZH_MAG


# ── Currency conversion (TWD equivalent annotation) ──

_RATE_CACHE: dict = {}
_RATE_CACHE_TIME: float = 0


def _fetch_rates() -> dict:
    """Fetch USD-based exchange rates (cached 6 hours)."""
    import time
    global _RATE_CACHE, _RATE_CACHE_TIME
    if _RATE_CACHE and time.time() - _RATE_CACHE_TIME < 21600:
        return _RATE_CACHE
    try:
        import httpx
        r = httpx.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        if r.status_code == 200:
            _RATE_CACHE = r.json().get("rates", {})
            _RATE_CACHE_TIME = time.time()
    except Exception:
        pass
    return _RATE_CACHE


def convert_to_twd(value: float, from_currency: str) -> float | None:
    """Convert a value from given currency to TWD. Returns None if unavailable."""
    rates = _fetch_rates()
    if not rates:
        return None
    twd_rate = rates.get("TWD")
    if not twd_rate:
        return None
    if from_currency == "TWD":
        return value
    if from_currency == "USD":
        return value * twd_rate
    # Convert via USD: foreign → USD → TWD
    foreign_rate = rates.get(from_currency)
    if not foreign_rate:
        return None
    usd_value = value / foreign_rate
    return usd_value * twd_rate


def annotate_currency_twd(zh_body: str) -> str:
    """Add TWD equivalent in parentheses after foreign currency amounts.
    
    Example: 17億美元 → 17億美元（約新台幣535億元）
    """
    rates = _fetch_rates()
    if not rates:
        return zh_body
    
    # Pattern: number + 億/萬/兆 + currency_name
    pattern = re.compile(
        r'([\d,]+\.?\d*)\s*(兆|億|萬)?\s*(美元|歐元|英鎊|日圓|日元|韓元|盧布|澳元|加元|印度盧比)'
        r'(?!（約)'  # don't double-annotate
    )
    
    def _add_twd(m):
        num_raw = m.group(1).replace(',', '')
        zh_mag = m.group(2) or ''
        cur_name = m.group(3)
        
        try:
            val = float(num_raw)
        except ValueError:
            return m.group(0)
        
        multiplier = _ZH_MAG.get(zh_mag, 1.0)
        absolute_val = val * multiplier
        
        iso = _CURRENCY_MAP.get(cur_name, '')
        if not iso:
            return m.group(0)
        
        twd = convert_to_twd(absolute_val, iso)
        if twd is None or twd < 1e4:  # skip tiny amounts
            return m.group(0)
        
        # Format TWD in 億/萬
        if twd >= 1e12:
            twd_str = f"{twd/1e12:.1f}兆"
        elif twd >= 1e8:
            twd_str = f"{twd/1e8:.0f}億"
        elif twd >= 1e4:
            twd_str = f"{twd/1e4:.0f}萬"
        else:
            twd_str = f"{twd:.0f}"
        
        return f"{m.group(0)}（約新台幣{twd_str}元）"
    
    return pattern.sub(_add_twd, zh_body)

