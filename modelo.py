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

    # =========================
    # 💰 GESTIÓN DE BANCA
    # =========================

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
            # ⚽ MODELO MEJORADO
            # =========================

            attack_home = 1.4
            defense_home = 1.0

            attack_away = 1.1
            defense_away = 1.3

            home_goals = attack_home * defense_away
            away_goals = attack_away * defense_home

            home_win = 0

            for i in range(6):

                for j in range(6):

                    p = poisson_prob(i, home_goals) * poisson_prob(j, away_goals)

                    if i > j:
                        home_win += p

            # =========================
            # 📊 EDGE + EV
            # =========================

            implied = 1 / odds_home

            edge = home_win - implied

            ev = (home_win * odds_home) - 1

            print(
                home_team,
                "vs",
                away_team,
                "Edge:",
                round(edge, 3),
                "EV:",
                round(ev, 3)
            )

            # =========================
            # 🚨 VALUE BET
            # =========================

            if edge > 0.08 and ev > 0.05 and odds_home >= 1.70:

                send(f"""🔥 VALUE BET DETECTADA

⚽ Partido:
{home_team} vs {away_team}

💰 Cuota:
{odds_home}

📊 Probabilidad modelo:
{round(home_win, 2)}

📈 Edge:
{round(edge, 3)}

💎 EV:
{round(ev, 3)}

💵 Stake recomendado:
€{round(stake, 2)}
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
