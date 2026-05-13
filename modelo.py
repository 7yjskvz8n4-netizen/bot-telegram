import requests
import math
import time
from datetime import datetime
import random

# =========================
# ⚙️ CONFIGURACIÓN (REVISADA)
# =========================
API_KEY = "167721723854a65832f09abdeb92952b"
TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"

BANK = 100                  
KELLY_FACTOR = 0.25      
MIN_ODDS = 1.45
MAX_ODDS = 2.65

BASE_URL = "https://v3.football.api-sports.io"

# Variables de tiempo (Asegúrate de que estas tres estén aquí)
HORA_INICIO = 13
HORA_FIN = 22
MINUTOS_ESPERA = 20  # <--- Esta es la que te faltaba

LEAGUES = [
    39, 140, 135, 78, 61,  # Las 5 grandes (Premier, LaLiga, Serie A, Bundesliga, Ligue 1)
    88, 94,                # Eredivisie y Portugal (Muy buenas para valor)
    71, 13,                # Brasil y Argentina
    2                      # Champions League
]

ciclos_sin_valor = 0

# =========================
# 📩 TELEGRAM
# =========================
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": 'HTML'})
    except Exception as e:
        print(f"❌ Error Telegram: {e}")

# =========================
# ⚽ MATEMÁTICAS
# =========================
def poisson(k, lam):
    return (lam ** k * math.exp(-lam)) / math.factorial(k)

def match_probs(home_xg, away_xg):
    home = draw = away = 0
    for i in range(7):
        for j in range(7):
            p = poisson(i, home_xg) * poisson(j, away_xg)
            if i > j: home += p
            elif i == j: draw += p
            else: away += p
    return home, draw, away

def kelly(prob, odds):
    if odds <= 1: return 0
    b = odds - 1
    q = 1 - prob
    f = (prob * b - q) / b
    return max(0, f * KELLY_FACTOR)

# =========================
# 📊 DATOS API
# =========================
def team_form(team_id):
    try:
        url = f"{BASE_URL}/fixtures"
        headers = {"x-apisports-key": API_KEY}
        params = {"team": team_id, "last": 5}
        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json().get("response", [])
        if not data: return 1.0
        goals = sum((m["goals"]["home"] or 0) + (m["goals"]["away"] or 0) for m in data)
        return max(0.5, goals / 10) 
    except:
        return 1.0

def get_odds(fixture_id):
    time.sleep(0.4) 
    url = f"{BASE_URL}/odds"
    headers = {"x-apisports-key": API_KEY}
    params = {"fixture": fixture_id}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json().get("response", [])
        if not data: return 0, 0, 0
        h, d, a = 0, 0, 0
        for book in data[0].get("bookmakers", []):
            for bet in book.get("bets", []):
                if bet["name"] == "Match Winner":
                    for v in bet["values"]:
                        if v["value"] == "Home": h = float(v["odd"])
                        if v["value"] == "Draw": d = float(v["odd"])
                        if v["value"] == "Away": a = float(v["odd"])
            if h > 0: break
        return h, d, a
    except:
        return 0, 0, 0

# =========================
# 🔍 ESCANEO
# =========================
def scan():
    global ciclos_sin_valor
    ahora_dt = datetime.now()
    ahora_str = ahora_dt.strftime('%H:%M:%S')
    
    if ahora_dt.hour < HORA_INICIO or ahora_dt.hour >= HORA_FIN:
        print(f"💤 [{ahora_str}] Fuera de horario (13:00 - 22:00).")
        return

    print(f"🔄 [{ahora_str}] Iniciando escaneo (Modo Ahorro de Créditos)...")
    headers = {"x-apisports-key": API_KEY}
    fecha_hoy = ahora_dt.strftime('%Y-%m-%d')
    
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=headers, params={"date": fecha_hoy})
        data = r.json().get("response", [])
        
        value_bets = []
        partidos_analizados = 0
        
        for m in data:
            if m["league"]["id"] not in LEAGUES: continue 
            
            fixture_id = m["fixture"]["id"]
            match_name = f"{m['teams']['home']['name']} vs {m['teams']['away']['name']}"

            # --- PASO 1: CONSULTAR CUOTAS PRIMERO (1 Crédito) ---
            h_o, d_o, a_o = get_odds(fixture_id)
            
            # Verificamos si alguna cuota llega al mínimo de 1.45
            if h_o < 1.45 and d_o < 1.45 and a_o < 1.45:
                # Si ninguna cuota sirve, pasamos al siguiente sin gastar en estadísticas
                continue

            # --- PASO 2: SOLO SI LA CUOTA SIRVE, CALCULAMOS PROBABILIDADES ---
            # Aquí es donde ahorramos 2 créditos si el paso 1 falló
            partidos_analizados += 1
            h_id, a_id = m["teams"]["home"]["id"], m["teams"]["away"]["id"]
            
            # xG dinámico (Ajustado para ser un poco más agresivo como pediste antes)
            h_xg = 1.4 + (team_form(h_id) * 0.8)
            a_xg = 1.1 + (team_form(a_id) * 0.6)
            
            h_p, d_p, a_p = match_probs(h_xg, a_xg)
            
            opciones = [(h_p, h_o, "HOME", "🏠"), (d_p, d_o, "DRAW", "🤝"), (a_p, a_o, "AWAY", "🚀")]
            
            for prob, odd, label, icon in opciones:
                # Filtro de cuota 1.45 aplicado aquí también
                if prob >= 0.51 and odd >= 1.45: 
                    edge = prob - (1/odd)
                    if edge > 0.001:
                        stake_final = kelly(prob, odd) * BANK
                        if stake_final > 1:
                            value_bets.append(
                                f"{icon} <b>{match_name}</b>\n"
                                f"➡️ Lado: <b>{label}</b> | Cuota: {odd}\n"
                                f"📊 Prob: {round(prob*100, 1)}% | Stake: €{round(stake_final, 2)}"
                            )

        if value_bets:
            send("🔥 <b>VALOR DETECTADO</b>\n\n" + "\n\n".join(value_bets[:5]))
            ciclos_sin_valor = 0 
        else:
            ciclos_sin_valor += 1
            print(f"🏁 Escaneo completado. Analizados a fondo {partidos_analizados} partidos con cuota atractiva.")
            
            if ciclos_sin_valor >= 3:
                send(f"🛰️ <b>Reporte:</b> Bot activo. Analizados {partidos_analizados} partidos con cuotas > 1.45.")
                ciclos_sin_valor = 0

    except Exception as e:
        print(f"❌ Error en scan: {e}")
# =========================
# 🚀 EJECUCIÓN (UNIFICADA)
# =========================
if __name__ == '__main__':
    print("🚀 BOT HEDGE FUND ACTIVADO")
    print(f"⏰ Horario: {HORA_INICIO}:00 a {HORA_FIN}:00")
    print(f"⏱️ Frecuencia: Cada {MINUTOS_ESPERA} minutos")
    
    send(f"🟢 <b>Bot Iniciado</b>\n⏰ Horario: {HORA_INICIO}:00 - {HORA_FIN}:00\n⏱️ Escaneo: Cada {MINUTOS_ESPERA} min.")
    
    while True:
        try:
            scan()
            time.sleep(MINUTOS_ESPERA * 60) 
        except KeyboardInterrupt:
            print("Deteniendo bot...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)
