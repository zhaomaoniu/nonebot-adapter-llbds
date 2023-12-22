import json
import asyncio
import contextlib
from typing import Any, Dict, Optional
from typing_extensions import override

from nonebot.drivers import (
    Driver,
    ASGIMixin,
    URL,
    WebSocketServerSetup,
    WebSocket,
    Request,
)
from nonebot.exception import WebSocketClosed
from nonebot.adapters import Adapter as BaseAdapter
from nonebot.internal.adapter.bot import Bot
from nonebot.utils import escape_tag

from .bot import Bot
from .config import Config
from .event import *
from .log import log
from .model import LLSEObject
from .exception import NetworkError


class Adapter(BaseAdapter):
    @override
    def __init__(self, driver: Driver, **kwargs: Any):
        super().__init__(driver, **kwargs)
        self.llbds_config: Config = Config(**self.config.dict())
        self.server_id = self.llbds_config.llbds_server_id
        self.bots: Dict[str, Bot] = {}
        self.ws: Optional[WebSocket] = None
        self._api_ret_dict = {}

        self.setup()

    @classmethod
    @override
    def get_name(cls) -> str:
        """适配器名称"""
        return "LLBDS"

    def setup(self) -> None:
        if not isinstance(self.driver, ASGIMixin):
            raise RuntimeError(
                f"Current driver {self.config.driver} does not support websocket server! "
                f"{self.get_name()} Adapter need a ASGIMixin Driver to work."
            )

        ws_setup = WebSocketServerSetup(
            URL("/llbds/"), f"{self.get_name()} WS", self._handle_ws
        )
        self.setup_websocket_server(ws_setup)

    async def _handle_ws(self, ws: WebSocket) -> None:
        await ws.accept()

        meta_pack: dict = json.loads(await ws.receive())

        if (token := meta_pack.get("token")) is None:
            await ws.close(1008, "Missing Authorization Header")

        llbds_token = self.llbds_config.llbds_token
        if llbds_token and llbds_token != token:
            msg = (
                "Authorization Header is invalid"
                if token
                else "Missing Authorization Header"
            )
            log("WARNING", msg)
            await ws.close(1008, msg)
            return None

        self.ws = ws
        self.bots[self.server_id] = Bot(self, self.server_id)
        self.bot_connect(self.bots[self.server_id])

        log("INFO", f"<y>Bot {escape_tag(self.server_id)}</y> connected")

        try:
            while True:
                data = await ws.receive()
                json_data = json.loads(data)

                if event := (await self.json_to_event(json_data)):
                    asyncio.create_task(self.bots[self.server_id].handle_event(event))

        except WebSocketClosed:
            log(
                "WARNING",
                f"WebSocket for Bot {escape_tag(self.server_id)} closed by peer",
            )
        except Exception as e:
            log(
                "ERROR",
                "<r><bg #f8bbd0>Error while process data from websocket "
                f"for bot {escape_tag(self.server_id)}.</bg #f8bbd0></r>",
                e,
            )
        finally:
            if self.bots.get(self.server_id):
                self.bot_disconnect(self.bots[self.server_id])
            with contextlib.suppress(Exception):
                await self.ws.close()

    async def json_to_event(self, data: dict) -> Optional[Event]:
        if not data.get("event_name"):
            return None

        if data["event_name"] == "Heartbeat":
            return None

        for obj_data in data["objects"]:
            data[f'_{obj_data["type"]}'] = LLSEObject(
                self, obj_data["index"], obj_data.get("name", None)
            )

        for direct_data in data["direct_data"]:
            data[direct_data["type"]] = direct_data["value"]

        data.pop("objects")
        data.pop("direct_data")

        if data["event_name"] == "PreJoin":
            return PreJoinEvent.parse_obj(data)
        if data["event_name"] == "Join":
            return JoinEvent.parse_obj(data)
        if data["event_name"] == "Left":
            return LeftEvent.parse_obj(data)
        if data["event_name"] == "Respawn":
            return RespawnEvent.parse_obj(data)
        if data["event_name"] == "PlayerDie":
            return PlayerDieEvent.parse_obj(data)
        if data["event_name"] == "PlayerCmd":
            return PlayerCmdEvent.parse_obj(data)
        if data["event_name"] == "Chat":
            return MessageEvent.parse_obj(data)

    async def _call_api(self, bot: Bot, api: str, **data: Any) -> Any:
        request = Request(
            "GET",
            f"{self.llbds_config.llbds_api_url}/llbds/{api}",
            params=data,
            headers={"Authorization": self.llbds_config.llbds_token},
            timeout=self.config.api_timeout,
        )
        response = await self.request(request)

        try:
            return json.loads(response.content)["data"]
        except asyncio.TimeoutError:
            raise NetworkError(f"Call api {api} timeout") from None
