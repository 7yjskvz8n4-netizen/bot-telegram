import requests
import math
import time
from datetime import datetime, timedelta

# =========================
# 🔑 CONFIG
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"
API_KEY = "167721723854a65832f09abdeb92952b"

BANK = 1000

MIN_ODDS = 1.65
FAV_THRESHOLD = 0.70

BASE_URL = "https://v3.football.api-sports.io"


# =========================
# 🏆 LIGAS TOP + SEGUNDA
# =========================

LEAGUES = [
    39, 140, 135, 78, 61,   # top
    40, 141, 1352, 79       # segundas
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
    except Exception as e:
        print("Telegram error:", e)


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
# 📊 FORMA EQUIPO
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
# 💰 ODDS REALES
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
                                if not best["Home"] or odd > best["Home"]:
                                    best["Home"] = odd

                            if v["value"] == "Away":
                                if not best["Away"] or odd > best["Away"]:
                                    best["Away"] = odd
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
# 🔍 SCAN JORNADA
# =========================

def scan():

    print("🔍 SCAN PRO ESTABLE")
    send("🔍 Bot PRO activo (10:00)")

    url = f"{BASE_URL}/fixtures"
    headers = {"x-apisports-key": API_KEY}
    params = {"season": 2025}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=20)
    except Exception as e:
        send("❌ ERROR API TIMEOUT")
        print(e)
        return

    if r.status_code != 200:
        send(f"❌ API ERROR {r.status_code}")
        return

    data = r.json().get("response", [])

    value_bets = []
    favorites = []

    for m in data:

        try:

            league = m["league"]["id"]

            if league not in LEAGUES:
                continue

            if m["goals"]["home"] is not None:
                continue

            home = m["teams"]["home"]["name"]
            away = m["teams"]["away"]["name"]

            home_form = team_form(m["teams"]["home"]["id"])
            away_form = team_form(m["teams"]["away"]["id"])

            home_xg = 1.1 + (home_form * 0.6)
            away_xg = 1.0 + (away_form * 0.6)

            home_p, draw_p, away_p = match_probs(home_xg, away_xg)

            home_p = (home_p * 0.9) + 0.05
            away_p = (away_p * 0.9) + 0.05

            home_odds, away_odds = get_odds(m["fixture"]["id"])

            if not home_odds or not away_odds:
                continue

            # =========================
            # VALUE BETS
            # =========================

            if home_odds >= MIN_ODDS:
                e = edge(home_p, home_odds)
                if e > 0:
                    value_bets.append(("HOME", home, away, e, home_odds))

            if away_odds >= MIN_ODDS:
                e = edge(away_p, away_odds)
                if e > 0:
                    value_bets.append(("AWAY", home, away, e, away_odds))

            # =========================
            # FAVORITOS
            # =========================

            if home_p >= FAV_THRESHOLD:
                favorites.append((home, away, home_p, "HOME"))

            if away_p >= FAV_THRESHOLD:
                favorites.append((home, away, away_p, "AWAY"))

        except:
            continue

    # =========================
    # TOP VALUE BETS
    # =========================

    value_bets.sort(key=lambda x: x[3], reverse=True)
    top_value = value_bets[:5]

    msg = "🔥 VALUE BETS PRO\n\n"

    for v in top_value:
        side, home, away, e, odds = v
        stake = max(0, e * BANK)

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
➡️ {side}

"""

    send(msg)
    print("SCAN OK")


# =========================
# ⏰ EJECUCIÓN 10:00 ESTABLE
# =========================

def wait_until_10():

    while True:

        now = datetime.now()

        target = now.replace(hour=10, minute=0, second=0, microsecond=0)

        if now > target:
            target += timedelta(days=1)

        wait = (target - now).total_seconds()

        print(f"⏳ Próxima ejecución en {int(wait)} segundos")

        time.sleep(wait)

        scan()


# =========================
# 🚀 START
# =========================

print("🔥 BOT PRO ESTABLE INICIADO")
send("🔥 Bot PRO activo - 10:00 + value + favoritos")

wait_until_10()
