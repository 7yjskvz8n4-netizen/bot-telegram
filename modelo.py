import requests
import math
import time
from datetime import datetime
import random

# =========================
# ⚙️ CONFIGURACIÓN
# =========================
API_KEY = "167721723854a65832f09abdeb92952b"
TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"

BANK = 100                  
KELLY_FACTOR = 0.50         
MIN_ODDS = 1.40             
BASE_URL = "[https://v3.football.api-sports.io](https://v3.football.api-sports.io)"

# Horario de funcionamiento
HORA_INICIO = 13
HORA_FIN = 22

LEAGUES = [
    39, 40, 41, 140, 141, 135, 136, 78, 79, 61, 62, 88, 94, 71, 13, 253, 2, 3
]

ciclos_sin_valor = 0

# =========================
# 📩 TELEGRAM
# =========================
def send(msg):
    try:
        url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": 'HTML'})
        print(f"📡 Mensaje enviado a Telegram")
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
    ahora = datetime.now()
    print(f"🔄 [{ahora.strftime('%H:%M:%S')}] Escaneando...")
    
    headers = {"x-apisports-key": API_KEY}
    fecha_hoy = ahora.strftime('%Y-%m-%d')
    
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=headers, params={"date": fecha_hoy})
        data = r.json().get("response", [])
        value_bets = []
        partidos_analizados = 0
        
        for m in data:
            if m["league"]["id"] not in LEAGUES: continue 

            partidos_analizados += 1
            h_id, a_id = m["teams"]["home"]["id"], m["teams"]["away"]["id"]
            h_xg = 1.2 + (team_form(h_id) * 0.8)
            a_xg = 1.0 + (team_form(a_id) * 0.6)
            h_p, d_p, a_p = match_probs(h_xg, a_xg)
            h_o, d_o, a_o = get_odds(m["fixture"]["id"])
            
            if h_o > 0:
                opciones = [(h_p, h_o, "HOME", "🏠"), (d_p, d_o, "DRAW", "🤝"), (a_p, a_o, "AWAY", "🚀")]
                for prob, odd, label, icon in opciones:
                    if prob >= 0.55 and odd >= MIN_ODDS:
                        edge = prob - (1/odd)
                        if edge > 0.005:
                            stake_final = kelly(prob, odd) * BANK
                            if stake_final > 0.5:
                                value_bets.append(
                                    f"{icon} <b>{m['teams']['home']['name']}</b> vs {m['teams']['away']['name']}\n"
                                    f"➡️ Lado: <b>{label}</b> | Cuota: {odd}\n"
                                    f"📊 Prob: {round(prob*100, 1)}% | Stake: €{round(stake_final, 2)}"
                                )

        if value_bets:
            send("🔥 <b>VALOR DETECTADO</b>\n\n" + "\n\n".join(value_bets[:5]))
            ciclos_sin_valor = 0 
        else:
            ciclos_sin_valor += 1
            # Reporte cada 3 ciclos (60 minutos, ya que el ciclo es de 20 min)
            if ciclos_sin_valor >= 3:
                send(f"🛰️ <b>Reporte:</b> Escaneo finalizado. {partidos_analizados} partidos revisados. Sin valor claro.")
                ciclos_sin_valor = 0

    except Exception as e:
        print(f"❌ Error en scan: {e}")

# =========================
# 🚀 LOOP DE EJECUCIÓN (CON HORARIO)
# =========================
if __name__ == '__main__':
    print("🚀 BOT ACTIVADO - HORARIO 13:00 a 22:00")
    send("🟢 <b>Bot Iniciado</b>\n⏰ Horario: 13:00 - 22:00\n⏱️ Frecuencia: 20 min.")
    
    while True:
        try:
            ahora = datetime.now()
            # Comprobar si estamos dentro del horario
            if HORA_INICIO <= ahora.hour < HORA_FIN:
                scan()
                wait_time = 1200 # 20 minutos
            else:
                print(f"💤 Fuera de horario ({ahora.strftime('%H:%M')}). Esperando a las 13:00...")
                wait_time = 600 # Comprobar cada 10 min si ya es hora de empezar
            
            time.sleep(wait_time)
            
        except KeyboardInterrupt:
            print("Det```

### ¿Qué haeniendo bot...")
            break
        except Exception as e:
            print(f"Error en loop: {e}")
            time.sleep(60)
 cambiado?
*   **`HORA_INICIO` y `HORA_FIN`**: El bot comprueba la hora actual. Si son las 2
