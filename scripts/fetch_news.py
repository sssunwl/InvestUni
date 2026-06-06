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
    """Return 'pre_market' or 'post_market' based on current time."""
    if market == 'us':
        now_ny = now_utc.astimezone(NY_TZ)
        t = now_ny.hour * 60 + now_ny.minute
        # Regular: 09:30-16:00 ET → pre if before close
        return 'pre_market' if t < 16 * 60 else 'post_market'
    elif market == 'crypto':
        return 'all'
    else:
        now_hk = now_utc.astimezone(HK_TZ)
        t = now_hk.hour * 60 + now_hk.minute
        close = {'hk': 16 * 60, 'tw': 13 * 60 + 30, 'jp': 14 * 60 + 30}
        return 'pre_market' if t < close.get(market, 16 * 60) else 'post_market'


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
        print(f"Fetching {market}...")
        news = fetch_google_news(query, limit=3)
        if not news:
            print(f"  Skipping {market} (no results)")
            continue

        if market == 'crypto':
            data['crypto'] = {'updated_at': now_str, 'news': news}
        else:
            section = get_section(market, now_utc)
            data[market][section] = {'updated_at': now_str, 'news': news}
            print(f"  Updated {market}/{section} with {len(news)} articles")

    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved → {data_path}")


if __name__ == '__main__':
    main()
