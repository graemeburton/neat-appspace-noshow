import requests
import json
from datetime import datetime, timedelta
import time
import pytz
import os
from dotenv import load_dotenv

load_dotenv()

# ========================== CONFIG (from .env) ==========================
NEAT_TENANT_ID = os.getenv("NEAT_TENANT_ID")
NEAT_API_KEY = os.getenv("NEAT_API_KEY")

APPSPACE_BASE_URL = os.getenv("APPSPACE_BASE_URL", "https://api.cloud.appspace.com")
APPSPACE_SUBJECT_ID = os.getenv("APPSPACE_SUBJECT_ID")
APPSPACE_REFRESH_TOKEN = os.getenv("APPSPACE_REFRESH_TOKEN")

TIMEZONE = pytz.timezone(os.getenv("TIMEZONE", "Australia/Melbourne"))
CHECK_WINDOW_MINUTES = int(os.getenv("CHECK_WINDOW_MINUTES", "5"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL")

RESOURCE_TO_ROOM_MAP = json.loads(os.getenv("RESOURCE_TO_ROOM_MAP", "{}"))

APPSPACE_LIST_RESERVATIONS_ENDPOINT = "/api/v3/reservations"
APPSPACE_CANCEL_RESERVATION_ENDPOINT = "/api/v3/reservations/{reservation_id}/cancel"
# =====================================================================

def get_appspace_token():
    url = f"{APPSPACE_BASE_URL}/api/v3/authorization/token"
    payload = {
        "subjectType": "Application",
        "subjectId": APPSPACE_SUBJECT_ID,
        "grantType": "refreshToken",
        "refreshToken": APPSPACE_REFRESH_TOKEN
    }
    resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    resp.raise_for_status()
    return resp.json()["accessToken"]

def get_neat_sensor_data(room_id: str):
    url = f"https://api.pulse.neat.no/v1/orgs/{NEAT_TENANT_ID}/rooms/{room_id}/sensor"
    headers = {"Authorization": f"Bearer {NEAT_API_KEY}", "Accept": "application/json"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    samples = data.get("data", []) or data.get("samples", [])
    for sample in samples:
        if sample.get("occupancy") or sample.get("presence") or sample.get("occupied"):
            return True
    return False

def get_current_reservations(token: str):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    now = datetime.now(TIMEZONE)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_end = (now + timedelta(days=1)).isoformat()

    reservations = []
    for resource_id in RESOURCE_TO_ROOM_MAP.keys():
        params = {"resourceId": resource_id, "startTime": today_start, "endTime": today_end, "status": "confirmed"}
        resp = requests.get(f"{APPSPACE_BASE_URL}{APPSPACE_LIST_RESERVATIONS_ENDPOINT}", headers=headers, params=params)
        if resp.status_code == 200:
            data = resp.json()
            res_list = data.get("data", []) if isinstance(data, dict) else data
            reservations.extend(res_list)
    return reservations

def should_cancel_reservation(reservation, now_utc):
    start_str = reservation.get("startTime") or reservation.get("start") or reservation.get("startDateTime")
    if not start_str:
        return False
    start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
    if start_time.tzinfo is None:
        start_time = pytz.utc.localize(start_time)
    start_time = start_time.astimezone(pytz.utc)
    minutes_since_start = (now_utc - start_time).total_seconds() / 60
    return 0 <= minutes_since_start <= CHECK_WINDOW_MINUTES

def send_notification(message: str):
    payload = {"text": message}
    if SLACK_WEBHOOK_URL:
        requests.post(SLACK_WEBHOOK_URL, json=payload)
    if TEAMS_WEBHOOK_URL:
        requests.post(TEAMS_WEBHOOK_URL, json=payload)

def cancel_reservation(token: str, reservation_id: str, resource_name: str = "Unknown Room"):
    if DRY_RUN:
        msg = f"🔍 DRY-RUN: Would have cancelled reservation {reservation_id} in {resource_name}"
        print(msg)
        send_notification(msg)
        return

    url = f"{APPSPACE_BASE_URL}{APPSPACE_CANCEL_RESERVATION_ENDPOINT.format(reservation_id=reservation_id)}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={})

    if resp.status_code in (200, 204):
        msg = f"✅ Cancelled reservation {reservation_id} in {resource_name}"
        print(msg)
        send_notification(msg)
    else:
        msg = f"❌ Failed to cancel {reservation_id}: {resp.status_code}"
        print(msg)
        send_notification(msg)

# ====================== MAIN ======================
def run_no_show_cleanup():
    print(f"[{datetime.now(TIMEZONE)}] Starting no-show cleanup check...")
    print(f"   → Monitoring {len(RESOURCE_TO_ROOM_MAP)} rooms | Dry-run: {DRY_RUN}")

    token = get_appspace_token()
    now_utc = datetime.now(pytz.utc)

    reservations = get_current_reservations(token)

    for res in reservations:
        res_id = res.get("id") or res.get("reservationId")
        resource_id = res.get("resourceId") or res.get("resource", {}).get("id")
        resource_name = res.get("resource", {}).get("name") or resource_id or "Unknown Room"

        if not resource_id or resource_id not in RESOURCE_TO_ROOM_MAP:
            continue

        neat_room_id = RESOURCE_TO_ROOM_MAP[resource_id]

        if should_cancel_reservation(res, now_utc):
            has_presence = get_neat_sensor_data(neat_room_id)
            if not has_presence:
                print(f"🚨 No-show detected for reservation {res_id} in {resource_name} → cancelling")
                cancel_reservation(token, res_id, resource_name)
            else:
                print(f"👤 Presence detected for reservation {res_id} in {resource_name} – keeping")

    print(f"[{datetime.now(TIMEZONE)}] Cleanup finished.\n")

if __name__ == "__main__":
    run_no_show_cleanup()
    # For continuous running (Docker / cron):
    # while True:
    #     run_no_show_cleanup()
    #     time.sleep(60)