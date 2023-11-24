import json
import queue
import asyncio
import threading
from typing import Any, Dict, Optional, TYPE_CHECKING
from nonebot.drivers import Request

from .log import log
from .exception import NetworkError

if TYPE_CHECKING:
    from .adapter import Adapter


class LLSEObject:
    def __init__(self, adapter: "Adapter", index: int):
        self._adapter = adapter
        self._index = index

    async def _get_llbds_result(
        self, attr: str, result_queue: queue.Queue, args: tuple, kwargs: Dict[str, Any]
    ):
        request = Request(
            "GET",
            f"{self._adapter.llbds_config.llbds_api_url}/llbds/get_attr",
            params={
                "content": json.dumps(
                    {"index": self._index, "args": args, "kwargs": kwargs, "attr": attr}
                )
            },
            headers={"Authorization": self._adapter.llbds_config.llbds_token},
            timeout=self._adapter.config.api_timeout,
        )
        resp = await self._adapter.request(request)

        if resp.status_code == 500:
            # 错误请求导致的，不raise
            return None
        
        if resp.status_code == 400:
            # 请求函数时候的参数错误
            return self.__getattribute__(attr)(*args, **kwargs)

        if resp.status_code != 200:
            raise NetworkError(f"Failed to get attr {attr} from LLBDS!")

        try:
            result = json.loads(resp.content)["data"]
        except json.JSONDecodeError:
            log("WARNING", "Failed to decode LLBDS result!")
            return None

        if isinstance(result, (str, int, float)):
            result_queue.put(result)
            return None
        elif isinstance(result, dict):
            result_queue.put(LLSEObject(self._adapter, result["index"]))
            return None
        raise ValueError("Invalid return value from LLBDS!")

    def _run_sync(self, attr: str, *args, **kwargs):
        result_queue = queue.Queue()

        thread = threading.Thread(
            target=asyncio.run,
            args=(self._get_llbds_result(attr, result_queue, args, kwargs),),
            daemon=True,
        )
        thread.start()
        thread.join()
        return result_queue.get()

    def __getattribute__(self, name: str):
        if name.startswith("_"):  # 避免内部属性触发递归调用
            return object.__getattribute__(self, name)

        return self._run_sync(name)
