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
TIMEZONE = ZoneInfo("Europe/Madrid")

BANKROLL = 50
MAX_DAILY_PICKS = 7

MIN_ODDS = 1.42
MAX_ODDS = 2.30
BASE_EDGE = 0.05

HEADERS = {"x-apisports-key": API_KEY}

# =========================
# LIGAS
# =========================

ALLOWED_LEAGUES = {
    13, 11, 71, 128, 103, 113,
    244, 165, 333, 866, 98, 292
}

# =========================
# CACHE
# =========================

CACHE_FILE = "fixtures_cache.json"
CACHE_MINUTES = 60

# =========================
# DB
# =========================

conn = sqlite3.connect("bot_v2.db", check_same_thread=False)
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
CREATE TABLE IF NOT EXISTS sent_picks (
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
# BOT SCHEDULE
# =========================

def bot_active():
    now = datetime.now(TIMEZONE)
    if now.weekday() < 5:
        return 17 <= now.hour < 22
    return 11 <= now.hour < 22

# =========================
# ANTI-SPAM
# =========================

def already_sent(fid, market):
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    c.execute(
        "SELECT 1 FROM sent_picks WHERE fixture_id=? AND market=? AND date=?",
        (fid, market, today)
    )
    return c.fetchone() is not None


def mark_sent(fid, market):
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    c.execute(
        "INSERT OR IGNORE INTO sent_picks VALUES (?,?,?)",
        (fid, market, today)
    )
    conn.commit()

# =========================
# CACHE FIXTURES
# =========================

def get_matches():
    try:
        if os.path.exists(CACHE_FILE):
            age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(CACHE_FILE))
            if age < timedelta(minutes=CACHE_MINUTES):
                return json.load(open(CACHE_FILE))

        date = datetime.now(TIMEZONE).strftime("%Y-%m-%d")

        r = requests.get(
            f"{BASE_URL}/fixtures",
            headers=HEADERS,
            params={"date": date}
        )

        data = r.json().get("response", [])

        with open(CACHE_FILE, "w") as f:
            json.dump(data, f)

        return data

    except:
        return []

# =========================
# POISSON CORE
# =========================

def poisson(lmbda, k):
    return (math.exp(-lmbda) * lmbda ** k) / math.factorial(k)


def match_prob(h, a):
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
# EXPECTED GOALS MODEL
# =========================

def expected_goals(home_avg, away_avg, home_conc, away_conc):
    home_xg = (home_avg + away_conc) / 2
    away_xg = (away_avg + home_conc) / 2
    return home_xg, away_xg

# =========================
# TEAM STRENGTH
# =========================

def team_strength(stats):

    gf = float(stats["goals"]["for"]["average"]["total"])
    ga = float(stats["goals"]["against"]["average"]["total"])
    form = stats["fixtures"]["wins"]["total"] / max(stats["fixtures"]["played"]["total"], 1)

    return gf, ga, form

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

        bets = data[0]["bookmakers"][0]["bets"]

        odds = {}

        for b in bets:

            # 1X2
            if b["name"] == "Match Winner":
                for v in b["values"]:
                    odds[v["value"]] = float(v["odd"])

            # BTTS
            if b["name"] == "Both Teams To Score":
                for v in b["values"]:
                    odds[v["value"]] = float(v["odd"])

            # Over/Under
            if "Goals Over/Under" in b["name"]:
                for v in b["values"]:
                    odds[v["value"]] = float(v["odd"])

        return odds

    except:
        return None

# =========================
# EDGE
# =========================

def edge(prob, odds):
    return prob - (1 / odds)

# =========================
# MAIN
# =========================

def run():

    if not bot_active():
        return

    matches = get_matches()

    picks_today = 0

    for m in matches:

        if picks_today >= MAX_DAILY_PICKS:
            break

        fid = m["fixture"]["id"]
        league = m["league"]["id"]

        if league not in ALLOWED_LEAGUES:
            continue

        home = m["teams"]["home"]["name"]
        away = m["teams"]["away"]["name"]

        odds = get_odds(fid)
        if not odds:
            continue

        try:
            home_stats = get_team_stats(league, m["teams"]["home"]["id"])
            away_stats = get_team_stats(league, m["teams"]["away"]["id"])
        except:
            continue

        # =========================
        # BUILD STRENGTH
        # =========================

        h_gf, h_ga, _ = team_strength(home_stats)
        a_gf, a_ga, _ = team_strength(away_stats)

        hxg, axg = expected_goals(h_gf, a_gf, h_ga, a_ga)

        home_p, draw_p, away_p = match_prob(hxg, axg)

        # =========================
        # 1X2 HOME
        # =========================

        if "Home" in odds and not already_sent(fid, "1X2_HOME"):

            p = home_p
            o = odds["Home"]

            if MIN_ODDS <= o <= MAX_ODDS and edge(p, o) > BASE_EDGE:

                send(f"""
⚽ {home} vs {away}
📊 1X2 HOME
💰 {o}
📈 Edge: {round(edge(p,o)*100,2)}%
""")

                mark_sent(fid, "1X2_HOME")
                picks_today += 1

        # =========================
        # OVER 2.5
        # =========================

        total_goals = hxg + axg

        if "Over 2.5" in odds and not already_sent(fid, "OVER_2.5"):

            over_prob = 1 if total_goals > 3 else 0.6

            o = odds["Over 2.5"]

            if edge(over_prob, o) > BASE_EDGE:

                send(f"""
⚽ {home} vs {away}
📊 OVER 2.5
💰 {o}
📈 Edge: {round(edge(over_prob,o)*100,2)}%
""")

                mark_sent(fid, "OVER_2.5")
                picks_today += 1

        # =========================
        # BTTS
        # =========================

        if "Yes" in odds and not already_sent(fid, "BTTS"):

            btts_prob = 0.5 if hxg > 1 and axg > 1 else 0.35

            o = odds["Yes"]

            if edge(btts_prob, o) > BASE_EDGE:

                send(f"""
⚽ {home} vs {away}
📊 BTTS YES
💰 {o}
📈 Edge: {round(edge(btts_prob,o)*100,2)}%
""")

                mark_sent(fid, "BTTS")
                picks_today += 1

# =========================
# TEAM STATS API
# =========================

def get_team_stats(league, team):

    r = requests.get(
        f"{BASE_URL}/teams/statistics",
        headers=HEADERS,
        params={
            "league": league,
            "season": datetime.now().year,
            "team": team
        }
    )

    return r.json()["response"]

# =========================
# LOOP
# =========================

send("🚀 V2.2 BOT INICIADO")

while True:
    try:
        run()
        time.sleep(3600)
    except Exception as e:
        send(f"ERROR: {e}")
        time.sleep(60)
