#!/usr/bin/env python3
"""
今すぐチェック - 日中いつでも実行
イントラデイデータ + 決算/経済指標アラート + トレンド分析 + Claudeプロンプト
"""

import yfinance as yf
import feedparser
import ssl
import os
import subprocess
import urllib.request
import json
import numpy as np
from datetime import datetime, date, timedelta

ssl._create_default_https_context = ssl._create_unverified_context

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "now.html")
WATCHLIST_FILE = os.path.join(SCRIPT_DIR, "watchlist.json")
GITHUB_REPO = os.path.join(SCRIPT_DIR, "stock-morning-pages")
CLAUDE_PROJECT = "https://claude.ai/project/019eee77-ec0f-76d0-9445-b731633c66ca"

BASE_UNIVERSE = {
    # 低〜中価格帯・流動性高
    "9434 ソフトバンク": "9434.T",
    "1570 日経レバETF": "1570.T",
    "1571 日経インバースETF": "1571.T",
    "2516 グロース250ETF": "2516.T",
    "4565 そーせいG": "4565.T",
    "3697 SHIFT": "3697.T",
    "2413 エムスリー": "2413.T",
    "4478 フリー": "4478.T",
    "3765 ガンホー": "3765.T",
    "6050 イー・ガーディアン": "6050.T",
    "3672 オルトプラス": "3672.T",
    "6200 インソース": "6200.T",
    "2370 メディネット": "2370.T",
    "8306 三菱UFJ": "8306.T",
    "6920 レーザーテック": "6920.T",
    "8035 東京エレクトロン": "8035.T",
    # 商品ETF
    "1540 純金信託": "1540.T",
    "1699 原油ETF": "1699.T",
    "1687 農産物ETF": "1687.T",
}

JP_LABELS = {
    "Non-Farm Employment Change": "米雇用統計",
    "CPI m/m": "米CPI",
    "CPI y/y": "米CPI(年率)",
    "Core CPI m/m": "米コアCPI",
    "FOMC Statement": "FOMC声明",
    "Federal Funds Rate": "米政策金利",
    "GDP q/q": "GDP速報",
    "Unemployment Rate": "失業率",
    "Retail Sales m/m": "米小売売上高",
    "ISM Manufacturing PMI": "ISM製造業",
    "BOJ Policy Rate": "日銀政策金利",
    "Monetary Policy Statement": "金融政策声明",
    "PPI m/m": "米PPI",
    "ADP Non-Farm Employment Change": "ADP雇用",
    "Trade Balance": "貿易収支",
    "Consumer Confidence": "消費者信頼感",
}

SURGE_UNIVERSE = {
    # 超低価格帯（〜50円）穴場・材料株
    "2370 メディネット": "2370.T", "3825 リミックスポイント": "3825.T",
    "3672 オルトプラス": "3672.T", "6552 GameWith": "6552.T",
    "3558 ロコンド": "3558.T", "6890 フェローテック": "6890.T",
    # 低価格帯（100〜500円）見逃されやすい銘柄
    "3672 オルトプラス": "3672.T", "9434 ソフトバンク": "9434.T",
    "1571 日経インバース": "1571.T", "2516 グロース250ETF": "2516.T",
    "8411 みずほFG": "8411.T", "9432 NTT": "9432.T",
    "7201 日産自動車": "7201.T", "5401 日本製鉄": "5401.T",
    "3765 ガンホー": "3765.T", "6200 インソース": "6200.T",
    "6050 イー・ガーディアン": "6050.T", "4565 そーせいG": "4565.T",
    "2413 エムスリー": "2413.T", "8306 三菱UFJ": "8306.T",
    "8316 三井住友FG": "8316.T", "3697 SHIFT": "3697.T",
    "4478 フリー": "4478.T", "2371 カカクコム": "2371.T",
    "4385 メルカリ": "4385.T", "6098 リクルートHD": "6098.T",
    "7203 トヨタ自動車": "7203.T", "8604 野村HD": "8604.T",
    "4568 第一三共": "4568.T", "4519 中外製薬": "4519.T",
    "6367 ダイキン": "6367.T", "7751 キヤノン": "7751.T",
    "6594 日本電産": "6594.T", "6762 TDK": "6762.T",
    "6902 デンソー": "6902.T", "8766 東京海上HD": "8766.T",
    "7267 ホンダ": "7267.T", "6503 三菱電機": "6503.T",
    "6501 日立製作所": "6501.T", "6758 ソニーG": "6758.T",
    "9983 ファストリ": "9983.T", "9984 ソフトバンクG": "9984.T",
    "6920 レーザーテック": "6920.T", "8035 東京エレクトロン": "8035.T",
    "6857 アドバンテスト": "6857.T", "6861 キーエンス": "6861.T",
    "7974 任天堂": "7974.T", "1570 日経レバETF": "1570.T",
    "9433 KDDI": "9433.T", "1540 純金信託": "1540.T",
    "1699 原油ETF": "1699.T", "1687 農産物ETF": "1687.T",
    # グロース・見逃されやすい小型株
    "4194 ビジョナル": "4194.T", "4011 ヘッドウォータース": "4011.T",
    "4384 ラクスル": "4384.T", "7342 ウェルスナビ": "7342.T",
    "4586 メドレックス": "4586.T", "6027 弁護士ドットコム": "6027.T",
    "6552 GameWith": "6552.T", "3558 ロコンド": "3558.T",
    "4883 モダリス": "4883.T", "5135 BlueMeme": "5135.T",
}

def get_jquants_stocks_now():
    """J-Quantsから全銘柄リストを取得"""
    try:
        token_path = os.path.join(SCRIPT_DIR, "jquants_token.txt")
        if not os.path.exists(token_path):
            return {}
        with open(token_path) as f:
            api_key = f.read().strip()
        req = urllib.request.Request(
            'https://api.jquants.com/v2/equities/master',
            headers={'x-api-key': api_key}
        )
        res = urllib.request.urlopen(req, timeout=15)
        data = json.loads(res.read())
        stocks = data[list(data.keys())[0]]
        result = {}
        for s in stocks:
            if s.get('MktNm') not in ['プライム', 'スタンダード', 'グロース']:
                continue
            code5 = s.get('Code', '')
            if not code5.isdigit() or len(code5) != 5:
                continue
            code4 = code5[:4]
            name = s.get('CoName', code4).strip()
            result[f"{code4} {name}"] = f"{code4}.T"
        return result
    except:
        return {}

