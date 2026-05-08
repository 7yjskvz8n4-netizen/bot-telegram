import requests
import time
import math
import sqlite3
from datetime import datetime

# =========================
# 🔑 CONFIG
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"
API_KEY = "167721723854a65832f09abdeb92952b"

BANK = 1000

ALLOWED_LEAGUES = [140, 78, 135, 39, 61]


# =========================
# 🗄 BASE DE DATOS
# =========================

conn = sqlite3.connect("bets.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match TEXT,
    side TEXT,
    odds_entry REAL,
    odds_close REAL,
    edge REAL,
    book TEXT,
    league TEXT,
    timestamp TEXT
)
""")

conn.commit()


def save_bet(match, side, odds_entry, edge, book, league):

    cursor.execute("""
        INSERT INTO bets (match, side, odds_entry, odds_close, edge, book, league, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        match,
        side,
        odds_entry,
        None,
        edge,
        book,
        league,
        datetime.now().isoformat()
    ))

    conn.commit()


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
# 📊 ODDS MULTI
# =========================

def get_odds_multi(fixture_id):

    url = "https://v3.football.api-sports.io/odds"
    headers = {"x-apisports-key": API_KEY}

    params = {"fixture": fixture_id}

    try:

        r = requests.get(url, headers=headers, params=params)

        data = r.json().get("response", [])

        best_home = None
        best_away = None
        best_book = "unknown"

        for item in data:

            bookmakers = item.get("bookmakers", [])

            for b in bookmakers:

                book_name = b.get("name", "unknown")

                for bet in b.get("bets", []):

                    if bet.get("name") != "Match Winner":
                        continue

                    for v in bet.get("values", []):

                        try:

                            odd = float(v["odd"])

                            if v["value"] == "Home":

                                if not best_home or odd > best_home:
                                    best_home = odd
                                    best_book = book_name

                            if v["value"] == "Away":

                                if not best_away or odd > best_away:
                                    best_away = odd

                        except:
                            continue

        return best_home, best_away, best_book

    except Exception as e:

        print("ODDS ERROR:", e)
        return None, None, None
