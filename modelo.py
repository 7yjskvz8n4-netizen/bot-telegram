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

MIN_ODDS = 1.42
MAX_ODDS = 2.30
BASE_EDGE = 0.05

HEADERS = {"x-apisports-key": API_KEY}

# =========================
# LIGAS
# =========================

LEAGUES = {
    13, 11, 71, 128, 103, 113,
    244, 165, 333, 866, 98, 292
}

# =========================
# CACHE
# =========================

FIXTURE_CACHE = "fixtures.json"
STATS_CACHE = "stats_cache.json"

# =========================
# DB
# =========================

conn = sqlite3.connect("bot_v23.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS picks (
id INTEGER PRIMARY KEY AUTOINCREMENT,
timestamp TEXT,
fixture_id INTEGER,
match TEXT,
league TEXT,
market TEXT,
selection TEXT,
odds REAL,
prob REAL,
edge REAL,
stake REAL,
result TEXT,
profit REAL
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
# SCHEDULE
# =========================

def bot_active():
    now = datetime.now(TZ)
    if now.weekday() < 5:
        return 17 <= now.hour < 22
    return 11 <= now.hour < 22

# =========================
# CACHE FIXTURES
# =========================

def get_fixtures():
    try:
        if os.path.exists(FIXTURE_CACHE):
            age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(FIXTURE_CACHE))
            if age < timedelta(minutes=60):
                return json.load(open(FIXTURE_CACHE))

        date = datetime.now(TZ).strftime("%Y-%m-%d")

        r = requests.get(
            f"{BASE_URL}/fixtures",
            headers=HEADERS,
            params={"date": date}
        )

        data = r.json().get("response", [])

        with open(FIXTURE_CACHE, "w") as f:
            json.dump(data, f)

        return data

    except:
        return []

# =========================
# STATS CACHE (MUY IMPORTANTE)
# =========================

def get_team_stats(league, team):

    if os.path.exists(STATS_CACHE):
        cache = json.load(open(STATS_CACHE))
    else:
        cache = {}

    key = f"{league}_{team}"

    if key in cache:
        return cache[key]

    r = requests.get(
        f"{BASE_URL}/teams/statistics",
        headers=HEADERS,
        params={
            "league": league,
            "season": datetime.now().year,
            "team": team
        }
    )

    data = r.json()["response"]

    cache[key] = data

    with open(STATS_CACHE, "w") as f:
        json.dump(cache, f)

    return data

# =========================
# MODEL
# =========================

def strength(stats):

    gf = float(stats["goals"]["for"]["average"]["total"])
    ga = float(stats["goals"]["against"]["average"]["total"])
    form = stats["fixtures"]["wins"]["total"] / max(stats["fixtures"]["played"]["total"], 1)

    return gf, ga, form


def xg(home, away):

    return (home[0] + away[1]) / 2, (away[0] + home[1]) / 2

# =========================
# POISSON
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
# EDGE
# =========================

def edge(p, o):
    return p - (1 / o)

# =========================
# ANTI SPAM
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
# MAIN
# =========================

def run():

    if not bot_active():
        return

    fixtures = get_fixtures()

    picks_today = 0

    for f in fixtures:

        if picks_today >= MAX_DAILY_PICKS:
            break

        fid = f["fixture"]["id"]
        league = f["league"]["id"]

        if league not in LEAGUES:
            continue

        home = f["teams"]["home"]
        away = f["teams"]["away"]

        stats_h = get_team_stats(league, home["id"])
        stats_a = get_team_stats(league, away["id"])

        h = strength(stats_h)
        a = strength(stats_a)

        hxg, axg = xg(h, a)

        ph, pd, pa = probs(hxg, axg)

        odds = get_odds(fid)
        if not odds:
            continue

        # =========================
        # 1X2 HOME
        # =========================

        if "Home" in odds and not sent(fid, "1X2_HOME"):

            o = odds["Home"]
            if MIN_ODDS <= o <= MAX_ODDS and edge(ph, o) > BASE_EDGE:

                send(f"""
⚽ {home['name']} vs {away['name']}
📊 1X2 HOME
💰 {o}
📈 Edge: {round(edge(ph,o)*100,2)}%
""")

                mark(fid, "1X2_HOME")
                picks_today += 1

        # =========================
        # OVER 2.5
        # =========================

        total = hxg + axg
        over_prob = 1 if total > 2.8 else 0.6

        if "Over 2.5" in odds and not sent(fid, "OVER"):

            o = odds["Over 2.5"]

            if edge(over_prob, o) > BASE_EDGE:

                send(f"""
⚽ {home['name']} vs {away['name']}
📊 OVER 2.5
💰 {o}
📈 Edge: {round(edge(over_prob,o)*100,2)}%
""")

                mark(fid, "OVER")
                picks_today += 1

        # =========================
        # BTTS
        # =========================

        if "Yes" in odds and not sent(fid, "BTTS"):

            btts = 0.5 if hxg > 1 and axg > 1 else 0.35

            o = odds["Yes"]

            if edge(btts, o) > BASE_EDGE:

                send(f"""
⚽ {home['name']} vs {away['name']}
📊 BTTS
💰 {o}
📈 Edge: {round(edge(btts,o)*100,2)}%
""")

                mark(fid, "BTTS")
                picks_today += 1

# =========================
# ODDS
# =========================

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

        odds = {}

        for b in data[0]["bookmakers"][0]["bets"]:

            if b["name"] == "Match Winner":
                for v in b["values"]:
                    odds[v["value"]] = float(v["odd"])

            if "Goals Over/Under" in b["name"]:
                for v in b["values"]:
                    odds[v["value"]] = float(v["odd"])

            if b["name"] == "Both Teams To Score":
                for v in b["values"]:
                    odds[v["value"]] = float(v["odd"])

        return odds

    except:
        return None

# =========================
# LOOP
# =========================

send("🚀 V2.3 FINAL STARTED")

while True:
    try:
        run()
        time.sleep(3600)
    except Exception as e:
        send(f"ERROR: {e}")
        time.sleep(60)
