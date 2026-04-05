from core.Task.Task import Task
from core.Agent.Agent import Agent


def process_user_task(task: Task):
    user=task.user
    """
    🔥 唯一处理入口
    网页、QQ 都调用这里
    调度、队列、AI 全在这里面
    """
    try:
        content=task.consume_temp_dialog_input()
        print(content)
        reply=Agent.user_chat(content,task.user.session_id)["agent_reply"]
        user.send(reply)
        user.send("任务已完成")
    except:
        user.send("服务繁忙")
