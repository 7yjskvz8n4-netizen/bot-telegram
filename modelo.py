import time
import math
import requests

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
# 🧠 KELLY
# =========================

def kelly(edge, odds):

    if edge <= 0:
        return 0

    b = odds - 1
    p = edge + (1 / odds)
    q = 1 - p

    f = (b * p - q) / b

    return max(0, f)

# =========================
# 🤖 BOT
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
        print("❌ Sin datos")
        return

    bank = 1000

    for match in data:

        try:

            home_team = match["home_team"]
            away_team = match["away_team"]

            bookmaker = match["bookmakers"][0]
            market = bookmaker["markets"][0]
            odds = market["outcomes"]

            odds_home = odds[0]["price"]

            # =========================
            # ⚽ MODELO DINÁMICO MEJORADO
            # =========================

            market_prob = 1 / odds_home

            home_goals = 1.0 + (market_prob * 1.2)
            away_goals = 1.0 + ((1 - market_prob) * 1.2)

            home_goals = max(0.6, min(home_goals, 2.8))
            away_goals = max(0.6, min(away_goals, 2.8))

            # =========================
            # 📊 POISSON
            # =========================

            home_win = 0

            for i in range(6):
                for j in range(6):

                    p = poisson_prob(i, home_goals) * poisson_prob(j, away_goals)

                    if i > j:
                        home_win += p

            implied = 1 / odds_home

            edge = home_win - implied

            ev = (home_win * odds_home) - 1

            # =========================
            # 💰 KELLY
            # =========================

            kelly_fraction = kelly(edge, odds_home)

            stake = bank * kelly_fraction

            print(
                home_team,
                "vs",
                away_team,
                "Edge:",
                round(edge, 3),
                "EV:",
                round(ev, 3),
                "Kelly:",
                round(kelly_fraction, 3)
            )

            # =========================
            # 🚨 VALUE BET FILTER
            # =========================

            if (
                edge > 0.06 and
                ev > 0.03 and
                odds_home >= 1.60 and
                kelly_fraction > 0
            ):

                send(f"""🔥 VALUE BET PRO

⚽ {home_team} vs {away_team}

💰 Cuota: {odds_home}

📊 Prob modelo: {round(home_win, 3)}

📈 Edge: {round(edge, 3)}

💎 EV: {round(ev, 3)}

🧠 Kelly: {round(kelly_fraction, 3)}

💵 Stake: €{round(stake, 2)}
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
