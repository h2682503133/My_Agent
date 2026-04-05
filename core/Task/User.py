from typing import overload

from typing_extensions import override


class User:
    """
    用户实体类
    职责：仅封装用户标识 + 消息推送，不处理任何任务/队列逻辑
    """
    def __init__(self, user_id: str, session_id: str, output):
        # 用户唯一ID
        self.id = user_id
        # 会话ID（同一对话窗口不变）
        self.session_id = session_id
        # 底层推送接口（WebOutput/QQOutput，实现send(text)方法）
        self.output = output
    def send(self, task) -> None:
        text=task.consume_temp_dialog_input()
        """
        统一消息发送入口
        仅执行底层发送，不做任何状态/栈判断
        """
        self.output.send(text)
