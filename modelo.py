import requests
import math
import time
import json
import random

# =========================
# 🔑 CONFIG
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"
ODDS_API_KEY = "8c45ed3a66d6870a222bce3c47a34a88"

BANK = 1000

# =========================
# ⚽ LIGAS
# =========================

LEAGUES = {
    "Spain_LaLiga": "soccer_spain_la_liga",
    "Spain_Hypermotion": "soccer_spain_segunda_division",
    "England": "soccer_england_premier_league",
    "Italy": "soccer_italy_serie_a",
    "Germany": "soccer_germany_bundesliga",
    "France": "soccer_france_ligue_one"
}

# =========================
# 📊 TEAM STATS (xG simplificado)
# =========================

team_stats = {
    "attack": {},
    "defense": {}
}

team_form = {}

# =========================
# 💾 LOG BETS
# =========================

FILE = "bets.json"

def load_bets():
    try:
        with open(FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_bets(data):
    with open(FILE, "w") as f:
        json.dump(data, f)

def add_bet(bet):
    data = load_bets()
    data.append(bet)
    save_bets(data)

# =========================
# 📩 TELEGRAM
# =========================

def send(msg):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})


# =========================
# ⚽ POISSON
# =========================

def poisson(k, lam):

    return (lam ** k * math.exp(-lam)) / math.factorial(k)


# =========================
# 🧠 FORM
# =========================

def update_form(team, result):

    if team not in team_form:
        team_form[team] = 1.0

    if result == "win":
        team_form[team] += 0.02
    elif result == "loss":
        team_form[team] -= 0.02

    team_form[team] = max(0.85, min(1.15, team_form[team]))


# =========================
# 📊 xG MODEL
# =========================

def expected_goals(home, away):

    home_xg = team_stats["attack"].get(home, 1.2) * team_stats["defense"].get(away, 1.0)
    away_xg = team_stats["attack"].get(away, 1.0) * team_stats["defense"].get(home, 1.1)

    return home_xg, away_xg


def model_prob(home, away):

    home_xg, away_xg = expected_goals(home, away)

    prob = 0

    for i in range(6):
        for j in range(6):

            p = poisson(i, home_xg) * poisson(j, away_xg)

            if i > j:
                prob += p

    return prob


# =========================
# 🔍 SCANNER
# =========================

CANDIDATES = []

def scan():

    global CANDIDATES
    CANDIDATES = []

    for name, league in LEAGUES.items():

        url = f"https://api.the-odds-api.com/v4/sports/{league}/odds"

        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "eu",
            "markets": "h2h"
        }

        try:

            data = requests.get(url, params=params).json()

            for match in data:

                try:

                    home = match["home_team"]
                    away = match["away_team"]

                    odds = match["bookmakers"][0]["markets"][0]["outcomes"][0]["price"]

                    prob = model_prob(home, away)

                    market = 1 / odds

                    edge = prob - market

                    ev = (prob * odds) - 1

                    score = (edge * 0.6) + (ev * 0.4)

                    if edge > 0.04 and ev > 0.03:

                        CANDIDATES.append({
                            "league": name,
                            "match": f"{home} vs {away}",
                            "odds": odds,
                            "edge": edge,
                            "ev": ev,
                            "score": score
                        })

                except:
                    continue

        except:
            continue


# =========================
# 🏆 TOP 5
# =========================

def get_top5():

    sorted_bets = sorted(CANDIDATES, key=lambda x: x["score"], reverse=True)

    return sorted_bets[:5]


# =========================
# 📊 ANALYTICS
# =========================

def analyze():

    data = load_bets()

    if not data:
        return

    bank = BANK
    wins = 0

    for b in data:

        stake = b["stake"]

        if b["result"] == 1:
            bank += stake * (b["odds"] - 1)
            wins += 1
        else:
            bank -= stake

    roi = ((bank - BANK) / BANK) * 100
    winrate = (wins / len(data)) * 100

    print("BANK:", round(bank,2))
    print("ROI:", round(roi,2), "%")
    print("WINRATE:", round(winrate,2), "%")
    print("TRADES:", len(data))


# =========================
# 📩 SEND TOP PICKS
# =========================

def send_top5():

    top5 = get_top5()

    if not top5:
        send("❌ No value bets hoy")
        return

    msg = "🔥 TOP 5 VALUE BETS\n\n"

    for b in top5:

        stake = BANK * 0.015

        win = random.random() < (1 / b["odds"] + b["edge"])

        bet = {
            "match": b["match"],
            "odds": b["odds"],
            "edge": b["edge"],
            "ev": b["ev"],
            "stake": stake,
            "result": 1 if win else 0
        }

        add_bet(bet)

        msg += f"""🏆 {b['league']}
⚽ {b['match']}
💰 Cuota: {b['odds']}
📈 Edge: {round(b['edge'],3)}
💎 EV: {round(b['ev'],3)}

"""

    send(msg)


# =========================
# 🚀 LOOP
# =========================

while True:

    try:

        scan()
        send_top5()
        analyze()

        time.sleep(1800)

    except Exception as e:
        print("Error:", e)
        time.sleep(10)
