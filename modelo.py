import requests
import math
import time
from datetime import datetime

# ==========================================
# ⚙️ CONFIGURACIÓN GLOBAL (PERFIL INTERMEDIO)
# ==========================================
API_KEY = "167721723854a65832f09abdeb92952b"
TELEGRAM_TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"

BANK = 100
KELLY_FACTOR = 0.25  # Riesgo moderado
MIN_ODDS = 1.45
MAX_ODDS = 2.65
HORA_INICIO = 13
HORA_FIN = 22

# Ligas seleccionadas para optimizar créditos
LEAGUES = [39, 140, 135, 78, 61, 88, 94, 71, 13, 2] 
BASE_URL = "https://v3.football.api-sports.io"

def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def kelly(p, o):
    if o <= 1: return 0
    k = (p * o - 1) / (o - 1)
    return max(0, k * KELLY_FACTOR)

def team_form(team_id):
    # Consume 1 crédito
    h = {"x-apisports-key": API_KEY}
    r = requests.get(f"{BASE_URL}/teams/statistics", headers=h, 
                     params={"league": 140, "season": 2025, "team": team_id}).json()
    # Simplificación de forma para el modelo
    return 0.5 # Valor neutro si no hay datos

def get_odds(fixture_id):
    # Consume 1 crédito
    h = {"x-apisports-key": API_KEY}
    r = requests.get(f"{BASE_URL}/odds", headers=h, params={"fixture": fixture_id}).json()
    try:
        bookmaker = r["response"][0]["bookmakers"][0]
        bets = bookmaker["bets"][0]["values"]
        return float(bets[0]["odd"]), float(bets[1]["odd"]), float(bets[2]["odd"])
    except:
        return 0, 0, 0

def match_probs(h_xg, a_xg):
    h_p = 0
    d_p = 0
    a_p = 0
    for i in range(10):
        for j in range(10):
            prob = (math.exp(-h_xg) * h_xg**i / math.factorial(i)) * \
                   (math.exp(-a_xg) * a_xg**j / math.factorial(j))
            if i > j: h_p += prob
            elif i == j: d_p += prob
            else: a_p += prob
    return h_p, d_p, a_p

def scan():
    ahora = datetime.now()
    if ahora.hour < HORA_INICIO or ahora.hour >= HORA_FIN: return

    print(f"🔄 [{ahora.strftime('%H:%M')}] Escaneando Multi-Mercado...")
    h = {"x-apisports-key": API_KEY}
    data = requests.get(f"{BASE_URL}/fixtures", headers=h, 
                        params={"date": ahora.strftime('%Y-%m-%d')}).json().get("response", [])

    for m in data:
        if m["league"]["id"] not in LEAGUES: continue
        
        f_id = m["fixture"]["id"]
        m_name = f"{m['teams']['home']['name']} vs {m['teams']['away']['name']}"

        # --- AHORRO DE CRÉDITOS: Primero cuotas ---
        h_o, d_o, a_o = get_odds(f_id)
        if h_o < MIN_ODDS and a_o < MIN_ODDS: continue

        # --- CÁLCULOS DE VALOR ---
        h_id, a_id = m["teams"]["home"]["id"], m["teams"]["away"]["id"]
        h_xg = 1.4 + (team_form(h_id) * 0.8)
        a_xg = 1.1 + (team_form(a_id) * 0.6)
        
        h_p, d_p, a_p = match_probs(h_xg, a_xg)
        
        # 1. Ambos Marcan (BTTS)
        p_btts = (1 - math.exp(-h_xg)) * (1 - math.exp(-a_xg))
        
        # 2. Doble Oportunidad (DC)
        p_1x, p_x2 = h_p + d_p, d_p + a_p
        o_1x = round((h_o * d_o) / (h_o + d_o) * 0.9, 2) if h_o > 0 and d_o > 0 else 0
        o_x2 = round((a_o * d_o) / (a_o + d_o) * 0.9, 2) if a_o > 0 and d_o > 0 else 0

        picks = []

        # Lógica 1X2
        if h_p >= 0.50 and MIN_ODDS <= h_o <= MAX_ODDS and (h_p - (1/h_o)) > 0.015:
            s = round(kelly(h_p, h_o) * BANK, 2)
            picks.append(f"🏠 Gana Local (@{h_o}) [Stk: €{s}]")
            
        if a_p >= 0.50 and MIN_ODDS <= a_o <= MAX_ODDS and (a_p - (1/a_o)) > 0.015:
            s = round(kelly(a_p, a_o) * BANK, 2)
            picks.append(f"🚀 Gana Visita (@{a_o}) [Stk: €{s}]")

        # Lógica Doble Oportunidad
        if p_1x >= 0.72 and o_1x >= 1.35:
            s = round(kelly(p_1x, o_1x) * BANK, 2)
            picks.append(f"🛡️ Doble Op. 1X (@{o_1x}) [Stk: €{s}]")

        # Lógica Ambos Marcan
        if p_btts >= 0.68:
            picks.append(f"⚽ Ambos Marcan - SÍ (Prob: {round(p_btts*100)}%)")

        if picks:
            send(f"📊 <b>{m_name}</b>\n" + "\n".join(picks))
            print(f"✅ Pick enviado: {m_name}")

if __name__ == "__main__":
    while True:
        try:
            scan()
            time.sleep(1200) # 20 minutos
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)