def get_surge_scanner_intraday():
    """イントラデイ版急騰スキャナー（J-Quants全銘柄対応）"""
    all_stocks = get_jquants_stocks_now()
    if all_stocks:
        import random
        existing = set(SURGE_UNIVERSE.values())
        extra = [(k,v) for k,v in all_stocks.items() if v not in existing]
        random.shuffle(extra)
        scan = dict(SURGE_UNIVERSE)
        scan.update(dict(extra[:320]))
        print(f"  固定{len(SURGE_UNIVERSE)}銘柄+J-Quants追加{min(320,len(extra))}銘柄をスキャン")
    else:
        scan = SURGE_UNIVERSE
    symbols = list(scan.values())
    name_map = {v: k for k, v in scan.items()}
    surges = []
    try:
        # 日足で出来高急増を検出（5分足は時間がかかるので日足ベース）
        data = yf.download(
            symbols, period="25d", interval="1d",
            group_by="ticker", auto_adjust=True, progress=False, threads=True
        )
    except:
        return []

    for sym in symbols:
        try:
            hist = data[sym] if sym in data.columns.get_level_values(0) else None
            if hist is None or len(hist) < 22:
                continue
            hist = hist.dropna()
            if len(hist) < 22:
                continue

            closes = hist["Close"].values.astype(float)
            volumes = hist["Volume"].values.astype(float)
            curr = closes[-1]
            prev = closes[-2]
            vol_today = volumes[-1]
            vol_avg20 = np.mean(volumes[-22:-2])

            if vol_avg20 == 0:
                continue

            vol_ratio = vol_today / vol_avg20
            change_pct = (curr - prev) / prev * 100
            surge_score = vol_ratio * (1 + abs(change_pct) / 5)

            if vol_ratio >= 2.0 or abs(change_pct) >= 2.0:
                surges.append({
                    "name": name_map.get(sym, sym),
                    "price": round(curr, 0),
                    "change_pct": round(change_pct, 2),
                    "vol_ratio": round(vol_ratio, 1),
                    "surge_score": round(surge_score, 1),
                })
        except:
            continue

    surges.sort(key=lambda x: x["surge_score"], reverse=True)
    return surges[:8]

def get_surge_continuation_filter(stocks_data):
    """急騰継続フィルター - ChatGPTの条件を実装
    翌日続伸の可能性が高い銘柄を特定する"""
    qualified = []
    for name, d in stocks_data:
        if not d:
            continue
        score = 0
        signals = []

        # ① 出来高が前日比3倍以上
        if d.get("vol_pace", 0) >= 80:  # 前日出来高の80%以上のペース
            vol_ratio_estimated = d["vol_pace"] / 100 * (390 / (datetime.now().hour * 60 + datetime.now().minute - 9*60-20 + 1))
            if vol_ratio_estimated >= 3 or d["vol_pace"] >= 200:
                score += 30
                signals.append("出来高急増🔥")

        # ② VWAPを維持（現値がVWAP以上）
        vwap_above = "上" in d.get("vwap_pos", "")
        if vwap_above:
            score += 25
            signals.append("VWAP維持✅")

        # ③ 高値圏を維持（現値がイントラデイ高値の97%以上）
        if d.get("high", 0) > 0 and d.get("price", 0) > 0:
            near_high_ratio = d["price"] / d["high"]
            if near_high_ratio >= 0.97:
                score += 20
                signals.append("高値圏維持📈")

        # ④ 上ヒゲが短い（上ヒゲ < レンジ全体の20%）
        if d.get("high") and d.get("low") and d.get("price"):
            total_range = d["high"] - d["low"]
            upper_shadow = d["high"] - d["price"]
            if total_range > 0 and upper_shadow / total_range < 0.2:
                score += 15
                signals.append("上ヒゲ短い✅")

        # ⑤ モメンタム継続（上昇中）
        if "↑" in d.get("momentum", ""):
            score += 10
            signals.append("上昇継続↑")

        # 合計3つ以上シグナルを満たした場合
        if score >= 55 and len(signals) >= 3:
            qualified.append({
                "name": name,
                "price": d.get("price", 0),
                "change_pct": d.get("change_from_prev", 0),
                "score": score,
                "signals": signals,
                "vwap": d.get("vwap", 0),
                "vol_pace": d.get("vol_pace", 0),
            })

    qualified.sort(key=lambda x: x["score"], reverse=True)
    return qualified

def load_watchlist():
    try:
        with open(WATCHLIST_FILE, "r") as f:
            data = json.load(f)
        return data.get("stocks", [])
    except:
        return []

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        return 100.0
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_gain / avg_loss)), 1)

