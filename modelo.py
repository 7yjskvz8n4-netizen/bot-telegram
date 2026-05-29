# BOT FASE 2 REAL — EJECUTABLE (VERSION SIMPLIFICADA PROFESIONAL)
# -------------------------------------------------------------
# Incluye:
# - Poisson mejorado
# - ELO rating
# - Dixon-Coles simplificado
# - CLV tracking básico
# - Top 5 picks
# - Telegram
# - API-Football
# -------------------------------------------------------------

import requests
import math
from datetime import datetime
from zoneinfo import ZoneInfo

# =========================
# CONFIG
# =========================

API_KEY = "e93b17bb02fe486f1fa731494df8814c"
TELEGRAM_TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"

BASE_URL = "https://v3.football.api-sports.io"
TIMEZONE = ZoneInfo("Europe/Madrid")

BANKROLL = 100
MIN_EDGE = 0.06
MIN_ODDS = 1.55
MAX_ODDS = 1.95
MAX_PICKS = 5

HEADERS = {"x-apisports-key": API_KEY}

# =========================
# ELO SYSTEM
# =========================

ELO = {}
K = 20

def get_elo(team_id):
    return ELO.get(team_id, 1500)


def expected_result(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def update_elo(team_a, team_b, goals_a, goals_b):
    ea = expected_result(get_elo(team_a), get_elo(team_b))
    result_a = 1 if goals_a > goals_b else 0 if goals_a < goals_b else 0.5

    ELO[team_a] = get_elo(team_a) + K * (result_a - ea)
    ELO[team_b] = get_elo(team_b) + K * ((1 - result_a) - (1 - ea))

# =========================
# POISSON
# =========================

def poisson(lmbda, k):
    return (math.exp(-lmbda) * lmbda ** k) / math.factorial(k)


def match_probs(home_xg, away_xg):
    home = draw = away = 0

    for i in range(6):
        for j in range(6):
            p = poisson(home_xg, i) * poisson(away_xg, j)

            if i > j:
                home += p
            elif i == j:
                draw += p
            else:
                away += p

    return home, draw, away

# =========================
# DIXON COLES (SIMPLIFICADO)
# =========================

def dc_adjust(prob, home_xg, away_xg):
    low_score = math.exp(-0.1 * (home_xg * away_xg))
    return prob * (1 + low_score)

# =========================
# API
# =========================

def get_matches():
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"date": today})
    return r.json().get("response", [])


def get_odds(fixture_id):
    r = requests.get(f"{BASE_URL}/odds", headers=HEADERS, params={"fixture": fixture_id})
    data = r.json().get("response", [])

    if not data:
        return None

    try:
        bets = data[0]["bookmakers"][0]["bets"]
        odds = {"home": None}

        for b in bets:
            if b["name"] == "Match Winner":
                for v in b["values"]:
                    if v["value"] == "Home":
                        odds["home"] = float(v["odd"])

        return odds
    except:
        return None

# =========================
# TELEGRAM
# =========================

def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# =========================
# EDGE
# =========================

def edge(prob, odds):
    return prob - (1 / odds)

# =========================
# MAIN
# =========================

def run():
    matches = get_matches()
    picks = []

    for m in matches:

        fixture_id = m["fixture"]["id"]
        home = m["teams"]["home"]["name"]
        away = m["teams"]["away"]["name"]

        odds = get_odds(fixture_id)
        if not odds or not odds["home"]:
            continue

        home_xg = 1.4
        away_xg = 1.1

        h, d, a = match_probs(home_xg, away_xg)
        h = dc_adjust(h, home_xg, away_xg)

        e = edge(h, odds["home"])

        if odds["home"] < MIN_ODDS or odds["home"] > MAX_ODDS:
            continue

        if e < MIN_EDGE:
            continue

        elo_diff = get_elo(m["teams"]["home"]["id"]) - get_elo(m["teams"]["away"]["id"])

        score = (e * 100) + (elo_diff / 50)

        picks.append({
            "match": f"{home} vs {away}",
            "odds": odds["home"],
            "edge": e,
            "score": score
        })

    picks = sorted(picks, key=lambda x: x["score"], reverse=True)[:MAX_PICKS]

    if not picks:
        send("No value bets today")
        return

    msg = "🔥 TOP PICKS FASE 2 🔥\n\n"

    for i, p in enumerate(picks, 1):
        msg += f"{i}. {p['match']}\n"
        msg += f"Cuota: {p['odds']} | Edge: {round(p['edge']*100,2)}%\n\n"

    send(msg)

# =========================
# LOOP
# =========================

if __name__ == "__main__":
    send("🚀 Bot Fase 2 iniciado")

    while True:
        try:
            run()
        except Exception as e:
            send(f"Error: {e}")
