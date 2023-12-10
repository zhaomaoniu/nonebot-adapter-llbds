<div align="center">

# NoneBot-Adapter-LLBDS

_✨ LiteLoaderBDS适配 ✨_

</div>

## 注意事项
适配器使用 `thread.join()` 方法，会导致一定程度的阻塞。因此，建议用户在内网中运行 LLBDS 和 NoneBot2，并减少适配器提供的接口的高频使用

适配器目前尚未完善，欢迎在 bot.py 中补充 API (LLEventBridge那边也是)，在 event.py 中补充事件！

## 配置
| 参数                   | 类型              | 描述                                                   | 默认值                         |
|-----------------------|-------------------|--------------------------------------------------------|--------------------------------|
| LLBDS_TOKEN           | str             | LLBDS令牌，用于连接ws时进行身份验证                        | 无                             |
| LLBDS_SERVER_ID       | Optional[str]       | LLBDS服务器ID，作为机器人的self_id，可留空                 | LLBDS                         |
| LLBDS_API_URL         | Optional[str]       | LLBDS API地址，例如 `http://127.0.0.1:8081`              | http://127.0.0.1:8081        |

## 驱动
DRIVER=~fastapi+~aiohttp

## LLBDS
参阅 [LLEventBridge](https://github.com/zhaomaoniu/LLEventBridge)

## 示例插件
```python
from nonebot import on_notice, on_command
from nonebot.params import CommandArg
from nonebot.log import logger
from nonebot_adapter_llbds.event import JoinEvent, MessageEvent
from nonebot_adapter_llbds.message import Message


notice = on_notice()
echo = on_command("echo", aliases={"回声"})


@notice.handle()
async def handle_join(event: JoinEvent):
    event.player.sendText("Hello, world!")


@echo.handle()
async def handle_echo(event: MessageEvent, message: Message = CommandArg()):
    await echo.send(message)
    logger.info(f"玩家 {event.player.name} 发送了 {event.message}")

```
