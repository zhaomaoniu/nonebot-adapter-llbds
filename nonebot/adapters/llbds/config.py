from pydantic import BaseModel, Extra
from typing import Optional


class Config(BaseModel, extra=Extra.ignore):
    llbds_token: str
    """LLBDS token, 用于连接 ws 时鉴权"""
    llbds_server_id: Optional[str] = "LLBDS"
    """LLBDS 服务器 ID, 用作 Bot 的 self_id, 可任填"""
    llbds_api_url: Optional[str] = "http://127.0.0.1:23303"
    """LLBDS API 地址，如 `http://127.0.0.1:23303`"""