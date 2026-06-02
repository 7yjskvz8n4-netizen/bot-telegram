import time
import requests

# =========================
# CONFIG (PEGA TUS CLAVES AQUÍ)
# =========================

API_KEY = "PEGA_API_KEY"
TELEGRAM_TOKEN = "PEGA_TELEGRAM_TOKEN"
CHAT_ID = "PEGA_CHAT_ID"

# =========================
# TELEGRAM TEST
# =========================

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except Exception as e:
        print("ERROR TELEGRAM:", e)

# =========================
# STARTUP
# =========================

print("🚀 BOT RESET SEGURO INICIADO")

send("🚀 Bot restaurado correctamente (RESET SEGURO)")

# =========================
# LOOP TEST
# =========================

while True:
    print("RUNNING SAFE BOT")
    time.sleep(60)
