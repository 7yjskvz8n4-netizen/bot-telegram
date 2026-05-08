import requests
import time

# =========================
# 🔑 CONFIG
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"
API_KEY = "167721723854a65832f09abdeb92952b"

BANK = 1000

ALLOWED_LEAGUES = [140, 78, 135]  # España, Premier, etc.


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
    except Exception as e:
        print("Error Telegram:", e)


# =========================
# 🔍 SCAN SIMPLE Y SEGURO
# =========================

def scan():

    print("🔍 scan iniciado")
    send("🔍 bot activo - escaneando partidos")

    url = "https://v3.football.api-sports.io/fixtures"

    headers = {
        "x-apisports-key": API_KEY
    }

    params = {
        "season": 2025
    }

    try:

        r = requests.get(url, headers=headers, params=params)

        print("STATUS API:", r.status_code)

        if r.status_code != 200:
            send(f"❌ API ERROR {r.status_code}")
            print(r.text)
            return

        data = r.json()["response"]

        bets_found = 0

        for match in data:

            league_id = match["league"]["id"]

            if league_id not in ALLOWED_LEAGUES:
                continue

            # solo partidos no jugados
            if match["goals"]["home"] is not None:
                continue

            home = match["teams"]["home"]["name"]
            away = match["teams"]["away"]["name"]

            # =========================
            # MODELO SIMPLE ESTABLE
            # =========================

            home_prob = 0.46
            away_prob = 0.28

            home_odds = 2.10
            away_odds = 3.30

            home_edge = home_prob - (1 / home_odds)
            away_edge = away_prob - (1 / away_odds)

            # =========================
            # FILTRO VALUE BET
            # =========================

            if home_edge > 0.01:

                msg = f"""🔥 VALUE BET

⚽ {home} vs {away}
➡️ HOME
💰 Cuota: {home_odds}
📈 Edge: {round(home_edge,3)}
"""

                send(msg)
                bets_found += 1

            if away_edge > 0.01:

                msg = f"""🔥 VALUE BET

⚽ {home} vs {away}
➡️ AWAY
💰 Cuota: {away_odds}
📈 Edge: {round(away_edge,3)}
"""

                send(msg)
                bets_found += 1

        if bets_found == 0:
            send("⚠️ No hay value bets este ciclo")

        print("SCAN COMPLETADO")

    except Exception as e:
        print("ERROR SCAN:", e)
        send(f"❌ ERROR: {e}")


# =========================
# 🚀 LOOP PRINCIPAL
# =========================

print("🔥 BOT INICIADO CORRECTAMENTE")
send("🔥 BOT ONLINE")

while True:

    try:

        scan()

        print("⏳ esperando siguiente ciclo...")

        time.sleep(180)

    except Exception as e:

        print("ERROR LOOP:", e)
        time.sleep(10)
