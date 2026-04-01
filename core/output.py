from __future__ import annotations

from typing import Callable


class WebOutput:
    """Web 通道输出：缓存文本，供 HTTP 响应读取。"""

    def __init__(self):
        self.messages: list[str] = []

    def send(self, text: str) -> None:
        self.messages.append(text)

    def last(self) -> str:
        return self.messages[-1] if self.messages else ""


class QQOutput:
    """QQ 通道输出：通过注入的发送函数推送。"""

    def __init__(self, sender: Callable[[str], None]):
        self._sender = sender

    def send(self, text: str) -> None:
        self._sender(text)
