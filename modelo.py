import requests
import time
import math

# =========================
# 🔑 CONFIG
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"
ODDS_API_KEY = "8c45ed3a66d6870a222bce3c47a34a88"

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
    except Exception as e:
        print("Error Telegram:", e)


# =========================
# 📊 MODELO SIMPLE
# =========================

def simple_prob_home():

    # Probabilidad fija temporal
    return 0.45


# =========================
# 🔍 SCANNER
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

        print("STATUS API:", response.status_code)

        data = response.json()

        # =========================
        # DEBUG API
        # =========================

        if not data:
            print("No hay partidos")
            send("⚠️ No hay partidos disponibles")
            return

        print("Partidos encontrados:", len(data))

        # =========================
        # RECORRER PARTIDOS
        # =========================

        for match in data:

            try:

                home = match["home_team"]
                away = match["away_team"]

                bookmakers = match["bookmakers"][0]
                markets = bookmakers["markets"][0]
                outcomes = markets["outcomes"]

                odds = outcomes[0]["price"]

            except Exception as e:

                print("Error leyendo partido:", e)
                continue

            # =========================
            # MODELO
            # =========================

            prob_model = simple_prob_home()

            market_prob = 1 / odds

            edge = prob_model - market_prob

            # =========================
            # DEBUG
            # =========================

            print(
                "PARTIDO:",
                home,
                "vs",
                away,
                "| Cuota:",
                odds,
                "| Edge:",
                round(edge, 3)
            )

            # =========================
            # VALUE BET
            # =========================

            if edge > 0.01:

                msg = f"""🔥 VALUE BET

⚽ {home} vs {away}

💰 Cuota: {odds}

📈 Prob modelo: {round(prob_model,2)}

💎 Edge: {round(edge,3)}
"""

                print("VALUE BET ENCONTRADA")

                send(msg)

    except Exception as e:

        print("ERROR API:", e)

        send(f"❌ ERROR API: {e}")


# =========================
# 🚀 MAIN LOOP
# =========================

print("🔥 BOT INICIADO")

while True:

    try:

        scan()

        print("⏳ Esperando siguiente ciclo...")

        time.sleep(1800)

    except Exception as e:

        print("ERROR GENERAL:", e)

        time.sleep(10)
