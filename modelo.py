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

# LIGAS PERMITIDAS (puedes añadir Hypermotion aquí)
ALLOWED_LEAGUES = [140, 135, 78]  # LaLiga, Serie A, Premier League (ejemplo)


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
# ⚽ POISSON
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
# 📊 FORM (SIMPLIFICADO BASE)
# =========================

def team_form_factor():

    # placeholder realista (luego se conecta a stats reales)
    return 1.0


# =========================
# 🔍 SCAN
# =========================

def scan():

    print("🔍 escaneando PRO system")
    send("🔍 escaneando value bets PRO")

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

        # =========================
        # FILTRO DE LIGAS
        # =========================

        if league_id not in ALLOWED_LEAGUES:
            continue

        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]

        goals_home = match["goals"]["home"]
        goals_away = match["goals"]["away"]

        # solo partidos no jugados
        if goals_home is not None:
            continue

        # =========================
        # POISSON BASE
        # =========================

        home_xg = 1.55 * team_form_factor()
        away_xg = 1.20 * team_form_factor()

        home_prob, draw_prob, away_prob = match_probs(home_xg, away_xg)

        # =========================
        # CUOTAS SIMPLIFICADAS (API base)
        # =========================

        home_odds = 2.10
        away_odds = 3.30

        home_edge = home_prob - (1 / home_odds)
        away_edge = away_prob - (1 / away_odds)

        bets.append(("HOME", home, away, home_edge, home_odds))
        bets.append(("AWAY", home, away, away_edge, away_odds))

    # =========================
    # 🏆 TOP 5
    # =========================

    bets.sort(key=lambda x: x[3], reverse=True)

    top5 = bets[:5]

    msg = "🔥 TOP 5 VALUE BETS PRO\n\n"

    found = False

    for b in top5:

        side, home, away, edge, odds = b

        if edge > 0.01:

            found = True

            msg += f"""⚽ {home} vs {away}
➡️ {side}
💰 Cuota: {odds}
📈 Edge: {round(edge,3)}
💵 Stake sugerido: {round(edge * BANK,2)}

"""

    if found:
        send(msg)
    else:
        send("⚠️ Sin value bets PRO en este ciclo")

    print("SCAN PRO terminado")


# =========================
# 🚀 LOOP
# =========================

print("🔥 BOT PRO INICIADO")

while True:

    try:
        scan()
        time.sleep(1800)

    except Exception as e:
        print("ERROR LOOP:", e)
        time.sleep(10)
