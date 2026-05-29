
import requests
import math
import time
import csv

from datetime import datetime
from zoneinfo import ZoneInfo

# =========================================================
# CONFIGURACION
# =========================================================

API_KEY = "e93b17bb02fe486f1fa731494df8814c"
TELEGRAM_TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"

BASE_URL = "https://v3.football.api-sports.io"

TIMEZONE = ZoneInfo("Europe/Madrid")

BANKROLL = 100

KELLY_FACTOR = 0.10
MAX_STAKE_PERCENT = 0.03

MIN_EDGE = 0.05
MIN_ODDS = 1.55
MAX_ODDS = 2.40

MAX_DAILY_PICKS = 5

SCAN_INTERVAL = 1800

LEAGUES = [
    39,   # Premier League
    140,  # LaLiga
    135,  # Serie A
    78,   # Bundesliga
    61,   # Ligue 1
    253,  # MLS
    71    # Brasil Serie A
]

HEADERS = {
    "x-apisports-key": API_KEY
}

# =========================================================
# TELEGRAM
# =========================================================


def send_telegram(message):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:

        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            },
            timeout=10
        )

    except Exception as e:

        print(f"Telegram Error: {e}")

# =========================================================
# KELLY
# =========================================================


def kelly(probability, odds):

    if odds <= 1:
        return 0

    k = ((probability * odds) - 1) / (odds - 1)

    k *= KELLY_FACTOR

    k = max(0, k)

    return min(k, MAX_STAKE_PERCENT)

# =========================================================
# POISSON
# =========================================================


def poisson_probability(lmbda, goals):

    return (
        math.exp(-lmbda)
        * (lmbda ** goals)
        / math.factorial(goals)
    )


def calculate_match_probs(home_xg, away_xg):

    home_prob = 0
    draw_prob = 0
    away_prob = 0

    for home_goals in range(8):

        for away_goals in range(8):

            p = (
                poisson_probability(home_xg, home_goals)
                * poisson_probability(away_xg, away_goals)
            )

            if home_goals > away_goals:
                home_prob += p

            elif home_goals == away_goals:
                draw_prob += p

            else:
                away_prob += p

    return home_prob, draw_prob, away_prob


def over25_probability(home_xg, away_xg):

    probability = 0

    for home_goals in range(8):

        for away_goals in range(8):

            total_goals = home_goals + away_goals

            p = (
                poisson_probability(home_xg, home_goals)
                * poisson_probability(away_xg, away_goals)
            )

            if total_goals >= 3:
                probability += p

    return probability


def btts_probability(home_xg, away_xg):

    probability = 0

    for home_goals in range(1, 8):

        for away_goals in range(1, 8):

            p = (
                poisson_probability(home_xg, home_goals)
                * poisson_probability(away_xg, away_goals)
            )

            probability += p

    return probability

# =========================================================
# API
# =========================================================


def get_today_matches():

    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")

    try:

        response = requests.get(
            f"{BASE_URL}/fixtures",
            headers=HEADERS,
            params={"date": today},
            timeout=20
        )

        return response.json()["response"]

    except Exception as e:

        print(f"Fixtures Error: {e}")

        return []


def get_last_matches(team_id):

    try:

        response = requests.get(
            f"{BASE_URL}/fixtures",
            headers=HEADERS,
            params={
                "team": team_id,
                "last": 5
            },
            timeout=20
        )

        return response.json()["response"]

    except:

        return []


def get_team_form(team_id):

    matches = get_last_matches(team_id)

    if not matches:

        return {
            "attack": 1.2,
            "defense": 1.2,
            "wins": 0.5
        }

    goals_scored = 0
    goals_conceded = 0
    wins = 0

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

        if scored > conceded:
            wins += 1

    return {
        "attack": goals_scored / len(matches),
        "defense": goals_conceded / len(matches),
        "wins": wins / len(matches)
    }


