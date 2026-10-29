"""Free phone notifications via ntfy.sh (no account, no key).
Install the ntfy app, subscribe to your secret topic name, and set NTFY_TOPIC in the repo secrets."""
import logging
import os

import requests

log = logging.getLogger(__name__)


def send(title, body, priority="default"):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return
    try:
        requests.post(f"https://ntfy.sh/{topic}", data=body.encode(), timeout=10,
                      headers={"Title": title.encode("ascii", "ignore").decode(), "Priority": priority})
    except Exception as e:
        log.info("notify failed: %s", e)
