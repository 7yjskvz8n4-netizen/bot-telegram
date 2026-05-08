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
# 📊 FORM SIMPLE
# =========================

def team_form(team_id):

    try:

        url = "https://v3.api-football.com/fixtures"
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

    url = "https://v3.api-football.com/odds"
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
# 🔍 SCAN PRINCIPAL
# =========================

def scan():

    print("🔍 SCAN ACTIVO (1.65 FILTER)")
    send("🔍 bot activo 1.65")

    url = "https://v3.api-football.com/fixtures"
    headers = {"x-apisports-key": API_KEY}
    params = {"season": 2025}

    r = requests.get(url, headers=headers, params=params)

    if r.status_code != 200:
        send("❌ API ERROR")
        return

    data = r.json().get("response", [])

    candidates = []

    for m in data:

        league = m["league"]["id"]

        if league not in LEAGUE_POOL:
            continue

        if m["goals"]["home"] is not None:
            continue

        try:

            home = m["teams"]["home"]["name"]
            away = m["teams"]["away"]["name"]

            # =========================
            # MODELO CALIBRADO
            # =========================

            home_form = team_form(m["teams"]["home"]["id"])
            away_form = team_form(m["teams"]["away"]["id"])

            home_xg = 1.1 + (home_form * 0.6)
            away_xg = 1.0 + (away_form * 0.6)

            home_p, draw_p, away_p = match_probs(home_xg, away_xg)

            home_p = (home_p * 0.9) + 0.05
            away_p = (away_p * 0.9) + 0.05

            # =========================
            # CUOTAS
            # =========================

            home_odds, away_odds = get_odds(m["fixture"]["id"])

            if not home_odds or not away_odds:
                continue

            # =========================
            # FILTRO 1.65
            # =========================

            if home_odds >= MIN_ODDS:
                home_edge = edge(home_p, home_odds)
                if home_edge > 0:
                    candidates.append(("HOME", home, away, home_edge, home_odds))

            if away_odds >= MIN_ODDS:
                away_edge = edge(away_p, away_odds)
                if away_edge > 0:
                    candidates.append(("AWAY", home, away, away_edge, away_odds))

        except Exception as e:
            print("MATCH ERROR:", e)
            continue

    # =========================
    # 🏆 RESULTADOS
    # =========================

    candidates.sort(key=lambda x: x[3], reverse=True)

    top = candidates[:5]

    if not top:
        send("⚠️ Sin picks con filtro 1.65")
        print("SIN BETS")
        return

    msg = "🔥 TOP VALUE BETS (>=1.65)\n\n"

    for b in top:

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

print("🔥 BOT FINAL 1.65 INICIADO")
send("🔥 BOT FINAL 1.65 ONLINE")

while True:

    try:
        scan()
        time.sleep(180)

    except Exception as e:
        print("ERROR:", e)
        time.sleep(60)
