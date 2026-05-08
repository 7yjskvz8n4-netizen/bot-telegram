import requests
import time
import math

# =========================
# 🔑 CONFIG
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"
ODDS_API_KEY = "8c45ed3a66d6870a222bce3c47a34a88
# =========================
# 📩 TELEGRAM
# =========================

def send(msg):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    try:
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg
        })
    except:
        print("Error enviando Telegram")


# =========================
# 📊 PROBABILIDAD SIMPLE
# =========================

def simple_prob_home():

    return 0.45  # base inicial estable


# =========================
# 🔍 SCAN DE PARTIDOS
# =========================

def scan():

    print("🔍 scan iniciado")
    send("🔍 bot escaneando partidos")

    url = "https://api.the-odds-api.com/v4/sports/soccer_spain_la_liga/odds"

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h"
    }

    try:

        response = requests.get(url, params=params)

        print("status API:", response.status_code)

        data = response.json()

        if not data:
            send("⚠️ No hay datos disponibles")
            return

        for match in data:

            try:

                home = match["home_team"]
                away = match["away_team"]

                odds = match["bookmakers"][0]["markets"][0]["outcomes"][0]["price"]

            except:
                continue

            prob_model = simple_prob_home()
            market_prob = 1 / odds

            edge = prob_model - market_prob

            print(home, away, "edge:", edge)

            if edge > 0.05:

                send(f"""🔥 VALUE BET

{home} vs {away}

Cuota: {odds}
Prob modelo: {round(prob_model,2)}
Edge: {round(edge,3)}
""")

    except Exception as e:
        print("ERROR API:", e)
        send(f"❌ error API: {e}")


# =========================
# 🚀 LOOP PRINCIPAL
# =========================

print("🔥 BOT INICIADO")

while True:

    try:

        scan()
        time.sleep(1800)

    except Exception as e:

        print("ERROR GENERAL:", e)
        time.sleep(10)
