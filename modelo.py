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

# Pool amplio de ligas (exploración)
LEAGUE_POOL = [140, 78, 135, 39, 61, 2, 3]


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

    home_win = draw = away_win = 0

    for i in range(6):
        for j in range(6):

            p = poisson(i, home_xg) * poisson(j, away_xg)

            if i > j:
                home_win += p
            elif i == j:
                draw += p
            else:
                away_win += p

    return home_win, draw, away_win


# =========================
# 📊 SCORE DE LIGA
# =========================

def league_score(league_id):

    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": API_KEY}

    params = {
        "league": league_id,
        "season": 2025,
        "last": 20
    }

    try:

        r = requests.get(url, headers=headers, params=params)
        data = r.json()["response"]

        goals = []

        for m in data:

            if m["goals"]["home"] is not None:

                total = (m["goals"]["home"] or 0) + (m["goals"]["away"] or 0)
                goals.append(total)

        if len(goals) < 5:
            return 0

        avg = sum(goals) / len(goals)

        var = sum((g - avg) ** 2 for g in goals) / len(goals)

        # score tipo trading
        return avg * 0.6 + var * 0.4

    except:

        return 0


# =========================
# 🏆 AUTO LIGAS RENTABLES
# =========================

def get_best_leagues():

    scored = []

    for league in LEAGUE_POOL:

        score = league_score(league)

        if score > 0:
            scored.append((league, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    best = [l[0] for l in scored[:3]]

    print("📊 Ligas seleccionadas:", best)

    return best


# =========================
# 🔍 SCAN
# =========================

def scan():

    print("🔍 SCAN INICIADO")
    send("🔍 bot activo - scan iniciado")

    best_leagues = get_best_leagues()

    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": API_KEY}
    params = {"season": 2025}

    r = requests.get(url, headers=headers, params=params)

    if r.status_code != 200:
        send(f"❌ API ERROR {r.status_code}")
        return

    data = r.json()["response"]

    bets = []

    for match in data:

        league = match["league"]["id"]

        if league not in best_leagues:
            continue

        if match["goals"]["home"] is not None:
            continue

        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]

        # =========================
        # MODELO SIMPLE ESTABLE
        # =========================

        home_xg = 1.5
        away_xg = 1.2

        home_prob, draw_prob, away_prob = match_probs(home_xg, away_xg)

        home_odds = 2.10
        away_odds = 3.30

        home_edge = home_prob - (1 / home_odds)
        away_edge = away_prob - (1 / away_odds)

        if home_edge > 0.02:
            bets.append(("HOME", home, away, home_edge, home_odds))

        if away_edge > 0.02:
            bets.append(("AWAY", home, away, away_edge, away_odds))

    # =========================
    # 🏆 TOP PICKS
    # =========================

    bets.sort(key=lambda x: x[3], reverse=True)

    top5 = bets[:5]

    if not top5:

        send("⚠️ Sin value bets este ciclo")
        print("SIN BETS")
        return

    msg = "🔥 TOP 5 VALUE BETS (AUTO LIGAS)\n\n"

    for b in top5:

        side, home, away, edge, odds = b

        stake = max(0, edge * BANK)

        msg += f"""⚽ {home} vs {away}
➡️ {side}
💰 Cuota: {odds}
📈 Edge: {round(edge,3)}
💵 Stake: €{round(stake,2)}

"""

    send(msg)
    print("SCAN OK")


# =========================
# 🚀 LOOP
# =========================

print("🔥 BOT AUTO-LIGAS INICIADO")
send("🔥 BOT AUTO-LIGAS ONLINE")

while True:

    try:
        scan()
        time.sleep(180)

    except Exception as e:
        print("ERROR:", e)
        time.sleep(10)
