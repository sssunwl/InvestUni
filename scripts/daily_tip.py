#!/usr/bin/env python3
"""Send daily investment tip + news digest to Telegram."""

import json
import os
import sys
import requests
from datetime import datetime
import pytz

BOT_TOKEN = os.environ.get('TG_BOT_TOKEN', '')
CHAT_ID = os.environ.get('TG_CHAT_ID', '')
ACADEMY_URL = 'https://sssunwl.github.io/InvestUni'

HK_TZ = pytz.timezone('Asia/Hong_Kong')
NY_TZ = pytz.timezone('America/New_York')

TIPS = [
    # Volume signals
    ("📊 成交量信號 — 放量上漲",
     "成交量大幅增加同時價格持續上漲，代表多方主力積極入場。\n"
     "這是最健康的買入型態，趨勢可持續性強，跟進比追高更安全。"),
    ("📊 成交量信號 — 縮量上漲",
     "漲勢靠慣性維持，新的買盤沒有進場。這是危險訊號——\n"
     "動能正在悄悄流失，持倉者考慮部分止盈，不宜追入。"),
    ("📊 成交量信號 — 放量下跌",
     "成交量爆增同時價格急跌，空方主力大量出貨。\n"
     "是空方力量最明確的表現，此時抄底是最常見的散戶陷阱。"),
    ("📊 成交量信號 — 高位縮量",
     "股票在高位運行時成交量萎縮，主力悄悄退場的訊號。\n"
     "散戶接盤能力不足，反轉風險急劇上升，應考慮逐步減倉。"),
    ("📊 成交量信號 — 量價背離",
     "價格創新高但成交量反而下降——量與價走向相反。\n"
     "這是趨勢可能反轉的重要預警，多方背離時減倉是正確的選擇。"),
    ("📊 成交量信號 — 異常成交量",
     "成交量突然爆增至平日數倍，通常與重大消息掛鉤。\n"
     "先觀察方向確認，再決定操作。方向未明前，耐心等待比衝動更值錢。"),
    ("📊 成交量信號 — 溫和放量",
     "成交量平穩有節奏地小幅增加，是最健康的上漲型態。\n"
     "市場充分消化籌碼，趨勢可持續性最強，這才是教科書式的買點。"),
    ("📊 成交量信號 — 成交量極端",
     "成交量達到歷史極端水平（極高或極低）。\n"
     "極高量可能代表主力出貨完成；極低量代表大行情蓄勢待發，注意突破方向。"),

    # K-line signals
    ("🕯 K線信號 — 錘子線",
     "下影線很長（至少是實體的2倍），出現在下跌趨勢末端。\n"
     "代表空方打壓後被多方強力反攻，是底部反轉的強力信號。\n"
     "出現在支撐位附近時效果最佳，次日確認後可考慮買入。"),
    ("🕯 K線信號 — 射擊之星",
     "上影線很長，出現在上漲趨勢高位，代表多方衝高後遭空方強力壓制。\n"
     "是頂部反轉的經典信號，持倉者看到這根K線要提高警覺。"),
    ("🕯 K線信號 — 十字星",
     "開盤與收盤幾乎相同，多空雙方勢力相當，市場陷入猶豫。\n"
     "本身不構成操作信號，需等待下一根K線確認方向後再行動。"),
    ("🕯 K線信號 — 晨星形態",
     "三根K線組合：大陰線 → 跳空小實體 → 大陽線收復。\n"
     "出現在下跌趨勢底部，是強力的底部反轉信號，等第三根陽線收盤確認後進場。"),
    ("🕯 K線信號 — 吞噬形態",
     "大陽線完全吞噬前一根陰線的實體，多方力量壓倒性勝出。\n"
     "吞噬的實體越大信號越強，吞噬當天或次日可考慮建倉。"),

    # Options knowledge
    ("⚡ 期權入門 — Call vs Put",
     "Call（看漲）= 賭正股上漲的彩券，最大損失僅限保費。\n"
     "Put（看跌）= 保護資產的保險單，大盤崩盤時的最佳對沖工具。\n"
     "兩者的共同點：損失有限，但需要時間和方向都判斷對。"),
    ("⚡ 期權入門 — Theta 時間小偷",
     "每過一天，期權的時間溢價就自動融化一部分。\n"
     "Theta 對期權買方是敵人，對期權賣方是朋友。\n"
     "這就是為什麼買了期權卻一直不動，你會慢慢虧損。"),
    ("⚡ 期權入門 — IV Crush 陷阱",
     "財報前IV被炒高，財報出來後IV瞬間暴跌。\n"
     "即使股票真的大漲，保費蒸發的損失可能超過獲利——你賭對了方向還是虧錢。\n"
     "解法：財報後IV回落時再建倉，或用Bull Call Spread代替。"),
    ("⚡ 期權入門 — Bull Call Spread",
     "同時買入低履約價Call + 賣出高履約價Call。\n"
     "最大風險 = 建倉成本（固定），最大利潤 = 價差寬度 - 成本。\n"
     "賣出的Call補貼了保費，抗Theta流逝能力遠高於單腿買Call。"),
    ("⚡ 期權入門 — Long Straddle",
     "同時買入相同履約價的Call + Put，不賭方向，只賭大地震。\n"
     "大盤走出單邊行情時回報可達100-160%+。\n"
     "但若市場原地不動，雙邊被Theta侵蝕，兩邊都虧——這叫「雙殺」。"),

    # Trading mechanics
    ("📖 投資名詞 — 中間價 Mid Price",
     "永遠用限價單以Bid與Ask的中間價建倉，永遠拒絕市價單。\n"
     "市價單 = 讓做市商決定你的成交價，等於主動送錢給對方。\n"
     "這是「不看盤流派」最重要的一條鋼鐵紀律。"),
    ("📖 投資名詞 — GTC 條件單",
     "Good 'Til Cancelled——撤單前有效，在券商雲端掛單長達90天。\n"
     "建倉後立刻掛上GTC止盈單，交給自動化全天候執行。\n"
     "條件達成自動成交，你可以去享受生活，不需要盯盤。"),
    ("📖 投資名詞 — VWAP",
     "成交量加權平均價，機構投資者評估交易成本的基準線。\n"
     "股價在VWAP上方 = 短線強勢；跌破VWAP = 短線偏弱。\n"
     "這條線是機構的心理防線，也是短線交易者最重要的參考指標之一。"),
    ("📖 投資名詞 — Opening Range",
     "開盤後前15-30分鐘形成的最高價與最低價區間。\n"
     "突破OR高點 = 看漲信號；跌破OR低點 = 看跌信號。\n"
     "這個區間是當日多空雙方的第一場博弈結果，意義重大。"),

    # Risk management
    ("💡 風險管理 — 位置大小控制",
     "手數×10 = 最大虧損×10 = 心理壓力×10 = 決策崩潰風險×10。\n"
     "實驗期間嚴格限制1-2手，買到睡得著的心理安全感才是最重要的。\n"
     "帳戶活著，機會永遠在。帳戶歸零，一切歸零。"),
    ("💡 風險管理 — 拒絕高頻操作",
     "每次交易都有Bid-Ask Spread與手續費摩擦損耗。\n"
     "高頻進出 = 讓券商和做市商持續「抽水」，利潤被慢性吃掉。\n"
     "少動、精準、等待高勝率機會，這才是長期生存之道。"),
    ("💡 風險管理 — 黃金交易窗口",
     "開盤後5-10分鐘：等市場情緒理智後再建倉，不要追開盤衝動。\n"
     "收盤前30分鐘：機構尾盤調倉，單邊趨勢最清晰的時段。\n"
     "財報日、FOMC、NFP：波動率暴漲，Straddle的黃金場景。"),
    ("💡 風險管理 — 操盤SOP",
     "① 等開盤5-10分鐘 → ② 以中間價建倉 → ③ 立刻退出畫面\n"
     "→ ④ 重新掛上GTC止盈限價單 → ⑤ 關閉軟體，去享受生活。\n"
     "能夠執行這個SOP的人，已經比99%的散戶更理性了。"),
]


