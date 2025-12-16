from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import websockets

from ps_agent.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ShowdownClientConfig:
    server_url: str
    username: str
    password: Optional[str] = None
    room: Optional[str] = None
    heartbeat_interval: float = 15.0


class ShowdownClient:
    """Thin async connector to a Showdown server or simulator."""

    def __init__(self, config: ShowdownClientConfig) -> None:
        self.config = config
        self._ws: Optional[websockets.WebSocketClientProtocol] = None

    async def __aenter__(self) -> "ShowdownClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def connect(self) -> None:
        logger.info("connecting_showdown", url=self.config.server_url)
        self._ws = await websockets.connect(self.config.server_url)
        # Authentication protocol should be handled here when integrating with real server.

    async def close(self) -> None:
        if self._ws:
            await self._ws.close()
            logger.info("showdown_connection_closed")
            self._ws = None

    async def send(self, message: str) -> None:
        if not self._ws:
            raise RuntimeError("Websocket not connected")
        logger.debug("sending_message", message=message)
        await self._ws.send(message)

    async def messages(self) -> AsyncIterator[str]:
        if not self._ws:
            raise RuntimeError("Websocket not connected")
        async for message in self._ws:
            yield message
