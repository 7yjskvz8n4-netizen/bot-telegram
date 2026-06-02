import requests
import math
import sqlite3
import time
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# =========================
# CONFIG
# =========================

API_KEY = "e93b17bb02fe486f1fa731494df8814c"
TELEGRAM_TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"

BASE_URL = "https://v3.football.api-sports.io"
TZ = ZoneInfo("Europe/Madrid")

BANKROLL = 50
MAX_DAILY_PICKS = 7

BASE_EDGE = 0.05

HEADERS = {"x-apisports-key": API_KEY}

# =========================
# LIGAS INICIALES
# =========================

ACTIVE_LEAGUES = {
    13, 11, 71, 128, 103, 113,
    244, 165, 866, 98, 292
}

# =========================
# DB
# =========================

conn = sqlite3.connect("bot_v23_1.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS league_stats (
league_id INTEGER PRIMARY KEY,
wins INTEGER DEFAULT 0,
losses INTEGER DEFAULT 0
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS sent (
fixture_id INTEGER,
market TEXT,
date TEXT,
PRIMARY KEY (fixture_id, market, date)
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
# BOT TIME
# =========================

def bot_active():
    return True

# =========================
# LIGA FACTOR
# =========================

def get_league_factor(league_id):

    c.execute("SELECT wins, losses FROM league_stats WHERE league_id=?",
              (league_id,))

    row = c.fetchone()

    if not row:
        return 1.0

    w, l = row
    total = w + l

    if total < 15:
        return 1.0

    wr = w / total

    if wr > 0.57:
        return 1.10
    elif wr > 0.52:
        return 1.00
    elif wr > 0.47:
        return 0.90
    else:
        return 0.75

# =========================
# AUTO ELIMINACIÓN DE LIGAS MALAS
# =========================

def update_league_filter():

    global ACTIVE_LEAGUES

    new_active = set()

    for lid in ACTIVE_LEAGUES:

        c.execute("SELECT wins, losses FROM league_stats WHERE league_id=?", (lid,))
        row = c.fetchone()

        if not row:
            new_active.add(lid)
            continue

        w, l = row
        total = w + l

        if total < 10:
            new_active.add(lid)
            continue

        wr = w / total

        # ❌ elimina ligas malas automáticamente
        if wr < 0.45:
            continue

        new_active.add(lid)

    ACTIVE_LEAGUES = new_active

# =========================
# EDGE
# =========================

def edge(prob, odds, league_id):

    base = prob - (1 / odds)
    return base * get_league_factor(league_id)

# =========================
# MARK SENT
# =========================

def sent(fid, market):
    today = datetime.now(TZ).strftime("%Y-%m-%d")

    c.execute("""
        SELECT 1 FROM sent WHERE fixture_id=? AND market=? AND date=?
    """, (fid, market, today))

    return c.fetchone() is not None


def mark(fid, market):
    today = datetime.now(TZ).strftime("%Y-%m-%d")

    c.execute("""
        INSERT OR IGNORE INTO sent VALUES (?,?,?)
    """, (fid, market, today))

    conn.commit()

# =========================
# POISSON SIMPLE
# =========================

def poisson(lmbda, k):
    return (math.exp(-lmbda) * lmbda ** k) / math.factorial(k)


def probs(h, a):

    home = draw = away = 0

    for i in range(6):
        for j in range(6):
            p = poisson(h, i) * poisson(a, j)

            if i > j:
                home += p
            elif i == j:
                draw += p
            else:
                away += p

    return home, draw, away

# =========================
# XG SIMPLE
# =========================

def xg(home, away):
    return (home[0] + away[1]) / 2, (away[0] + home[1]) / 2

# =========================
# TEAM STRENGTH (simplificado)
# =========================

def strength(stats):

    gf = float(stats["goals"]["for"]["average"]["total"])
    ga = float(stats["goals"]["against"]["average"]["total"])
    return gf, ga

# =========================
# FIXTURES
# =========================

def get_fixtures():

    date = datetime.now(TZ).strftime("%Y-%m-%d")

    r = requests.get(
        f"{BASE_URL}/fixtures",
        headers=HEADERS,
        params={"date": date}
    )

    data = r.json()

    return data.get("response", [])


# =========================
# ODDS
# =========================

def get_odds(fid):

    r = requests.get(
        f"{BASE_URL}/odds",
        headers=HEADERS,
        params={"fixture": fid}
    )

    data = r.json().get("response", [])
    if not data:
        return None

    odds = {}

    for b in data[0]["bookmakers"][0]["bets"]:

        if b["name"] == "Match Winner":
            for v in b["values"]:
                odds[v["value"]] = float(v["odd"])

    return odds

# =========================
# LEAGUE UPDATE RESULT (manual futuro)
# =========================

def update_result(league_id, win):

    c.execute("SELECT wins, losses FROM league_stats WHERE league_id=?", (league_id,))
    row = c.fetchone()

    if not row:
        c.execute("INSERT INTO league_stats VALUES (?,0,0)", (league_id,))
        conn.commit()
        row = (0, 0)

    w, l = row

    if win:
        w += 1
    else:
        l += 1

    c.execute("""
        UPDATE league_stats
        SET wins=?, losses=?
        WHERE league_id=?
    """, (w, l, league_id))

    conn.commit()

# =========================
# RUN
# =========================
def run():

    print("RUN EJECUTADO")

    fixtures = get_fixtures()

    print(f"FIXTURES ENCONTRADOS: {len(fixtures)}")
    send(f"FIXTURES ENCONTRADOS: {len(fixtures)}")

    picks = 0

    for f in fixtures:

        if picks >= MAX_DAILY_PICKS:
            break

        league = f["league"]["id"]

        if league not in ACTIVE_LEAGUES:
            continue

        fid = f["fixture"]["id"]

        home = f["teams"]["home"]
        away = f["teams"]["away"]

        odds = get_odds(fid)
        if not odds:
            continue

        h_stats = strength(home)
        a_stats = strength(away)

        hxg, axg = xg(h_stats, a_stats)

        ph, pd, pa = probs(hxg, axg)

        if "Home" in odds and not sent(fid, "HOME"):

            o = odds["Home"]

            e = edge(ph, o, league)

            print(f"{home['name']} vs {away['name']} | Edge={round(e,3)}")

            if e > BASE_EDGE:

                send(f"""
⚽ {home['name']} vs {away['name']}
💰 {o}
📈 Edge: {round(e*100,2)}%
""")

                mark(fid, "HOME")
                picks += 1
        # =========================
        # PICK SIMPLE HOME
        # =========================

        if "Home" in odds and not sent(fid, "HOME"):

            o = odds["Home"]

            if edge(ph, o, league) > BASE_EDGE:

                send(f"""
⚽ {home['name']} vs {away['name']}
📊 HOME WIN
💰 {o}
📈 Edge: {round(edge(ph,o,league)*100,2)}%
""")

                mark(fid, "HOME")
                picks += 1

# =========================
# LOOP
# =========================

print("BOT INICIADO")
send("🚀 V2.3.1 AUTO LIGA CLEANER INICIADO")

while True:
    try:
        run()
        time.sleep(3600)
    except Exception as e:
        send(f"ERROR: {e}")
        time.sleep(60)
