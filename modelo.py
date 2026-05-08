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

LEAGUE_POOL = [140, 78, 135, 39, 61]


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
# 📊 FORM SIMPLE (STABLE)
# =========================

def team_form(team_id):

    try:

        url = "https://v3.football.api-sports.io/fixtures"
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
# 💰 ODDS MULTI
# =========================

def get_odds(fixture_id):

    url = "https://v3.football.api-sports.io/odds"
    headers = {"x-apisports-key": API_KEY}

    params = {"fixture": fixture_id}

    try:

        r = requests.get(url, headers=headers, params=params)
        data = r.json().get("response", [])

        best = {"Home": None, "Away": None}

        for item in data:

            for b in item.get("bookmakers", []):

                for bet in b.get("bets", []):

                    if bet["name"] != "Match Winner":
                        continue

                    for v in bet["values"]:

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
# 🔍 SCAN PRINCIPAL
# =========================

def scan():

    print("🔍 SCAN CALIBRADO")
    send("🔍 bot calibrado activo")

    url = "https://v3.football.api-sports.io/fixtures"

    headers = {"x-apisports-key": API_KEY}

    params = {"season": 2025}

    r = requests.get(url, headers=headers, params=params)

    if r.status_code != 200:
        send("❌ API ERROR")
        return

    data = r.json().get("response", [])

    bets = []

    for m in data:

        league = m["league"]["id"]

        if league not in LEAGUE_POOL:
            continue

        if m["goals"]["home"] is not None:
            continue

        try:

            home_team = m["teams"]["home"]["name"]
            away_team = m["teams"]["away"]["name"]

            # =========================
            # MODELO CALIBRADO
            # =========================

            home_form = team_form(m["teams"]["home"]["id"])
            away_form = team_form(m["teams"]["away"]["id"])

            home_xg = 1.1 + (home_form * 0.6)
            away_xg = 1.0 + (away_form * 0.6)

            home_p, draw_p, away_p = match_probs(home_xg, away_xg)

            # suavizado tipo mercado
            home_p = (home_p * 0.9) + 0.05
            away_p = (away_p * 0.9) + 0.05

            # =========================
            # CUOTAS REALES
            # =========================

            home_odds, away_odds = get_odds(m["fixture"]["id"])

            if not home_odds or not away_odds:
                continue

            # =========================
            # EDGE
            # =========================

            home_edge = edge(home_p, home_odds)
            away_edge = edge(away_p, away_odds)

            # filtro calibrado (no demasiado duro)
            if home_edge > 0.008 and home_p > 0.25:
                bets.append(("HOME", home_team, away_team, home_edge, home_odds))

            if away_edge > 0.008 and away_p > 0.25:
                bets.append(("AWAY", home_team, away_team, away_edge, away_odds))

        except Exception as e:
            print("MATCH ERROR:", e)
            continue

    # =========================
    # 🏆 TOP PICKS
    # =========================

    bets.sort(key=lambda x: x[3], reverse=True)

    top5 = bets[:5]

    if not top5:

        send("⚠️ Sin picks en este ciclo")
        print("SIN BETS")
        return

    msg = "🔥 TOP VALUE BETS CALIBRADOS\n\n"

    for b in top5:

        side, home, away, edge_val, odds = b

        stake = max(0, edge_val * BANK)

        msg += f"""⚽ {home} vs {away}
➡️ {side}
💰 Cuota: {odds}
📈 Edge: {round(edge_val,3)}
💵 Stake: €{round(stake,2)}

"""

    send(msg)
    print("SCAN OK")


# =========================
# 🚀 LOOP
# =========================

print("🔥 BOT CALIBRADO INICIADO")
send("🔥 BOT CALIBRADO ONLINE")

while True:

    try:
        scan()
        time.sleep(180)

    except Exception as e:
        print("ERROR:", e)
        time.sleep(10)
