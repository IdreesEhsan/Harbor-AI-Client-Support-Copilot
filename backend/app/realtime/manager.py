import asyncio
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


logger = logging.getLogger(
    "harbor.realtime"
)


class NotificationConnectionManager:
    """
    Maintain active Harbor WebSocket connections.

    Customers:
        stored by Harbor user ID.

    Staff:
        support_agent/admin sockets share one pool.

    Important:
        This works correctly with one FastAPI process.

        If Harbor later uses multiple workers/containers,
        use Redis Pub/Sub or another shared event broker.
    """

    def __init__(
        self,
    ) -> None:
        self._customer_connections: dict[
            str,
            set[WebSocket],
        ] = defaultdict(set)

        self._staff_connections: set[
            WebSocket
        ] = set()

        self._lock = asyncio.Lock()


    async def register(
        self,
        *,
        websocket: WebSocket,
        user_id: str,
        role: str,
    ) -> None:
        async with self._lock:

            if role == "customer":
                self._customer_connections[
                    user_id
                ].add(
                    websocket
                )

            elif role in {
                "support_agent",
                "admin",
            }:
                self._staff_connections.add(
                    websocket
                )

            else:
                raise ValueError(
                    "Unsupported realtime role."
                )


        logger.info(
            (
                "Realtime registered | "
                "user_id=%s | role=%s"
            ),
            user_id,
            role,
        )


    async def disconnect(
        self,
        *,
        websocket: WebSocket,
        user_id: str,
        role: str,
    ) -> None:
        async with self._lock:

            if role == "customer":
                connections = (
                    self
                    ._customer_connections
                    .get(
                        user_id
                    )
                )

                if connections:
                    connections.discard(
                        websocket
                    )

                    if not connections:
                        self._customer_connections.pop(
                            user_id,
                            None,
                        )

            elif role in {
                "support_agent",
                "admin",
            }:
                self._staff_connections.discard(
                    websocket
                )


        logger.info(
            (
                "Realtime disconnected | "
                "user_id=%s | role=%s"
            ),
            user_id,
            role,
        )


    async def send_to_customer(
        self,
        *,
        user_id: str,
        payload: dict[str, Any],
    ) -> None:
        async with self._lock:
            sockets = list(
                self
                ._customer_connections
                .get(
                    user_id,
                    set(),
                )
            )


        if not sockets:
            return


        dead_sockets = []


        for websocket in sockets:

            try:
                await websocket.send_json(
                    payload
                )

            except Exception:
                dead_sockets.append(
                    websocket
                )


        if dead_sockets:

            async with self._lock:

                current = (
                    self
                    ._customer_connections
                    .get(
                        user_id
                    )
                )

                if current:

                    for websocket in dead_sockets:
                        current.discard(
                            websocket
                        )

                    if not current:
                        self._customer_connections.pop(
                            user_id,
                            None,
                        )


    async def send_to_staff(
        self,
        *,
        payload: dict[str, Any],
    ) -> None:
        async with self._lock:
            sockets = list(
                self._staff_connections
            )


        if not sockets:
            return


        dead_sockets = []


        for websocket in sockets:

            try:
                await websocket.send_json(
                    payload
                )

            except Exception:
                dead_sockets.append(
                    websocket
                )


        if dead_sockets:

            async with self._lock:

                for websocket in dead_sockets:
                    self._staff_connections.discard(
                        websocket
                    )


notification_manager = (
    NotificationConnectionManager()
)