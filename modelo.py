import time
import math
import requests

# =========================
# 🔑 CONFIGURACIÓN
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"
ODDS_API_KEY = "8c45ed3a66d6870a222bce3c47a34a88"

# =========================
# 📩 TELEGRAM
# =========================

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": msg
        }
    )

# =========================
# 📊 POISSON
# =========================

def poisson_prob(k, lam):
    return (lam ** k * math.exp(-lam)) / math.factorial(k)

# =========================
# 🤖 BOT PRINCIPAL
# =========================

def run_bot():

    print("🔄 Analizando mercados...")

    url = "https://api.the-odds-api.com/v4/sports/soccer_spain_la_liga/odds"

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h"
    }

    response = requests.get(url, params=params)

    data = response.json()

    if not data:
        print("❌ No hay datos")
        return

    # 💰 Gestión de banca
    bank = 1000
    risk = 0.02
    stake = bank * risk

    # =========================
    # 🔁 RECORRER PARTIDOS
    # =========================

    for match in data:

        try:

            home_team = match["home_team"]
            away_team = match["away_team"]

            bookmaker = match["bookmakers"][0]

            market = bookmaker["markets"][0]

            odds = market["outcomes"]

            odds_home = odds[0]["price"]

            # =========================
            # 📊 MODELO SIMPLE
            # =========================

            home_goals = 1.6
            away_goals = 1.2

            home_win = 0

            for i in range(6):

                for j in range(6):

                    p = poisson_prob(i, home_goals) * poisson_prob(j, away_goals)

                    if i > j:
                        home_win += p

            # =========================
            # 💰 VALUE
            # =========================

            implied = 1 / odds_home

            edge = home_win - implied

            print(
                home_team,
                "vs",
                away_team,
                "Edge:",
                round(edge, 3)
            )

            # =========================
            # 🚨 VALUE BET
            # =========================

            if edge > 0.05:

                send(f"""🔥 VALUE BET

{home_team} vs {away_team}

Cuota: {odds_home}

Prob modelo: {round(home_win, 2)}

Edge: {round(edge, 3)}

Stake recomendado: €{round(stake, 2)}
""")

        except Exception as e:

            print("❌ Error partido:", e)

# =========================
# 🔄 LOOP 24/7
# =========================

while True:

    try:

        run_bot()

        print("⏳ Esperando 30 minutos...")

        time.sleep(1800)

    except Exception as e:

        print("❌ Error general:", e)

        time.sleep(10)
