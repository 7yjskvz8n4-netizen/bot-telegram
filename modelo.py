import requests
import math
import sqlite3
import time
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

# =========================
# CONFIG
# =========================

HEADERS = {"User-Agent": "Mozilla/5.0"}

TZ = ZoneInfo("Europe/Madrid")

MAX_PICKS = 5  # 🔥 menos picks, más calidad
EDGE_MIN = 0.03

# =========================
# TELEGRAM
# =========================

TELEGRAM_TOKEN = "8647764005:AAEt7k4vsUpQLMuti6iqGIDBF7ngOJ9vqRA"
CHAT_ID = "1335805552"

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
# LIGAS
# =========================

LEAGUES = {
    "mls": "https://www.espn.com/soccer/league/_/name/usa.1",
    "brazil": "https://www.espn.com/soccer/league/_/name/bra.1",
    "argentina": "https://www.espn.com/soccer/league/_/name/arg.1"
}

# =========================
# DB
# =========================

conn = sqlite3.connect("bot_v12.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS bets (
id INTEGER PRIMARY KEY AUTOINCREMENT,
home TEXT,
away TEXT,
league TEXT,
prob REAL,
odds REAL,
stake REAL,
ev REAL
)
""")

conn.commit()

# =========================
# FETCH
# =========================

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        if r.status_code != 200:
            return None
        return r.text
    except:
        return None

# =========================
# MATCHES
# =========================

def get_matches():

    send("🚀 SCRAPING INICIADO")

    matches = []

    for league, url in LEAGUES.items():

        html = fetch(url)

        if not html:
            continue

        for line in html.split("\n"):

            if " vs " in line.lower():

                matches.append({
                    "league": league,
                    "match": line.strip()
                })

    if len(matches) == 0:
        matches = [
            {"league": "fallback", "match": "Inter Miami vs LA Galaxy"},
            {"league": "fallback", "match": "Flamengo vs Palmeiras"},
            {"league": "fallback", "match": "Boca Juniors vs River Plate"}
        ]

    return matches

# =========================
# CLEAN
# =========================

def clean_match(text):

    try:
        if "vs" not in text.lower():
            return None, None

        a, b = text.split("vs")

        return a.strip(), b.strip()

    except:
        return None, None

# =========================
# MODEL (POISSON SIMPLE)
# =========================

def poisson(lmbda, k):
    return (math.exp(-lmbda) * lmbda ** k) / math.factorial(k)

def probs(hxg, axg):

    home = draw = away = 0

    for i in range(6):
        for j in range(6):

            p = poisson(hxg, i) * poisson(axg, j)

            if i > j:
                home += p
            elif i == j:
                draw += p
            else:
                away += p

    total = home + draw + away

    return home/total, draw/total, away/total

# =========================
# XG SIMPLE
# =========================

def xg(team):
    return 1.4, 1.1

# =========================
# ODDS (SIMULADO)
# =========================

def get_odds(home, away):
    return {"Home": 2.05, "Draw": 3.10, "Away": 3.60}

# =========================
# VALUE BET ENGINE V12
# =========================

def expected_value(prob, odds):
    return (prob * odds) - 1

def kelly(prob, odds):

    b = odds - 1
    q = 1 - prob

    if b <= 0:
        return 0

    k = (b * prob - q) / b

    return max(0, min(k, 0.15))  # 🔥 conservador

def is_good_bet(prob, odds):

    implied = 1 / odds
    edge = prob - implied

    return edge > EDGE_MIN

# =========================
# SAVE
# =========================

def save(home, away, league, prob, odds, stake, ev):

    c.execute("""
    INSERT INTO bets (home, away, league, prob, odds, stake, ev)
    VALUES (?,?,?,?,?,?,?)
    """, (home, away, league, prob, odds, stake, ev))

    conn.commit()

# =========================
# RUN
# =========================

def run():

    send("🚀 V12 VALUE BET INICIADO")

    matches = get_matches()

    send(f"📊 Partidos encontrados: {len(matches)}")

    picks = 0

    for m in matches[:25]:

        home, away = clean_match(m["match"])
        if not home or not away:
            continue

        league = m["league"]

        hxg, _ = xg(home)
        axg, _ = xg(away)

        ph, pd, pa = probs(hxg, axg)

        odds = get_odds(home, away)

        if not is_good_bet(ph, odds["Home"]):
            continue

        ev = expected_value(ph, odds["Home"])
        stake = min(kelly(ph, odds["Home"]), 0.10)

        if ev > 0.03 and stake > 0.02:

            save(home, away, league, ph, odds["Home"], stake, ev)

            send(f"""
⚽ {home} vs {away}
🌍 {league}

💰 Cuota: {odds['Home']}
📊 Prob: {round(ph,3)}
📈 EV: {round(ev,3)}
💵 Stake: {round(stake*100,2)}%
""")

            picks += 1

            if picks >= MAX_PICKS:
                break

    send("✅ CICLO COMPLETADO")

# =========================
# START
# =========================

send("🧪 TEST TELEGRAM OK")
run()
