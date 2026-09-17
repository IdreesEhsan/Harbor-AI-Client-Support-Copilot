import asyncio
import logging

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)

from jwt import (
    ExpiredSignatureError,
    InvalidTokenError,
)

from app.db.supabase import (
    get_supabase_client,
)

from app.realtime.manager import (
    notification_manager,
)

from app.services.auth import (
    decode_access_token,
)


router = APIRouter()

logger = logging.getLogger(
    "harbor.realtime.api"
)


def authenticate_realtime_token(
    token: str,
) -> dict | None:
    if not isinstance(
        token,
        str,
    ):
        return None


    token = token.strip()


    if not token:
        return None


    try:
        payload = (
            decode_access_token(
                token
            )
        )


        user_id = (
            payload.get(
                "sub"
            )
        )


        if not user_id:
            return None


    except (
        ExpiredSignatureError,
        InvalidTokenError,
    ):
        return None


    client = (
        get_supabase_client()
    )


    response = (
        client
        .table("users")
        .select(
            (
                "id,"
                "email,"
                "full_name,"
                "age,"
                "country,"
                "is_active,"
                "role"
            )
        )
        .eq(
            "id",
            user_id,
        )
        .limit(1)
        .execute()
    )


    if not response.data:
        return None


    user = (
        response.data[0]
    )


    if not user.get(
        "is_active"
    ):
        return None


    if user.get(
        "role"
    ) not in {
        "customer",
        "support_agent",
        "admin",
    }:
        return None


    return user


@router.websocket(
    "/ws/notifications"
)
async def notification_websocket(
    websocket: WebSocket,
):
    """
    Harbor realtime notification connection.

    Client connects once and immediately sends:

        {
            "type": "authenticate",
            "token": "..."
        }

    After authentication the socket stays idle until
    a real notification needs to be pushed.
    """

    await websocket.accept()


    user_id = None
    role = None


    try:
        authentication_message = (
            await asyncio.wait_for(
                websocket.receive_json(),
                timeout=10,
            )
        )


        if (
            authentication_message.get(
                "type"
            )
            != "authenticate"
        ):
            await websocket.send_json(
                {
                    "type":
                        "authentication_error",

                    "message":
                        "Realtime authentication is required.",
                }
            )

            await websocket.close(
                code=4401
            )

            return


        token = str(
            authentication_message.get(
                "token",
                "",
            )
        )


        user = (
            authenticate_realtime_token(
                token
            )
        )


        if user is None:

            await websocket.send_json(
                {
                    "type":
                        "authentication_error",

                    "message":
                        "Realtime authentication failed.",
                }
            )

            await websocket.close(
                code=4401
            )

            return


        user_id = str(
            user["id"]
        )

        role = str(
            user["role"]
        )


        await notification_manager.register(
            websocket=websocket,
            user_id=user_id,
            role=role,
        )


        await websocket.send_json(
            {
                "type":
                    "ready",

                "role":
                    role,
            }
        )


        while True:
            message = (
                await websocket.receive_json()
            )


            if (
                message.get(
                    "type"
                )
                == "ping"
            ):
                await websocket.send_json(
                    {
                        "type":
                            "pong",
                    }
                )


    except asyncio.TimeoutError:

        try:
            await websocket.close(
                code=4401
            )

        except Exception:
            pass


    except WebSocketDisconnect:
        pass


    except Exception:
        logger.exception(
            "Unexpected realtime WebSocket error."
        )


    finally:

        if (
            user_id
            and role
        ):
            await notification_manager.disconnect(
                websocket=websocket,
                user_id=user_id,
                role=role,
            )