from playwright.sync_api import sync_playwright
import time
import random
from datetime import datetime
import requests
import threading
import tkinter as tk
import winsound

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
        "url": "https://www.amazon.com/dp/B0GXC89N66/"
    },
    {
        "name": "Hobbit Gift Bundle",
        "url": "https://www.amazon.com/Magic-Gathering-Hobbit-Collectible-Trading/dp/B0GWS8DC8C"
    }
]

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1501086028042342481/Vsq-rZPxZeO0-1JwzFqv6jOBOmg2bo_mAsLTKSaIoFIEkS2UAnc9AJnhRsMIrR-vM8JD"

# ----------------------------
# DISCORD
# ----------------------------
def send_discord_alert(message: str):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10)
    except Exception as e:
        print(f"[ERROR] Discord webhook failed: {e}")

# ----------------------------
# AVAILABILITY CHECK
# ----------------------------
def is_available(page) -> bool:
    try:
        page.wait_for_selector("#productTitle", timeout=5000)

        add_to_cart = page.query_selector("#add-to-cart-button")
        unavailable = page.locator("text=Currently unavailable").count() > 0

        return add_to_cart is not None and not unavailable

    except Exception:
        return False

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
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )

    page = context.new_page()

    while True:
        cycle += 1
        cycle_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        print(f"\n=== Cycle #{cycle} | {cycle_time} ===")

        # ----------------------------
        # FIRST RUN (INITIAL BASELINE)
        # ----------------------------
        if first_run:
            for item in ITEMS:
                try:
                    page.goto(item["url"], timeout=30000)
                    available = is_available(page)

                    name = item["name"]
                    state_text = "ACTIVE" if available else "INACTIVE"

                    msg = f"[INIT] {cycle_time} | {name} -> {state_text}"
                    print(msg)
                    send_discord_alert(msg)

                    status[name] = available

                except Exception as e:
                    print(f"[ERROR] {item['name']} -> {e}")

            first_run = False
            print("Baseline status stored. Monitoring started.")
            continue

        # ----------------------------
        # NORMAL MONITORING
        # ----------------------------
        changed_items = []

        for item in ITEMS:
            try:
                page.goto(item["url"], timeout=30000)
                available = is_available(page)

                name = item["name"]

                if name in status and status[name] != available:
                    changed_items.append((name, available, item["url"]))
                    status[name] = available

                elif name not in status:
                    status[name] = available

            except Exception as e:
                print(f"[ERROR] {item['name']} -> {e}")

        # ----------------------------
        # REPORTING
        # ----------------------------
        if not changed_items:
            msg = f"[CYCLE] {cycle_time} | Cycle #{cycle} | no status changes"
            print(msg)
            send_discord_alert(msg)
        else:
            for name, available, url in changed_items:
                state_text = "NOW ACTIVE" if available else "NOW INACTIVE"
                msg = f"[STATUS CHANGE] {cycle_time} | {name} | {state_text} | {url}"

                print(msg)
                send_discord_alert(msg)

                if available:
                    show_popup("ITEM AVAILABLE", msg)

        print("=" * 60)

        time.sleep(random.uniform(30, 120))