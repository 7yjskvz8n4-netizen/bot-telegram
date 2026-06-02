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

MAX_PICKS = 5
EDGE_MIN = 0.05

TZ = ZoneInfo("Europe/Madrid")

# =========================
# LIGAS
# =========================

LEAGUES = {
    "brazil": "https://www.espn.com/soccer/league/_/name/bra.1",
    "mls": "https://www.espn.com/soccer/league/_/name/usa.1",
    "japan": "https://www.espn.com/soccer/league/_/name/jpn.1",
    "korea": "https://www.espn.com/soccer/league/_/name/kor.1",
    "norway": "https://www.espn.com/soccer/league/_/name/nor.1",
    "sweden": "https://www.espn.com/soccer/league/_/name/swe.1",
    "argentina": "https://www.espn.com/soccer/league/_/name/arg.1"
}

# =========================
# DB
# =========================

conn = sqlite3.connect("v11_ligues.db", check_same_thread=False)
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
# TELEGRAM (LOG)
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
# FETCH
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
# GET MATCHES BY LEAGUE
# =========================

def get_matches():

    matches = []

    for league, url in LEAGUES.items():

        html = fetch(url)

        if not html:
            continue

        lines = html.split("\n")

        for line in lines:

            if " vs " in line.lower():

                matches.append({
                    "league": league,
                    "match": line.strip()
                })

    # fallback seguro
    if len(matches) == 0:

        matches = [
            {"league": "fallback", "match": "Barcelona vs Real Madrid"},
            {"league": "fallback", "match": "Milan vs Inter"}
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
# XG SIMPLE
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

    send("🚀 V11.5 BOT LIGAS INICIADO")

    raw = get_matches()

    matches = []

    for item in raw:

        home, away = clean_match(item["match"])

        if home and away:

            matches.append({
                "home": home,
                "away": away,
                "league": item["league"]
            })

    send(f"📊 Partidos encontrados: {len(matches)}")

    picks = 0

    for m in matches[:20]:

        home = m["home"]
        away = m["away"]
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
🌍 Liga: {league}

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
# LOOP 24/7 + HORARIO
# =========================

def main_loop():

    while True:

        now = datetime.now(TZ)

        if 10 <= now.hour < 20:

            run()
            time.sleep(1800)  # cada 30 min

        else:

            print("⏳ Fuera de horario (20:00–10:00)")
            time.sleep(300)

# =========================
# START
# =========================

def main_loop():

    print("🚀 LOOP INICIADO")

    while True:

        try:
            print("⏳ CHECK HORARIO")

            now = datetime.now(TZ)
            print("🕒 Hora:", now)

            if 10 <= now.hour < 20:
                print("🟢 ACTIVO")
                run()
            else:
                print("🔴 FUERA DE HORARIO")

        except Exception as e:
            print("❌ ERROR:", str(e))

        time.sleep(30)
