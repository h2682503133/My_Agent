from core.Task import Task
def process_user_task(task, user):
    task.user.output.send("已收到信息"+task.content)
