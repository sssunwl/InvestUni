#!/usr/bin/env python3
"""Fetch market news from Google News RSS and update data/news.json"""

import feedparser
import json
import os
import sys
import html
from datetime import datetime
from urllib.parse import quote
import pytz

HK_TZ = pytz.timezone('Asia/Hong_Kong')
NY_TZ = pytz.timezone('America/New_York')

QUERIES = {
    'us':     '美股 市場行情',
    'hk':     '港股 恒生指數',
    'tw':     '台股 加權指數',
    'jp':     '日股 日經225',
    'crypto': '比特幣 以太坊 加密貨幣',
}

TICKER_MAP = {
    'NVDA':    ['NVIDIA', '輝達', '英偉達'],
    'AAPL':    ['蘋果', 'Apple', 'iPhone'],
    'TSLA':    ['特斯拉', 'Tesla'],
    'MU':      ['美光', 'Micron'],
    'TSM':     ['台積電', 'TSMC'],
    'AMZN':    ['亞馬遜', 'Amazon'],
    'MSFT':    ['微軟', 'Microsoft'],
    'GOOGL':   ['谷歌', 'Google', 'Alphabet'],
    'META':    ['Meta', '臉書', 'Facebook'],
    'PLTR':    ['Palantir', '鈀蘭提爾'],
    '^HSI':    ['恒生', '恒指', 'HSI'],
    '^TWII':   ['加權指數', 'TAIEX'],
    '^N225':   ['日經', 'Nikkei', 'N225'],
    'SPY':     ['標普', 'S&P 500', 'S&P500'],
    'QQQ':     ['納指', 'Nasdaq', '那斯達克'],
    '0700.HK': ['騰訊', 'Tencent'],
    '9988.HK': ['阿里巴巴', 'Alibaba'],
    'BTC':     ['比特幣', 'Bitcoin'],
    'ETH':     ['以太坊', 'Ethereum'],
    'BNB':     ['幣安', 'BNB'],
}


def extract_tickers(text):
    found = []
    for ticker, keywords in TICKER_MAP.items():
        for kw in keywords:
            if kw in text and ticker not in found:
                found.append(ticker)
                break
    return found


def fetch_google_news(query, limit=3):
    url = (
        f"https://news.google.com/rss/search"
        f"?q={quote(query)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    )
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; InvestUni/1.0)'}
    try:
        feed = feedparser.parse(url, request_headers=headers)
        items = []
        for entry in feed.entries[:limit]:
            title = html.unescape(entry.get('title', ''))
            link = entry.get('link', '')
            source = ''
            if hasattr(entry, 'source') and isinstance(entry.source, dict):
                source = entry.source.get('title', '')
            items.append({
                'title': title,
                'url': link,
                'source': source,
                'related': extract_tickers(title),
            })
        return items
    except Exception as e:
        print(f"[WARN] Failed to fetch '{query}': {e}", file=sys.stderr)
        return []


def get_section(market, now_utc):
    """
    Return 'pre_market', 'post_market', 'all', or None (skip).

    盤前 = 30-45 min window before market opens (preview)
    盤後 = after all sessions end, including after-hours/夜盤 (daily summary)
    """
    if market == 'crypto':
        return 'all'

    now_hk = now_utc.astimezone(HK_TZ)
    hk_t = now_hk.hour * 60 + now_hk.minute

    if market == 'us':
        now_ny = now_utc.astimezone(NY_TZ)
        ny_t = now_ny.hour * 60 + now_ny.minute
        # Pre: 08:45–09:30 ET (45 min window before regular open)
        if 8 * 60 + 45 <= ny_t < 9 * 60 + 30:
            return 'pre_market'
        # Post: after 20:00 ET (after-hours/夜盤 ends) OR HKT 07:00–13:00 (US night just ended)
        if ny_t >= 20 * 60 or (7 * 60 <= hk_t <= 13 * 60):
            return 'post_market'
        return None

    elif market == 'hk':
        # Pre: 08:45–09:30 HKT
        if 8 * 60 + 45 <= hk_t < 9 * 60 + 30:
            return 'pre_market'
        # Post: 16:30+ HKT (30 min after close)
        if hk_t >= 16 * 60 + 30:
            return 'post_market'
        return None

    elif market == 'tw':
        # Pre: 08:30–09:00 HKT (TW opens 09:00 HKT)
        if 8 * 60 + 30 <= hk_t < 9 * 60:
            return 'pre_market'
        # Post: 14:00+ HKT (30 min after close at 13:30 HKT)
        if hk_t >= 14 * 60:
            return 'post_market'
        return None

    elif market == 'jp':
        # Pre: 07:30–08:15 HKT (JP opens 08:00 HKT)
        if 7 * 60 + 30 <= hk_t < 8 * 60 + 15:
            return 'pre_market'
        # Post: 15:00+ HKT (30 min after close at 14:30 HKT)
        if hk_t >= 15 * 60:
            return 'post_market'
        return None

    return None


def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def ensure_structure(data):
    template_section = {'updated_at': None, 'news': []}
    for m in ['us', 'hk', 'tw', 'jp']:
        data.setdefault(m, {})
        data[m].setdefault('pre_market', dict(template_section))
        data[m].setdefault('post_market', dict(template_section))
    data.setdefault('crypto', {'updated_at': None, 'news': []})
    return data


def main():
    now_utc = datetime.now(pytz.utc)
    now_hk = now_utc.astimezone(HK_TZ)
    now_str = now_hk.strftime('%Y-%m-%d %H:%M HKT')

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, '..', 'data', 'news.json')
    data_path = os.path.normpath(data_path)

    data = ensure_structure(load_json(data_path))

    for market, query in QUERIES.items():
        section = get_section(market, now_utc)
        if section is None:
            print(f"  [{market}] Not in update window — skip")
            continue

        print(f"Fetching {market} ({section})...")
        news = fetch_google_news(query, limit=3)
        if not news:
            print(f"  [{market}] No results")
            continue

        if market == 'crypto':
            data['crypto'] = {'updated_at': now_str, 'news': news}
        else:
            data[market][section] = {'updated_at': now_str, 'news': news}
        print(f"  [{market}] {section} updated with {len(news)} articles")

    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved → {data_path}")


if __name__ == '__main__':
    main()
