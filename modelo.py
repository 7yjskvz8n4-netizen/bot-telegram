import requests
import time
import math

# =========================
# 🔑 CONFIG
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"

# 👇 PEGA TU API KEY REAL
ODDS_API_KEY = "90ae2f6d7b5ddcd76926f1cf40be2ad7"
"

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

    # Probabilidad base temporal
    return 0.45


# =========================
# 🔍 SCANNER
# =========================

def scan():

    print("🔍 scan iniciado")

    send("🔍 bot escaneando partidos")

    # 👇 ENDPOINT MÁS ESTABLE
    url = "https://api.the-odds-api.com/v4/sports/upcoming/odds"

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }

    try:

        response = requests.get(url, params=params)

        print("STATUS API:", response.status_code)

        # =========================
        # CONTROL ERRORES API
        # =========================

        if response.status_code != 200:

            print("ERROR API:", response.text)

            send(f"❌ API ERROR {response.status_code}")

            return

        data = response.json()

        # =========================
        # DEBUG
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

                # 👇 CUOTA LOCAL
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

                print("✅ VALUE BET ENCONTRADA")

                send(msg)

    except Exception as e:

        print("ERROR GENERAL API:", e)

        send(f"❌ ERROR API: {e}")


# =========================
# 🚀 MAIN LOOP
# =========================

print("🔥 BOT INICIADO")

while True:

    try:

        scan()

        print("⏳ Esperando siguiente ciclo...")

        # 30 minutos
        time.sleep(1800)

    except Exception as e:

        print("ERROR LOOP:", e)

        time.sleep(10)
