import requests
import math
import sqlite3
import time
from datetime import datetime
from zoneinfo import ZoneInfo

# =========================
# CONFIG
# =========================

API_KEY = "b9bb7b48b07befece1272eb59c391bea"
TELEGRAM_TOKEN = "8510764547:AAG1lOyQN5UoeiYEzIcuY-WZI_QykbbEwik"
CHAT_ID = "1335805552"

BASE_URL = "https://v3.football.api-sports.io"
TZ = ZoneInfo("Europe/Madrid")

MAX_CALLS = 100
MAX_PICKS = 5
TOP_N = 8

BASE_EDGE = 0.03

ACTIVE_LEAGUES = {13, 11, 71, 128, 103, 113, 244, 165, 866, 98, 292}

HEADERS = {"x-apisports-key": API_KEY}

api_calls = 0

# =========================
# DB
# =========================

conn = sqlite3.connect("bot_v6.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS bets (
fixture_id INTEGER PRIMARY KEY,
league_id INTEGER,
prob REAL,
result INTEGER
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
# SAFE REQUEST
# =========================

def safe_request(url, params=None):
    global api_calls

    if api_calls >= MAX_CALLS:
        return None

    r = requests.get(url, headers=HEADERS, params=params)
    api_calls += 1

    if r.status_code != 200:
        return None

    return r.json()

# =========================
# 1. FIXTURES (CALL #1)
# =========================

def get_fixtures():

    data = safe_request(
        f"{BASE_URL}/fixtures",
        {"date": datetime.now(TZ).strftime("%Y-%m-%d")}
    )

    if not data:
        return []

    return data.get("response", [])

# =========================
# 2. QUICK SCORING (NO API)
# =========================

def score_fixture(f):

    league = f["league"]["id"]
    home = f["teams"]["home"]["name"]
    away = f["teams"]["away"]["name"]

    score = 0

    if league in ACTIVE_LEAGUES:
        score += 3

    if home != away:
        score += 1

    # partidos más “normales” suelen ser mejores
    if f["fixture"]["status"]["long"] == "Not Started":
        score += 1

    return score

# =========================
# 3. GET ODDS (CALL #2 / #3)
# =========================

def get_odds(fid):

    data = safe_request(
        f"{BASE_URL}/odds",
        {"fixture": fid}
    )

    if not data:
        return None

    for b in data[0]["bookmakers"]:

        if b["name"] != "Bet365":
            continue

        odds = {}

        for bet in b["bets"]:
            if bet["name"] == "Match Winner":
                for v in bet["values"]:
                    odds[v["value"]] = float(v["odd"])

        return odds

    return None

# =========================
# 4. SIMPLE MODEL (Poisson básico estable)
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

    total = home + draw + away

    return home/total, draw/total, away/total

# =========================
# EDGE
# =========================

def edge(prob, odds):
    return prob - (1 / odds)

# =========================
# SAVE BET
# =========================

def save(fid, league, prob):

    c.execute("""
        INSERT OR REPLACE INTO bets VALUES (?,?,?,NULL)
    """, (fid, league, prob))

    conn.commit()

# =========================
# RUN (3 CALL STRATEGY)
# =========================

def run():

    global api_calls
    api_calls = 0

    send("🚀 V6 OPTIMIZADO INICIADO")

    # =====================
    # CALL 1: FIXTURES
    # =====================
    fixtures = get_fixtures()

    send(f"📊 Partidos: {len(fixtures)}")

    # =====================
    # RANKING SIN API
    # =====================
    ranked = sorted(fixtures, key=score_fixture, reverse=True)

    selected = ranked[:TOP_N]

    send(f"🎯 Seleccionados: {len(selected)}")

    picks = 0

    # =====================
    # CALLS 2-3: SOLO TOP
    # =====================
    for f in selected:

        if api_calls >= MAX_CALLS:
            break

        fid = f["fixture"]["id"]
        league = f["league"]["id"]

        home = f["teams"]["home"]
        away = f["teams"]["away"]

        odds = get_odds(fid)  # CALL CONTROLADO
        if not odds:
            continue

        # modelo simple estable (puedes mejorar luego con xG)
        ph, pd, pa = probs(0.55, 0.45)

        if "Home" in odds:

            o = odds["Home"]
            e = edge(ph, o)

            save(fid, league, ph)

            if e > BASE_EDGE:

                send(f"""
⚽ {home['name']} vs {away['name']}
💰 Cuota: {o}
📈 Edge: {round(e*100,2)}%
""")

                picks += 1

                if picks >= MAX_PICKS:
                    break

    send(f"✅ Picks: {picks}")
    send(f"🔌 API calls: {api_calls}")

# =========================
# LOOP
# =========================

send("🚀 BOT V6 START")

while True:
    run()
    time.sleep(86400)
