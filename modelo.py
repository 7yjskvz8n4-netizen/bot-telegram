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

# ligas base (luego se auto-optimizan)
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
# ⚽ MODELO POISSON
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
# 📊 ODDS REALES (MERCADO SHARP)
# =========================

def get_odds(fixture_id):

    url = "https://v3.football.api-sports.io/odds"
    headers = {"x-apisports-key": API_KEY}

    params = {"fixture": fixture_id}

    try:

        r = requests.get(url, headers=headers, params=params)
        data = r.json().get("response", [])

        best = {}

        for item in data:

            try:

                for b in item.get("bookmakers", []):

                    book = b.get("name")

                    for bet in b.get("bets", []):

                        if bet["name"] != "Match Winner":
                            continue

                        for v in bet["values"]:

                            val = v["value"]
                            odd = float(v["odd"])

                            if val not in best or odd > best[val]["odd"]:

                                best[val] = {
                                    "odd": odd,
                                    "book": book
                                }

            except:
                continue

        home = best.get("Home", {}).get("odd")
        away = best.get("Away", {}).get("odd")

        return home, away

    except:

        return None, None


# =========================
# 📊 EDGE SHARP
# =========================

def edge(prob, odds):

    if not odds:
        return None

    return prob - (1 / odds)


# =========================
# 🔍 SCAN SHARP
# =========================

def scan():

    print("🔍 SCAN SHARP INICIADO")
    send("🔍 sistema SHARP activo")

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

        home_team = m["teams"]["home"]["name"]
        away_team = m["teams"]["away"]["name"]

        # =========================
        # MODELO BASE
        # =========================

        home_xg = 1.5
        away_xg = 1.2

        home_p, draw_p, away_p = match_probs(home_xg, away_xg)

        # =========================
        # CUOTAS REALES
        # =========================

        home_odds, away_odds = get_odds(m["fixture"]["id"])

        if not home_odds or not away_odds:
            continue

        # =========================
        # EDGE REAL
        # =========================

        home_edge = edge(home_p, home_odds)
        away_edge = edge(away_p, away_odds)

        if home_edge and home_edge > 0.02:
            bets.append(("HOME", home_team, away_team, home_edge, home_odds))

        if away_edge and away_edge > 0.02:
            bets.append(("AWAY", home_team, away_team, away_edge, away_odds))

    # =========================
    # 🏆 TOP PICKS
    # =========================

    bets.sort(key=lambda x: x[3], reverse=True)

    top = bets[:5]

    if not top:
        send("⚠️ Sin edge SHARP este ciclo")
        print("SIN BETS")
        return

    msg = "🔥 SHARP VALUE BETS\n\n"

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
    print("SCAN SHARP OK")


# =========================
# 🚀 LOOP
# =========================

print("🔥 SISTEMA SHARP INICIADO")
send("🔥 SHARP BOT ONLINE")

while True:

    try:
        scan()
        time.sleep(180)

    except Exception as e:
        print("ERROR:", e)
        time.sleep(10)
