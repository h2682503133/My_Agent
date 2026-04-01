
import time
from user import User

class Task:
    """
    任务核心类
    职责：存储全流程数据、上下文栈、任务状态、记忆日志
    静态task_map：仅存储【暂停状态】的任务
    """
    # 静态字典：仅 暂停(pending) 状态的任务存入，key=user_id, value=Task实例
    task_map: dict[str, "Task"] = {}

    def __init__(self, task_id: str, user_id: str, content: str):
        # 任务唯一ID
        self.task_id = task_id
        # 归属用户ID
        self.user_id = user_id
        # 任务创建时间戳
        self.create_time = time.time()
        # 用户原始输入内容
        self.content = content

        # ==================== 调度状态 ====================
        # 任务状态：waiting / running / pending / completed
        self.status = "waiting"
        # 重试次数
        self.retry_count = 0
        # 调度槽位编号
        self.slot_index = -1

        # ==================== 核心上下文栈（数组模拟栈） ====================
        # 结构：[{"from": 指针, "input": 内容}]
        # 空栈 = 触发最终流程
        self.agent_context = []

        # ==================== 结果与反思 ====================
        # 最终输出结果
        self.final_result = ""
        # 总结反思内容
        self.reflection = ""

        # ==================== 记忆日志（用于总结反思） ====================
        self.memory_log = []

    # ==================== 上下文栈操作方法 ====================
    def push_context(self, from_obj, input_text: str) -> None:
        """入栈：新增一层智能体调用"""
        self.agent_context.append({
            "from": from_obj,
            "input": input_text
        })

    def pop_context(self) -> dict | None:
        """出栈：移除当前层，栈底可删除"""
        if self.agent_context:
            return self.agent_context.pop()
        return None

    # ==================== 静态方法：管理暂停任务 ====================
    @classmethod
    def save_pending_task(cls, user_id: str, task: "Task") -> None:
        """仅暂停任务时存储到task_map"""
        cls.task_map[user_id] = task

    @classmethod
    def get_pending_task(cls, user_id: str) -> "Task | None":
        """获取用户暂停的任务"""
        return cls.task_map.get(user_id)

    @classmethod
    def remove_pending_task(cls, user_id: str) -> None:
        """从task_map移除任务（完成/恢复时调用）"""
        if user_id in cls.task_map:
            del cls.task_map[user_id]