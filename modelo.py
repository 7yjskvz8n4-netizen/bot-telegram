import requests
import time
import math

# =========================
# 🔑 CONFIG
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"
ODDS_API_KEY = "90ae2f6d7b5ddcd76926f1cf40be2ad7"

BANK = 1000

# =========================
# 📩 TELEGRAM
# =========================

def send(msg):

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": msg
            }
        )
    except:
        print("Error Telegram")


# =========================
# ⚽ POISSON
# =========================

def poisson(k, lam):
    return (lam ** k * math.exp(-lam)) / math.factorial(k)


def match_prob(home_xg, away_xg):

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
# 🔍 SCAN
# =========================

def scan():

    print("🔍 scan iniciado")
    send("🔍 escaneando value bets")

    url = "https://api.the-odds-api.com/v4/sports/upcoming/odds"

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }

    r = requests.get(url, params=params)

    if r.status_code != 200:
        send(f"❌ API ERROR {r.status_code}")
        return

    data = r.json()

    bets = []

    for match in data:

        try:

            home = match["home_team"]
            away = match["away_team"]

            bookmakers = match["bookmakers"][0]
            outcomes = bookmakers["markets"][0]["outcomes"]

            home_odds = outcomes[0]["price"]
            away_odds = outcomes[1]["price"]

        except:
            continue

        # =========================
        # 🔥 XG SIMPLIFICADO (base)
        # =========================

        home_xg = 1.5
        away_xg = 1.1

        home_prob, draw_prob, away_prob = match_prob(home_xg, away_xg)

        home_edge = home_prob - (1 / home_odds)
        away_edge = away_prob - (1 / away_odds)

        bets.append(("HOME", home, away, home_edge, home_odds))
        bets.append(("AWAY", home, away, away_edge, away_odds))

    # =========================
    # 🏆 TOP 5
    # =========================

    bets.sort(key=lambda x: x[3], reverse=True)

    top5 = bets[:5]

    msg = "🔥 TOP 5 VALUE BETS\n\n"

    found = False

    for b in top5:

        side, home, away, edge, odds = b

        if edge > 0.01:

            found = True

            msg += f"""⚽ {home} vs {away}
➡️ {side}
💰 Cuota: {odds}
📈 Edge: {round(edge,3)}

"""

    if found:
        send(msg)
        print("TOP 5 enviado")
    else:
        send("⚠️ Sin value bets este ciclo")
        print("Sin bets")


# =========================
# 🚀 LOOP
# =========================

print("🔥 BOT POISSON INICIADO")

while True:

    try:
        scan()
        time.sleep(1800)

    except Exception as e:
        print("ERROR LOOP:", e)
        time.sleep(10)
