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

MAX_PICKS = 5
EDGE_MIN = 0.05

# =========================
# LIGAS (SOLO LAS QUE QUIERES)
# =========================

LEAGUES = {
    "mls": "https://www.espn.com/soccer/league/_/name/usa.1",
    "brazil_serie_a": "https://www.espn.com/soccer/league/_/name/bra.1",
    "argentina": "https://www.espn.com/soccer/league/_/name/arg.1"
}

# =========================
# DB
# =========================

conn = sqlite3.connect("bot_ligas.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS predictions (
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
# LOG
# =========================

def send(msg):
    print(msg)

# =========================
# TIMEOUT SAFE FETCH
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
# MATCH SCRAPER
# =========================

def get_matches():

    print("🚀 SCRAPING INICIADO")

    matches = []

    for league, url in LEAGUES.items():

        print(f"🌍 Liga: {league}")

        html = fetch(url)

        if not html:
            print(f"❌ Fallo scraping: {league}")
            continue

        lines = html.split("\n")

        for line in lines:

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
# CLEAN MATCH
# =========================

def clean_match(text):

    try:
        if "vs" not in text.lower():
            return None, None

        parts = text.split("vs")

        if len(parts) != 2:
            return None, None

        return parts[0].strip(), parts[1].strip()

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

    return {
        "Home": 2.05,
        "Draw": 3.10,
        "Away": 3.60
    }

# =========================
# EV + KELLY
# =========================

def expected_value(prob, odds):
    return (prob * odds) - 1

def kelly(prob, odds):

    b = odds - 1
    q = 1 - prob

    if b == 0:
        return 0

    k = (b * prob - q) / b

    return max(0, min(k, 0.2))

def valid(ev, stake):
    return ev > 0 and stake > 0

# =========================
# SAVE
# =========================

def save(home, away, league, prob, odds, stake, ev):

    c.execute("""
    INSERT INTO predictions (home, away, league, prob, odds, stake, ev)
    VALUES (?,?,?,?,?,?,?)
    """, (home, away, league, prob, odds, stake, ev))

    conn.commit()

# =========================
# RUN
# =========================

def run():

    send("🚀 BOT 3 LIGAS INICIADO")

    matches = get_matches()

    send(f"📊 Partidos encontrados: {len(matches)}")

    picks = 0

    for m in matches[:20]:

        home, away = clean_match(m["match"])

        if not home or not away:
            continue

        league = m["league"]

        hxg, _ = xg(home)
        axg, _ = xg(away)

        ph, pd, pa = probs(hxg, axg)

        odds = get_odds(home, away)

        ev = expected_value(ph, odds["Home"])
        stake = kelly(ph, odds["Home"])

        if valid(ev, stake):

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
# START SAFE (NO FREEZE)
# =========================

print("🚀 BOT INICIADO")

run()
