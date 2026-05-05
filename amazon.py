import requests
import time
import random
from datetime import datetime
import tkinter as tk
import winsound
import threading

# ----------------------------
# CONFIG
# ----------------------------
ITEMS = [
    {
        "name": "Strixhaven Sanity Check",
        "url": "https://www.amazon.com/Magic-Gathering-Secrets-Strixhaven-Booster/dp/B0GFDJ7GVL"
    },
    {
        "name": "Hobbit CBB",
        "url": "https://www.amazon.com/dp/B0GXC89N66/?coliid=I1FXUO0NHWN806&colid=1FOPYWHMPI8YU&psc=0"
    },
    {
        "name": "Hobbit Gift Bundle",
        "url": "https://www.amazon.com/Magic-Gathering-Hobbit-Collectible-Trading/dp/B0GWS8DC8C"
    }
]

# ----------------------------
# DISCORD WEBHOOK
# ----------------------------
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1501086028042342481/Vsq-rZPxZeO0-1JwzFqv6jOBOmg2bo_mAsLTKSaIoFIEkS2UAnc9AJnhRsMIrR-vM8JD"

def send_discord_alert(message: str):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10)
    except Exception as e:
        print(f"[ERROR] Discord webhook failed: {e}")

# ----------------------------
# HEADERS
# ----------------------------
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

# ----------------------------
# CHECK LOGIC
# ----------------------------
def is_available(html: str) -> bool:
    html = html.lower()
    return (
        "add-to-cart-button" in html and
        "currently unavailable" not in html
    )

# ----------------------------
# STATE STORAGE
# ----------------------------
status = {}
first_run = True

# ----------------------------
# SOUND + POPUP SYSTEM
# ----------------------------
alarm_active = False

def sound_loop():
    while alarm_active:
        winsound.Beep(500, 200)
        time.sleep(0.4)

def show_popup(title, message):
    global alarm_active

    alarm_active = True
    threading.Thread(target=sound_loop, daemon=True).start()

    def acknowledge():
        global alarm_active
        alarm_active = False
        root.destroy()

    root = tk.Tk()
    root.title(title)
    root.geometry("500x220")
    root.attributes("-topmost", True)

    label = tk.Label(
        root,
        text=message,
        wraplength=450,
        font=("Arial", 12)
    )
    label.pack(pady=20)

    btn = tk.Button(root, text="ACKNOWLEDGE", command=acknowledge, height=2, width=20)
    btn.pack(pady=10)

    root.mainloop()

# ----------------------------
# MAIN LOOP
# ----------------------------
while True:
    cycle_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n--- Cycle started at {cycle_time} ---")

    for item in ITEMS:
        try:
            request_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            response = requests.get(item["url"], headers=headers, timeout=10)
            html = response.text

            available = is_available(html)
            name = item["name"]

            previous = status.get(name)

            state_text = "ACTIVE" if available else "INACTIVE"
            print(f"[{request_time}] {name} -> {state_text}")

            # ----------------------------
            # INIT
            # ----------------------------
            if first_run:
                init_msg = f"[INIT] {request_time} | {name} | {state_text}"
                send_discord_alert(init_msg)

            # ----------------------------
            # STATUS CHANGE
            # ----------------------------
            elif previous is not None and previous != available:
                if available:
                    msg = f"[STATUS CHANGE] {request_time} | {name} | NOW ACTIVE | {item['url']}"
                else:
                    msg = f"[STATUS CHANGE] {request_time} | {name} | NOW INACTIVE"

                send_discord_alert(msg)

                # ALERT (popup + sound)
                show_popup("STATUS CHANGE", msg)

            else:
                print(f"[{request_time}] {name} status unchanged")

            status[name] = available

        except Exception as e:
            print(f"[ERROR] {item['name']} -> {e}")

    first_run = False

    print("\n" + "=" * 60)
    time.sleep(random.uniform(60, 180))