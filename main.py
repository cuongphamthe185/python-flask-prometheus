from flask import Flask, Response
from prometheus_client import CollectorRegistry, Gauge, generate_latest
import requests
from datetime import datetime
import os

# ===== SFTPGo API settings =====
SFTPGO_BASE_URL = os.getenv(
    "SFTPGO_BASE_URL", "https://sftp-ext.onprem.vpbank.dev/api/v2"
)
USERNAME = os.getenv(
    "SFTPGO_DEFAULT_ADMIN_USERNAME", os.getenv("SFTPGO_USERNAME", "sftp-ext")
)
PASSWORD = os.getenv("SFTPGO_DEFAULT_ADMIN_PASSWORD", os.getenv("SFTPGO_PASSWORD", ""))
VERIFY_SSL = False


def get_access_token():
    r = requests.get(
        f"{SFTPGO_BASE_URL}/token", auth=(USERNAME, PASSWORD), verify=VERIFY_SSL
    )
    r.raise_for_status()
    return r.json().get("access_token")


def get_users(token):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{SFTPGO_BASE_URL}/users", headers=headers, verify=VERIFY_SSL)
    r.raise_for_status()
    return r.json()


def get_event_rules(token):
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    r = requests.get(
        f"{SFTPGO_BASE_URL}/eventrules", headers=headers, verify=VERIFY_SSL
    )
    r.raise_for_status()
    return r.json()


# ===== Flask App =====
app = Flask(__name__)
registry = CollectorRegistry()

# Gauges
total_users_gauge = Gauge(
    "sftpgo_total_users", "Total users in the system", registry=registry
)
users_created_this_year_gauge = Gauge(
    "sftpgo_users_created_this_year",
    "Users created in the current year",
    registry=registry,
)
webhook_total_gauge = Gauge(
    "sftpgo_webhook_total", "Number of event rules with trigger = 1", registry=registry
)


@app.route("/metrics")
def metrics():
    try:
        token = get_access_token()

        # ---- Users metrics ----
        users = get_users(token)
        total_users = len(users)

        current_year = datetime.now().year
        created_this_year = 0
        for u in users:
            ts = u.get("created_at")
            if ts:
                if ts > 1e12:  # ms to s
                    ts = ts / 1000.0
                created_year = datetime.fromtimestamp(ts).year
                if created_year == current_year:
                    created_this_year += 1

        total_users_gauge.set(total_users)
        users_created_this_year_gauge.set(created_this_year)

        # ---- Event rules metrics ----
        event_rules = get_event_rules(token)
        trigger1_count = sum(1 for rule in event_rules if rule.get("trigger") == 1)
        webhook_total_gauge.set(trigger1_count)

    except Exception as e:
        print("Error in /metrics:", e)
        total_users_gauge.set(-1)
        users_created_this_year_gauge.set(-1)
        webhook_total_gauge.set(-1)

    return Response(generate_latest(registry), mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8195)
r
