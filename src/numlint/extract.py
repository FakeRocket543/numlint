"""Multilingual number extraction from text (28 languages).

Supports: EN, FR, DE, ES, PT, RU, JA, KO, AR, ID, TR, IT, NL, VI,
SV, DA, TH, PL, RO, EL, HU, FI, HE, HI, BN, UR, MS, CZ
"""
import re
from typing import NamedTuple

class NumVal(NamedTuple):
    raw: str       # original text
    value: float   # normalized value
    unit: str      # '', '%', 'currency'
    currency: str  # 'USD', 'EUR', 'JPY', etc. or ''
    magnitude: str # 'T', 'B', 'M', 'K', '' (trillion/billion/million/thousand)


# ── Multilingual magnitude words ──
_MAG_PATTERNS = {
    # English
    'trillion': 1e12, 'billion': 1e9, 'million': 1e6, 'thousand': 1e3,
    'bn': 1e9, 'bln': 1e9, 'mn': 1e6, 'mln': 1e6, 'tn': 1e12, 'trn': 1e12,
    # French
    'milliard': 1e9, 'milliards': 1e9, 'millions': 1e6, 'mille': 1e3,
    # Spanish/Portuguese
    'billón': 1e12, 'billones': 1e12, 'millones': 1e6,
    'bilhões': 1e9, 'bilhão': 1e9, 'milhões': 1e6, 'milhão': 1e6, 'trilhões': 1e12,
    # German
    'milliarden': 1e9, 'milliarde': 1e9, 'millionen': 1e6, 'tausend': 1e3, 'mrd': 1e9, 'mio': 1e6,
    # Russian/Ukrainian
    'трлн': 1e12, 'млрд': 1e9, 'млн': 1e6, 'тыс': 1e3,
    'триллион': 1e12, 'миллиард': 1e9, 'миллион': 1e6, 'тысяч': 1e3,
    # Japanese
    '兆': 1e12, '億': 1e8, '万': 1e4,
    # Korean
    '조': 1e12, '억': 1e8, '만': 1e4,
    # Arabic
    'مليار': 1e9, 'مليون': 1e6, 'ألف': 1e3,
    # Indonesian/Malay
    'triliun': 1e12, 'miliar': 1e9, 'bilion': 1e9, 'juta': 1e6, 'ribu': 1e3,
    # Turkish
    'trilyon': 1e12, 'milyar': 1e9, 'milyon': 1e6, 'bin': 1e3,
    # Italian
    'miliardi': 1e9, 'miliardo': 1e9, 'milioni': 1e6, 'milione': 1e6,
    # Dutch
    'miljard': 1e9, 'miljarden': 1e9, 'miljoen': 1e6,
    # Swedish/Danish/Norwegian
    'miljarder': 1e9, 'milliarder': 1e9, 'miljoner': 1e6, 'millioner': 1e6,
    # Vietnamese
    'tỷ': 1e9, 'triệu': 1e6, 'nghìn': 1e3,
    # Thai
    'ล้านล้าน': 1e12, 'พันล้าน': 1e9, 'ล้าน': 1e6, 'แสน': 1e5, 'พัน': 1e3,
    # Polish
    'miliardów': 1e9, 'milionów': 1e6, 'tysięcy': 1e3, 'tysiąc': 1e3,
    # Czech/Slovak
    'miliarda': 1e9, 'miliárd': 1e9, 'milión': 1e6, 'tisíc': 1e3,
    # Romanian
    'miliarde': 1e9, 'milioane': 1e6, 'mii': 1e3,
    # Greek
    'δισεκατομμύρια': 1e9, 'δισεκατομμύριο': 1e9, 'δισ': 1e9,
    'εκατομμύρια': 1e6, 'εκατομμύριο': 1e6, 'εκατ': 1e6,
    'χιλιάδες': 1e3, 'χιλιάδα': 1e3,
    # Hungarian
    'milliárd': 1e9, 'millió': 1e6, 'ezer': 1e3,
    # Finnish
    'miljardi': 1e9, 'miljoona': 1e6, 'miljoonaa': 1e6, 'tuhat': 1e3, 'tuhatta': 1e3,
    # Hebrew
    'מיליארד': 1e9, 'מיליון': 1e6, 'אלף': 1e3,
    # Bengali
    'বিলিয়ন': 1e9, 'মিলিয়ন': 1e6, 'কোটি': 1e7, 'লাখ': 1e5,
    # Urdu
    'ارب': 1e9, 'کروڑ': 1e7, 'لاکھ': 1e5,
    # Indian English
    'lakh': 1e5, 'lakhs': 1e5, 'crore': 1e7, 'crores': 1e7,
}

