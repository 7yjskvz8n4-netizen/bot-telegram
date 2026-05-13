import requests
import math
import time
from datetime import datetime

# === CONFIGURACIÓN ===
API_KEY = "167721723854a65832f09abdeb92952b"
TELEGRAM_TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"

BANK = 100
KELLY_FACTOR = 0.25  
MIN_ODDS = 1.45
MAX_ODDS = 2.65

LEAGUES = [39, 140, 135, 78, 61, 88, 94, 71, 13, 2] 
BASE_URL = "https://v3.football.api-sports.io"

# Variable global para controlar el aviso de actividad cada hora
ultima_hora_aviso = -1

# === FUNCIONES DE APOYO ===

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
    return 0.5 

def get_odds(fixture_id):
    h = {"x-apisports-key": API_KEY}
    try:
        r = requests.get(f"{BASE_URL}/odds", headers=h, params={"fixture": fixture_id}).json()
        bookmaker = r["response"][0]["bookmakers"][0]
        bets = bookmaker["bets"][0]["values"]
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

# === FUNCIÓN PRINCIPAL DE ESCANEO ===

def scan():
    global ultima_hora_aviso
    ahora = datetime.now()
    dia_semana = ahora.weekday() 
    hora_actual = ahora.hour

    # Lógica de Horarios
    h_inicio = 17 if dia_semana < 5 else 11
    h_fin = 22

    # Aviso de Actividad (Se envía una vez cada hora si el bot está corriendo)
    if hora_actual != ultima_hora_aviso:
        status_msg = f"📡 <b>Bot Activo</b>\n⏰ Hora: {ahora.strftime('%H:%M')}\n⚙️ Estado: Analizando mercados..."
        send(status_msg)
        ultima_hora_aviso = hora_actual

    if hora_actual < h_inicio or hora_actual >= h_fin:
        print(f"💤 [{ahora.strftime('%H:%M')}] Fuera de horario operativo.")
        return

    print(f"🔄 [{ahora.strftime('%H:%M')}] Iniciando escaneo de partidos...")
    headers = {"x-apisports-key": API_KEY}
    
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=headers, params={"date": ahora.strftime('%Y-%m-%d')})
        data = r.json().get("response", [])
    except:
        print("❌ Error conectando con la API")
        return

    partidos_analizados = 0
    for m in data:
        if m["league"]["id"] not in LEAGUES: continue
        
        partidos_analizados += 1
        f_id = m["fixture"]["id"]
        m_name = f"{m['teams']['home']['name']} vs {m['teams']['away']['name']}"
        league_name = m["league"]["name"]

        h_o, d_o, a_o = get_odds(f_id)
        if h_o < MIN_ODDS and a_o < MIN_ODDS: continue

        h_id, a_id = m["teams"]["home"]["id"], m["teams"]["away"]["id"]
        h_xg = 1.4 + (team_form(h_id) * 0.8)
        a_xg = 1.1 + (team_form(a_id) * 0.6)
        
        h_p, d_p, a_p = match_probs(h_xg, a_xg)
        
        current_picks = []

        # Lógica Gana Local
        if h_p >= 0.50 and MIN_ODDS <= h_o <= MAX_ODDS:
            if (h_p - (1/h_o)) > 0.015:
                s = round(kelly(h_p, h_o) * BANK, 2)
                current_picks.append({"label": "Gana Local", "odd": h_o, "stake": s})

        # Lógica Gana Visitante
        if a_p >= 0.50 and MIN_ODDS <= a_o <= MAX_ODDS:
            if (a_p - (1/a_o)) > 0.015:
                s = round(kelly(a_p, a_o) * BANK, 2)
                current_picks.append({"label": "Gana Visita", "odd": a_o, "stake": s})

        if current_picks:
            msg_lines = [f"📊 <b>{m_name}</b> ({league_name})"]
            
            try:
                with open("registro_apuestas.csv", "a", encoding="utf-8") as f:
                    for pick in current_picks:
                        msg_lines.append(f"✅ {pick['label']} (@{pick['odd']}) [Stk: €{pick['stake']}]")
                        
                        fecha_csv = ahora.strftime('%Y-%m-%d')
                        # Usamos replace para que Excel español detecte los números correctamente
                        linea = f"{fecha_csv};{m_name};{league_name};{pick['label']};{str(pick['odd']).replace('.', ',')};{str(pick['stake']).replace('.', ',')}\n"
                        f.write(linea)
                
                send("\n".join(msg_lines))
                print(f"✅ Pick enviado: {m_name}")
                
            except Exception as e:
                print(f"❌ Error al escribir registro: {e}")

    print(f"✅ Escaneo finalizado. Partidos en tus ligas hoy: {partidos_analizados}")

if __name__ == "__main__":
    print("🚀 Bot Iniciado con aviso horario.")
    while True:
        try:
            scan()
            # Escaneo cada 30 minutos para no saturar la API
            time.sleep(1800) 
        except KeyboardInterrupt:
            print("🛑 Bot detenido.")
            break
        except Exception as e:
            print(f"Error crítico: {e}")
            time.sleep(60)
