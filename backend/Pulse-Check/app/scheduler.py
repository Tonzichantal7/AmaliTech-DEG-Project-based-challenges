import asyncio
import logging
from datetime import datetime, timezone

from app.store import get_store, MonitorStatus
from app.alerts import fire_alert

logger = logging.getLogger("watchdog.scheduler")

_task: asyncio.Task = None
TICK_INTERVAL = 1  # seconds


async def _check_loop():
    """Main loop: every tick, inspect all active monitors."""
    while True:
        await asyncio.sleep(TICK_INTERVAL)
        now = datetime.now(timezone.utc)
        store = get_store()

        for monitor in list(store.values()):
            if monitor.status != MonitorStatus.ACTIVE:
                continue
            if monitor.deadline and now >= monitor.deadline and not monitor.alert_fired:
                monitor.status = MonitorStatus.DOWN
                monitor.alert_fired = True
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
