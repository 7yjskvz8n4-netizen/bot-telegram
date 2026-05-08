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

    url = "https://v
