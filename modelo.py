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

EDGE_MIN = 0.05
MAX_PICKS = 5

TZ = ZoneInfo("Europe/Madrid")

# =========================
# DB
# =========================

conn = sqlite3.connect("v10_system.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS predictions (
id INTEGER PRIMARY KEY AUTOINCREMENT,
home TEXT,
away TEXT,
prob REAL,
odds REAL,
stake REAL,
ev REAL
)
""")

conn.commit()

# =========================
# TELEGRAM (opcional)
# =========================

def send(msg):
    print(msg)

# =========================
# TIME CONTROL
# =========================

def is_market_open():

    now = datetime.now(TZ)
    return 10 <= now.hour < 20

# =========================
# FETCH SAFE
# =========================

def fetch(url):

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)

        if r.status_code != 200:
            return None

        return r.text

    except:
        return None

# =========================
# GET MATCHES
# =========================

def get_matches():

    urls = [
        "https://www.espn.com/soccer/scoreboard",
        "https://www.skysports.com/football/live-scores"
    ]

    matches = []

    for url in urls:

        html = fetch(url)

        if not html:
            continue

        lines = html.split("\n")

        for line in lines:

            if " vs " in line.lower():
                matches.append(line.strip())

    # fallback seguro
    if len(matches) == 0:

        matches = [
            "Barcelona vs Real Madrid",
            "Milan vs Inter",
            "Arsenal vs Chelsea"
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

        home = parts[0].strip()
        away = parts[1].strip()

        return home, away

    except:
        return None, None

# =========================
# POISSON MODEL
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
# SIMPLE XG
# =========================

def xg(team):
    return 1.4, 1.1

# =========================
# ODDS (PLACEHOLDER)
# =========================

def get_odds(home, away):

    return {
        "Home": 2.00,
        "Draw": 3.20,
        "Away": 3.80
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

def save(home, away, prob, odds, stake, ev):

    c.execute("""
    INSERT INTO predictions (home, away, prob, odds, stake, ev)
    VALUES (?,?,?,?,?,?)
    """, (home, away, prob, odds, stake, ev))

    conn.commit()

# =========================
# CORE RUN
# =========================

def run():

    send("🚀 BOT ACTIVO (VENTANA 10:00–20:00)")

    raw = get_matches()

    matches = []

    for m in raw:

        home, away = clean_match(m)

        if home and away:
            matches.append((home, away))

    send(f"📊 Partidos encontrados: {len(matches)}")

    picks = 0

    for home, away in matches[:20]:

        hxg, _ = xg(home)
        axg, _ = xg(away)

        ph, pd, pa = probs(hxg, axg)

        odds = get_odds(home, away)

        ev = expected_value(ph, odds["Home"])
        stake = kelly(ph, odds["Home"])

        if valid(ev, stake):

            save(home, away, ph, odds["Home"], stake, ev)

            send(f"""
⚽ {home} vs {away}

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
# LOOP 24/7 CONTROLADO
# =========================

def main_loop():

    while True:

        if is_market_open():

            run()
            time.sleep(1800)  # cada 30 min

        else:

            print("⏳ Mercado cerrado (20:00–10:00)")
            time.sleep(300)  # check cada 5 min

# =========================
# START
# =========================

main_loop()