def load_news():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, '..', 'data', 'news.json')
    try:
        with open(os.path.normpath(path), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def format_news_block(items, limit=3):
    if not items:
        return '  暫無最新資料\n'
    lines = []
    for item in items[:limit]:
        title = item.get('title', '')[:60]
        tickers = ' '.join(f"#{t}" for t in item.get('related', [])[:2])
        url = item.get('url', '')
        line = f'  • <a href="{url}">{title}</a>'
        if tickers:
            line += f' {tickers}'
        lines.append(line)
    return '\n'.join(lines) + '\n'


def get_tip(now_hk):
    idx = now_hk.timetuple().tm_yday % len(TIPS)
    return TIPS[idx]


def build_morning_message(data, now_hk):
    """盤後總結 — 09:00 HKT，回顧美股盤後 + 亞洲開市預覽"""
    date_str = now_hk.strftime('%Y年%m月%d日')
    tip_title, tip_body = get_tip(now_hk)

    us_post = data.get('us', {}).get('post_market', {}).get('news', [])
    hk_pre = data.get('hk', {}).get('pre_market', {}).get('news', [])
    tw_pre = data.get('tw', {}).get('pre_market', {}).get('news', [])
    crypto = data.get('crypto', {}).get('news', [])

    msg = (
        f"🌅 <b>Suniverse 投資學堂 — 早安播報</b>\n"
        f"📅 {date_str}　09:00 HKT\n\n"
        f"🇺🇸 <b>美股盤後精選</b>\n"
        f"{format_news_block(us_post)}\n"
        f"🇭🇰 <b>港股今日前瞻</b>\n"
        f"{format_news_block(hk_pre)}\n"
        f"🇹🇼 <b>台股今日前瞻</b>\n"
        f"{format_news_block(tw_pre)}\n"
        f"🌐 <b>加密貨幣市場</b>\n"
        f"{format_news_block(crypto, limit=2)}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💡 <b>{tip_title}</b>\n"
        f"{tip_body}\n\n"
        f"📚 <a href=\"{ACADEMY_URL}\">投資學堂 完整版</a>"
    )
    return msg


def build_afternoon_message(data, now_hk):
    """盤前預覽 — 16:30 HKT，美股即將開市"""
    date_str = now_hk.strftime('%Y年%m月%d日')
    tip_title, tip_body = get_tip(now_hk)

    us_pre = data.get('us', {}).get('pre_market', {}).get('news', [])
    crypto = data.get('crypto', {}).get('news', [])

    msg = (
        f"🌇 <b>Suniverse 投資學堂 — 美股盤前預覽</b>\n"
        f"📅 {date_str}　16:30 HKT\n\n"
        f"🇺🇸 <b>美股盤前精選</b>\n"
        f"{format_news_block(us_pre)}\n"
        f"🌐 <b>加密貨幣市場</b>\n"
        f"{format_news_block(crypto, limit=2)}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💡 <b>{tip_title}</b>\n"
        f"{tip_body}\n\n"
        f"📚 <a href=\"{ACADEMY_URL}\">投資學堂 完整版</a>"
    )
    return msg


def send_tg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': False,
    }
    r = requests.post(url, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()


def main():
    if not BOT_TOKEN:
        print("ERROR: TG_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    if not CHAT_ID:
        print("ERROR: TG_CHAT_ID not set", file=sys.stderr)
        sys.exit(1)

    now_utc = datetime.now(pytz.utc)
    now_hk = now_utc.astimezone(HK_TZ)
    utc_hour = now_utc.hour

    data = load_news()

    # 01:00 UTC = 09:00 HKT → morning message
    # 08:30 UTC = 16:30 HKT → afternoon message
    if utc_hour < 5:
        msg = build_morning_message(data, now_hk)
        label = '盤後總結'
    else:
        msg = build_afternoon_message(data, now_hk)
        label = '盤前預覽'

    print(f"Sending {label} message...")
    result = send_tg(msg)
    if result.get('ok'):
        print("Sent successfully!")
    else:
        print(f"Failed: {result}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
