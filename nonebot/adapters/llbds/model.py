import json
import queue
import asyncio
import threading
from typing import Any, Dict, Optional, Callable, TYPE_CHECKING
from nonebot.drivers import Request

from .log import log
from .exception import NetworkError, LLBDSInternalError

if TYPE_CHECKING:
    from .adapter import Adapter


class LLSEObject:
    def __init__(
        self, adapter: "Adapter", index: int, name: Optional[str] = None
    ) -> None:
        self._adapter = adapter
        self._index = index
        self._name = name
        self._types = {}

    async def _get_llbds_result(
        self, result_queue: queue.Queue, attr: str, *args, **kwargs
    ) -> None:
        request = Request(
            "GET",
            f"{self._adapter.llbds_config.llbds_api_url}/llbds/_get_attr",
            params={
                "content": json.dumps(
                    {"index": self._index, "args": args, "kwargs": kwargs, "attr": attr}
                )
            },
            headers={"Authorization": self._adapter.llbds_config.llbds_token},
            timeout=self._adapter.config.api_timeout,
        )
        try:
            resp = await self._adapter.request(request)
        except Exception:
            result_queue.put(None)
            raise NetworkError("Failed to request LLBDS, check your config!")

        if resp.status_code == 500:
            # 错误请求导致的，不raise
            result_queue.put(None)
            return None

        if resp.status_code == 400:
            # 请求函数时候的参数错误
            result_queue.put(None)
            return self.__getattribute__(attr)(*args, **kwargs)

        if resp.status_code != 200:
            result_queue.put(None)
            raise NetworkError(
                f"Failed to get attr {attr} from LLBDS! Status code: {resp.status_code}"
            )

        try:
            result = json.loads(resp.content)["data"]
        except json.JSONDecodeError:
            log("WARNING", "Failed to decode LLBDS result!")
            result_queue.put(None)
            return None

        if isinstance(result, (str, int, float)):
            result_queue.put(result)
            return None
        elif isinstance(result, dict):
            result_queue.put(LLSEObject(self._adapter, result["index"]))
            return None
        result_queue.put(None)
        raise ValueError("Invalid return value from LLBDS!")

    async def _get_type(self, result_queue: queue.Queue, name: str) -> None:
        request = Request(
            "GET",
            f"{self._adapter.llbds_config.llbds_api_url}/llbds/_get_type",
            params={"content": json.dumps({"index": self._index, "name": name})},
            headers={"Authorization": self._adapter.llbds_config.llbds_token},
            timeout=self._adapter.config.api_timeout,
        )
        resp = await self._adapter.request(request)

        if resp.status_code != 200:
            result_queue.put({"type": "value", "value": None})
            return None

        try:
            type_ = json.loads(resp.content)["data"]
        except json.JSONDecodeError:
            raise LLBDSInternalError("Failed to decode LLBDS result!")

        result_queue.put(type_)

    def _run_sync(self, func: Callable, *args, **kwargs) -> Any:
        result_queue = queue.Queue()

        thread = threading.Thread(
            target=asyncio.run,
            args=(func(result_queue, *args, **kwargs),),
            daemon=True,
        )
        thread.start()
        thread.join()
        return result_queue.get()

    def __getattribute__(self, name: str) -> Any:
        if name.startswith("_"):  # 避免内部属性触发递归调用
            return object.__getattribute__(self, name)

        if name == "name" and self._name is not None:
            return self._name

        if name in self._types:
            type_ = self._types[name]
        else:
            data: Dict[str, Any] = self._run_sync(self._get_type, name)
            type_ = data["type"]

            if (value := data.get("value")) is not None:
                self._types[name] = type_
                return value

        if type_ == "function":
            return lambda *args, **kwargs: self._run_sync(
                self._get_llbds_result, name, *args, **kwargs
            )

        return self._run_sync(self._get_llbds_result, name)

    def __repr__(self) -> str:
        return f"<LLSEObject index={self._index}>"

    def __str__(self) -> str:
        return self.__repr__()
