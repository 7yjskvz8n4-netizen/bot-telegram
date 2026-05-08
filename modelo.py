import requests
import time
import math

# =========================
# 🔑 CONFIG
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"
API_KEY = "167721723854a65832f09abdeb92952b"

BANK = 1000

# LIGAS RENTABLES (añade Hypermotion aquí si quieres)
ALLOWED_LEAGUES = [140, 78, 135]


# =========================
# 📩 TELEGRAM
# =========================

def send(msg):

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        print("Error Telegram")


# =========================
# ⚽ POISSON AVANZADO
# =========================

def poisson(k, lam):
    return (lam ** k * math.exp(-lam)) / math.factorial(k)


def match_probs(home_xg, away_xg):

    home_win = 0
    draw = 0
    away_win = 0

    for i in range(6):
        for j in range(6):

            p = poisson(i, home_xg) * poisson(j, away_xg)

            if i > j:
                home_win += p
            elif i == j:
                draw += p
            else:
                away_win += p

    return home_win, draw, away_win


# =========================
# 📊 FORMA REAL (BÁSICA PERO REAL)
# =========================

def get_team_strength(team_id):

    url = "https://v3.football.api-sports.io/fixtures"

    headers = {"x-apisports-key": API_KEY}

    params = {
        "team": team_id,
        "last": 5
    }

    try:

        r = requests.get(url, headers=headers, params=params)

        data = r.json()["response"]

        goals_scored = 0
        goals_conceded = 0

        for m in data:

            goals_scored += m["goals"]["home"] or 0
            goals_scored += m["goals"]["away"] or 0

        # simplificado
        return 1.0 + (goals_scored / 10)

    except:

        return 1.0


# =========================
# 🔍 SCAN
# =========================

def scan():

    print("🔍 escaneo avanzado")
    send("🔍 escaneo AVANZADO iniciado")

    url = "https://v3.football.api-sports.io/fixtures"

    headers = {
        "x-apisports-key": API_KEY
    }

    params = {
        "season": 2025
    }

    r = requests.get(url, headers=headers, params=params)

    if r.status_code != 200:
        send(f"❌ API ERROR {r.status_code}")
        return

    data = r.json()["response"]

    bets = []

    for match in data:

        league_id = match["league"]["id"]

        if league_id not in ALLOWED_LEAGUES:
            continue

        if match["goals"]["home"] is not None:
            continue

        home = match["teams"]["home"]
        away = match["teams"]["away"]

        home_name = home["name"]
        away_name = away["name"]

        home_strength = get_team_strength(home["id"])
        away_strength = get_team_strength(away["id"])

        # =========================
        # POISSON AJUSTADO
        # =========================

        base_home_xg = 1.5
        base_away_xg = 1.2

        home_xg = base_home_xg * home_strength
        away_xg = base_away_xg * away_strength

        home_prob, draw_prob, away_prob = match_probs(home_xg, away_xg)

        # cuotas simuladas base (luego se mejora con odds reales)
        home_odds = 2.05
        away_odds = 3.40

        home_edge = home_prob - (1 / home_odds)
        away_edge = away_prob - (1 / away_odds)

        bets.append(("HOME", home_name, away_name, home_edge, home_odds))
        bets.append(("AWAY", home_name, away_name, away_edge, away_odds))

    # =========================
    # 🏆 TOP 5 CALIDAD
    # =========================

    bets.sort(key=lambda x: x[3], reverse=True)

    top5 = bets[:5]

    msg = "🔥 TOP 5 VALUE BETS AVANZADO\n\n"

    found = False
