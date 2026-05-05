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
# DISCORD
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
    "User-Agent": "Mozilla/5.0",
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
# POPUP + SOUND
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

    tk.Label(root, text=message, wraplength=450, font=("Arial", 12)).pack(pady=20)
    tk.Button(root, text="ACKNOWLEDGE", command=acknowledge, height=2, width=20).pack(pady=10)

    root.mainloop()

# ----------------------------
# STATE
# ----------------------------
status = {}
first_run = True
cycle = 0

# ----------------------------
# MAIN LOOP
# ----------------------------
while True:
    cycle += 1
    cycle_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"\n=== Cycle #{cycle} | {cycle_time} ===")

    changed_items = []

    for item in ITEMS:
        try:
            response = requests.get(item["url"], headers=headers, timeout=10)
            available = is_available(response.text)

            name = item["name"]
            state_text = "ACTIVE" if available else "INACTIVE"

            # ----------------------------
            # FIRST RUN (BASELINE)
            # ----------------------------
            if first_run:
                msg = f"[INIT] {cycle_time} | {name} -> {state_text}"
                print(msg)
                send_discord_alert(msg)

                status[name] = available
                continue

            # ----------------------------
            # COMPARE STATES (FIXED - NO "previous" BUG)
            # ----------------------------
            if name in status and status[name] != available:
                changed_items.append((name, available, item["url"]))
                status[name] = available

            elif name not in status:
                status[name] = available

        except Exception as e:
            print(f"[ERROR] {item['name']} -> {e}")

    # ----------------------------
    # END FIRST RUN
    # ----------------------------
    if first_run:
        first_run = False
        print("Baseline status stored. Monitoring started.")
        continue

    # ----------------------------
    # OUTPUT
    # ----------------------------
    if not changed_items:
        msg = f"Cycle #{cycle}: no status changes"
        print(msg)
        send_discord_alert(msg)

    else:
        for name, available, url in changed_items:
            state_text = "NOW ACTIVE" if available else "NOW INACTIVE"
            msg = f"[STATUS CHANGE] {cycle_time} | {name} | {state_text} | {url}"

            print(msg)
            send_discord_alert(msg)
            show_popup("STATUS CHANGE", msg)

    print("=" * 60)

    time.sleep(random.uniform(60, 180))