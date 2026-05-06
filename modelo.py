import requests
from scipy.stats import poisson

ODDS_API_KEY = "8c45ed3a66d6870a222bce3c47a34a88"
TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = 1335805552

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# =========================
# 📊 OBTENER DATOS
# =========================

url = "https://api.the-odds-api.com/v4/sports/soccer_spain_la_liga/odds"

params = {
    "apiKey": ODDS_API_KEY,
    "regions": "eu",
    "markets": "h2h"
}

response = requests.get(url, params=params)
data = response.json()

# =========================
# 🔁 RECORRER PARTIDOS
# =========================

for match in data:

    try:
        home_team = match["home_team"]
        away_team = match["away_team"]

        bookmaker = match["bookmakers"][0]
        odds = bookmaker["markets"][0]["outcomes"]

        odds_home = odds[0]["price"]

        # 📊 POISSON SIMPLE
        home_goals = 1.6
        away_goals = 1.2

        home_win = 0

        for i in range(6):
            for j in range(6):

                p = poisson.pmf(i, home_goals) * poisson.pmf(j, away_goals)

                if i > j:
                    home_win += p

        # 💰 VALUE BET
        implied = 1 / odds_home
        edge = home_win - implied

        print(home_team, "vs", away_team)
        print("Edge:", round(edge, 3))

        if edge > 0.05:

            send(f"""🔥 VALUE BET

{home_team} vs {away_team}

Cuota: {odds_home}
Prob modelo: {round(home_win,2)}
Edge: {round(edge,3)}
""")

    except Exception as e:
        print("Error en partido:", e)
        import time

while True:

    print("🔄 Analizando mercado...")

    # 👉 AQUÍ PEGAS TU FUNCIÓN PRINCIPAL
    # (el código que ya tienes de análisis)

    # espera 30 minutos
    time.sleep(1800)
    bank = 1000  # banca inicial €

risk = 0.02   # 2% por apuesta

stake = bank * risk
 if edge > 0.05:

    stake = bank * risk

    send(f"""🔥 VALUE BET

{home_team} vs {away_team}

Cuota: {odds_home}
Edge: {round(edge,3)}

💰 Stake recomendado: €{round(stake,2)}
""")