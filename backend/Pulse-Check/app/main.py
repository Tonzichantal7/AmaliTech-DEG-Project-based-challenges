import logging
logging.basicConfig(level=logging.DEBUG)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routers import monitors
from app.scheduler import start_scheduler, stop_scheduler
from app import store


@asynccontextmanager
async def lifespan(app: FastAPI):
    await store.connect()
    await start_scheduler()
    yield
    await stop_scheduler()
    await store.disconnect()


app = FastAPI(
    title="Watchdog Sentinel API",
    description="Dead Man's Switch API for CritMon Servers Inc. — tracks remote device heartbeats and fires alerts on silence.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(monitors.router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "Watchdog Sentinel", "version": "1.0.0"}