def get_intraday(symbol):
    try:
        ticker = yf.Ticker(symbol)
        intra = ticker.history(period="1d", interval="5m")
        daily = ticker.history(period="10d", interval="1d")
        if len(intra) == 0 or len(daily) < 2:
            return None

        curr = float(intra["Close"].iloc[-1])
        open_p = float(intra["Open"].iloc[0])
        intra_high = float(intra["High"].max())
        intra_low = float(intra["Low"].min())
        intra_vol = int(intra["Volume"].sum())
        prev_close = float(daily["Close"].iloc[-2])
        prev_vol = int(daily["Volume"].iloc[-2])
        prev_high = float(daily["High"].iloc[-2])
        prev_low = float(daily["Low"].iloc[-2])

        # VWAP
        vwap = float((intra["Close"] * intra["Volume"]).sum() / intra["Volume"].sum()) \
               if intra["Volume"].sum() > 0 else curr

        # 出来高ペース
        vol_pace = intra_vol / prev_vol * 100 if prev_vol > 0 else 0

        # モメンタム（直近5本）
        if len(intra) >= 5:
            recent = intra["Close"].values[-5:]
            momentum = "↑上昇中" if recent[-1] > recent[0] else "↓下落中"
            momentum_strength = abs(recent[-1] - recent[0]) / recent[0] * 100
        else:
            momentum = "-"
            momentum_strength = 0

        # 日足RSI
        closes_daily = daily["Close"].values.astype(float)
        rsi = calc_rsi(closes_daily)

        # 5分足RSI（短期）
        if len(intra) > 15:
            rsi_short = calc_rsi(intra["Close"].values.astype(float), period=9)
        else:
            rsi_short = None

        # ボリンジャーバンド（日足20日）
        if len(closes_daily) >= 20:
            ma20 = np.mean(closes_daily[-20:])
            std20 = np.std(closes_daily[-20:])
            bb_upper = ma20 + 2 * std20
            bb_lower = ma20 - 2 * std20
            bb_pos = (curr - bb_lower) / (bb_upper - bb_lower) * 100 if bb_upper != bb_lower else 50
        else:
            bb_pos = None

        # 前日レンジとの関係
        if curr > prev_high:
            range_pos = "前日高値突破🔥"
        elif curr < prev_low:
            range_pos = "前日安値割れ⚠️"
        else:
            range_pos = "前日レンジ内"

        return {
            "price": curr,
            "open": open_p,
            "high": intra_high,
            "low": intra_low,
            "vwap": round(vwap, 1),
            "vwap_pos": "VWAP上(強)" if curr > vwap else "VWAP下(弱)",
            "change_from_prev": (curr - prev_close) / prev_close * 100,
            "change_from_open": (curr - open_p) / open_p * 100,
            "intra_vol": intra_vol,
            "vol_pace": round(vol_pace, 0),
            "momentum": momentum,
            "momentum_pct": round(momentum_strength, 2),
            "rsi": rsi,
            "rsi_short": rsi_short,
            "bb_pos": round(bb_pos, 0) if bb_pos is not None else None,
            "range_pos": range_pos,
            "prev_close": prev_close,
            "prev_high": prev_high,
            "prev_low": prev_low,
        }
    except:
        return None

def get_market_now():
    syms = {
        "日経平均": "^N225",
        "グロース250": "2516.T",
        "ドル円": "USDJPY=X",
        "ダウ先物": "YM=F",
    }
    result = {}
    for name, sym in syms.items():
        try:
            h = yf.Ticker(sym).history(period="5d", interval="1d")
            if len(h) >= 2:
                prev = float(h["Close"].iloc[-2])
                curr = float(h["Close"].iloc[-1])
                result[name] = {"price": curr, "change_pct": (curr - prev) / prev * 100}
        except:
            pass
    return result

def get_earnings_today():
    """本日〜3日以内の決算銘柄を警告"""
    today = date.today()
    soon = today + timedelta(days=3)
    warnings = []
    for name, symbol in BASE_UNIVERSE.items():
        try:
            cal = yf.Ticker(symbol).calendar
            if not cal:
                continue
            earn_dates = cal.get("Earnings Date", [])
            for ed in earn_dates:
                if hasattr(ed, 'date') and callable(ed.date):
                    ed = ed.date()
                if today <= ed <= soon:
                    warnings.append({
                        "name": name,
                        "date": str(ed),
                        "days_left": (ed - today).days
                    })
                    break
        except:
            continue
    return sorted(warnings, key=lambda x: x["days_left"])

