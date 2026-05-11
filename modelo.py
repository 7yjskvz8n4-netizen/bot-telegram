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
    url = f"{BASE_URL}/odds"
    headers = {"x-apisports-key": API_KEY}
    params = {"fixture": fixture_id}
    try:
        r = requests.get(url, headers=headers, params=params)
        data = r.json().get("response", [])
        best_home = best_draw = best_away = 0
        
        for item in data:
            for b in item.get("bookmakers", []):
                for bet in b.get("bets", []):
                    if bet.get("name") == "Match Winner":
                        for v in bet.get("values", []):
                            val = float(v["odd"])
                            if v["value"] == "Home": best_home = max(best_home, val)
                            if v["value"] == "Draw": best_draw = max(best_draw, val)
                            if v["value"] == "Away": best_away = max(best_away, val)
        return best_home, best_draw, best_away
    except:
        return 0, 0, 0

# =========================
# 🔍 SCAN (LÓGICA 360° AGRESIVA)
# =========================
def scan():
    print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Escaneando mercado...")
    headers = {"x-apisports-key": API_KEY}
    
    # ELIMINAMOS 'season' para evitar errores de año y buscamos más partidos
    params = {"next": 100} 
    
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=headers, params=params)
        data = r.json().get("response", [])
        print(f"⚽ Partidos recibidos de la API: {len(data)}") # Esto saldrá en tu terminal
        
        value_bets = []
        
        for m in data:
            # Quitamos el filtro de LEAGUES temporalmente para ver si entra ALGO
            # if m["league"]["id"] not in LEAGUES: continue 

            h_id, a_id = m["teams"]["home"]["id"], m["teams"]["away"]["id"]
            
            # Cálculo de xG
            h_xg = 1.2 + (team_form(h_id) * 0.8)
            a_xg = 1.0 + (team_form(a_id) * 0.6)
            h_p, d_p, a_p = match_probs(h_xg, a_xg)
            
            h_o, d_o, a_o = get_odds(m["fixture"]["id"])
            
            analisis = [(h_p, h_o, "HOME", "🏠"), (d_p, d_o, "DRAW", "🤝"), (a_p, a_o, "AWAY", "🚀")]

            for prob, odd, label, icon in analisis:
                if odd > 1.10: # Bajamos la cuota mínima drásticamente
                    edge = prob - (1/odd)
                    # Si tiene más de 55% de prob y el valor es aunque sea un poquito positivo
                    if prob >= 0.55 and edge > 0.001: 
                        stake = kelly(prob, odd) * BANK
                        if stake > 0.5:
                            prob_pct = round(prob * 100, 1)
                            value_bets.append(
                                f"{icon} <b>{m['teams']['home']['name']}</b> vs {m['teams']['away']['name']}\n"
                                f"➡️ Lado: <b>{label}</b> | Cuota: {odd}\n"
                                f"📊 Probabilidad: {prob_pct}% | Edge: {round(edge*100,1)}%"
                            )

        if value_bets:
            send("🚀 <b>Picks encontrados:</b>\n\n" + "\n\n".join(value_bets[:5]))
        else:
            print("Sigue sin haber valor claro en los próximos 100 partidos.")

    except Exception as e:
        print(f"❌ Error en scan: {e}")
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
