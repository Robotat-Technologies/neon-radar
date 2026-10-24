"""Calling the app in tests without a server or a lifespan (PHASE-4.md M4.1)."""

import asyncio
from typing import Any

import httpx
from fastapi import FastAPI

BASE = "http://127.0.0.1:8000"


def call(app: FastAPI, method: str, path: str, base: str = BASE, **kwargs: Any) -> httpx.Response:
    async def go() -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url=base) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(go())
