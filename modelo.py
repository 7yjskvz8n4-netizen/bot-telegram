import requests
import math
import time
import csv
from datetime import datetime, timedelta

# =========================================================
# CONFIG
# =========================================================

API_KEY = "e93b17bb02fe486f1fa731494df8814c"
TELEGRAM_TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"

BASE_URL = "https://v3.football.api-sports.io"

BANKROLL = 100
KELLY_FACTOR = 0.15
MAX_STAKE_PERCENT = 0.03

MIN_EDGE = 0.05
MIN_ODDS = 1.50
MAX_ODDS = 2.50

SCAN_INTERVAL = 1800

LEAGUES = [
   
    39,   # Premier League (Inglaterra)
    140,  # LaLiga (España)
    135,  # Serie A (Italia)
    78,   # Bundesliga (Alemania)
    61,   # Ligue 1 (Francia)

    253,  # MLS (Estados Unidos)
    71,   # Brasileirao Serie A (Brasil)

]

HEADERS = {
    "x-apisports-key": API_KEY
}

# =========================================================
# TELEGRAM
# =========================================================

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:
        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": msg,
                "parse_mode": "HTML"
            },
            timeout=10
        )
    except Exception as e:
        print(f"Telegram Error: {e}")

# =========================================================
# KELLY
# =========================================================

def kelly(prob, odds):

    if odds <= 1:
        return 0

    k = ((prob * odds) - 1) / (odds - 1)

    k *= KELLY_FACTOR

    k = max(0, k)

    return min(k, MAX_STAKE_PERCENT)

# =========================================================
# POISSON
# =========================================================

def poisson_probability(lmbda, k):
    return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)

def calculate_match_probs(home_xg, away_xg):

    home_prob = 0
    draw_prob = 0
    away_prob = 0

    for home_goals in range(8):
        for away_goals in range(8):

            p = (
                poisson_probability(home_xg, home_goals) *
                poisson_probability(away_xg, away_goals)
            )

            if home_goals > away_goals:
                home_prob += p
            elif home_goals == away_goals:
                draw_prob += p
            else:
                away_prob += p

    return home_prob, draw_prob, away_prob

def over25_probability(home_xg, away_xg):

    prob = 0

    for home_goals in range(8):
        for away_goals in range(8):

            total = home_goals + away_goals

            p = (
                poisson_probability(home_xg, home_goals) *
                poisson_probability(away_xg, away_goals)
            )

            if total >= 3:
                prob += p

    return prob

# =========================================================
# API HELPERS
# =========================================================

def get_today_matches():

    today = datetime.now().strftime("%Y-%m-%d")

    try:
        r = requests.get(
            f"{BASE_URL}/fixtures",
            headers=HEADERS,
            params={"date": today},
            timeout=20
        )

        return r.json()["response"]

    except Exception as e:
        print(f"Fixtures Error: {e}")
        return []

def get_last_matches(team_id):

    try:
        r = requests.get(
            f"{BASE_URL}/fixtures",
            headers=HEADERS,
            params={
                "team": team_id,
                "last": 5
            },
            timeout=20
        )

        return r.json()["response"]

    except:
        return []

def get_team_form(team_id):

    matches = get_last_matches(team_id)

    if not matches:
        return {
            "attack": 1.2,
            "defense": 1.2
        }

    goals_scored = 0
    goals_conceded = 0

    for match in matches:

        home_id = match["teams"]["home"]["id"]

        if home_id == team_id:
            scored = match["goals"]["home"]
            conceded = match["goals"]["away"]
        else:
            scored = match["goals"]["away"]
            conceded = match["goals"]["home"]

        goals_scored += scored
        goals_conceded += conceded

    avg_scored = goals_scored / len(matches)
    avg_conceded = goals_conceded / len(matches)

    return {
        "attack": avg_scored,
        "defense": avg_conceded
    }

