from copy import copy
from datetime import datetime
from typing import Optional, Any, TYPE_CHECKING
from typing_extensions import override

from nonebot.adapters import Event as BaseEvent
from nonebot.utils import escape_tag

from .message import Message

if TYPE_CHECKING:
    from llpy import Player, Entity


class Event(BaseEvent):
    event_name: str

    @override
    def get_event_name(self) -> str:
        return self.event_name

    @override
    def get_event_description(self) -> str:
        return escape_tag(repr(self.dict()))

    @override
    def get_message(self):
        raise ValueError("Event has no message!")

    @override
    def get_user_id(self) -> str:
        raise ValueError("Event has no context!")

    @override
    def get_session_id(self) -> str:
        raise ValueError("Event has no context!")

    @override
    def is_tome(self) -> bool:
        return False

    # TODO
    @property
    def time(self) -> datetime:
        # 在事件实例化时，自动设置时间
        ...


class PlayerEvent(Event):
    event_name: str
    _player: Any

    @property
    def player(self) -> "Player":
        return self._player

    @override
    def get_type(self) -> str:
        return "notice"

    @override
    def get_user_id(self) -> str:
        return self.player.xuid

    @override
    def get_session_id(self) -> str:
        return f"{self.event_name.lower()}_{self.player.xuid}"


class PreJoinEvent(PlayerEvent):
    event_name: str = "Prejoin"

    @override
    def get_event_description(self) -> str:
        return f"玩家 {self.player.name} 正在加入游戏"


class JoinEvent(PlayerEvent):
    event_name: str = "Join"

    @override
    def get_event_description(self) -> str:
        return f"玩家 {self.player.name} 加入了游戏"


class LeftEvent(PlayerEvent):
    event_name: str = "Left"

    @override
    def get_event_description(self) -> str:
        return f"玩家 {self.player.name} 离开了游戏"


class RespawnEvent(PlayerEvent):
    event_name: str = "Respawn"

    @override
    def get_event_description(self) -> str:
        return f"玩家 {self.player.name} 重生"


class PlayerDieEvent(PlayerEvent):
    event_name: str = "PlayerDie"
    _source: Optional[Any]

    @property
    def source(self) -> Optional["Entity"]:
        return self._source

    @override
    def get_event_description(self) -> str:
        return (
            f"玩家 {self.player.name} 死亡"
            if self.source.name is None
            else f"玩家 {self.player.name} 因 {self.source.name} 死亡"
        )


class PlayerCmdEvent(PlayerEvent):
    event_name: str = "PlayerCmd"
    cmd: str

    @override
    def get_event_description(self) -> str:
        return f"玩家 {self.player.name} 执行了 {self.cmd}"

    @override
    def get_message(self):
        return self.cmd


class MessageEvent(PlayerEvent):
    if TYPE_CHECKING:
        message: Message
        original_message: Message

    event_name: str = "Chat"
    content: str
    to_me: bool = False
    reply: Any = None
    message_id: str = ""


    @override
    def get_type(self) -> str:
        return "message"

    @override
    def get_event_description(self) -> str:
        return f"玩家 {self.player.name} 发送了消息 {self.content}"

    @override
    def get_message(self) -> Message:
        if not hasattr(self, "message"):
            msg = Message(self.content)
            setattr(self, "message", msg)
            setattr(self, "original_message", copy(msg))
        return getattr(self, "message")
