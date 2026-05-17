from motor.motor_asyncio import AsyncIOMotorClient
from enum import Enum

import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

_is_atlas = MONGO_URI.startswith("mongodb+srv")
DB_NAME = "watchdog"
COLLECTION = "monitors"

client: AsyncIOMotorClient = None


class MonitorStatus(str, Enum):
    ACTIVE = "active"
    DOWN = "down"
    PAUSED = "paused"


def get_collection():
    return client[DB_NAME][COLLECTION]


async def connect():
    global client
    kwargs = {"tls": True, "tlsAllowInvalidCertificates": True} if _is_atlas else {}
    client = AsyncIOMotorClient(MONGO_URI, **kwargs)


async def disconnect():
    global client
    if client:
        client.close()