def get_odds(fixture_id):

    try:

        r = requests.get(
            f"{BASE_URL}/odds",
            headers=HEADERS,
            params={"fixture": fixture_id},
            timeout=20
        )

        data = r.json()["response"]

        if not data:
            return None

        bookmakers = data[0]["bookmakers"]

        if not bookmakers:
            return None

        bets = bookmakers[0]["bets"]

        match_winner = None

        for bet in bets:
            if bet["name"] == "Match Winner":
                match_winner = bet
                break

        if not match_winner:
            return None

        odds = {}

        for value in match_winner["values"]:
            odds[value["value"]] = float(value["odd"])

        return {
            "home": odds.get("Home"),
            "draw": odds.get("Draw"),
            "away": odds.get("Away")
        }

    except Exception as e:
        print(f"Odds Error: {e}")
        return None

# =========================================================
# VALUE BET
# =========================================================

def calculate_edge(probability, odds):

    implied = 1 / odds

    return probability - implied

# =========================================================
# CSV
# =========================================================

def save_pick(data):

    file_exists = False

    try:
        with open("registro_apuestas.csv", "r", encoding="utf-8"):
            file_exists = True
    except:
        pass

    with open(
        "registro_apuestas.csv",
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file, delimiter=";")

        if not file_exists:
            writer.writerow([
                "Fecha",
                "Partido",
                "Liga",
                "Pick",
                "Cuota",
                "Probabilidad",
                "Edge",
                "Stake"
            ])

        writer.writerow(data)

# =========================================================
# MAIN SCAN
# =========================================================

def analyze_matches():

    print("Analizando partidos...")

    matches = get_today_matches()

    total = 0
    picks = 0

    for match in matches:

        league_id = match["league"]["id"]

        if league_id not in LEAGUES:
            continue

        total += 1

        fixture_id = match["fixture"]["id"]

        home_team = match["teams"]["home"]["name"]
        away_team = match["teams"]["away"]["name"]

        league_name = match["league"]["name"]

        print(f"Checking {home_team} vs {away_team}")

        odds = get_odds(fixture_id)

        if not odds:
            continue

        if not odds["home"] or not odds["away"]:
            continue

        if odds["home"] < MIN_ODDS or odds["home"] > MAX_ODDS:
            continue

        home_form = get_team_form(match["teams"]["home"]["id"])
        away_form = get_team_form(match["teams"]["away"]["id"])

        home_xg = (
            (home_form["attack"] * 1.15) -
            (away_form["defense"] * 0.85)
        )

        away_xg = (
            (away_form["attack"] * 1.00) -
            (home_form["defense"] * 0.75)
        )

        home_xg = max(0.4, home_xg)
        away_xg = max(0.4, away_xg)

        home_prob, draw_prob, away_prob = calculate_match_probs(
            home_xg,
            away_xg
        )

        edge = calculate_edge(home_prob, odds["home"])

        if edge >= MIN_EDGE:

            stake_percent = kelly(home_prob, odds["home"])

            stake = round(BANKROLL * stake_percent, 2)

            msg = (
                f"🔥 <b>VALUE BET DETECTADA</b>\n\n"
                f"⚽ {home_team} vs {away_team}\n"
                f"🏆 {league_name}\n\n"
                f"✅ Pick: Gana Local\n"
                f"💰 Cuota: {odds['home']}\n"
                f"📈 Probabilidad: {round(home_prob*100,2)}%\n"
                f"💎 Edge: {round(edge*100,2)}%\n"
                f"💵 Stake: €{stake}\n"
                f"📊 xG: {round(home_xg,2)} - {round(away_xg,2)}"
            )

            send_telegram(msg)

            save_pick([
                datetime.now().strftime("%Y-%m-%d"),
                f"{home_team} vs {away_team}",
                league_name,
                "Home Win",
                odds["home"],
                round(home_prob * 100, 2),
                round(edge * 100, 2),
                stake
            ])

            print(f"VALUE FOUND: {home_team}")

            picks += 1

    print(f"Partidos analizados: {total}")
    print(f"Picks enviadas: {picks}")

# =========================================================
# LOOP
# =========================================================

if __name__ == "__main__":

    print("BOT INICIADO")

    send_telegram("🚀 Bot iniciado correctamente")

    while True:

        try:

            analyze_matches()

            print(f"Esperando {SCAN_INTERVAL/60} minutos...")

            time.sleep(SCAN_INTERVAL)

        except KeyboardInterrupt:

            print("Bot detenido")
            break

        except Exception as e:

            print(f"Critical Error: {e}")

            send_telegram(f"❌ Error crítico:\n{e}")

            time.sleep(60)
