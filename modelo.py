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

# LIGAS RENTABLES (puedes ajustar)
ALLOWED_LEAGUES = [140, 78, 135]  # LaLiga, Premier, Serie A


# =========================
# 📩 TELEGRAM
# =========================

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except Exception as e:
        print("Telegram error:", e)


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
# 📊 FORMA SIMPLE (REAL API BASE)
# =========================

def team_form(team_id):

    try:

        url = "https://v3.football.api-sports.io/fixtures"

        headers = {"x-apisports-key": API_KEY}

        params = {
            "team": team_id,
            "last": 5
        }

        r = requests.get(url, headers=headers, params=params)

        data = r.json()["response"]

        goals = 0

        for m in data:
            goals += (m["goals"]["home"] or 0)
            goals += (m["goals"]["away"] or 0)

        return 1 + (goals / 12)

    except:
        return 1


# =========================
# 💰 KELLY SIMPLIFICADO
# =========================

def kelly(edge, odds):

    if edge <= 0:
        return 0

    b = odds - 1
    p = edge + (1 / odds)
    q = 1 - p

    return max(0, (b * p - q) / b)


# =========================
# 🔍 SCAN
# =========================

def scan():

    print("🔍 scan PRO iniciado")
    send("🔍 escaneo PRO activo")

    url = "https://v3.football.api-sports.io/fixtures"

    headers = {"x-apisports-key": API_KEY}

    params = {"season": 2025}

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

        # =========================
        # FORMA REAL
        # =========================

        home_form = team_form(home["id"])
        away_form = team_form(away["id"])

        # =========================
        # POISSON AJUSTADO
        # =========================

        base_home_xg = 1.5 * home_form
        base_away_xg = 1.2 * away_form

        home_prob, draw_prob, away_prob = match_probs(base_home_xg, base_away_xg)

        # cuotas simuladas (puedes sustituir luego por odds reales)
        home_odds = 2.10
        away_odds = 3.40

        home_edge = home_prob - (1 / home_odds)
        away_edge = away_prob - (1 / away_odds)

        bets.append(("HOME", home_name, away_name, home_edge, home_odds))
        bets.append(("AWAY", home_name, away_name, away_edge, away_odds))

    # =========================
    # 🏆 TOP PICKS
    # =========================

    bets.sort(key=lambda x: x[3], reverse=True)

    top5 = bets[:5]

    msg = "🔥 TOP 5 VALUE BETS PRO\n\n"

    found = False

    for b in top5:

        side, home, away, edge, odds = b

        if edge > 0.01:

            stake = kelly(edge, odds) * BANK

            found = True

            msg += f"""⚽ {home} vs {away}
➡️ {side}
💰 Cuota: {odds}
📈 Edge: {round(edge,3)}
💵 Stake: €{round(stake,2)}

"""

    if found:
        send(msg)
    else:
        send("⚠️ Sin value bets PRO este ciclo")

    print("SCAN PRO terminado")


# =========================
# 🚀 LOOP
# =========================

print("🔥 BOT PRO AVANZADO INICIADO")
send("🔥 BOT PRO ONLINE")

while True:

    try:
        scan()
        time.sleep(180)

    except Exception as e:
        print("ERROR LOOP:", e)
        time.sleep(10)
