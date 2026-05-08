import requests
import time
import math

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"
ODDS_API_KEY = "8c45ed3a66d6870a222bce3c47a34a88"

BANK = 1000

# =========================
# TELEGRAM
# =========================

def send(msg):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg
    })


# =========================
# POISSON SIMPLE
# =========================

def poisson(k, lam):

    return (lam ** k * math.exp(-lam)) / math.factorial(k)


# =========================
# PROBABILIDAD SIMPLE
# =========================

def model_prob():

    home_goals = 1.4
    away_goals = 1.1

    prob = 0

    for i in range(6):
        for j in range(6):

            p = poisson(i, home_goals) * poisson(j, away_goals)

            if i > j:
                prob += p

    return prob


# =========================
# SCANNER
# =========================

def scan():

    url = "https://api.the-odds-api.com/v4/sports/soccer_spain_la_liga/od
