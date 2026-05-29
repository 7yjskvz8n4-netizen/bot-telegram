import requests
import math
import sqlite3
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import random

# =========================
# CONFIG
# =========================

API_KEY = "e93b17bb02fe486f1fa731494df8814c"
TELEGRAM_TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"

BASE_URL = "https://v3.football.api-sports.io"
TIMEZONE = ZoneInfo("Europe/Madrid")

BANKROLL = 100

# valores iniciales (se ajustan solos)
MIN_ODDS = 1.42
MAX_ODDS = 2.30
MAX_PICKS = 7

BASE_EDGE = 0.04

HEADERS = {"x-apisports-key": API_KEY}

# =========================
# DB
# =========================

conn = sqlite3.connect("ml_bot.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS picks (
id INTEGER PRIMARY KEY AUTOINCREMENT,
timestamp TEXT,
fixture_id INTEGER,
match TEXT,
league TEXT,
odds REAL,
prob REAL,
edge REAL,
stake REAL,
result TEXT,
profit REAL
)
""")

conn.commit()

# =========================
# TELEGRAM
# =========================

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass

# =========================
# POISSON SIMPLE
# =========================

def poisson(lmbda, k):
    return (math.exp(-lmbda) * lmbda ** k) / math.factorial(k)

def match_prob(h, a):
    home = 0
    for i in range(6):
        for j in range(6):
            p = poisson(h, i) * poisson(a, j)
            if i > j:
                home += p
    return home

# =========================
# XG (placeholder)
# =========================

def get_xg():
    return 1.4, 1.1

# =========================
# EDGE
# =========================

def edge(prob, odds):
    return prob - (1 / odds)

# =========================
# DATA
# =========================

def get_matches():
    try:
        today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
        r = requests.get(
            f"{BASE_URL}/fixtures",
            headers=HEADERS,
            params={"date": today}
        )
        return r.json().get("response", [])
    except:
        return []

def get_odds(fid):
    try:
        r = requests.get(
            f"{BASE_URL}/odds",
            headers=HEADERS,
            params={"fixture": fid}
        )
        data = r.json().get("response", [])
        if not data:
            return None

        bets = data[0]["bookmakers"][0]["bets"]
        for b in bets:
            if b["name"] == "Match Winner":
                for v in b["values"]:
                    if v["value"] == "Home":
                        return float(v["odd"])
        return None
    except:
        return None

# =========================
# ML SIMPLE (AUTO AJUSTE)
# =========================

def get_stats():
    c.execute("SELECT odds, edge, profit FROM picks WHERE result IS NOT NULL")
    rows = c.fetchall()

    wins = [r for r in rows if r[2] and r[2] > 0]

    if len(rows) < 20:
        return {
            "edge_adjust": 0,
            "odds_bias": 0
        }

    avg_edge_wins = sum([r[1] for r in wins]) / max(len(wins), 1)

    # si el sistema gana poco → subir exigencia
    if len(wins) / len(rows) < 0.45:
        return {"edge_adjust": +0.01, "odds_bias": +0.05}

    # si gana bien → relajamos
    if len(wins) / len(rows) > 0.55:
        return {"edge_adjust": -0.005, "odds_bias": -0.03}

    return {"edge_adjust": 0, "odds_bias": 0}

# =========================
# DECISIÓN ADAPTATIVA
# =========================

def adaptive_edge(base, stats):
    return max(0.02, base + stats["edge_adjust"])

def adaptive_odds(min_odds, stats):
    return max(1.35, min_odds + stats["odds_bias"])

# =========================
# SAVE
# =========================

def save(p):
    c.execute("""
        INSERT INTO picks VALUES (NULL,?,?,?,?,?,?,?,?,?)
    """, p)
    conn.commit()

# =========================
# RUN
# =========================

def run():

    stats = get_stats()

    min_odds = adaptive_odds(MIN_ODDS, stats)
    min_edge = adaptive_edge(BASE_EDGE, stats)

    matches = get_matches()
    picks = []

    for m in matches:

        fid = m["fixture"]["id"]
        home = m["teams"]["home"]["name"]
        away = m["teams"]["away"]["name"]
        league = m["league"]["name"]

        odds = get_odds(fid)
        if not odds:
            continue

        if odds < min_odds or odds > MAX_ODDS:
            continue

        hxg, axg = get_xg()
        prob = match_prob(hxg, axg)

        e = edge(prob, odds)
        if e < min_edge:
            continue

        stake = BANKROLL * 0.02
        profit = 0

        picks.append([
            datetime.now().isoformat(),
            fid,
            f"{home} vs {away}",
            league,
            odds,
            prob,
            e,
            stake,
            "",
            profit
        ])

    picks = sorted(picks, key=lambda x: x[6], reverse=True)[:MAX_PICKS]

    for p in picks:
        save(p)

        send(
            f"🤖 ML PICK\n"
            f"⚽ {p[2]}\n"
            f"💰 {p[4]}\n"
            f"📊 Edge: {round(p[6]*100,2)}%\n"
            f"🧠 Auto-edge activo"
        )

# =========================
# LOOP
# =========================

send("🚀 BOT ML AUTO-OPTIMIZADO INICIADO")

while True:
    try:
        run()
        time.sleep(1800)
    except Exception as e:
        send(f"Error: {e}")
        time.sleep(60)
