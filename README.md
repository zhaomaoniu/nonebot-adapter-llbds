<div align="center">

# NoneBot-Adapter-LLBDS

_✨ LiteLoaderBDS适配 ✨_

</div>

## Notice
The adapter uses the `thread.join()` method, causing a certain degree of blocking. Therefore, it is recommended for users to run LLBDS and NoneBot2 in the same intranet and be cautious about reducing the high-frequency usage of interfaces provided by this adapter.

## Config
| Parameter             | Type             | Description                                               | Default Value                   |
|-----------------------|------------------|-----------------------------------------------------------|---------------------------------|
| LLBDS_TOKEN           | str              | LLBDS token, used for authentication when connecting to ws | N/A                             |
| LLBDS_SERVER_ID       | Optional[str]    | LLBDS server ID, serves as Bot's self_id, can be left empty | LLBDS                         |
| LLBDS_API_URL         | Optional[str]    | LLBDS API address, e.g., `http://127.0.0.1:8081`          | http://127.0.0.1:8081        |

## Driver
DRIVER=~fastapi+~aiohttp

## LLBDS
See [LLEventBridge](https://github.com/zhaomaoniu/LLEventBridge)

## Example Plugin
```python
from nonebot import on_notice
from nonebot_adapter_llbds.event import JoinEvent

join = on_notice()

@echo.handle()
async def handle_join(event: JoinEvent):
    event.player.sendToast(f"Welcome {event.player.name}!", "hello from nonebot-adapter-llbds")
```
