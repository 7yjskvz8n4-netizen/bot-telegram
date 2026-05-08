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
RISK = 0.5  # reducción de Kelly (más seguro)

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
    except:
        print("Telegram error")


# =========================
# ⚽ POISSON
# =========================

def poisson(k, lam):
    return (lam ** k * math.exp(-lam)) / math.factorial(k)


def match_probs(home_xg, away_xg):

    home_win = draw = away_win = 0

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
# 📊 FORM + STRENGTH
# =========================

def team_strength(team_id):

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

        return 1 + (goals / 15)

    except:
        return 1


# =========================
# 💰 KELLY
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

    print("🔍 SCAN PRO FINAL")
    send("🔍 escaneo PRO FINAL activo")

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

        league = match["league"]["id"]

        if league not in ALLOWED_LEAGUES:
            continue

        if match["goals"]["home"] is not None:
            continue

        home = match["teams"]["home"]
        away = match["teams"]["away"]

        home_name = home["name"]
        away_name = away["name"]

        # =========================
        # STRENGTH
        # =========================

        h_strength = team_strength(home["id"])
        a_strength = team_strength(away["id"])

        # =========================
        # XG MODEL
        # =========================

        home_xg = 1.55 * h_strength
        away_xg = 1.20 * a_strength

        home_prob, draw_prob, away_prob = match_probs(home_xg, away_xg)

        # =========================
        # ODDS SIMULADAS (fase final)
        # =========================

        home_odds = 2.05
        away_odds = 3.30

        home_edge = home_prob - (1 / home_odds)
        away_edge = away_prob - (1 / away_odds)

        # filtro anti ruido
        if home_edge > 0.015:
            bets.append(("HOME", home_name, away_name, home_edge, home_odds))

        if away_edge > 0.015:
            bets.append(("AWAY", home_name, away_name, away_edge, away_odds))

    # =========================
    # 🏆 TOP 5 FINAL
    # =========================

    bets.sort(key=lambda x: x[3], reverse=True)

    top5 = bets[:5]

    msg = "🔥 TOP 5 VALUE BETS PRO FINAL\n\n"

    if not top5:
        send("⚠️ Sin value bets en este ciclo")
        return

    for b in top5:

        side, home, away, edge, odds = b

        stake = kelly(edge, odds) * BANK * RISK

        msg += f"""⚽ {home} vs {away}
➡️ {side}
💰 Cuota: {odds}
📈 Edge: {round(edge,3)}
💵 Stake: €{round(stake,2)}

"""

    send(msg)
    print("SCAN FINAL OK")


# =========================
# 🚀 LOOP
# =========================

print("🔥 BOT PRO FINAL INICIADO")
send("🔥 BOT PRO FINAL ONLINE")

while True:

    try:
        scan()
        time.sleep(180)

    except Exception as e:
        print("ERROR LOOP:", e)
        time.sleep(10)
