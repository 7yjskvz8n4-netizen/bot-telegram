import requests
import math
import sqlite3
from bs4 import BeautifulSoup

# =========================
# CONFIG
# =========================

EDGE_MIN = 0.05
MAX_PICKS = 5

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# DB
# =========================

conn = sqlite3.connect("v10_system.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS predictions (
id INTEGER PRIMARY KEY AUTOINCREMENT,
home TEXT,
away TEXT,
prob REAL,
odds REAL,
stake REAL,
result INTEGER,
ev REAL
)
""")

conn.commit()

# =========================
# TELEGRAM (opcional)
# =========================

def send(msg):
    print(msg)

# =========================
# SCRAPER MATCHES
# =========================

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        return r.text
    except:
        return None

def get_matches():

    url = "https://www.espn.com/soccer/scoreboard"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)

        if r.status_code != 200:
            return []

        text = r.text

        matches = []

        # búsqueda simple de patrones de equipos
        lines = text.split("\n")

        for i in range(len(lines)):
            if " vs " in lines[i].lower():
                matches.append(lines[i].strip())

        return matches

    except:
        return []

    html = fetch(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    matches = []

    for row in soup.find_all("tr"):

        text = row.get_text(" ", strip=True)

        if " - " in text and len(text) < 80:
            matches.append(text)

    return matches

def clean_match(text):

    try:
        parts = text.split("-")
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip()
    except:
        pass

    return None, None

# =========================
# POISSON MODEL
# =========================

def poisson(lmbda, k):
    return (math.exp(-lmbda) * lmbda ** k) / math.factorial(k)

def probs(hxg, axg):

    home = draw = away = 0

    for i in range(6):
        for j in range(6):

            p = poisson(hxg, i) * poisson(axg, j)

            if i > j:
                home += p
            elif i == j:
                draw += p
            else:
                away += p

    total = home + draw + away

    return home/total, draw/total, away/total

# =========================
# SIMPLE XG MODEL (LOCAL)
# =========================

def xg(team):

    # base sin API (mejora con learning)
    return 1.4, 1.1

# =========================
# ODDS (PLACEHOLDER V10)
# =========================

def get_odds(home, away):

    return {
        "Home": 2.00,
        "Draw": 3.20,
        "Away": 3.80
    }

# =========================
# EV + KELLY
# =========================

def expected_value(prob, odds):
    return (prob * odds) - 1

def kelly(prob, odds):

    b = odds - 1
    q = 1 - prob

    if b == 0:
        return 0

    k = (b * prob - q) / b

    return max(0, min(k, 0.2))

def is_valid(ev, stake):

    return ev > 0 and stake > 0

# =========================
# LEARNING SYSTEM (V10 CORE)
# =========================

def save_prediction(home, away, prob, odds, stake, ev):

    c.execute("""
    INSERT INTO predictions (home, away, prob, odds, stake, ev)
    VALUES (?,?,?,?,?,?)
    """, (home, away, prob, odds, stake, ev))

    conn.commit()

def model_bias():

    c.execute("SELECT prob, result FROM predictions WHERE result IS NOT NULL")

    data = c.fetchall()

    if len(data) < 20:
        return 1.0

    error = 0

    for p, r in data:
        error += (p - r)

    bias = error / len(data)

    return max(0.85, min(1.15, 1 - bias))

def adjust_prob(prob):
    return prob * model_bias()

# =========================
# MAIN BOT
# =========================

def run():

    send("🚀 V10 FULL SYSTEM INICIADO")

    raw_matches = get_matches()

    matches = []

    for m in raw_matches:
        home, away = clean_match(m)
        if home and away:
            matches.append((home, away))

    send(f"📊 Partidos encontrados: {len(matches)}")

    picks = 0

    for home, away in matches[:20]:

        hxg, _ = xg(home)
        axg, _ = xg(away)

        ph, pd, pa = probs(hxg, axg)

        ph = adjust_prob(ph)

        odds = get_odds(home, away)

        ev = expected_value(ph, odds["Home"])
        stake = kelly(ph, odds["Home"])

        if is_valid(ev, stake):

            save_prediction(home, away, ph, odds["Home"], stake, ev)

            send(f"""
⚽ {home} vs {away}

💰 Cuota: {odds['Home']}
📊 Prob: {round(ph,3)}
📈 EV: {round(ev,3)}
💵 Stake: {round(stake*100,2)}%
""")

            picks += 1

            if picks >= MAX_PICKS:
                break

    send("✅ V10 COMPLETADO")

# =========================
# START
# =========================

run()
