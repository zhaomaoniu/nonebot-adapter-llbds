import re
import json
from typing import TYPE_CHECKING, Any, Union, Set
from typing_extensions import override

from nonebot.message import handle_event
from nonebot.adapters import Bot as BaseBot

from .event import Event, MessageEvent
from .log import log
from .message import Message, MessageSegment

if TYPE_CHECKING:
    from llpy.types import T_RunCmdExRet
    from .adapter import Adapter


def _check_nickname(event: Event, nickname: Set[str]):
    if not isinstance(event, MessageEvent):
        return None

    if not event.get_message():
        event.message.append(MessageSegment.text(""))

    first_msg_seg = event.message[0]

    nicknames = {re.escape(n) for n in nickname}
    if not nicknames:
        return None

    nickname_regex = "|".join(nicknames)
    first_text = first_msg_seg.data["text"]
    if m := re.search(rf"^({nickname_regex})([\s,，]*|$)", first_text, re.IGNORECASE):
        event.to_me = True
        first_msg_seg.data["text"] = first_text[m.end() :]


class Bot(BaseBot):
    """
    LLBDS 协议 Bot 适配。
    """

    @override
    def __init__(self, adapter: "Adapter", self_id: str, **kwargs: Any):
        super().__init__(adapter, self_id)
        self.adapter: "Adapter" = adapter
        # 一些有关 Bot 的信息也可以在此定义和存储

    async def handle_event(self, event: Event):
        _check_nickname(event, self.adapter.config.nickname)
        await handle_event(self, event)

    @override
    async def send(
        self,
        event: Event,
        message: Union[str, Message, MessageSegment],
        **kwargs: Any,
    ) -> Any:
        if kwargs.get("all_server") is True:
            await self.send_server_message(message)
        elif hasattr(event, "player"):
            await self.send_player_message(message, event.player.name)
        else:
            log("WARNING", "获取玩家信息失败，将发送全服消息")
            await self.send_server_message(message)

    async def send_server_message(self, message: Union[str, Message, MessageSegment]):
        raw_json = json.dumps({"rawtext": [{"text": str(message)}]})
        await self.call_api("runcmdEx", cmd=f"tellraw @a {raw_json}")

    async def send_player_message(
        self, message: Union[str, Message, MessageSegment], player_name: str
    ):
        raw_json = json.dumps({"rawtext": [{"text": str(message)}]})
        await self.call_api("runcmdEx", cmd=f"tellraw {player_name} {raw_json}")

    async def runcmd(self, cmd: str) -> bool:
        return await self.call_api("runcmd", cmd=cmd)

    async def runcmdEx(self, cmd: str) -> "T_RunCmdExRet":
        return await self.call_api("runcmdEx", cmd=cmd)
