from core.Task import Task
from core.User import User
from core.Agent import Agent
from core.logger import chat_log
def process_user_task(task: Task):
    user=task.user
    """
    🔥 唯一处理入口
    网页、QQ 都调用这里
    调度、队列、AI 全在这里面
    """
    try:
        #result = Agent.handle_task(task, user)
        #reply = f"{Agent.default_agent[user.session_id]}：{result['agent_reply']}"
        reply=Agent.user_chat(task.consume_temp_dialog_input(),task.user.session_id)
        user.send(reply)
        user.send("任务已完成")
    except:
        user.send("服务繁忙")