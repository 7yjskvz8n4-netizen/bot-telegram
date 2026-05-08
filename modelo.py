import requests
import time

# =========================
# 🔑 CONFIG
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"

API_KEY = "167721723854a65832f09abdeb92952b"

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
# 🔍 SCAN PARTIDOS
# =========================

def scan():

    print("🔍 escaneando partidos")
    send("🔍 escaneando mercados")

    url = "https://v3.football.api-sports.io/fixtures"

    headers = {
        "x-apisports-key": API_KEY
    }

    params = {
        "league": 140,  # La Liga
        "season": 2025
    }

    try:

        r = requests.get(url, headers=headers, params=params)

        print("STATUS:", r.status_code)

        if r.status_code != 200:

            send(f"❌ API ERROR {r.status_code}")
            return

        data = r.json()["response"]

        bets = []

        for match in data:

            home = match["teams"]["home"]["name"]
            away = match["teams"]["away"]["name"]

            goals_home = match["goals"]["home"]
            goals_away = match["goals"]["away"]

            # si aún no jugado
            if goals_home is not None:
                continue

            # =========================
            # MODELO SIMPLE BASE
            # =========================

            home_prob = 0.46
            away_prob = 0.28

            home_odds = 2.10
            away_odds = 3.40

            home_edge = home_prob - (1 / home_odds)
            away_edge = away_prob - (1 / away_odds)

            bets.append(("HOME", home, away, home_edge, home_odds))
            bets.append(("AWAY", home, away, away_edge, away_odds))

        # =========================
        # TOP 5
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
        else:
            send("⚠️ Sin value bets en este ciclo")

    except Exception as e:

        print("ERROR:", e)
        send(f"❌ ERROR: {e}")


# =========================
# 🚀 LOOP
# =========================

print("🔥 BOT API-FOOTBALL INICIADO")

while True:

    try:
        scan()
        time.sleep(1800)

    except Exception as e:
        print("ERROR LOOP:", e)
        time.sleep(10)