# ── Currency symbols/words → ISO code ──
_CURRENCY_MAP = {
    '$': 'USD', '＄': 'USD', 'usd': 'USD', 'dollars': 'USD', 'dollar': 'USD',
    '€': 'EUR', 'eur': 'EUR', 'euros': 'EUR', 'euro': 'EUR',
    '£': 'GBP', 'gbp': 'GBP', 'pounds': 'GBP', 'pound': 'GBP',
    '¥': 'JPY', 'yen': 'JPY', 'jpy': 'JPY',  # also CNY context-dependent
    '₩': 'KRW', 'won': 'KRW', 'krw': 'KRW',
    '₹': 'INR', 'rupees': 'INR', 'inr': 'INR', 'crore': 'INR',  # 1 crore = 10M
    'r$': 'BRL', 'brl': 'BRL', 'reais': 'BRL', 'real': 'BRL',
    '₽': 'RUB', 'rub': 'RUB', 'rubles': 'RUB', 'рублей': 'RUB', 'руб': 'RUB',
    'rm': 'MYR', 'myr': 'MYR', 'ringgit': 'MYR',
    '₺': 'TRY', 'tl': 'TRY', 'lira': 'TRY',
    # Chinese output patterns
    '美元': 'USD', '歐元': 'EUR', '英鎊': 'GBP', '日圓': 'JPY', '日元': 'JPY',
    '韓元': 'KRW', '韓圜': 'KRW', '盧布': 'RUB', '人民幣': 'CNY', '台幣': 'TWD',
    '新台幣': 'TWD', '澳元': 'AUD', '加元': 'CAD', '印度盧比': 'INR',
    '先令': 'KES',  # context: Kenya shillings
}

# Chinese magnitude
_ZH_MAG = {'兆': 1e12, '億': 1e8, '萬': 1e4}


