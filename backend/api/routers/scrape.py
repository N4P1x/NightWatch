"""
Night-Watch Scrape API Router
Endpoints for triggering, monitoring, and controlling scraping operations.
"""

import asyncio

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_active_user, log_audit, manager, require_roles
from backend.core.config import get_settings
from backend.core.database import AsyncSessionLocal, get_db
from backend.models.user import User as UserModel
from backend.services.scrape_service import ScrapeService

settings = get_settings()
router = APIRouter(prefix="/api/v1/scrape", tags=["Scraping"])


@router.get("/status")
async def get_scrape_status(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = ScrapeService(db)
    return await service.get_stats()


@router.get("/health")
async def get_scrape_health(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = ScrapeService(db)
    return await service.get_health()


@router.post("/trigger")
async def trigger_scrape(
    source_id: int = Query(None, description="Specific source ID to scrape"),
    max_urls: int = Query(50, ge=1, le=500, description="Max URLs to scrape"),
    max_concurrent: int = Query(5, ge=1, le=50, description="Max concurrent requests"),
    current_user: UserModel = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    service = ScrapeService(db)
    result = await service.trigger_scrape(
        source_id=source_id,
        max_urls=max_urls,
        max_concurrent=max_concurrent,
    )

    await log_audit(db, current_user.id, "trigger_scrape", "scrape", details=f"Triggered scrape: {result}")

    return result


@router.post("/stop")
async def stop_scrape(
    current_user: UserModel = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    service = ScrapeService(db)
    result = await service.stop_scrape()

    await log_audit(db, current_user.id, "stop_scrape", "scrape", details="Stopped scrape operation")

    return result


@router.websocket("/ws/stats")
async def scrape_stats_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time scrape statistics."""
    subprotocols = websocket.scope.get("subprotocols", [])
    selected = next((p for p in subprotocols if p.startswith("night-watch.")), None)
    await websocket.accept(subprotocol=selected)
    token = selected[len("night-watch."):] if selected else None
    if not token:
        token = websocket.cookies.get("access_token")
    if token:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            username: str = payload.get("sub")
            if username:
                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(UserModel).filter(UserModel.username == username))
                    user = result.scalars().first()
                    if user and user.is_active:
                        await manager.connect(websocket, channels=["scrape"])
                        try:
                            while True:
                                async with AsyncSessionLocal() as session:
                                    service = ScrapeService(session)
                                    stats = await service.get_stats()
                                    await websocket.send_json(stats)
                                await asyncio.sleep(5)
                        except WebSocketDisconnect:
                            await manager.disconnect(websocket)
                        except Exception:
                            await manager.disconnect(websocket)
                        return
        except JWTError:
            pass
    await websocket.close(code=1008)
