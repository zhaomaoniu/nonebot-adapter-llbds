import json
import asyncio
import contextlib
from typing import Any, Optional
from typing_extensions import override

from nonebot.drivers import Driver, ASGIMixin, URL, WebSocketServerSetup, WebSocket
from nonebot.exception import WebSocketClosed
from nonebot.adapters import Adapter as BaseAdapter
from nonebot.internal.adapter.bot import Bot
from nonebot.utils import escape_tag

from .bot import Bot
from .config import Config
from .event import *
from .log import log
from .store import ResultStore
from .model import LLSEObject
from .exception import NetworkError


class Adapter(BaseAdapter):
    @override
    def __init__(self, driver: Driver, **kwargs: Any):
        super().__init__(driver, **kwargs)
        self.llbds_config: Config = Config(**self.config.dict())
        self.bot: Optional[Bot] = None
        self._api_ret_dict = {}
        self._store = ResultStore()

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

        token = json.loads(await ws.receive())["token"]

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
        self.bot = Bot(self, self.llbds_config.llbds_server_id)

        log("INFO", f"<y>Bot {escape_tag(self.bot.self_id)}</y> connected")

        try:
            while True:
                data = await ws.receive()
                json_data = json.loads(data)
                if "echo" in json_data:
                    self._store.add_result(json_data)
                    log("DEBUG", f"Receive echo {json_data}")
                    continue

                if event := self.json_to_event(json_data):
                    asyncio.create_task(self.bot.handle_event(event))

        except WebSocketClosed:
            log(
                "WARNING",
                f"WebSocket for Bot {escape_tag(self.bot.self_id)} closed by peer",
            )
        except Exception as e:
            log(
                "ERROR",
                "<r><bg #f8bbd0>Error while process data from websocket "
                f"for bot {escape_tag(self.bot.self_id)}.</bg #f8bbd0></r>",
                e,
            )
        finally:
            self.bot_disconnect(self.bot)
            with contextlib.suppress(Exception):
                await self.ws.close()

    def json_to_event(self, data: dict) -> Optional[Event]:
        if not data.get("event_name"):
            return None

        for obj_data in data["objects"]:
            data[f'_{obj_data["type"]}'] = LLSEObject(self, obj_data["index"])
        
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
        seq = self._store.get_seq()
        json_data = json.dumps(
            {"api": api, "data": data, "echo": str(seq)},
        )
        log("DEBUG", f"Calling API {api} with data {data}")
        await self.ws.send(json_data)

        try:
            return (await self._store.fetch(seq, self.config.api_timeout))["data"]
        except asyncio.TimeoutError:
            raise NetworkError(f"WebSocket call api {api} timeout") from None
