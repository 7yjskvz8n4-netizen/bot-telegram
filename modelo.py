import requests
import math
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

# =========================
# CONFIG
# =========================

API_KEY = "b9bb7b48b07befece1272eb59c391bea"
TELEGRAM_TOKEN = "8647764005:AAEt7k4vsUpQLMuti6iqGIDBF7ngOJ9vqRA"
CHAT_ID = "1335805552"

BASE_URL = "https://v3.football.api-sports.io"
TZ = ZoneInfo("Europe/Madrid")

MAX_CALLS = 100
TOP_N = 10
MAX_PICKS = 5
EDGE_MIN = 0.05

HEADERS = {"x-apisports-key": API_KEY}

api_calls = 0

# =========================
# DB (learning simple)
# =========================

conn = sqlite3.connect("bot_v5.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS league_stats (
league_id INTEGER PRIMARY KEY,
score REAL DEFAULT 1
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

    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        api_calls += 1

        if r.status_code != 200:
            return None

        return r.json()

    except:
        return None

# =========================
# FIXTURES
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
# LEAGUE LEARNING
# =========================

def league_score(league_id):

    c.execute("SELECT score FROM league_stats WHERE league_id=?", (league_id,))
    row = c.fetchone()

    if not row:
        return 1.0

    return row[0]

def update_league(league_id, win):

    score = league_score(league_id)

    if win:
        score *= 1.02
    else:
        score *= 0.98

    c.execute("""
    INSERT OR REPLACE INTO league_stats VALUES (?,?)
    """, (league_id, score))

    conn.commit()

# =========================
# POISSON
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
# XG REAL PROXY (MEJORADO)
# =========================

def xg_from_team(team_id):

    data = safe_request(
        f"{BASE_URL}/teams/statistics",
        {"team": team_id, "season": 2024}
    )

    if not data or not data.get("response"):
        return 1.2, 1.2

    stats = data["response"]

    gf = stats["goals"]["for"]["total"]["home"] or 0
    ga = stats["goals"]["against"]["total"]["home"] or 0

    matches = stats["fixtures"]["played"]["home"] or 1

    attack = gf / matches
    defense = ga / matches

    # suavizado
    xg = (attack + 1.2) / 2
    xga = (defense + 1.2) / 2

    return xg, xga

# =========================
# ODDS
# =========================

def get_odds(fid):

    data = safe_request(
        f"{BASE_URL}/odds",
        {"fixture": fid}
    )

    if not data:
        return None

    res = data.get("response", [])
    if not res:
        return None

    for b in res[0].get("bookmakers", []):

        if b.get("name") != "Bet365":
            continue

        odds = {}

        for bet in b.get("bets", []):

            if bet.get("name") == "Match Winner":

                for v in bet.get("values", []):
                    odds[v["value"]] = float(v["odd"])

        return odds

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

    global api_calls
    api_calls = 0

    send("🚀 V5 PRO INICIADO")

    fixtures = get_fixtures()

    send(f"📊 Partidos: {len(fixtures)}")

    picks = 0

    ranked = sorted(
        fixtures,
        key=lambda x: league_score(x["league"]["id"]),
        reverse=True
    )

    for f in ranked[:TOP_N]:

        if api_calls >= MAX_CALLS:
            break

        fid = f["fixture"]["id"]
        league = f["league"]["id"]

        home = f["teams"]["home"]
        away = f["teams"]["away"]

        odds = get_odds(fid)
        if not odds:
            continue

        # xG real proxy
        hxg, hxa = xg_from_team(home["id"])
        axg, axa = xg_from_team(away["id"])

        ph, pd, pa = probs(hxg, axg)

        if "Home" in odds:

            o = odds["Home"]
            e = edge(ph, o)

            if e > EDGE_MIN:

                send(f"""
⚽ {home['name']} vs {away['name']}
💰 Cuota: {o}
📈 Edge: {round(e*100,2)}%
""")

                update_league(league, True)

                picks += 1

                if picks >= MAX_PICKS:
                    break

    send(f"✅ Picks: {picks}")
    send(f"🔌 API calls: {api_calls}")

# =========================
# START
# =========================

send("🚀 BOT V5 ARRANCADO")
run()
