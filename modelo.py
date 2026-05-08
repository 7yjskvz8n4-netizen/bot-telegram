import requests
import time
import math

# =========================
# 🔑 CONFIG
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"
API_KEY = "167721723854a65832f09abdeb92952b"

BANK = 1000

LEAGUE_POOL = [39, 140, 135, 78, 61]  # EPL, LaLiga, Serie A, Bundesliga, Ligue 1

BASE_URL = "https://v3.football.api-sports.io"

MIN_ODDS = 1.65


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
# 📊 FORMA SIMPLE
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

    if not odds:
        return -999

    return prob - (1 / odds)


# =========================
# 🔍 SCAN
# =========================

def scan():

    print("🔍 SCAN ACTIVO")
    send("🔍 BOT ONLINE")

    url = f"{BASE_URL}/fixtures"
    headers = {"x-apisports-key": API_KEY}
    params = {"season": 2025}

    try:
        r = requests.get(url, headers=headers, params=params)
    except Exception as e:
        print("REQUEST ERROR:", e)
        return

    if r.status_code != 200:
        send(f"❌ API ERROR {r.status_code}")
        return

    data = r.json().get("response", [])

    candidates = []

    for m in data:

        try:

            league = m["league"]["id"]

            if league not in LEAGUE_POOL:
                continue

            if m["goals"]["home"] is not None:
                continue

            home = m["teams"]["home"]["name"]
            away = m["teams"]["away"]["name"]

            # =========================
            # MODELO
            # =========================

            home_form = team_form(m["teams"]["home"]["id"])
            away_form = team_form(m["teams"]["away"]["id"])

            home_xg = 1.1 + (home_form * 0.6)
            away_xg = 1.0 + (away_form * 0.6)

            home_p, draw_p, away_p = match_probs(home_xg, away_xg)

            home_p = (home_p * 0.9) + 0.05
            away_p = (away_p * 0.9) + 0.05

            # =========================
            # ODDS
            # =========================

            home_odds, away_odds = get_odds(m["fixture"]["id"])

            if not home_odds or not away_odds:
                continue

            # =========================
            # FILTRO CUOTA
            # =========================

            if home_odds >= MIN_ODDS:
                e = edge(home_p, home_odds)
                if e > 0:
                    candidates.append(("HOME", home, away, e, home_odds))

            if away_odds >= MIN_ODDS:
                e = edge(away_p, away_odds)
                if e > 0:
                    candidates.append(("AWAY", home, away, e, away_odds))

        except Exception as e:
            print("MATCH ERROR:", e)
            continue

    # =========================
    # RESULTADOS
    # =========================

    candidates.sort(key=lambda x: x[3], reverse=True)

    top = candidates[:5]

    if not top:
        send("⚠️ Sin value bets este ciclo")
        print("SIN BETS")
        return

    msg = "🔥 VALUE BETS (>=1.65)\n\n"

    for b in top:

        side, home, away, e, odds = b

        stake = max(0, e * BANK)

        msg += f"""⚽ {home} vs {away}
➡️ {side}
💰 Cuota: {odds}
📈 Edge: {round(e,3)}
💵 Stake: €{round(stake,2)}

"""

    send(msg)
    print("SCAN OK")


# =========================
# 🔁 LOOP 6H
# =========================

print("🔥 BOT INICIADO")
send("🔥 BOT ONLINE")

while True:

    try:
        scan()
        time.sleep(21600)  # 6 horas

    except Exception as e:
        print("FATAL ERROR:", e)
        time.sleep(60)
