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
    }
]

# Original logging webhook
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1501086028042342481/Vsq-rZPxZeO0-1JwzFqv6jOBOmg2bo_mAsLTKSaIoFIEkS2UAnc9AJnhRsMIrR-vM8JD"

# NEW: alert webhook + user ping
DISCORD_WEBHOOK_URL_ALERT = "https://discord.com/api/webhooks/1501398425084624947/ui96sjHQ8hdBCcHwHnCafCpP5Zm26cs0cJFhuMcKe4I4QkSuCyz5X8jGuK6N0WDb7Kat"
DISCORD_USER_ID = "652031558210813961"  # replace with your actual user ID
DISCORD_USER_ID2 = "359832173882245120"

# ----------------------------
# DISCORD
# ----------------------------
def send_discord_alert(message: str):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10)
    except Exception as e:
        print(f"[ERROR] Discord webhook failed: {e}")

def send_discord_ping(message: str):
    try:
        payload = {
            "content": f"<@{DISCORD_USER_ID}>, <@{DISCORD_USER_ID2}> {message}"
        }
        requests.post(DISCORD_WEBHOOK_URL_ALERT, json=payload, timeout=10)
    except Exception as e:
        print(f"[ERROR] Discord ping webhook failed: {e}")

# ----------------------------
# AVAILABILITY CHECK
# ----------------------------
def is_available(page) -> bool:
    try:
        page.wait_for_selector("#productTitle", timeout=5000)

        purchase_signals = [
            "#add-to-cart-button",
            "#buy-now-button",
            "#preorder-button",
        ]

        for selector in purchase_signals:
            if page.query_selector(selector):
                return True

        if page.locator("text=See All Buying Options").count() > 0:
            return True

        if page.locator("text=Pre-order").count() > 0:
            return True

        if page.locator("text=Currently unavailable").count() > 0:
            return False

        return False

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
# WORKER FUNCTION
# ----------------------------
def monitor_worker(worker_id, item):
    local_status = None
    first_run = True
    cycle = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )
        page = context.new_page()

        while True:
            cycle += 1
            print("=" * 60)
            cycle_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            name = item["name"]
            url = item["url"]

            print(f"[Worker {worker_id}] Cycle #{cycle} | {cycle_time} | {name}")

            try:
                page.goto(url, timeout=30000)
                available = is_available(page)
                state_text = "ACTIVE" if available else "INACTIVE"

                # FIRST RUN
                if first_run:
                    msg = f"[INIT][W{worker_id}] {cycle_time} | {name} -> {state_text}"
                    print(msg)
                    send_discord_alert(msg)

                    local_status = available
                    first_run = False

                # STATUS CHANGE
                elif local_status != available:
                    state_text = "NOW ACTIVE" if available else "NOW INACTIVE"
                    msg = f"[CHANGE][W{worker_id}] {cycle_time} | {name} | {state_text} | {url}"

                    print(msg)
                    send_discord_alert(msg)

                    # ✅ ONLY ping when item becomes available
                    if available:
                        send_discord_ping(msg)
                        show_popup("ITEM AVAILABLE", msg)

                    local_status = available

                    if available:
                        show_popup("ITEM AVAILABLE", msg)

                # NO CHANGE
                else:
                    msg = f"[W{worker_id}] {cycle_time} | Cycle #{cycle} | no changes"
                    print(msg)
                    send_discord_alert(msg)

            except Exception as e:
                print(f"[Worker {worker_id} ERROR] {name} -> {e}")

            print("=" * 60)
            time.sleep(random.uniform(30, 120))

# ----------------------------
# START WORKERS
# ----------------------------
if __name__ == "__main__":
    threads = []

    for i, item in enumerate(ITEMS):
        t = threading.Thread(
            target=monitor_worker,
            args=(i + 1, item),
            daemon=True
        )
        t.start()
        threads.append(t)

        time.sleep(10)

    while True:
        time.sleep(1)