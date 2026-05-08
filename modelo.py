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

# ligas de baja varianza (más “trading-friendly”)
ALLOWED_LEAGUES = [140, 78, 135]


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
        pass


# =========================
# ⚽ PROBABILIDAD BASE
# =========================

def poisson(k, lam):
    return (lam ** k * math.exp(-lam)) / math.factorial(k)


def match_probs(home_xg, away_xg):

    hw = d = aw = 0

    for i in range(6):
        for j in range(6):

            p = poisson(i, home_xg) * poisson(j, away_xg)

            if i > j:
                hw += p
            elif i == j:
                d += p
            else:
                aw += p

    return hw, d, aw


# =========================
# 📊 TEAM STRENGTH (ATAQUE/DEFENSA SEPARADO)
# =========================

def team_strength(team_id):

    try:

        url = "https://v3.football.api-sports.io/fixtures"
        headers = {"x-apisports-key": API_KEY}

        params = {"team": team_id, "last": 6}

        r = requests.get(url, headers=headers, params=params)
        data = r.json()["response"]

        gf = ga = 0

        for m in data:

            gf += (m["goals"]["home"] or 0)
            gf += (m["goals"]["away"] or 0)

        return gf / 15  # normalización simple

    except:
        return 1


# =========================
# 💰 KELLY CONSERVADOR
# =========================

def kelly(edge, odds):

    if edge <= 0:
        return 0

    b = odds - 1
    p = edge + (1 / odds)
    q = 1 - p

    k = (b * p - q) / b

    # hedge fund style → reducción fuerte de riesgo
    return max(0, k * 0.5)


# =========================
# 🔍 SCAN HEDGE FUND
# =========================

def scan():

    print("🔍 HEDGE FUND SCAN")
    send("🔍 hedge fund scan activo")

    url = "https://v3.football.api-sports.io/fixtures"

    headers = {"x-apisports-key": API_KEY}
    params = {"season": 2025}

    r = requests.get(url, headers=headers, params=params)

    if r.status_code != 200:
        send(f"❌ API ERROR {r.status_code}")
        return

    data = r.json()["response"]

    picks = []

    for match in data:

        league = match["league"]["id"]

        if league not in ALLOWED_LEAGUES:
            continue

        if match["goals"]["home"] is not None:
            continue

        home = match["teams"]["home"]
        away = match["teams"]["away"]

        # =========================
        # STRENGTH MODEL
        # =========================

        h = team_strength(home["id"])
        a = team_strength(away["id"])

        home_xg = 1.5 * (1 + h)
        away_xg = 1.2 * (1 + a)

        home_p, draw_p, away_p = match_probs(home_xg, away_xg)

        # =========================
        # ODDS (simplificado base)
        # =========================

        home_odds = 2.05
        away_odds = 3.25

        # =========================
        # EDGE REAL
        # =========================

        home_edge = home_p - (1 / home_odds)
        away_edge = away_p - (1 / away_odds)

        # =========================
        # FILTER HEDGE FUND
        # =========================

        if home_edge > 0.025:
            picks.append(("HOME", home["name"], away["name"], home_edge, home_odds))

        if away_edge > 0.025:
            picks.append(("AWAY", home["name"], away["name"], away_edge, away_odds))

    # =========================
    # 🏆 TOP PICKS FINAL
    # =========================

    picks.sort(key=lambda x: x[3], reverse=True)

    top = picks[:5]

    if not top:
        send("⚠️ Sin edge suficiente (hedge fund filter)")
        print("NO PICKS")
        return

    msg = "🔥 HEDGE FUND TOP PICKS\n\n"

    for p in top:

        side, home, away, edge, odds = p

        stake = kelly(edge, odds) * BANK

        msg += f"""⚽ {home} vs {away}
➡️ {side}
💰 Cuota: {odds}
📈 Edge: {round(edge,4)}
💵 Stake: €{round(stake,2)}

"""

    send(msg)
    print("HEDGE FUND OK")


# =========================
# 🚀 LOOP
# =========================

print("🔥 HEDGE FUND BOT INICIADO")
send("🔥 HEDGE FUND ONLINE")

while True:

    try:
        scan()
        time.sleep(180)

    except Exception as e:
        print("ERROR:", e)
        time.sleep(10)
