import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("watchdog.alerts")


async def fire_alert(monitor) -> None:
    """
    Fire an alert for a monitor that has gone silent.
    Currently logs a critical JSON payload; extend to send email/webhook here.
    """
    last_ping = monitor.get("last_ping_at") if isinstance(monitor, dict) else monitor.last_ping_at
    payload = {
        "ALERT": f"Device {monitor['id'] if isinstance(monitor, dict) else monitor.id} is down!",
        "device_id": monitor["id"] if isinstance(monitor, dict) else monitor.id,
        "alert_email": monitor["alert_email"] if isinstance(monitor, dict) else monitor.alert_email,
        "timeout_seconds": monitor["timeout"] if isinstance(monitor, dict) else monitor.timeout,
        "last_ping_at": last_ping.isoformat() if last_ping else None,
        "time": datetime.now(timezone.utc).isoformat(),
    }

    # ── Core requirement: console.log equivalent ──────────────────────────────
    print(json.dumps(payload, indent=2))
    logger.critical(json.dumps(payload))

    # ── Extension point: send email / post webhook ────────────────────────────
    # Uncomment and configure to send a real email via SMTP or a webhook POST.
    #
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     await client.post(
    #         "https://your-webhook-url.example.com/alert",
    #         json=payload,
    #     )
    #
    # Or with smtplib for email:
    # send_email(to=monitor.alert_email, subject="[CritMon] Device Down", body=json.dumps(payload))
