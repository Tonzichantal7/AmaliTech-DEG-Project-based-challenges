from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timezone, timedelta

from app.store import get_store, Monitor, MonitorStatus
from app.schemas import CreateMonitorRequest, MonitorResponse, MessageResponse

router = APIRouter(prefix="/monitors", tags=["Monitors"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# POST /monitors  — Register a new monitor
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=MonitorResponse,
    summary="Register a new device monitor",
)
def create_monitor(body: CreateMonitorRequest):
    store = get_store()

    if body.id in store:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Monitor '{body.id}' already exists. Use heartbeat to reset it.",
        )

    now = _now()
    monitor = Monitor(
        id=body.id,
        timeout=body.timeout,
        alert_email=body.alert_email,
        created_at=now,
        deadline=now + timedelta(seconds=body.timeout),
    )
    store[body.id] = monitor
    return MonitorResponse(**monitor.to_dict())


# ─────────────────────────────────────────────────────────────────────────────
# POST /monitors/{id}/heartbeat  — Reset the countdown
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/{monitor_id}/heartbeat",
    response_model=MessageResponse,
    summary="Send a heartbeat to reset the countdown",
)
def heartbeat(monitor_id: str):
    store = get_store()
    monitor = store.get(monitor_id)

    if not monitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Monitor '{monitor_id}' not found.")

    if monitor.status == MonitorStatus.DOWN:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"Monitor '{monitor_id}' has already fired its alert (status: down). Re-register to start fresh.",
        )

    now = _now()
    monitor.last_ping_at = now
    monitor.deadline = now + timedelta(seconds=monitor.timeout)

    # Auto-unpause if it was paused (bonus feature)
    if monitor.status == MonitorStatus.PAUSED:
        monitor.status = MonitorStatus.ACTIVE

    return MessageResponse(message="Heartbeat received. Timer reset.", monitor_id=monitor_id)


# ─────────────────────────────────────────────────────────────────────────────
# POST /monitors/{id}/pause  — Pause the monitor (Bonus)
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/{monitor_id}/pause",
    response_model=MessageResponse,
    summary="Pause monitoring to avoid false alarms during maintenance",
)
def pause_monitor(monitor_id: str):
    store = get_store()
    monitor = store.get(monitor_id)

    if not monitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Monitor '{monitor_id}' not found.")

    if monitor.status == MonitorStatus.DOWN:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot pause a monitor that is already down.")

    if monitor.status == MonitorStatus.PAUSED:
        return MessageResponse(message="Monitor is already paused.", monitor_id=monitor_id)

    monitor.status = MonitorStatus.PAUSED
    monitor.deadline = None  # freeze the timer

    return MessageResponse(message="Monitor paused. No alerts will fire until the next heartbeat.", monitor_id=monitor_id)


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /monitors/{id}  — Developer's Choice: deregister a monitor
# ─────────────────────────────────────────────────────────────────────────────
@router.delete(
    "/{monitor_id}",
    response_model=MessageResponse,
    summary="[Dev Choice] Permanently deregister a monitor",
)
def delete_monitor(monitor_id: str):
    store = get_store()
    if monitor_id not in store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Monitor '{monitor_id}' not found.")

    del store[monitor_id]
    return MessageResponse(message="Monitor deregistered and removed.", monitor_id=monitor_id)


# ─────────────────────────────────────────────────────────────────────────────
# GET /monitors  — Developer's Choice: list all monitors
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "",
    response_model=list[MonitorResponse],
    summary="[Dev Choice] List all registered monitors and their current status",
)
def list_monitors():
    store = get_store()
    return [MonitorResponse(**m.to_dict()) for m in store.values()]


# ─────────────────────────────────────────────────────────────────────────────
# GET /monitors/{id}  — Developer's Choice: inspect a single monitor
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/{monitor_id}",
    response_model=MonitorResponse,
    summary="[Dev Choice] Get the current state of a specific monitor",
)
def get_monitor(monitor_id: str):
    store = get_store()
    monitor = store.get(monitor_id)
    if not monitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Monitor '{monitor_id}' not found.")
    return MonitorResponse(**monitor.to_dict())
