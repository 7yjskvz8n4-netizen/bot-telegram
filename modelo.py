import time
import math
import requests

# =========================
# 🔑 CONFIG
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"

ODDS_API_KEY = "8c45ed3a66d6870a222bce3c47a34a88"
FOOTBALL_API_KEY = "c4c1545b17ef9e743e0277f07870bb28"

# =========================
# 📩 TELEGRAM
# =========================

def send(msg):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

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
# ⚽ DATOS REALES (FORMA)
# =========================

def get_real_form(team_id):

    url = "https://v3.football.api-sports.io/fixtures"

    headers = {
        "x-apisports-key": FOOTBALL_API_KEY
    }

    params = {
        "team": team_id,
        "last": 5
    }

    r = requests.get(url, headers=headers, params=params)

    data = r.json()

    goals_for = 0
    goals_against = 0
    matches = 0

    for match in data.get("response", []):

        home = match["teams"]["home"]["id"]
        away = match["teams"]["away"]["id"]

        goals_home = match["goals"]["home"] or 0
        goals_away = match["goals"]["away"] or 0

        if home == team_id:
            goals_for += goals_home
            goals_against += goals_away

        else:
            goals_for += goals_away
            goals_against += goals_home

        matches += 1

    if matches == 0:
        return 1.2, 1.2

    attack = goals_for / matches
    defense = goals_against / matches

    return attack, defense

# =========================
# 🤖 BOT
# =========================

def run_bot():

    print("🔄 Analizando mercado real...")

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
            # ⚽ FORMA REAL (HISTÓRICA)
            # =========================

            home_id = match.get("home_team_id", 0)
            away_id = match.get("away_team_id", 0)

            home_attack, home_defense = get_real_form(home_id)
            away_attack, away_defense = get_real_form(away_id)

            # =========================
            # 📊 GOLES ESPERADOS
            # =========================

            home_goals = home_attack * away_defense * 1.05
            away_goals = away_attack * home_defense

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

            # =========================
            # 📈 EDGE REAL
            # =========================

            edge = (home_win - implied) * 1.15

            ev = (home_win * odds_home) - 1

            kelly_fraction = kelly(edge, odds_home)

            stake = bank * kelly_fraction

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
            # 🚨 FILTRO PRO
            # =========================

            if (
                edge > 0.05 and
                ev > 0.03 and
                kelly_fraction > 0 and
                1.6 <= odds_home <= 3.5
            ):

                send(f"""🔥 VALUE BET REAL DATA

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
# 🔄 LOOP
# =========================

while True:

    try:

        run_bot()

        print("⏳ Esperando 30 minutos...")

        time.sleep(1800)

    except Exception as e:

        print("❌ Error general:", e)

        time.sleep(10)