def get_econ_today():
    """本日の重要経済指標"""
    try:
        req = urllib.request.Request(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        data = urllib.request.urlopen(req, timeout=8).read()
        events = json.loads(data)
        today_str = datetime.now().strftime("%Y-%m-%d")
        result = []
        for e in events:
            if e.get("impact") not in {"High", "Medium"}:
                continue
            country = e.get("country", "")
            currency = {"United States": "USD", "Japan": "JPY",
                       "China": "CNY", "European Union": "EUR"}.get(country, "")
            if currency not in {"USD", "JPY"}:
                continue
            if e.get("date", "")[:10] == today_str:
                title = e.get("title", "")
                result.append({
                    "time": e.get("time", ""),
                    "label": JP_LABELS.get(title, title),
                    "impact": e.get("impact"),
                    "currency": currency,
                    "actual": e.get("actual", ""),
                    "forecast": e.get("forecast", ""),
                })
        return result
    except:
        return []

def get_quick_news():
    news = []
    feeds = [
        ("NHK経済", "https://www3.nhk.or.jp/rss/news/cat5.xml", False),
        ("Yahoo!株式", "https://news.yahoo.co.jp/rss/topics/business.xml", False),
        ("Investing.com", "https://jp.investing.com/rss/news_25.rss", True),
        ("Investing.com経済", "https://jp.investing.com/rss/news_285.rss", True),
    ]
    keywords = ["株","日経","相場","市場","円","為替","決算","急騰","急落","上昇","下落",
                "材料","買い","売り","半導体","AI","銀行","金利","先物"]
    src_colors = {
        "NHK経済": "#c0392b", "Yahoo!株式": "#6200ea",
        "Investing.com": "#ff6b35", "Investing.com経済": "#e67e22"
    }
    for name, url, ua in feeds:
        try:
            if ua:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(req, timeout=6).read()
                feed = feedparser.parse(data)
            else:
                feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries[:20]:
                title = entry.get("title", "")
                if any(kw in title for kw in keywords):
                    news.append({
                        "source": name,
                        "title": title,
                        "link": entry.get("link", "#"),
                        "color": src_colors.get(name, "#555")
                    })
                    count += 1
                    if count >= 5:
                        break
        except:
            pass
    return news[:20]

def build_now_text(market, stocks_data, earnings, econ_today, now_str):
    lines = [f"【現在時刻】{now_str}", ""]

    # 市場
    lines.append("【現在の主要指数】")
    for name, d in market.items():
        sign = "+" if d["change_pct"] >= 0 else ""
        lines.append(f"・{name}: {d['price']:,.2f} ({sign}{d['change_pct']:.2f}%)")

    # 決算アラート
    if earnings:
        lines.append("\n【⚠️ 決算間近の銘柄（手を出すな）】")
        for e in earnings:
            days = e["days_left"]
            label = "🔴本日決算！" if days == 0 else f"🟡{days}日後に決算"
            lines.append(f"・{label} {e['name']} ({e['date']})")

    # 本日の経済指標
    if econ_today:
        lines.append("\n【📅 本日の重要経済指標】")
        for e in econ_today:
            flag = "🔴" if e["impact"] == "High" else "🟡"
            actual = f" 結果:{e['actual']}" if e.get("actual") else ""
            forecast = f" 予想:{e['forecast']}" if e.get("forecast") else ""
            lines.append(f"・{flag} {e['time']} [{e['currency']}] {e['label']}{forecast}{actual}")

    # 銘柄データ
    lines.append("\n【現在の銘柄データ（リアルタイム）】")
    for name, d in stocks_data:
        if not d:
            continue
        sign_p = "+" if d["change_from_prev"] >= 0 else ""
        rsi_str = f"RSI日足:{d['rsi']}" if d["rsi"] else ""
        rsi_s_str = f" RSI短期:{d['rsi_short']}" if d.get("rsi_short") else ""
        bb_str = f" BB位置:{d['bb_pos']}%" if d.get("bb_pos") is not None else ""
        lines.append(
            f"・{name}: {d['price']:.0f}円 "
            f"前日比{sign_p}{d['change_from_prev']:.1f}% "
            f"VWAP:{d['vwap']}({d['vwap_pos']}) "
            f"出来高ペース:{d['vol_pace']:.0f}% "
            f"{d['momentum']}({d['momentum_pct']:.1f}%) "
            f"{d['range_pos']} "
            f"{rsi_str}{rsi_s_str}{bb_str}"
        )
    return "\n".join(lines)

def generate_now_html(market, stocks_data, surges, continuation, earnings, econ_today, news, now_str, fetch_time):
    now_text = build_now_text(market, stocks_data, earnings, econ_today, now_str)
    now_text_escaped = now_text.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

    # 急騰情報テキスト
    if surges:
        surge_lines = ["【🚀 急騰・出来高急増スキャン結果】"]
        for s in surges:
            sign = "+" if s["change_pct"] >= 0 else ""
            surge_lines.append(f"・{s['name']}: {s['price']:.0f}円 ({sign}{s['change_pct']:.1f}%) 出来高{s['vol_ratio']}倍 急騰度:{s['surge_score']}")
        surge_info = "\n".join(surge_lines)
    else:
        surge_info = ""
    surge_info_escaped = surge_info.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

    # 急騰継続フィルター情報をテキスト化
    if continuation:
        cont_lines = ["", "【🔥 急騰継続シグナル（翌日続伸候補）】"]
        for s in continuation:
            cont_lines.append(f"・{s['name']}: {s['price']:.0f}円 ({s['change_pct']:+.1f}%) 条件:{' '.join(s['signals'][:3])}")
        cont_info = "\n".join(cont_lines)
    else:
        cont_info = ""
    cont_info_escaped = cont_info.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

    # 時間帯判定
    hour = datetime.now().hour
    minute = datetime.now().minute
    total_min = hour * 60 + minute
    if total_min < 9 * 60 + 20:
        time_advice = "🚫 9:20前 → まだエントリー禁止。様子見の時間です"
        time_cls = "time-danger"
    elif total_min < 9 * 60 + 30:
        time_advice = "👀 9:20〜9:30 → トレンド確認中。焦らず観察"
        time_cls = "time-watch"
    elif total_min < 11 * 60 + 30:
        time_advice = "✅ 前場メイン → エントリー検討OK"
        time_cls = "time-ok"
    elif total_min < 12 * 60 + 30:
        time_advice = "😴 昼休み(11:30〜12:30) → ポジション整理の時間"
        time_cls = "time-watch"
    elif total_min < 14 * 60 + 30:
        time_advice = "✅ 後場 → エントリー可。ただし引けに注意"
        time_cls = "time-ok"
    elif total_min < 15 * 60:
        time_advice = "⚠️ 引け30分前 → 新規エントリーは避ける"
        time_cls = "time-watch"
    else:
        time_advice = "🏁 取引終了(15:00) → 今日の振り返りをしましょう"
        time_cls = "time-danger"

    # 市場カード
    market_cards = ""
    for name, d in market.items():
        sign = "+" if d["change_pct"] >= 0 else ""
        cls = "up" if d["change_pct"] >= 0 else "down"
        arrow = "▲" if d["change_pct"] >= 0 else "▼"
        market_cards += f"""<div class="m-card">
          <div class="m-name">{name}</div>
          <div class="m-price">{d['price']:,.2f}</div>
          <div class="m-change {cls}">{arrow}{sign}{d['change_pct']:.2f}%</div>
        </div>"""

    # アラートHTML
    alert_html = ""
    if earnings:
        items = ""
        for e in earnings:
            cls2 = "earn-today" if e["days_left"] == 0 else "earn-soon"
            label = "🔴 本日決算！絶対に触るな" if e["days_left"] == 0 else f"🟡 {e['days_left']}日後に決算"
            items += f'<div class="alert-item {cls2}"><strong>{label}</strong>: {e["name"]}</div>'
        alert_html += f'<div class="alert-card danger"><div class="alert-title">⚠️ 決算間近銘柄（保有・新規禁止）</div>{items}</div>'

    if econ_today:
        items = ""
        for e in econ_today:
            flag = "🔴" if e["impact"] == "High" else "🟡"
            actual = f" → 結果: {e['actual']}" if e.get("actual") else ""
            forecast = f"（予想: {e['forecast']}）" if e.get("forecast") else ""
            items += f'<div class="alert-item econ-today">{flag} <strong>{e["time"]} [{e["currency"]}] {e["label"]}</strong>{forecast}{actual}</div>'
        alert_html += f'<div class="alert-card warning"><div class="alert-title">📅 本日の重要経済指標（急変動に注意）</div>{items}</div>'

    if not alert_html:
        alert_html = '<div class="alert-card safe"><div class="alert-title">✅ 本日は重大アラートなし</div></div>'

    # 急騰継続フィルターHTML
    continuation_html = ""
    if continuation:
        cont_rows = ""
        for s in continuation:
            sign = "+" if s["change_pct"] >= 0 else ""
            cont_rows += f"""<tr>
              <td style="font-size:0.75rem;font-weight:bold">{s['name']}</td>
              <td style="font-weight:bold">{s['price']:.0f}円</td>
              <td class="up">{sign}{s['change_pct']:.1f}%</td>
              <td style="color:#3fb950;font-size:0.72rem">{' '.join(s['signals'][:3])}</td>
            </tr>"""
        continuation_html = f"""<div class="card" style="border-color:#3fb950">
  <div class="card-title" style="color:#3fb950">🔥 急騰継続シグナル（翌日続伸候補）</div>
  <div style="font-size:0.72rem;color:#8b949e;margin-bottom:8px">出来高3倍以上・VWAP維持・高値圏維持・上ヒゲ短い を満たす銘柄</div>
  <table>
    <tr><th>銘柄</th><th>現値</th><th>前日比</th><th>満たした条件</th></tr>
    {cont_rows}
  </table>
  <div style="font-size:0.7rem;color:#8b949e;margin-top:6px">「急騰後も値を保っている = 需給が強い」→ 翌日の続伸可能性が比較的高い</div>
</div>"""

    # 急騰スキャンHTML
    surge_html = ""
    if surges:
        surge_rows = ""
        for s in surges:
            sign = "+" if s["change_pct"] >= 0 else ""
            cls = "up" if s["change_pct"] >= 0 else "down"
            cp = abs(s["change_pct"])
            if cp >= 5:
                risk_badge = '<span style="color:#ff4d4d;font-weight:bold;font-size:0.72rem">⚠️高値注意</span>'
            elif cp >= 3:
                risk_badge = '<span style="color:#f0a500;font-size:0.72rem">⚡5〜10分待て</span>'
            else:
                risk_badge = '<span style="color:#58a6ff;font-size:0.72rem">✅押し目可</span>'
            surge_rows += f"""<tr>
              <td style="font-size:0.75rem;font-weight:bold">{s['name']}</td>
              <td style="font-weight:bold">{s['price']:.0f}円</td>
              <td class="{cls}">{sign}{s['change_pct']:.1f}%</td>
              <td style="color:#f0a500">{s['vol_ratio']}倍</td>
              <td>{risk_badge}</td>
            </tr>"""
        surge_html = f"""<div class="card" style="border-color:#f0a500">
  <div class="card-title" style="color:#f0a500">🚀 急騰・出来高急増スキャン <span style="font-size:0.65rem;color:#8b949e;font-weight:normal">{len(SURGE_UNIVERSE)}銘柄中</span></div>
  <table>
    <tr><th>銘柄</th><th>現値</th><th>前日比</th><th>出来高比</th><th>エントリー</th></tr>
    {surge_rows}
  </table>
  <div class="legend">⚠️高値注意(5%超)=飛びつき禁止 ⚡5〜10分待って押し目確認 ✅落ち着いており押し目狙い可</div>
</div>"""
    else:
        surge_html = ""

    # 銘柄テーブル
    rows = ""
    for name, d in stocks_data:
        if not d:
            continue
        sign_p = "+" if d["change_from_prev"] >= 0 else ""
        sign_o = "+" if d["change_from_open"] >= 0 else ""
        cls_p = "up" if d["change_from_prev"] >= 0 else "down"
        vwap_cls = "up" if "上" in d["vwap_pos"] else "down"
        vol_cls = "vol-hot" if d["vol_pace"] >= 80 else ""
        rsi = d["rsi"] or "-"
        rsi_cls = "rsi-hot" if d["rsi"] and d["rsi"] >= 70 else ("rsi-cold" if d["rsi"] and d["rsi"] <= 30 else "")
        mom_cls = "up" if "↑" in d["momentum"] else "down"
        bb_str = f"{d['bb_pos']}%" if d.get("bb_pos") is not None else "-"
        range_cls = "vol-hot" if "突破" in d["range_pos"] else ("rsi-hot" if "割れ" in d["range_pos"] else "")
        rows += f"""<tr>
          <td class="s-name">{name.split(' ', 1)[-1]}<br><span class="code">{name.split(' ')[0]}</span></td>
          <td class="price">{d['price']:.0f}円</td>
          <td class="{cls_p}">{sign_p}{d['change_from_prev']:.1f}%</td>
          <td class="{vwap_cls}">{d['vwap']}</td>
          <td class="{vol_cls}">{d['vol_pace']:.0f}%</td>
          <td class="{rsi_cls}">{rsi}</td>
          <td class="{mom_cls}">{d['momentum']}</td>
          <td class="{range_cls}" style="font-size:0.65rem">{d['range_pos']}</td>
        </tr>"""

    # ニュース
    news_html = ""
    for n in news:
        title_esc = n["title"].replace('"','&quot;').replace('<','&lt;').replace('>','&gt;')
        news_html += f"""<a href="{n['link']}" target="_blank" class="news-item">
          <span class="ns" style="background:{n['color']}">{n['source']}</span>
          <span class="nt">{title_esc}</span>
        </a>"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>⚡ 今すぐチェック</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans",sans-serif;background:#0d1117;color:#e6edf3;padding:14px;max-width:680px;margin:0 auto}}
    .top-bar{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}}
    h1{{font-size:1.1rem}}
    .fetch-time{{font-size:0.72rem;color:#8b949e}}
    .back-btn{{display:inline-block;background:#21262d;border:1px solid #30363d;color:#e6edf3;padding:5px 12px;border-radius:8px;font-size:0.78rem;text-decoration:none;margin-bottom:10px}}
    /* 時間帯バナー */
    .time-banner{{border-radius:10px;padding:11px 14px;margin-bottom:12px;font-size:0.88rem;font-weight:bold;text-align:center}}
    .time-ok{{background:#0d1f12;border:1px solid #238636;color:#3fb950}}
    .time-watch{{background:#1a1500;border:1px solid #5a4500;color:#f0a500}}
    .time-danger{{background:#1f0d0d;border:1px solid #6e1a1a;color:#f85149}}
    /* 指数 */
    .market-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-bottom:12px}}
    .m-card{{background:#161b22;border:1px solid #30363d;border-radius:9px;padding:9px 8px;text-align:center}}
    .m-name{{font-size:0.65rem;color:#8b949e;margin-bottom:2px}}
    .m-price{{font-size:0.88rem;font-weight:bold}}
    .m-change{{font-size:0.75rem;margin-top:1px}}
    .up{{color:#3fb950}}.down{{color:#f85149}}
    /* アラート */
    .alert-card{{border-radius:10px;padding:11px 13px;margin-bottom:10px;border:1px solid}}
    .alert-card.danger{{background:#1f0d0d;border-color:#6e1a1a}}
    .alert-card.warning{{background:#1a1500;border-color:#5a4500}}
    .alert-card.safe{{background:#0d1f12;border-color:#238636}}
    .alert-title{{font-size:0.82rem;font-weight:bold;margin-bottom:6px}}
    .alert-card.danger .alert-title{{color:#f85149}}
    .alert-card.warning .alert-title{{color:#f0a500}}
    .alert-card.safe .alert-title{{color:#3fb950}}
    .alert-item{{font-size:0.78rem;padding:3px 0;line-height:1.5}}
    .earn-today{{color:#f85149}}.earn-soon{{color:#f0a500}}
    .econ-today{{color:#e6edf3}}
    /* テーブル */
    .card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:13px;margin-bottom:12px}}
    .card-title{{font-size:0.88rem;font-weight:bold;margin-bottom:10px;display:flex;align-items:center;gap:8px}}
    .badge{{font-size:0.65rem;background:#21262d;color:#8b949e;padding:2px 7px;border-radius:10px}}
    table{{width:100%;border-collapse:collapse;font-size:0.73rem}}
    th{{color:#8b949e;font-size:0.65rem;padding:3px 3px;border-bottom:1px solid #21262d;text-align:left;white-space:nowrap}}
    td{{padding:5px 3px;border-bottom:1px solid #21262d;vertical-align:middle}}
    .s-name{{font-weight:bold;font-size:0.75rem}}
    .code{{font-size:0.6rem;color:#8b949e}}
    .price{{font-weight:bold}}
    .vol-hot{{color:#f0a500;font-weight:bold}}
    .rsi-hot{{color:#f85149;font-weight:bold}}
    .rsi-cold{{color:#58a6ff;font-weight:bold}}
    .legend{{font-size:0.6rem;color:#8b949e;margin-top:6px;line-height:1.7}}
    /* ニュース */
    .news-item{{display:flex;align-items:flex-start;gap:7px;padding:7px 0;border-bottom:1px solid #21262d;text-decoration:none;color:inherit}}
    .news-item:last-child{{border-bottom:none}}
    .ns{{flex-shrink:0;font-size:0.6rem;color:#fff;padding:2px 5px;border-radius:4px;margin-top:2px;white-space:nowrap}}
    .nt{{font-size:0.8rem;line-height:1.4}}
    /* ボタン */
    .btn{{display:block;width:100%;padding:14px;border-radius:10px;border:none;font-size:0.93rem;font-weight:bold;cursor:pointer;margin-bottom:10px}}
    .btn-gen{{background:linear-gradient(135deg,#238636,#1a6128);color:#fff}}
    .btn-claude{{background:linear-gradient(135deg,#1f6feb,#1158c7);color:#fff;text-decoration:none;text-align:center;display:block;padding:14px;border-radius:10px;font-size:0.93rem;font-weight:bold}}
    .toast{{display:none;background:#238636;color:#fff;padding:10px;border-radius:8px;text-align:center;font-size:0.85rem;margin-bottom:10px}}
  </style>
</head>
<body>
<!-- 共通ナビ（index.htmlと同じ見た目） -->
<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:5px;margin-bottom:14px">
  <a href="index.html" style="display:block;padding:10px 4px;border-radius:10px;border:none;background:#21262d;color:#e6edf3;font-size:0.78rem;font-weight:bold;cursor:pointer;text-align:center;text-decoration:none">🌅 朝の分析</a>
  <a href="index.html#target" style="display:block;padding:10px 4px;border-radius:10px;border:none;background:#21262d;color:#e6edf3;font-size:0.78rem;font-weight:bold;cursor:pointer;text-align:center;text-decoration:none">🎯 今日の狙い</a>
  <a href="index.html#log" style="display:block;padding:10px 4px;border-radius:10px;border:none;background:#21262d;color:#e6edf3;font-size:0.78rem;font-weight:bold;cursor:pointer;text-align:center;text-decoration:none">📒 ログ</a>
  <a href="index.html#stats" style="display:block;padding:10px 4px;border-radius:10px;border:none;background:#21262d;color:#e6edf3;font-size:0.78rem;font-weight:bold;cursor:pointer;text-align:center;text-decoration:none">📊 統計</a>
  <a href="now.html" style="display:block;padding:10px 4px;border-radius:10px;border:none;background:#1f6feb;color:#fff;font-size:0.78rem;font-weight:bold;cursor:pointer;text-align:center;text-decoration:none">⚡ 今すぐ</a>
</div>
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
  <h1 style="font-size:1.1rem">⚡ 今すぐチェック</h1>
  <span style="font-size:0.72rem;color:#8b949e">更新: {fetch_time}</span>
</div>

<!-- 時間帯バナー -->
<div class="time-banner {time_cls}">{time_advice}</div>

<!-- 指数 -->
<div class="market-row">{market_cards}</div>

<!-- アラート -->
{alert_html}

<!-- 急騰継続フィルター -->
{continuation_html}

<!-- 急騰スキャン -->
{surge_html}

<!-- 銘柄テーブル -->
<div class="card">
  <div class="card-title">📊 銘柄リアルタイム<span class="badge">VWAP・出来高・RSI・モメンタム</span></div>
  <table>
    <tr><th>銘柄</th><th>現値</th><th>前日比</th><th>VWAP</th><th>出来高%</th><th>RSI</th><th>方向</th><th>レンジ</th></tr>
    {rows}
  </table>
  <div class="legend">
    出来高%: 前日出来高に対する本日のペース（80%超=勢いあり）｜ VWAP上=機関買い優勢 ｜ 前日高値突破=ブレイクアウト
  </div>
</div>

<!-- ニュース -->
<div class="card">
  <div class="card-title">📰 直近ニュース</div>
  {news_html}
</div>

<!-- Claude相談 -->
<div class="card">
  <div class="card-title">⚡ 今からClaudeに相談</div>

  <!-- 持ち越し判断 -->
  <div style="margin-bottom:10px">
    <div style="font-size:0.75rem;color:#8b949e;margin-bottom:6px">📌 持ち越し判断（保有中の銘柄を入力）</div>
    <div style="display:flex;gap:6px;margin-bottom:6px">
      <input type="text" id="hold-stock" placeholder="例: 6200 インソース" style="flex:1;background:#0d1117;border:1px solid #30363d;border-radius:8px;color:#e6edf3;padding:8px;font-size:0.83rem">
      <input type="number" id="hold-price" placeholder="買値" style="width:80px;background:#0d1117;border:1px solid #30363d;border-radius:8px;color:#e6edf3;padding:8px;font-size:0.83rem">
    </div>
    <button class="btn" onclick="genHoldPrompt()" style="background:linear-gradient(135deg,#7c3aed,#5b21b6);color:#fff;padding:11px;margin-bottom:8px">🟣 持ち越すべき？今売るべき？を聞く</button>
  </div>

  <button class="btn btn-gen" onclick="genPrompt()" style="margin-bottom:8px">✨ 今すぐ新規エントリー分析</button>
  <div class="toast" id="toast">✅ コピーしました！Claude.aiに貼り付けてください</div>
  <a href="{CLAUDE_PROJECT}" target="_blank" id="claude-link" style="display:none">
    <span class="btn-claude">🤖 Claude.aiプロジェクトを開く →</span>
  </a>
</div>

<script>
const NOW_DATA = `{now_text_escaped}`;
const NOW_TIME = "{now_str}";
const HOUR = {hour};
const MIN = {minute};
const SURGE_INFO = `{surge_info_escaped}`;
const CONT_INFO = `{cont_info_escaped}`;

function getPersonalProfile() {{
  try {{
    const list = JSON.parse(localStorage.getItem('reflections') || '[]').filter(r => r.pnl !== null);
    if (list.length < 3) return '';
    const wins = list.filter(r => r.result === 'win');
    const losses = list.filter(r => r.result === 'loss');
    const totalPnl = list.reduce((s, r) => s + r.pnl, 0);
    const winRate = Math.round(wins.length / list.length * 100);
    let streak = 0;
    for (let i = 0; i < Math.min(list.length, 5); i++) {{
      if (list[i].result === 'loss') streak++;
      else break;
    }}
    const streakNote = streak >= 3 ? `⚠️ 現在${{streak}}連敗中。今日は特に慎重に。` : '';
    return `【📊 あなたの取引プロファイル（${{list.length}}回の実績より）】
・通算勝率: ${{winRate}}% (${{wins.length}}勝${{losses.length}}敗)
・累計損益: ${{totalPnl >= 0 ? '+' : ''}}${{totalPnl.toLocaleString()}}円
${{streakNote}}`;
  }} catch(e) {{ return ''; }}
}}

function genHoldPrompt() {{
  const stock = document.getElementById('hold-stock').value.trim();
  const buyPrice = document.getElementById('hold-price').value.trim();
  if (!stock) {{ alert('銘柄名を入力してください'); return; }}

  const prompt = ['あなたは日本株専門のプロトレーダーです。',
    '現在保有中の銘柄について「持ち越すべきか・今売るべきか」を判断してください。',
    '',
    '【現在の市場状況】',
    NOW_DATA,
    SURGE_INFO ? '\\n' + SURGE_INFO : '',
    CONT_INFO ? '\\n' + CONT_INFO : '',
    '',
    '【保有中の銘柄】',
    '銘柄: ' + stock,
    buyPrice ? '買値: ' + buyPrice + '円' : '',
    '',
    '⚠️ まずBing検索で「' + stock + ' 株価 今日 材料 チャート」を調べてから判断してください。',
    '',
    '━━━━━━━━━━━━━━',
    '【判断依頼】',
    '━━━━━━━━━━━━━━',
    '',
    '■ 1. 今すぐ売るべきか・持ち越すべきか（結論を最初に）',
    '   → 🔵 今日中に売る / 🟣 2〜3日持つ / 🌙 来週まで持つ / ❌ 損切りすべき',
    '',
    '■ 2. 判断理由',
    '   ・現在の値動き・出来高・VWAPの状況',
    '   ・今日の地合いと明日以降の見通し',
    '   ・この銘柄特有のリスク・材料',
    '',
    '■ 3. 持ち越す場合のシナリオ',
    '   ・利確目標: 〇〇円（+〇%）',
    '   ・損切りライン: 〇〇円（-〇%）',
    '   ・注意すべきタイミング',
    '',
    '■ 4. 今売る場合のタイミング',
    '   ・今すぐ成行 or 〇〇円で指値',
    '',
    '※前提: 資金10万円・損切りは苦手・欲張らない方針'].filter(Boolean).join('\\n');

  navigator.clipboard.writeText(prompt).then(() => {{
    document.getElementById('toast').style.display = 'block';
    document.getElementById('claude-link').style.display = 'block';
    setTimeout(() => document.getElementById('toast').style.display = 'none', 3000);
  }}).catch(() => {{
    const el = document.createElement('textarea');
    el.value = prompt; document.body.appendChild(el); el.select();
    document.execCommand('copy'); document.body.removeChild(el);
    document.getElementById('toast').style.display = 'block';
    document.getElementById('claude-link').style.display = 'block';
    setTimeout(() => document.getElementById('toast').style.display = 'none', 3000);
  }});
}}

function genPrompt() {{
  const totalMin = HOUR * 60 + MIN;
  let timeAdvice = '';
  if (totalMin < 9*60+20) timeAdvice = '※現在9:20前のため、エントリーは禁止です。まず様子見してください。';
  else if (totalMin >= 14*60+30) timeAdvice = '※引け30分前。新規エントリーは避け、保有中のものを整理することを優先してください。';
  else if (totalMin >= 15*60) timeAdvice = '※取引終了時間です。今日の振り返りをしましょう。';

  const surgeText = SURGE_INFO || '';
  const contText = CONT_INFO || '';
  const profileText = getPersonalProfile();

  const prompt = `あなたは20年以上の経験を持つ日本株専門のプロトレーダーです。
現在${{NOW_TIME}}のリアルタイムデータを基に、今から取れる最善の行動を教えてください。

━━━━━━━━━━━━━━━━━━━━
【現在のリアルタイムデータ】
━━━━━━━━━━━━━━━━━━━━
${{NOW_DATA}}
${{surgeText ? '\\n' + surgeText : ''}}
${{contText ? '\\n' + contText : ''}}
${{profileText ? '\\n' + profileText : ''}}

━━━━━━━━━━━━━━━━━━━━
【今すぐの判断依頼】
━━━━━━━━━━━━━━━━━━━━

■ 1. 現時点の市場の空気感（1〜2行）
・VWAP上/下の銘柄比率・出来高の勢い・モメンタムの方向

■ 2. 急騰・出来高急増銘柄の解読
・急騰スキャンに出た銘柄の「なぜ今動いているか」を推測
・今から乗れるか・乗るべきでないか

■ 3. 今から狙える銘柄（最大2つ・厳選）
⚠️ このうち最低1つは1株700円以下（100株=7万円以内）の銘柄にすること
各銘柄：
・銘柄名・コード・現在値（💚低価格帯 or 通常）
・根拠: VWAP・出来高ペース・モメンタム・前日高値突破・RSIを組み合わせて
・エントリー: 今すぐ成行 or 〇〇円指値
・利確目標: 第1目標〇〇円、第2目標〇〇円
・損切りライン: 〇〇円割れで即撤退（最大損失〇〇円以内）
・リスクリワード比: 〇:1
・信頼度: ★〜★★★★★

■ 4. ${{NOW_TIME}}という時間帯の注意点
・残り取引時間を踏まえたリスク
・この時間帯特有の動きパターン

■ 5. 今日「休む」べきなら正直に言ってください

${{timeAdvice}}

━━━━━━━━━━━━━━━━━━━━
私のルール（毎回必ず守る）：
・資金: 10万円
・エントリー: 9:20以降のみ・寄り付き直後は絶対触らない
・1回の最大損失: 2,000〜3,000円で即損切り
・1日の最大損失: 5,000円で今日は終了
・目標: 1日1,000〜3,000円（欲張らない・確実に積み上げる）
・保有: 基本デイトレ（その日中に決済）
・弱点: 含み損になると損切りできなくなる
━━━━━━━━━━━━━━━━━━━━`;

  navigator.clipboard.writeText(prompt).then(() => {{
    document.getElementById('toast').style.display = 'block';
    document.getElementById('claude-link').style.display = 'block';
    setTimeout(() => document.getElementById('toast').style.display = 'none', 3000);
  }}).catch(() => {{
    const el = document.createElement('textarea');
    el.value = prompt;
    document.body.appendChild(el); el.select();
    document.execCommand('copy'); document.body.removeChild(el);
    document.getElementById('toast').style.display = 'block';
    document.getElementById('claude-link').style.display = 'block';
    setTimeout(() => document.getElementById('toast').style.display = 'none', 3000);
  }});
}}
</script>
</body>
</html>"""

def push_file(repo_dir, filename):
    try:
        subprocess.run(["git", "-C", repo_dir, "add", filename], check=True)
        t = datetime.now().strftime("%Y-%m-%d %H:%M")
        result = subprocess.run(
            ["git", "-C", repo_dir, "commit", "-m", f"now-update: {t}"],
            capture_output=True, text=True
        )
        if "nothing to commit" in result.stdout:
            return True
        subprocess.run(["git", "-C", repo_dir, "push"], check=True)
        return True
    except:
        return False

def main():
    import sys
    push_to_gh = "--push" in sys.argv

    now = datetime.now()
    now_str = now.strftime("%Y年%m月%d日 %H:%M")
    fetch_time = now.strftime("%H:%M:%S")

    print(f"⚡ 現在({now_str})のデータ取得中...")

    # ウォッチリスト追加
    watchlist = load_watchlist()
    universe = dict(BASE_UNIVERSE)
    for item in watchlist:
        code = item.get("code", "")
        name = item.get("name", code)
        if code:
            universe[name] = code
    print(f"📋 監視銘柄: {len(universe)}銘柄")

    print("📈 主要指数取得中...")
    market = get_market_now()

    print("⚠️ 決算アラート確認中...")
    earnings = get_earnings_today()
    if earnings:
        print(f"  🔴 決算間近: {', '.join(e['name'] for e in earnings)}")
    else:
        print("  ✅ 決算間近なし")

    print("📅 本日の経済指標確認中...")
    econ_today = get_econ_today()
    if econ_today:
        print(f"  ⚠️ 本日指標: {', '.join(e['label'] for e in econ_today)}")
    else:
        print("  ✅ 本日の重大指標なし")

    print("🔬 銘柄データ取得中（しばらくかかります）...")
    stocks_data = []
    for name, symbol in universe.items():
        d = get_intraday(symbol)
        if d:
            stocks_data.append((name, d))
            sign = "+" if d["change_from_prev"] >= 0 else ""
            print(f"  ✓ {name}: {d['price']:.0f}円 前日比{sign}{d['change_from_prev']:.1f}% {d['momentum']}")

    # スコアリング（変動率 + 出来高ペース + モメンタム）
    stocks_data.sort(key=lambda x: (
        abs(x[1]["change_from_prev"]) * 2 +
        x[1]["vol_pace"] / 10 +
        x[1]["momentum_pct"] * 3
    ), reverse=True)

    print("🚀 急騰・出来高急増スキャン中...")
    surges = get_surge_scanner_intraday()
    if surges:
        print(f"  🔥 急騰候補: {', '.join(s['name'] for s in surges[:3])}")
    else:
        print("  本日は急騰銘柄なし")

    print("📰 ニュース取得中...")
    news = get_quick_news()
    print(f"✅ ニュース {len(news)}件")

    # 急騰継続フィルター
    continuation = get_surge_continuation_filter(stocks_data)
    if continuation:
        print(f"🔥 急騰継続シグナル: {', '.join(s['name'] for s in continuation[:3])}")
    else:
        print("  急騰継続シグナルなし")

    print("📝 HTML生成中...")
    html = generate_now_html(market, stocks_data, surges, continuation, earnings, econ_today, news, now_str, fetch_time)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 生成完了")

    if os.path.isdir(GITHUB_REPO):
        gh_path = os.path.join(GITHUB_REPO, "now.html")
        with open(gh_path, "w", encoding="utf-8") as f:
            f.write(html)
        if push_to_gh:
            if push_file(GITHUB_REPO, "now.html"):
                print("🚀 GitHub Pages反映完了")
                print("📱 iPhone: https://airin-crm.github.io/stock-morning/now.html")

    import subprocess as sp
    sp.Popen(["open", OUTPUT_HTML])
    print(f"\n✅ ブラウザで開きました！")

if __name__ == "__main__":
    main()