def get_odds(fixture_id):

    try:

        response = requests.get(
            f"{BASE_URL}/odds",
            headers=HEADERS,
            params={"fixture": fixture_id},
            timeout=20
        )

        data = response.json()["response"]

        if not data:
            return None

        bookmakers = data[0]["bookmakers"]

        if not bookmakers:
            return None

        odds_data = {
            "home": None,
            "draw": None,
            "away": None,
            "over25": None,
            "btts": None
        }

        for bet in bookmakers[0]["bets"]:

            # Match Winner
            if bet["name"] == "Match Winner":

                for value in bet["values"]:

                    if value["value"] == "Home":
                        odds_data["home"] = float(value["odd"])

                    elif value["value"] == "Draw":
                        odds_data["draw"] = float(value["odd"])

                    elif value["value"] == "Away":
                        odds_data["away"] = float(value["odd"])

            # Over 2.5
            if bet["name"] == "Goals Over/Under":

                for value in bet["values"]:

                    if value["value"] == "Over 2.5":
                        odds_data["over25"] = float(value["odd"])

            # BTTS
            if bet["name"] == "Both Teams Score":

                for value in bet["values"]:

                    if value["value"] == "Yes":
                        odds_data["btts"] = float(value["odd"])

        return odds_data

    except Exception as e:

        print(f"Odds Error: {e}")

        return None

# =========================================================
# SCORE
# =========================================================


def calculate_edge(probability, odds):

    implied = 1 / odds

    return probability - implied


def calculate_score(edge, form, total_xg, odds):

    edge_score = min(edge * 100, 15)

    form_score = form * 20

    xg_score = min(total_xg * 8, 25)

    odds_score = 15

    if odds > 2.10:
        odds_score = 10

    if odds < 1.65:
        odds_score = 12

    total = (
        edge_score
        + form_score
        + xg_score
        + odds_score
        + 25
    )

    return round(total, 2)

# =========================================================
# CSV
# =========================================================


def save_pick(data):

    file_exists = False

    try:

        with open("registro_apuestas.csv", "r"):
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
                "Mercado",
                "Cuota",
                "Probabilidad",
                "Edge",
                "Score",
                "Stake"
            ])

        writer.writerow(data)

# =========================================================
# ANALISIS PRINCIPAL
# =========================================================


