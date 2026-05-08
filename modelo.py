import requests
import time
import math

# =========================
# 🔑 CONFIG
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"
ODDS_API_KEY = "90ae2f6d7b5ddcd76926f1cf40be2ad7"

# =========================
# 📩 TELEGRAM
# =========================

def send(msg):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    try:
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg
        })
    except:
        print("Error Telegram")


# =========================
# ⚽ POISSON
# =========================

def poisson(k, lam):

    return (lam ** k * math.exp(-lam)) / math.factorial(k)


# =========================
# 📊 PROBABILIDAD PARTIDO
# =========================

def match_probs(home_xg, away_xg):

    home_win = 0
    draw = 0
    away_win = 0

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
# 🔍 SCAN
# =========================

def scan():

    print("🔍 scan iniciado")
    send("🔍 escaneando mercados")

    url = "https://api.the-odds-api.com/v4/sports/upcoming/odds"

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }

    try:

        r = requests.get(url, params=params)

        if r.status_code != 200:

            send(f"❌ API ERROR {r.status_code}")
            return

        data = r.json()

        bets = []

        for match in data:

            try:

                home = match["home_team"]
                away = match["away_team"]

                odds = match["bookmakers"][0]["markets"][0]["outcomes"]

                # cuotas
                home_odds = odds[0]["price"]
                away_odds = odds[1]["price"]

            except:
                continue

            # =========================
            # 🔥 XG SIMPLIFICADO
            # =========================

            home_xg = 1.6
            away_xg = 1.1

            home_prob, draw_prob, away_prob = match_probs(home_xg, away_xg)

            # =========================
            # EDGE
            # =========================

            home_edge = home_prob - (1 / home_odds)
            away_edge = away_prob - (1 / away_odds)

            bets.append({
                "match": f"{home} vs {away}",
                "home_edge": home_edge,
                "away_edge": away_edge,
                "home_odds": home_odds,
                "away_odds": away_odds
            })

        # =========================
        # 🏆 TOP 5 BETS
        # =========================

        all_bets = []

        for b in bets:

            all_bets.append(("HOME", b["match"], b["home_edge"], b["home_odds"]))
            all_bets.append(("AWAY", b["match"], b["away_edge"], b["away_odds"]))

        # ordenar por edge
        all_bets.sort(key=lambda x: x[2], reverse=True)

        top5 = all_bets[:5]

        msg = "🔥 TOP 5 VALUE BETS\n\n"

        for t in top5:

            side, match, edge, odds = t

            if edge > 0.01:

                msg += f"""⚽ {match}
➡️ {side}
💰 Cuota: {odds}
📈 Edge: {round(edge,3)}

"""

        send(msg)

        print("TOP 5 enviado")

    except Exception as e:

        print("ERROR:", e)
        send(f"❌ ERROR: {e}")


# =========================
# 🚀 LOOP
# =========================

print("🔥 BOT POISSON INICIADO")

while True:

    try:

        scan()
        time.sleep(1800)

    except Exception as e:

        print("ERROR LOOP:", e)
        time.sleep(10)
