"""Financial data verification. Validates stock/forex/oil prices against live market data.

Validates stock prices, forex rates, and index levels mentioned in articles
against real-time market data. No LLM — pure API + arithmetic.

Usage:
    from numlint import verify_financial_claims
    issues = verify_financial_claims(zh_body)
"""
import re
import time

import httpx

# ── Cache ──
_CACHE: dict = {}
_CACHE_TTL = 3600  # 1 hour


def _cached_get(url: str, **kwargs) -> dict | None:
    """GET with 1-hour cache."""
    now = time.time()
    if url in _CACHE and now - _CACHE[url][1] < _CACHE_TTL:
        return _CACHE[url][0]
    try:
        r = httpx.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"}, **kwargs)
        if r.status_code == 200:
            data = r.json()
            _CACHE[url] = (data, now)
            return data
    except (httpx.HTTPError, ValueError):
        return None
    return None


# ── Forex verification ──

def _get_forex_rate(base: str, quote: str) -> float | None:
    """Get exchange rate base/quote."""
    data = _cached_get(f"https://api.exchangerate-api.com/v4/latest/{base}")
    if data:
        return data.get("rates", {}).get(quote)
    return None


def _verify_forex(pairs: list[tuple[str, str, float]]) -> list[tuple[str, str, str]]:
    """Verify forex rates mentioned in text.
    pairs: [(base, quote, mentioned_rate), ...]
    """
    issues = []
    for base, quote, mentioned in pairs:
        actual = _get_forex_rate(base, quote)
        if actual is None:
            continue
        deviation = abs(mentioned - actual) / actual
        if deviation > 0.05:  # >5% off
            issues.append(("warn", f"forex deviation: {base}/{quote} 文中={mentioned:.2f}, 實際≈{actual:.2f} (差{deviation*100:.1f}%)", "check forex rate"))
    return issues


# ── Stock/Index verification ──

_INDEX_SYMBOLS = {
    '道瓊': '^DJI', '道瓊斯': '^DJI', 'dow jones': '^DJI', 'dow': '^DJI',
    '標普': '^GSPC', 's&p': '^GSPC', 's&p 500': '^GSPC',
    '那斯達克': '^IXIC', 'nasdaq': '^IXIC',
    '日經': '^N225', 'nikkei': '^N225',
    '恒生': '^HSI', '恒指': '^HSI', 'hang seng': '^HSI',
    'kospi': '^KS11',
    'dax': '^GDAXI',
    'ftse': '^FTSE', '富時': '^FTSE',
    'cac': '^FCHI',
}

_STOCK_SYMBOLS = {
    '台積電': 'TSM', 'tsmc': 'TSM',
    '蘋果': 'AAPL', 'apple': 'AAPL',
    '輝達': 'NVDA', 'nvidia': 'NVDA',
    '特斯拉': 'TSLA', 'tesla': 'TSLA',
    '三星': '005930.KS', 'samsung': '005930.KS',
    '微軟': 'MSFT', 'microsoft': 'MSFT',
    '亞馬遜': 'AMZN', 'amazon': 'AMZN',
    '谷歌': 'GOOGL', 'google': 'GOOGL', 'alphabet': 'GOOGL',
}


# ── Price fetching with fallback chain ──
# Yahoo Finance v8 is primary but frequently breaks (rate limits, CORS, endpoint
# changes).  We fall back to Twelve Data (free tier), then Google Finance scrape.
# The existing _CACHE (1h TTL) is preserved — each source URL is cached independently.

