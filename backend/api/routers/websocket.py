from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import manager
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.models.user import User as UserModel

settings = get_settings()
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: str = Query("default"),
    db: AsyncSession = Depends(get_db),
):
    selected_protocol = None
    token = None
    subprotocols: list = websocket.scope.get("subprotocols", [])
    for p in subprotocols:
        if p.startswith("night-watch."):
            token = p[len("night-watch."):]
            selected_protocol = p
            break

    if selected_protocol:
        await websocket.accept(subprotocol=selected_protocol)
    else:
        await websocket.accept()

    user = None
    if token:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            username: str = payload.get("sub")
            if username:
                result = await db.execute(
                    select(UserModel).filter(UserModel.username == username)
                )
                user = result.scalars().first()
        except JWTError:
            pass

    if not user or not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, channels=[channel] if channel != "default" else None)

    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)
