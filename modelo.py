import math
import requests
import time
import random
from datetime import datetime

# =========================
# ⚙️ CONFIGURACIÓN AGRESIVA
# =========================
# RECUERDA COMPLETAR TUS KEYS
TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"
API_KEY = "167721723854a65832f09abdeb92952b"

BANK = 100          # Capital total para apuestas
KELLY_FACTOR = 0.50      # Más agresivo (Medio Kelly)
MIN_ODDS = 1.40         # Bajamos el umbral para detectar más picks
BASE_URL = "https://v3.football.api-sports.io"

# LIGAS AMPLIADAS (Incluye las principales europeas y secundarias para más volumen)
LEAGUES = [
    39, 40, 41,     # Premier League, Championship, League One
    140, 141,       # LaLiga, Segunda División
    135, 136,       # Serie A, Serie B
    78, 79,         # Bundesliga, 2. Bundesliga
    61, 62,         # Ligue 1, Ligue 2
    88, 94,         # Eredivisie, Primeira Liga (Portugal)
    71, 13,         # Serie A Brasil, Primera División Argentina
    253,            # MLS
    2, 3            # Champions League, Europa League
]

# =========================
# 📩 TELEGRAM (REPORTES)
# =========================
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": 'HTML'})
        print(f"📡 Telegram enviado")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

# =========================
# ⚽ MATEMÁTICAS (POISSON & KELLY)
# =========================
def poisson(k, lam):
    return (lam ** k * math.exp(-lam)) / math.factorial(k)

def match_probs(home_xg, away_xg):
    home = draw = away = 0
    for i in range(7): # Aumentado a 7 para mayor precisión en goleadas
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
        r = requests.get(url, headers=headers, params=params)
        data = r.json().get("response", [])
        if not data: return 1.0
        goals = sum((m["goals"]["home"] or 0) + (m["goals"]["away"] or 0) for m in data)
        return goals / 10
    except:
        return 1.0

def get_odds(fixture_id):
    # Añadimos un pequeño retraso para no saturar la API gratuita
    time.sleep(0.5) 
    url = f"{BASE_URL}/odds"
    headers = {"x-apisports-key": API_KEY}
    params = {"fixture": fixture_id}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json().get("response", [])
        if not data: return 0, 0, 0
        
        # Extraer cuotas 1X2
        h, d, a = 0, 0, 0
        for book in data[0].get("bookmakers", []):
            for bet in book.get("bets", []):
                if bet["name"] == "Match Winner":
                    for v in bet["values"]:
                        if v["value"] == "Home": h = float(v["odd"])
                        if v["value"] == "Draw": d = float(v["odd"])
                        if v["value"] == "Away": a = float(v["odd"])
            if h > 0: break # Si ya encontramos cuotas en una casa, paramos
        return h, d, a
    except:
        return 0, 0, 0

def scan():
    print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Iniciando escaneo de 182 partidos...")
    headers = {"x-apisports-key": API_KEY}
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=headers, params={"date": fecha_hoy})
        data = r.json().get("response", [])
        
        value_bets = []
        count = 0
        
        for m in data:
            count += 1
            # Solo analizamos ligas que conocemos para ir más rápido
            # if m["league"]["id"] not in LEAGUES: continue 

            # Imprimimos progreso para que veas que NO está congelado
            if count % 10 == 0:
                print(f"⏳ Analizando partido {count} de {len(data)}...")

            h_id, a_id = m["teams"]["home"]["id"], m["teams"]["away"]["id"]
            h_p, d_p, a_p = match_probs(1.3, 1.1) # Cálculo base rápido
            
            # Intentar obtener cuotas
            h_o, d_o, a_o = get_odds(m["fixture"]["id"])
            
            if h_o > 0:
                # --- TU FILTRO DE GANAR A MENUDO ---
                analisis = [(h_p, h_o, "HOME", "🏠"), (d_p, d_o, "DRAW", "🤝"), (a_p, a_o, "AWAY", "🚀")]
                for prob, odd, label, icon in analisis:
                    if prob >= 0.55 and odd >= 1.40:
                        edge = prob - (1/odd)
                        if edge > 0.005:
                            value_bets.append(f"{icon} <b>{m['teams']['home']['name']}</b> | @{odd} | Prob: {round(prob*100)}%")

        if value_bets:
            send("✅ <b>Picks detectados:</b>\n\n" + "\n\n".join(value_bets[:5]))
        else:
            print("🏁 Escaneo finalizado. Sin oportunidades de valor ahora.")

    except Exception as e:
        print(f"❌ Error: {e}")