def extract_numbers(text: str) -> list[NumVal]:
    """Extract numbers with magnitude and currency from multilingual source text."""
    results = []
    
    # Pattern: optional currency symbol + number + optional magnitude word
    # Handles: $1.8 billion, 3,5 milliards d'euros, 18億円, 1.7B shillings
    num_pattern = re.compile(
        r'([$€£¥₩₹₽₺]|R\$)?\s*'  # optional currency symbol
        r'([\d]+[,.\s]?[\d]*(?:[,.\s]\d+)?)\s*'  # number (handles 1,500 / 1.5 / 1 500)
        r'(\w+)?',  # optional unit word after
        re.UNICODE
    )
    
    for m in num_pattern.finditer(text):
        cur_sym = m.group(1) or ''
        num_raw = m.group(2).replace(' ', '').replace('\u00a0', '')
        unit_word = (m.group(3) or '').lower()
        
        # Normalize number (handle European comma decimals)
        if ',' in num_raw and '.' in num_raw:
            num_raw = num_raw.replace(',', '')  # 1,500.00
        elif ',' in num_raw and len(num_raw.split(',')[-1]) <= 2:
            num_raw = num_raw.replace(',', '.')  # 1,5 → 1.5 (European)
        else:
            num_raw = num_raw.replace(',', '')  # 1,500 → 1500
        
        # Handle ES/PT thousand-dot: 1.800 (3 digits after dot = thousands sep)
        if '.' in num_raw:
            parts = num_raw.split('.')
            if len(parts) == 2 and len(parts[1]) == 3 and parts[0].isdigit():
                num_raw = num_raw.replace('.', '')  # 1.800 → 1800
        
        try:
            val = float(num_raw)
        except ValueError:
            continue
        
        if val == 0:
            continue
            
        # Determine magnitude (match longest pattern first)
        mag = ''
        multiplier = 1.0
        for mag_word, mag_val in sorted(_MAG_PATTERNS.items(), key=lambda x: -len(x[0])):
            if unit_word == mag_word or (len(mag_word) >= 3 and unit_word.startswith(mag_word)):
                multiplier = mag_val
                if mag_val >= 1e12: mag = 'T'
                elif mag_val >= 1e9: mag = 'B'
                elif mag_val >= 1e6: mag = 'M'
                elif mag_val >= 1e3: mag = 'K'
                break
        
        # Determine currency
        currency = ''
        if cur_sym:
            currency = _CURRENCY_MAP.get(cur_sym, '')
        elif unit_word:
            currency = _CURRENCY_MAP.get(unit_word, '')
        
        # Special: Indian crore = 10M
        if unit_word in ('crore', 'crores'):
            multiplier = 1e7
            mag = 'M'
        
        normalized = val * multiplier
        unit_type = 'currency' if currency else ('%' if unit_word in ('percent', '%', 'pct') else '')
        
        if normalized > 0:
            results.append(NumVal(raw=m.group(0).strip(), value=normalized, unit=unit_type, currency=currency, magnitude=mag))
    
    # Secondary pass: CJK + Thai + Bengali + Hebrew + Urdu magnitude (scripts not caught by \w+ Latin regex)
    _NON_LATIN_MAG = '|'.join(sorted([
        # CJK
        '兆', '億', '万', '조', '억', '만',
        # Thai
        'ล้านล้าน', 'พันล้าน', 'ล้าน', 'แสน', 'พัน',
        # Bengali
        'বিলিয়ন', 'মিলিয়ন', 'কোটি', 'লাখ',
        # Hebrew
        'מיליארד', 'מיליון', 'אלף',
        # Urdu
        'ارب', 'کروڑ', 'لاکھ',
    ], key=len, reverse=True))
    for m in re.finditer(rf'(\d+\.?\d*)\s*({_NON_LATIN_MAG})', text):
        val = float(m.group(1))
        mag_char = m.group(2)
        multiplier = _MAG_PATTERNS.get(mag_char, 1.0)
        normalized = val * multiplier
        mag = 'T' if multiplier >= 1e12 else ('B' if multiplier >= 1e8 else ('M' if multiplier >= 1e4 else 'K'))
        results.append(NumVal(raw=m.group(0), value=normalized, unit='', currency='', magnitude=mag))
    
    # Tertiary pass: compound CJK/KR magnitudes (6조4000억 = 6.4兆)
    _CJK_MAG_CHARS = {'조': 1e12, '억': 1e8, '만': 1e4, '兆': 1e12, '億': 1e8, '万': 1e4, '萬': 1e4}
    _cjk_mag_re = '|'.join(sorted(_CJK_MAG_CHARS.keys(), key=len, reverse=True))
    for compound_m in re.finditer(rf'((\d+\.?\d*)\s*({_cjk_mag_re})){{2,}}', text):
        segments = re.findall(rf'(\d+\.?\d*)\s*({_cjk_mag_re})', compound_m.group())
        if len(segments) >= 2:
            total = sum(float(n) * _CJK_MAG_CHARS[m] for n, m in segments)
            mag = 'T' if total >= 1e12 else ('B' if total >= 1e8 else 'M')
            results.append(NumVal(raw=compound_m.group(), value=total, unit='', currency='', magnitude=mag))

    # Quaternary pass: Indian compound (lakh crore)
    for m in re.finditer(r'(\d+\.?\d*)\s*lakh\s*crores?', text, re.IGNORECASE):
        val = float(m.group(1)) * 1e12  # lakh × crore = 1e5 × 1e7
        results.append(NumVal(raw=m.group(), value=val, unit='', currency='', magnitude='T'))

    return results


def extract_zh_numbers(zh_body: str) -> list[NumVal]:
    """Extract numbers from Chinese output."""
    results = []
    
    # Pattern: number + 兆/億/萬 + optional currency
    zh_pattern = re.compile(
        r'([\d,]+\.?\d*)\s*(兆|億|萬)?\s*(美元|歐元|英鎊|日圓|日元|韓元|盧布|人民幣|台幣|新台幣|澳元|加元|先令|%)?'
    )
    
    for m in zh_pattern.finditer(zh_body):
        num_raw = m.group(1).replace(',', '')
        zh_mag = m.group(2) or ''
        zh_cur = m.group(3) or ''
        
        try:
            val = float(num_raw)
        except ValueError:
            continue
        
        if val == 0:
            continue
        
        multiplier = _ZH_MAG.get(zh_mag, 1.0)
        normalized = val * multiplier
        
        mag = ''
        if zh_mag == '兆': mag = 'T'
        elif zh_mag == '億': mag = 'B'  # Note: 億=1e8, but in news context 18億≈1.8B
        elif zh_mag == '萬': mag = 'M'
        
        currency = _CURRENCY_MAP.get(zh_cur, '')
        unit_type = 'currency' if currency else ('%' if zh_cur == '%' else '')
        
        results.append(NumVal(raw=m.group(0).strip(), value=normalized, unit=unit_type, currency=currency, magnitude=mag))
    
    return results


