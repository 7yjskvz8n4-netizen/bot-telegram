import requests
import math
import time
import json
import random
from datetime import datetime, timedelta

# =========================
# 🔑 CONFIG (RELLENA ESTO)
# =========================
TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"
API_KEY = "167721723854a65832f09abdeb92952b"

BANK = 200
KELLY_FACTOR = 0.25
MIN_ODDS = 1.50
BASE_URL = "https://v3.football.api-sports.io"
RESULTS_FILE = "results.json"

# LIGAS
LEAGUES = [39, 140, 135, 78, 61, 40, 141, 1352, 79]

# =========================
# 📩 TELEGRAM (REAL)
# =========================
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
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
    for i in range(6):
        for j in range(6):
            p = poisson(i, home_xg) * poisson(j, away_xg)
            if i > j: home += p
            elif i == j: draw += p
            else: away += p
    return home, draw, away

def kelly(prob, odds):
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
        goals = sum((m["goals"]["home"] or 0) + (m["goals"]["away"] or 0) for m in data)
        return goals / 10
    except:
        return 1

def get_odds(fixture_id):
    url = f"{BASE_URL}/odds"
    headers = {"x-apisports-key": API_KEY}
    params = {"fixture": fixture_id}
    try:
        r = requests.get(url, headers=headers, params=params)
        data = r.json().get("response", [])
        best_home = 0
        best_away = 0
        for item in data:
            for b in item.get("bookmakers", []):
                for bet in b.get("bets", []):
                    if bet.get("name") == "Match Winner":
                        for v in bet.get("values", []):
                            if v["value"] == "Home": best_home = max(best_home, float(v["odd"]))
                            if v["value"] == "Away": best_away = max(best_away, float(v["odd"]))
        return best_home, best_away
    except:
        return 0, 0

# =========================
# 🔍 SCAN (LÓGICA PRINCIPAL)
# =========================
def scan():
    print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Iniciando escaneo de mercado completo (1X2)...")
    
    headers = {"x-apisports-key": API_KEY}
    params = {"season": 2025, "next": 50} 
    
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=headers, params=params)
        data = r.json().get("response", [])
        
        value_bets = []
        
        for m in data:
            league = m["league"]["id"]
            if league not in LEAGUES: continue

            home_id = m["teams"]["home"]["id"]
            away_id = m["teams"]["away"]["id"]
            
            # Cálculo de xG basado en forma (Usando tu mejora de 0.8)
            home_xg = 1.2 + (team_form(home_id) * 0.8)
            away_xg = 1.0 + (team_form(away_id) * 0.6)
            
            # Obtenemos probabilidades para Local, Empate y Visitante
            h_p, d_p, a_p = match_probs(home_xg, away_xg)
            
            # Obtenemos las mejores cuotas de la API
            # Nota: Para el empate necesitarías modificar get_odds, 
            # pero por ahora usemos las de Local y Visitante que ya tienes.
            h_odds, a_odds = get_odds(m["fixture"]["id"])
            
            # --- ANALIZAR VICTORIA LOCAL (HOME) ---
            if h_odds >= MIN_ODDS:
                edge_h = h_p - (1/h_odds)
                if edge_h > 0.02: # Filtro de 2% de ventaja mínima
                    stake = kelly(h_p, h_odds) * BANK
                    if stake > 1: # Solo si sugiere apostar más de 1€
                        value_bets.append(f"🏠 <b>{m['teams']['home']['name']}</b> vs {m['teams']['away']['name']}\n➡️ Lado: <b>HOME</b> | Cuota: {h_odds}\n📈 Edge: {round(edge_h*100,2)}% | Stake: €{round(stake,2)}")

            # --- ANALIZAR VICTORIA VISITANTE (AWAY) ---
            if a_odds >= MIN_ODDS:
                edge_a = a_p - (1/a_odds)
                if edge_a > 0.02:
                    stake = kelly(a_p, a_odds) * BANK
                    if stake > 1:
                        value_bets.append(f"🚀 {m['teams']['home']['name']} vs <b>{m['teams']['away']['name']}</b>\n➡️ Lado: <b>AWAY</b> | Cuota: {a_odds}\n📈 Edge: {round(edge_a*100,2)}% | Stake: €{round(stake,2)}")

        if value_bets:
            # Enviamos las mejores 5 oportunidades encontradas
            full_msg = "🔥 <b>OPORTUNIDADES DE VALOR ENCONTRADAS</b>\n\n" + "\n\n".join(value_bets[:5])
            send(full_msg)
        else:
            print("No se encontraron desajustes de cuotas en este escaneo.")

    except Exception as e:
        print(f"❌ Error en scan: {e}")

# =========================
# 🚀 LOOP DE EJECUCIÓN
# =========================
if __name__ == "__main__":
    print("🚀 HEDGE FUND BOT ACTIVADO")
    send("🟢 <b>Bot Hedge Fund</b> iniciado correctamente. Escaneando cada 5 min.")
    
    # Variable para controlar el aviso cada hora
    last_heartbeat = time.time() 

    while True:
        try:
            scan()
            
            # --- LÓGICA DE "ESTOY VIVO" CADA HORA ---
            current_time = time.time()
            if current_time - last_heartbeat >= 3600:
                send("🤖 <b>Reporte de estado:</b> El bot sigue activo y escaneando.")
                last_heartbeat = current_time # Reiniciamos el contador de la hora
            # ----------------------------------------

            # Espera 5 min + un poco de aleatoriedad
            wait_time = 300 + random.randint(-15, 15)
            print(f"⏳ Durmiendo {wait_time} segundos...")
            time.sleep(wait_time)
            
        except KeyboardInterrupt:
            print("Stopping...")
            break
        except Exception as e:
            print(f"Falló el loop: {e}")
            time.sleep(60)