def analyze_matches():

    now = datetime.now(TIMEZONE)

    weekday = now.weekday()

    current_hour = now.hour

    start_hour = 17 if weekday < 5 else 11
    end_hour = 22

    if current_hour < start_hour or current_hour >= end_hour:

        print("Fuera de horario")

        return

    print("Analizando partidos...")

    all_picks = []

    matches = get_today_matches()

    for match in matches:

        league_id = match["league"]["id"]

        if league_id not in LEAGUES:
            continue

        fixture_id = match["fixture"]["id"]

        home_team = match["teams"]["home"]["name"]
        away_team = match["teams"]["away"]["name"]

        league_name = match["league"]["name"]

        odds = get_odds(fixture_id)

        if not odds:
            continue

        home_form = get_team_form(match["teams"]["home"]["id"])
        away_form = get_team_form(match["teams"]["away"]["id"])

        home_xg = (
            (home_form["attack"] * 1.20)
            - (away_form["defense"] * 0.80)
            + 0.35
        )

        away_xg = (
            (away_form["attack"] * 1.05)
            - (home_form["defense"] * 0.75)
        )

        home_xg = max(0.5, home_xg)
        away_xg = max(0.5, away_xg)

        total_xg = home_xg + away_xg

        home_prob, draw_prob, away_prob = (
            calculate_match_probs(home_xg, away_xg)
        )

        over25_prob = over25_probability(home_xg, away_xg)

        btts_prob = btts_probability(home_xg, away_xg)

        # =====================================================
        # HOME WIN
        # =====================================================

        if odds["home"]:

            if MIN_ODDS <= odds["home"] <= MAX_ODDS:

                edge = calculate_edge(
                    home_prob,
                    odds["home"]
                )

                if edge >= MIN_EDGE:

                    form = (
                        home_form["wins"]
                        - away_form["wins"]
                        + 0.5
                    )

                    score = calculate_score(
                        edge,
                        form,
                        total_xg,
                        odds["home"]
                    )

                    all_picks.append({
                        "market": "Home Win",
                        "match": f"{home_team} vs {away_team}",
                        "league": league_name,
                        "probability": home_prob,
                        "odds": odds["home"],
                        "edge": edge,
                        "score": score,
                        "xg": total_xg
                    })

        # =====================================================
        # OVER 2.5
        # =====================================================

        if odds["over25"]:

            if MIN_ODDS <= odds["over25"] <= MAX_ODDS:

                edge = calculate_edge(
                    over25_prob,
                    odds["over25"]
                )

                if edge >= MIN_EDGE and total_xg >= 2.6:

                    score = calculate_score(
                        edge,
                        0.7,
                        total_xg,
                        odds["over25"]
                    )

                    all_picks.append({
                        "market": "Over 2.5",
                        "match": f"{home_team} vs {away_team}",
                        "league": league_name,
                        "probability": over25_prob,
                        "odds": odds["over25"],
                        "edge": edge,
                        "score": score,
                        "xg": total_xg
                    })

        # =====================================================
        # BTTS
        # =====================================================

        if odds["btts"]:

            if MIN_ODDS <= odds["btts"] <= MAX_ODDS:

                edge = calculate_edge(
                    btts_prob,
                    odds["btts"]
                )

                if edge >= MIN_EDGE:

                    if home_xg >= 1.1 and away_xg >= 1.0:

                        score = calculate_score(
                            edge,
                            0.7,
                            total_xg,
                            odds["btts"]
                        )

                        all_picks.append({
                            "market": "BTTS",
                            "match": f"{home_team} vs {away_team}",
                            "league": league_name,
                            "probability": btts_prob,
                            "odds": odds["btts"],
                            "edge": edge,
                            "score": score,
                            "xg": total_xg
                        })

    # =========================================================
    # TOP PICKS
    # =========================================================

    all_picks.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    best_picks = all_picks[:MAX_DAILY_PICKS]

    if not best_picks:

        print("No hay picks de calidad")

        return

    send_telegram(
        "🔥 <b>TOP PICKS DEL DIA</b> 🔥"
    )

    for index, pick in enumerate(best_picks, start=1):

        stake_percent = kelly(
            pick["probability"],
            pick["odds"]
        )

        stake = round(
            BANKROLL * stake_percent,
            2
        )

        message = (
            f"🔥 <b>TOP PICK #{index}</b>\n\n"
            f"⚽ {pick['match']}\n"
            f"🏆 {pick['league']}\n\n"
            f"✅ Mercado: {pick['market']}\n"
            f"💰 Cuota: {pick['odds']}\n"
            f"📈 Probabilidad: "
            f"{round(pick['probability']*100,2)}%\n"
            f"💎 Edge: "
            f"{round(pick['edge']*100,2)}%\n"
            f"📊 xG Total: "
            f"{round(pick['xg'],2)}\n"
            f"🏅 Score: "
            f"{pick['score']}/100\n"
            f"💵 Stake: €{stake}"
        )

        send_telegram(message)

        save_pick([
            now.strftime("%Y-%m-%d"),
            pick["match"],
            pick["league"],
            pick["market"],
            pick["odds"],
            round(pick["probability"] * 100, 2),
            round(pick["edge"] * 100, 2),
            pick["score"],
            stake
        ])

        time.sleep(2)

    print("TOP 5 enviadas correctamente")

# =========================================================
# LOOP
# =========================================================

if __name__ == "__main__":

    print("BOT SEMIPRO INICIADO")

    send_telegram(
        "🚀 Bot semiprofesional iniciado"
    )

    while True:

        try:

            analyze_matches()

            print("Esperando siguiente escaneo...")

            time.sleep(SCAN_INTERVAL)

        except KeyboardInterrupt:

            print("Bot detenido")

            break

        except Exception as e:

            print(f"Critical Error: {e}")

            send_telegram(
                f"❌ Error crítico:\n{e}"
            )

            time.sleep(60)
```

# RECOMENDACIONES IMPORTANTES

## Antes de usar:

1. Cambia:

* TU_API_KEY
* TU_TELEGRAM_TOKEN
* TU_CHAT_ID

2. Instala:

```bash
pip install requests
```

3. Ejecuta:

```bash
python bot.py
```

# QUÉ HACE ESTE BOT

✅ Analiza Top 5 ligas + MLS + Brasil

✅ Analiza:

* Home Win
* Over 2.5
* BTTS

✅ Filtra apuestas basura

✅ Envía SOLO las 5 mejores del día

✅ Usa score inteligente

✅ Usa Poisson

✅ Usa gestión bankroll

✅ Guarda histórico CSV

✅ Funciona con horario Madrid

# CONSEJO IMPORTANTE

Aunque el modelo es mucho más serio que un bot amateur, lo ideal es hacer:

* backtesting
* CLV
* análisis de yield
* revisión mensual

antes de meter stakes grandes.
