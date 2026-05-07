# =========================
# 📩 TELEGRAM
# =========================

def send(msg):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.post(
        url,
        data={"chat_id": CHAT_ID, "text": msg}
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

    return max(0, (b * p - q) / b)

# =========================
# 🤖 BOT PRINCIPAL
# =========================

def run_bot():

    print("🔄 Analizando mercado...")

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
            # ⚽ MODELO DINÁMICO
            # =========================

            market_prob = 1 / odds_home

            home_goals = 1.0 + (market_prob * 1.2)
            away_goals = 1.0 + ((1 - market_prob) * 1.2)

            home_goals = max(0.4, min(home_goals, 3.5))
            away_goals = max(0.4, min(away_goals, 3.5))

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

            edge = (home_win - implied) * 1.15

            ev = (home_win * odds_home) - 1

            # =========================
            # 🧠 SCORE
            # =========================

            score = (edge * 0.5) + (ev * 0.5)

            # =========================
            # 💰 KELLY CONSERVADOR
            # =========================

            kelly_fraction = kelly(edge, odds_home) * 0.3

            stake = bank * kelly_fraction

            print(
                home_team,
                "vs",
                away_team,
                "Edge:",
                round(edge, 3),
                "EV:",
                round(ev, 3),
                "Score:",
                round(score, 3)
            )

            # =========================
            # 🚨 FILTRO TRADING
            # =========================

            if (
                edge > 0.06 and
                ev > 0.04 and
                score > 0.05 and
                1.7 <= odds_home <= 3.2 and
                kelly_fraction > 0
            ):

                send(f"""📊 TRADE DETECTADO

⚽ {home_team} vs {away_team}

💰 Cuota: {odds_home}

📈 Edge: {round(edge,3)}
💎 EV: {round(ev,3)}
🧠 Score: {round(score,3)}

💰 Stake: €{round(stake,2)}
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