def _get_price_yahoo(symbol: str) -> dict | None:
    """Fetch price from Yahoo Finance v8 chart API."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
    data = _cached_get(url)
    if not data:
        return None
    try:
        result = data["chart"]["result"][0]
        meta = result["meta"]
        return {
            "price": meta.get("regularMarketPrice", 0),
            "prev_close": meta.get("previousClose") or meta.get("chartPreviousClose", 0),
            "currency": meta.get("currency", "USD"),
        }
    except (KeyError, IndexError):
        return None


def _get_price_twelve_data(symbol: str) -> dict | None:
    """Fetch price from Twelve Data (free tier, no key required for basic quotes)."""
    # Map common symbols for Twelve Data format
    td_symbol = symbol.replace("^", "") if symbol.startswith("^") else symbol
    # Twelve Data uses .KS suffix same as Yahoo for Korean stocks
    url = f"https://api.twelvedata.com/price?symbol={td_symbol}&apikey=demo"
    data = _cached_get(url)
    if not data:
        return None
    try:
        price = float(data.get("price", 0))
        if price <= 0:
            return None
        return {
            "price": price,
            "prev_close": 0,  # not available from this endpoint
            "currency": "USD",
        }
    except (ValueError, TypeError):
        return None


def _get_price_google(symbol: str) -> dict | None:
    """Fetch price from Google Finance as last-resort fallback."""
    # Google Finance URL format — extract price from the redirect/JSON page
    url = f"https://www.google.com/finance/quote/{symbol}:NYSE"
    try:
        r = httpx.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
        if r.status_code != 200:
            return None
        # Try to extract price from the HTML/JSON response
        # Google Finance embeds data in a script tag
        match = re.search(r'data-last-price="([0-9.]+)"', r.text)
        if not match:
            match = re.search(r'"lastPrice"\s*:\s*([0-9.]+)', r.text)
        if match:
            price = float(match.group(1))
            if price > 0:
                return {
                    "price": price,
                    "prev_close": 0,
                    "currency": "USD",
                }
    except (httpx.HTTPError, ValueError):
        return None
    return None


def _get_price(symbol: str) -> dict | None:
    """Get latest price data with fallback chain: Yahoo → Twelve Data → Google Finance."""
    # Try Yahoo Finance first (existing, most reliable when available)
    result = _get_price_yahoo(symbol)
    if result:
        return result

    # Fallback 1: Twelve Data free tier
    result = _get_price_twelve_data(symbol)
    if result:
        return result

    # Fallback 2: Google Finance scrape (best-effort)
    result = _get_price_google(symbol)
    if result:
        return result

    return None


def _verify_prices(claims: list[tuple[str, float]]) -> list[tuple[str, str, str]]:
    """Verify stock/index prices.
    claims: [(name_or_symbol, mentioned_price), ...]
    """
    issues = []
    for name, mentioned in claims:
        name_lower = name.lower()
        symbol = _INDEX_SYMBOLS.get(name_lower) or _STOCK_SYMBOLS.get(name_lower)
        if not symbol:
            continue
        data = _get_price(symbol)
        if not data or not data["price"]:
            continue
        actual = data["price"]
        deviation = abs(mentioned - actual) / actual
        if deviation > 0.10:  # >10% off (indices can be volatile intraday)
            issues.append(("warn", f"price deviation: {name} 文中={mentioned:.0f}, 實際≈{actual:.0f} (差{deviation*100:.1f}%)", "check reported figure"))
    return issues


# ── Main extraction + verification ──

def verify_financial_claims(zh_body: str) -> list[tuple[str, str, str]]:
    """Extract and verify financial claims in Chinese text.
    Returns list of (severity, issue, suggestion).
    """
    issues = []

    # 1. Forex: 美元兌日圓 XXX / 歐元兌美元 X.XX
    forex_pattern = re.compile(
        r'(美元|歐元|英鎊|日圓|日元|人民幣|韓元|澳元)'
        r'(?:兌|對|/)'
        r'(美元|歐元|英鎊|日圓|日元|人民幣|韓元|澳元)'
        r'[^\d]{0,5}?(\d+\.?\d*)'
    )
    _CURRENCY_ISO = {
        '美元': 'USD', '歐元': 'EUR', '英鎊': 'GBP', '日圓': 'JPY', '日元': 'JPY',
        '人民幣': 'CNY', '韓元': 'KRW', '澳元': 'AUD',
    }
    forex_pairs = []
    for m in forex_pattern.finditer(zh_body):
        base = _CURRENCY_ISO.get(m.group(1), '')
        quote = _CURRENCY_ISO.get(m.group(2), '')
        rate = float(m.group(3))
        if base and quote and rate > 0:
            forex_pairs.append((base, quote, rate))
    if forex_pairs:
        issues.extend(_verify_forex(forex_pairs))

    # 2. Index levels: 道瓊指數 XX,XXX / 日經指數 XX,XXX
    index_pattern = re.compile(
        r'(道瓊|標普|那斯達克|日經|恒生|恒指|富時|DAX|KOSPI)'
        r'[^\d]{0,15}?'
        r'(?:至|收|報|為|達)\s*'  # must have a level-indicating verb
        r'([\d,]+\.?\d*)\s*點?'
    )
    price_claims = []
    for m in index_pattern.finditer(zh_body):
        name = m.group(1)
        val = float(m.group(2).replace(',', ''))
        if val > 100:  # skip percentages
            price_claims.append((name, val))
    if price_claims:
        issues.extend(_verify_prices(price_claims))

    # 3. Oil price: 原油/布蘭特/WTI XX美元
    oil_pattern = re.compile(r'(?:原油|布蘭特|WTI|Brent)[^\d]{0,10}?(\d+\.?\d*)\s*美元')
    for m in oil_pattern.finditer(zh_body):
        price = float(m.group(1))
        # Verify against CL=F (WTI crude)
        data = _get_price("CL=F")
        if data and data["price"]:
            deviation = abs(price - data["price"]) / data["price"]
            if deviation > 0.15:
                issues.append(("warn", f"oil price deviation: 文中={price:.1f}, 實際≈{data['price']:.1f}美元", "check oil price"))

    return issues


if __name__ == '__main__':
    # Self-test
    test = "道瓊指數下跌400點至42,100點。美元兌日圓升至159.3。原油跌至每桶67美元。"
    print(f"測試: {test}\n")
    issues = verify_financial_claims(test)
    if issues:
        for s, i, f in issues:
            print(f"  [{s}] {i} | {f}")
    else:
        print("  ✅ 所有金融數據驗證通過")
