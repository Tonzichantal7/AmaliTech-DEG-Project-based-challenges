from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timezone, timedelta

from app.store import get_collection, MonitorStatus
from app.schemas import CreateMonitorRequest, MonitorResponse, MessageResponse

router = APIRouter(prefix="/monitors", tags=["Monitors"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_response(doc: dict) -> MonitorResponse:
    doc.pop("_id", None)
    return MonitorResponse(**doc)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MonitorResponse)
async def create_monitor(body: CreateMonitorRequest):
    col = get_collection()
    if await col.find_one({"id": body.id}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Monitor '{body.id}' already exists.")

    now = _now()
    doc = {
        "id": body.id,
        "timeout": body.timeout,
        "alert_email": body.alert_email,
        "status": MonitorStatus.ACTIVE,
        "created_at": now,
        "last_ping_at": None,
        "deadline": now + timedelta(seconds=body.timeout),
        "alert_fired": False,
    }
    await col.insert_one(doc)
    return _to_response(doc)


@router.post("/{monitor_id}/heartbeat", response_model=MessageResponse)
async def heartbeat(monitor_id: str):
    col = get_collection()
    monitor = await col.find_one({"id": monitor_id})

    if not monitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Monitor '{monitor_id}' not found.")
    if monitor["status"] == MonitorStatus.DOWN:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=f"Monitor '{monitor_id}' is down. Re-register to start fresh.")

    now = _now()
    await col.update_one(
        {"id": monitor_id},
        {"$set": {"last_ping_at": now, "deadline": now + timedelta(seconds=monitor["timeout"]), "status": MonitorStatus.ACTIVE}},
    )
    return MessageResponse(message="Heartbeat received. Timer reset.", monitor_id=monitor_id)


@router.post("/{monitor_id}/pause", response_model=MessageResponse)
async def pause_monitor(monitor_id: str):
    col = get_collection()
    monitor = await col.find_one({"id": monitor_id})

    if not monitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Monitor '{monitor_id}' not found.")
    if monitor["status"] == MonitorStatus.DOWN:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot pause a monitor that is already down.")
    if monitor["status"] == MonitorStatus.PAUSED:
        return MessageResponse(message="Monitor is already paused.", monitor_id=monitor_id)

    await col.update_one({"id": monitor_id}, {"$set": {"status": MonitorStatus.PAUSED, "deadline": None}})
    return MessageResponse(message="Monitor paused. No alerts will fire until the next heartbeat.", monitor_id=monitor_id)


@router.delete("/{monitor_id}", response_model=MessageResponse)
async def delete_monitor(monitor_id: str):
    col = get_collection()
    result = await col.delete_one({"id": monitor_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Monitor '{monitor_id}' not found.")
    return MessageResponse(message="Monitor deregistered and removed.", monitor_id=monitor_id)


@router.get("", response_model=list[MonitorResponse])
async def list_monitors():
    col = get_collection()
    return [_to_response(doc) async for doc in col.find()]


@router.get("/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(monitor_id: str):
    col = get_collection()
    monitor = await col.find_one({"id": monitor_id})
    if not monitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Monitor '{monitor_id}' not found.")
    return _to_response(monitor)
