import asyncio
import logging
from datetime import datetime, timezone

from app.store import get_collection, MonitorStatus
from app.alerts import fire_alert

logger = logging.getLogger("watchdog.scheduler")

_task: asyncio.Task = None
TICK_INTERVAL = 1


async def _check_loop():
    while True:
        await asyncio.sleep(TICK_INTERVAL)
        now = datetime.now(timezone.utc)
        col = get_collection()

        async for monitor in col.find({"status": MonitorStatus.ACTIVE, "alert_fired": False}):
            if monitor.get("deadline") and now >= monitor["deadline"]:
                await col.update_one(
                    {"id": monitor["id"]},
                    {"$set": {"status": MonitorStatus.DOWN, "alert_fired": True}},
                )
                await fire_alert(monitor)


async def start_scheduler():
    global _task
    _task = asyncio.create_task(_check_loop())
    logger.info("Watchdog scheduler started.")


async def stop_scheduler():
    global _task
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    logger.info("Watchdog scheduler stopped.")
