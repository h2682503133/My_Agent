# 项目介绍
本项目核心思想为提前预制智能体与其路由方式
1. 实现通过差异化智能体调用来切分智能体所加载的系统提示词与任务中的记忆，依次降低token消耗
2. 提前设定不同智能体所用模型，可以根据不同任务需求与模型特点选择合适模型，同时可以使用本地化模型降低云端模型调用消耗
# 依赖项目介绍
1. clawhub https://github.com/openclaw/clawhub
2. openviking https://github.com/volcengine/OpenViking
3. LLOneBot https://github.com/LLOneBot/LuckyLilliaBot
(用于对接qq部分，如果使用其他方式请自行修改qq_bridge.py)
# 文件结构介绍
1. .bat文件 - windows的启动文件直接双击可启动
2. workspace - 工作空间，智能体读写的默认目录
2. system_prompt - 系统提示词目录，可以给不同智能体的写系统提示词
4. config - 配置文件目录，配置智能体与网络路由的参数
如果需要新建智能体，只需添加系统提示词与修改配置文件即可
5. skill - 技能目录，存放clawhub下载的技能文件
# 实现介绍
必须配置main、tool、reader三个智能体
1. 每当智能体向其他智能体对话，或调用工具时，都会将自身id与一条字符串压入栈中，当完成一次智能体对话后会进行弹栈，将这条消息与对话返回一起作为输入向id匹配的智能体进行对话(具体实现参考agent.py的process_task函数，可修改send函数来修改拼接方式，目前已经实现向其他智能体对话可以附带对话请求的信息，连续的工具调用存储第一次调用依赖的指令与反馈)压栈操作为task的成员函数，理论上说可以在除工具/技能调用工程中以外的任意地方进行，以修改上下文拼接的内容，该方式主要用于非复杂操作的短期记忆，如果需要长时间记忆请修改send的上下文拼接方式
2. user-task介绍，qq，web用http请求与task_creator交换信息，将请求发至任务构造器，构造任务，可自行修改任务构造器实现，但必须给task的user对象提供一种以task作为参数的send方式