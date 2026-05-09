import requests
import math
import time
import json
from datetime import datetime, timedelta

# =========================
# 🔑 CONFIG
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-"
CHAT_ID = "1335805552"
API_KEY = "167721723854a65832f09abdeb92952b"

BANK = 200
KELLY_FACTOR = 0.25

MIN_ODDS = 1.65
FAV_THRESHOLD = 0.70

BASE_URL = "https://v3.football.api-sports.io"

RESULTS_FILE = "results.json"


# =========================
# 🏆 LIGAS
# =========================

LEAGUES = [
    39, 140, 135, 78, 61,
    40, 141, 1352, 79
]


# =========================
# 📩 TELEGRAM
# =========================

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        print("Telegram error")


# =========================
# ⚽ POISSON
# =========================

def poisson(k, lam):
    return (lam ** k * math.exp(-lam)) / math.factorial(k)


def match_probs(home_xg, away_xg):

    home = draw = away = 0

    for i in range(6):
        for j in range(6):
            p = poisson(i, home_xg) * poisson(j, away_xg)

            if i > j:
                home += p
            elif i == j:
                draw += p
            else:
                away += p

    return home, draw, away


# =========================
# 📊 FORMA
# =========================

def team_form(team_id):

    try:
        url = f"{BASE_URL}/fixtures"
        headers = {"x-apisports-key": API_KEY}
        params = {"team": team_id, "last": 5}

        r = requests.get(url, headers=headers, params=params)
        data = r.json().get("response", [])

        goals = 0

        for m in data:
            goals += (m["goals"]["home"] or 0)
            goals += (m["goals"]["away"] or 0)

        return goals / 10

    except:
        return 1


# =========================
# 💰 ODDS
# =========================

def get_odds(fixture_id):

    url = f"{BASE_URL}/odds"
    headers = {"x-apisports-key": API_KEY}
    params = {"fixture": fixture_id}

    try:
        r = requests.get(url, headers=headers, params=params)
        data = r.json().get("response", [])

        best = {"Home": None, "Away": None}

        for item in data:
            for b in item.get("bookmakers", []):
                for bet in b.get("bets", []):
                    if bet.get("name") != "Match Winner":
                        continue

                    for v in bet.get("values", []):

                        try:
                            odd = float(v["odd"])

                            if v["value"] == "Home":
                                best["Home"] = max(best["Home"] or 0, odd)

                            if v["value"] == "Away":
                                best["Away"] = max(best["Away"] or 0, odd)

                        except:
                            continue

        return best["Home"], best["Away"]

    except:
        return None, None


# =========================
# 📉 EDGE
# =========================

def edge(prob, odds):
    return prob - (1 / odds)


# =========================
# 🧠 KELLY (REDUCIDO)
# =========================

def kelly(prob, odds):

    b = odds - 1
    q = 1 - prob

    f = (prob * b - q) / b

    return max(0, f * KELLY_FACTOR)


# =========================
# 💾 LOG RESULTADOS
# =========================

def save_result(data):

    try:
        try:
            with open(RESULTS_FILE, "r") as f:
                results = json.load(f)
        except:
            results = []

        results.append(data)

        with open(RESULTS_FILE, "w") as f:
            json.dump(results, f)

    except:
        pass


# =========================
# 🔍 SCAN
# =========================

def scan():

    print("🔍 HEDGE FUND BOT INICIADO")
    send("🔥 Bot Hedge Fund activo (10:00)")

    url = f"{BASE_URL}/fixtures"
    headers = {"x-apisports-key": API_KEY}
    params = {"season": 2025}

    r = requests.get(url, headers=headers, params=params)

    if r.status_code != 200:
        send("❌ API ERROR")
        return

    data = r.json().get("response", [])

    value_bets = []
    favorites = []
    league_stats = {}

    for m in data:

        try:

            league = m["league"]["id"]

            if league not in LEAGUES:
                continue

            if m["goals"]["home"] is not None:
                continue

            home = m["teams"]["home"]["name"]
            away = m["teams"]["away"]["name"]

            home_id = m["teams"]["home"]["id"]
            away_id = m["teams"]["away"]["id"]

            home_form = team_form(home_id)
            away_form = team_form(away_id)

            home_xg = 1.1 + (home_form * 0.6)
            away_xg = 1.0 + (away_form * 0.6)

            home_p, draw_p, away_p = match_probs(home_xg, away_xg)

            home_p = (home_p * 0.9) + 0.05
            away_p = (away_p * 0.9) + 0.05

            home_odds, away_odds = get_odds(m["fixture"]["id"])

            if not home_odds or not away_odds:
                continue

            # =========================
            # VALUE BETS + KELLY
            # =========================

            if home_odds >= MIN_ODDS:
                e = edge(home_p, home_odds)
                if e > 0:
                    stake = kelly(home_p, home_odds) * BANK

                    value_bets.append(("HOME", home, away, e, home_odds, stake))

                    league_stats[league] = league_stats.get(league, 0) + 1

                    save_result({
                        "match": f"{home} vs {away}",
                        "side": "HOME",
                        "odds": home_odds,
                        "prob": home_p,
                        "stake": stake
                    })

            if away_odds >= MIN_ODDS:
                e = edge(away_p, away_odds)
                if e > 0:
                    stake = kelly(away_p, away_odds) * BANK

                    value_bets.append(("AWAY", home, away, e, away_odds, stake))

                    league_stats[league] = league_stats.get(league, 0) + 1

        except:
            continue

    # =========================
    # TOP PICKS
    # =========================

    value_bets.sort(key=lambda x: x[3], reverse=True)
    top = value_bets[:5]

    msg = "🔥 VALUE BETS (HEDGE FUND MODE)\n\n"

    for v in top:
        side, home, away, e, odds, stake = v

        msg += f"""⚽ {home} vs {away}
➡️ {side}
💰 Cuota: {odds}
📈 Edge: {round(e,3)}
💵 Stake: €{round(stake,2)}

"""

    # =========================
    # FAVORITOS
    # =========================

    if favorites:
        msg += "\n🟡 FAVORITOS (>70%)\n\n"

        for f in favorites[:5]:
            home, away, prob, side = f
            msg += f"""⚽ {home} vs {away}
📊 Prob: {round(prob*100,1)}%

"""

    # =========================
    # RANKING LIGAS
    # =========================

    msg += "\n🏆 LIGAS MÁS RENTABLES\n\n"

    for k, v in sorted(league_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
        msg += f"Liga {k}: {v} picks\n"

    send(msg)
    print("SCAN OK")


# =========================
# ⏰ 10:00 LOOP
# =========================

def wait_until_10():

    while True:

        now = datetime.now()
        target = now.replace(hour=8, minute=0, second=0, microsecond=0)

        if now >= target:
            target += timedelta(days=1)

        wait = (target - now).total_seconds()

        print(f"⏳ Esperando {int(wait)} segundos  ")

        time.sleep(wait)

        scan()

        time.sleep(65)


# =========================
# 🚀 START
# =========================

print("🔥 HEDGE FUND BOT INICIADO")
send("🔥 Hedge Fund Bot activo")

wait_until_8()