# =========================
# 🔍 SCAN (LÓGICA 360° AGRESIVA)
# =========================
def scan():
    ahora = datetime.now().strftime('%H:%M:%S')
    print(f"🔄 [{ahora}] Iniciando escaneo blindado...")
    
    headers = {"x-apisports-key": API_KEY}
    
    # 1. Buscamos partidos para la fecha de HOY (es lo más seguro en el plan FREE)
    # Usamos la fecha del sistema
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    url = f"{BASE_URL}/fixtures"
    params = {"date": fecha_hoy}
    
    try:
        print(f"📡 Llamando a la API para la fecha: {fecha_hoy}...")
        r = requests.get(url, headers=headers, params=params)
        
        # Imprimimos el código de estado para diagnóstico
        print(f"📊 Código de respuesta API: {r.status_code}")
        
        res_json = r.json()
        
        # Si hay errores de la API, los mostramos
        if res_json.get("errors"):
            print(f"❌ Error reportado por la API: {res_json['errors']}")
            return

        data = res_json.get("response", [])
        print(f"✅ Partidos encontrados hoy: {len(data)}")
        
        if len(data) == 0:
            print("❓ Qué raro... la API dice que no hay partidos hoy. Probemos con mañana.")
            # Intento extra con fecha de mañana por si es tarde
            return

        value_bets = []
        for m in data:
            # Analizamos todos los partidos que tengan cuotas disponibles
            h_id, a_id = m["teams"]["home"]["id"], m["teams"]["away"]["id"]
            
            # Cálculo rápido de probabilidades
            h_xg = 1.2 + (team_form(h_id) * 0.8)
            a_xg = 1.0 + (team_form(a_id) * 0.6)
            h_p, d_p, a_p = match_probs(h_xg, a_xg)
            
            # Obtener cuotas
            h_o, d_o, a_o = get_odds(m["fixture"]["id"])
            
            # Solo si hay cuotas (si no, no podemos calcular valor)
            if h_o > 0:
                opciones = [(h_p, h_o, "HOME", "🏠"), (d_p, d_o, "DRAW", "🤝"), (a_p, a_o, "AWAY", "🚀")]
                for prob, odd, label, icon in opciones:
                    if prob >= 0.60 and odd >= 1.40: # Filtro de "Ganar a menudo"
                        edge = prob - (1/odd)
                        if edge > 0.01:
                            stake = kelly(prob, odd) * BANK
                            if stake > 0.5:
                                value_bets.append(
                                    f"{icon} <b>{m['teams']['home']['name']}</b> vs {m['teams']['away']['name']}\n"
                                    f"➡️ Lado: <b>{label}</b> | Cuota: {odd} | Prob: {round(prob*100)}%"
                                )

        if value_bets:
            send("🔥 <b>VALOR ENCONTRADO</b>\n\n" + "\n\n".join(value_bets[:5]))
            print(f"📡 {len(value_bets)} picks enviados a Telegram.")
        else:
            print("🤖 He analizado los partidos de hoy, pero ninguno cumple el filtro de 60% de probabilidad y valor.")

    except Exception as e:
        print(f"❌ Error total en scan: {e}")
# =========================
# 🚀 LOOP DE EJECUCIÓN
# =========================
if __name__ == '__main__':
    print("🚀 HEDGE FUND BOT ACTIVADO - MODO AGRESIVO")
    send("🟢 <b>Bot Hedge Fund</b> iniciado correctamente.\n✅ Modo: Agresivo (1X2)\n⏱️ Escaneo: Cada 5 min.")
    
    last_heartbeat = time.time() 

    while True:
        try:
            scan()
            
            # Reporte de estado cada hora
            current_time = time.time()
            if current_time - last_heartbeat >= 3600:
                send("🤖 <b>Reporte de estado:</b> El bot sigue activo y rastreando valor.")
                last_heartbeat = current_time 

            # Espera 5 min + pequeña variación
            wait_time = 300 + random.randint(-15, 15)
            print(f"⏳ Durmiendo {wait_time} segundos...")
            time.sleep(wait_time)
            
        except KeyboardInterrupt:
            print("Deteniendo bot...")
            break
        except Exception as e:
            print(f"Error en loop principal: {e}")
            time.sleep(60)
