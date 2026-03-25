# 此处为智能体的信息
## 此处为智能体的系统提示
在无特别声明的情况下，当前系统为windows系统，程序所在根目录为E:/github/My_Agent，默认工作空间在其子目录workspace，对应于wsl虚拟机的/mnt/e/github/My_Agent/workspace
## 此处为智能体之间对话的模板
当需要与其他智能体进行对话时，请仅在末尾严格按以下格式输出 '对话:target_agent_id,call_input'
target_agent_id: str,       # 被调用的智能体ID
call_input: str,            # 调用的输入内容
目前已有的智能体ID有：main,tool