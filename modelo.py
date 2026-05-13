import requests
import math
import time
from datetime import datetime

# ==========================================
# ⚙️ CONFIGURACIÓN GLOBAL
# ==========================================
API_KEY = "167721723854a65832f09abdeb92952b"
TELEGRAM_TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"

BANK = 100
KELLY_FACTOR = 0.25  # Perfil Intermedio
MIN_ODDS = 1.45
MAX_ODDS = 2.65

# Ligas seleccionadas para optimizar tus 100 créditos
LEAGUES = [39, 140, 135, 78, 61, 88, 94, 71, 13, 2] 
BASE_URL = "https://v3.football.api-sports.io"

def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")

def kelly(p, o):
    if o <= 1: return 0
    k = (p * o - 1) / (o - 1)
    return max(0, k * KELLY_FACTOR)

def team_form(team_id):
    # Nota: Esta función consume 1 crédito. 
    # Para ahorrar, podrías cachear estos resultados o usar un valor base.
    return 0.5 

def get_odds(fixture_id):
    h = {"x-apisports-key": API_KEY}
    try:
        r = requests.get(f"{BASE_URL}/odds", headers=h, params={"fixture": fixture_id}).json()
        bookmaker = r["response"][0]["bookmakers"][0]
        bets = bookmaker["bets"][0]["values"]
        # Retorna: Local, Empate, Visitante
        return float(bets[0]["odd"]), float(bets[1]["odd"]), float(bets[2]["odd"])
    except:
        return 0, 0, 0

def match_probs(h_xg, a_xg):
    h_p, d_p, a_p = 0, 0, 0
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
    dia_semana = ahora.weekday() # 0=Lunes, 6=Domingo
    hora_actual = ahora.hour

    # Lógica de Horarios solicitada
    if dia_semana < 5:  # Lunes a Viernes
        h_inicio = 17
    else:               # Sábado y Domingo
        h_inicio = 11
    
    h_fin = 22

    if hora_actual < h_inicio or hora_actual >= h_fin:
        print(f"💤 [{ahora.strftime('%H:%M')}] Fuera de horario ({h_inicio}:00 - {h_fin}:00).")
        return

    print(f"🔄 [{ahora.strftime('%H:%M')}] Iniciando escaneo Multi-Mercado...")
    h = {"x-apisports-key": API_KEY}
    
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=h, params={"date": ahora.strftime('%Y-%m-%d')})
        data = r.json().get("response", [])
    except:
        print("❌ Error conectando con la API")
        return

    for m in data:
        if m["league"]["id"] not in LEAGUES: continue
        
        f_id = m["fixture"]["id"]
        m_name = f"{m['teams']['home']['name']} vs {m['teams']['away']['name']}"

        # --- PASO 1: CUOTAS (Ahorro de créditos) ---
        h_o, d_o, a_o = get_odds(f_id)
        if h_o < MIN_ODDS and a_o < MIN_ODDS: continue

        # --- PASO 2: ESTADÍSTICAS ---
        h_id, a_id = m["teams"]["home"]["id"], m["teams"]["away"]["id"]
        h_xg = 1.4 + (team_form(h_id) * 0.8)
        a_xg = 1.1 + (team_form(a_id) * 0.6)
        
        h_p, d_p, a_p = match_probs(h_xg, a_xg)
        
        # Probabilidades extra
        p_btts = (1 - math.exp(-h_xg)) * (1 - math.exp(-a_xg))
        p_1x, p_x2 = h_p + d_p, d_p + a_p
        
        # Estimación de cuotas para Doble Oportunidad
        o_1x = round((h_o * d_o) / (h_o + d_o) * 0.9, 2) if h_o > 0 and d_o > 0 else 0
        o_x2 = round((a_o * d_o) / (a_o + d_o) * 0.9, 2) if a_o > 0 and d_o > 0 else 0

        picks = []

        # Mercado 1X2
        if h_p >= 0.50 and MIN_ODDS <= h_o <= MAX_ODDS:
            if (h_p - (1/h_o)) > 0.015:
                s = round(kelly(h_p, h_o) * BANK, 2)
                picks.append(f"🏠 Gana Local (@{h_o}) [Stk: €{s}]")
            
        if a_p >= 0.50 and MIN_ODDS <= a_o <= MAX_ODDS:
            if (a_p - (1/a_o)) > 0.015:
                s = round(kelly(a_p, a_o) * BANK, 2)
                picks.append(f"🚀 Gana Visita (@{a_o}) [Stk: €{s}]")

        # Mercado Doble Oportunidad
        if p_1x >= 0.72 and o_1x >= 1.35:
            s = round(kelly(p_1x, o_1x) * BANK, 2)
            picks.append(f"🛡️ Doble Op. 1X (@{o_1x}) [Stk: €{s}]")

        # Mercado Ambos Marcan
        if p_btts >= 0.68:
            picks.append(f"⚽ Ambos Marcan - SÍ (Prob: {round(p_btts*100)}%)")

        if picks:
            send(f"📊 <b>{m_name}</b>\n" + "\n".join(picks))
            print(f"✅ Alerta enviada para: {m_name}")

if __name__ == "__main__":
    # Mensaje de inicio
    print("🚀 Bot Activo con Horario Diferenciado")
    while True:
        try:
            scan()
            time.sleep(1200) # Escaneo cada 20 min
        except Exception as e:
            print(f"Error crítico: {e}")
            time.sleep(60)
