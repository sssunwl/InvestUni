import json
import requests
from datetime import datetime
import pytz

try:
    import yfinance as yf
    YF_OK = True
except ImportError:
    YF_OK = False

HKT = pytz.timezone('Asia/Hong_Kong')

STOCK_CFG = {
    'us':     {'symbols': ['MU','NVDA','AAPL','TSLA','SPY'],                             'prefix': '$'},
    'hk':     {'symbols': ['0700.HK','1024.HK','9988.HK','3690.HK','1299.HK'],          'prefix': 'HK$'},
    'tw':     {'symbols': ['2330.TW','2317.TW','2454.TW','2382.TW','2308.TW'],          'prefix': 'NT$'},
    'jp':     {'symbols': ['6758.T','7203.T','9984.T','7974.T','6501.T'],                'prefix': '¥'},
}

CRYPTO_MAP = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'BNB': 'binancecoin',
    'SOL': 'solana',
    'XRP': 'ripple',
}


def fmt_price(price, prefix='$'):
    if price is None:
        return '--'
    if price >= 10000:
        return f"{prefix}{price:,.0f}"
    elif price >= 100:
        return f"{prefix}{price:,.1f}"
    elif price >= 1:
        return f"{prefix}{price:.2f}"
    else:
        return f"{prefix}{price:.4f}"


def fmt_pct(pct):
    if pct is None:
        return '--'
    sign = '+' if pct >= 0 else ''
    return f"{sign}{pct:.2f}%"


def direction(pct):
    if pct is None or abs(pct) < 0.005:
        return 'flat'
    return 'up' if pct > 0 else 'dn'


def fetch_stocks(mkt, symbols, prefix):
    if not YF_OK:
        return [{'symbol': s, 'price': '--', 'pct': '--', 'dir': 'flat'} for s in symbols]
    result = []
    try:
        tickers = ' '.join(symbols)
        raw = yf.download(tickers, period='2d', interval='1d',
                          auto_adjust=True, progress=False, group_by='ticker')
        for sym in symbols:
            try:
                col = raw[sym]['Close'] if len(symbols) > 1 else raw['Close']
                closes = col.dropna()
                if len(closes) == 0:
                    raise ValueError('no data')
                cur = float(closes.iloc[-1])
                prev = float(closes.iloc[-2]) if len(closes) >= 2 else cur
                pct = (cur - prev) / prev * 100 if prev else 0
                result.append({
                    'symbol': sym,
                    'price': fmt_price(cur, prefix),
                    'pct':   fmt_pct(pct),
                    'dir':   direction(pct),
                })
            except Exception as e:
                print(f"  {sym}: {e}")
                result.append({'symbol': sym, 'price': '--', 'pct': '--', 'dir': 'flat'})
    except Exception as e:
        print(f"  Download failed ({mkt}): {e}")
        result = [{'symbol': s, 'price': '--', 'pct': '--', 'dir': 'flat'} for s in symbols]
    return result


def fetch_crypto():
    result = []
    try:
        ids = ','.join(CRYPTO_MAP.values())
        url = (f"https://api.coingecko.com/api/v3/simple/price"
               f"?ids={ids}&vs_currencies=usd&include_24hr_change=true")
        r = requests.get(url, timeout=12, headers={'Accept': 'application/json'})
        r.raise_for_status()
        data = r.json()
        for sym, cg_id in CRYPTO_MAP.items():
            d = data.get(cg_id, {})
            price = d.get('usd')
            pct = d.get('usd_24h_change')
            result.append({
                'symbol': sym,
                'price':  fmt_price(price, '$') if price else '--',
                'pct':    fmt_pct(pct) if pct is not None else '--',
                'dir':    direction(pct) if pct is not None else 'flat',
            })
    except Exception as e:
        print(f"  Crypto error: {e}")
        result = [{'symbol': s, 'price': '--', 'pct': '--', 'dir': 'flat'} for s in CRYPTO_MAP]
    return result


def main():
    now = datetime.now(HKT).strftime('%Y-%m-%d %H:%M HKT')
    out = {'updated_at': now}

    for mkt, cfg in STOCK_CFG.items():
        print(f"Fetching {mkt} ({', '.join(cfg['symbols'])})...")
        out[mkt] = {'stocks': fetch_stocks(mkt, cfg['symbols'], cfg['prefix'])}

    print("Fetching crypto...")
    out['crypto'] = {'stocks': fetch_crypto()}

    with open('data/stocks.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"stocks.json saved — {now}")


if __name__ == '__main__':
    main()
