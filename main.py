from core.Agent import Agent
from flask import Flask, render_template_string, request, jsonify
import socket
app = Flask(__name__)
import patch.fix_ov_windows
# HTML对话气泡页面（直接内嵌在代码里）
HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <!-- 移动端核心适配标签（唯一新增） -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>智能体对话</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        /* 移动端全屏适配 */
        body{
            height:90vh;
            display:flex;
            flex-direction:column;
            background:#f5f5f5;
            font-family:微软雅黑;
            overflow:hidden;
        }
        /* 聊天区域：手机自适应滚动 */
        .chat{
            flex:1;
            overflow-y:auto;
            padding:20px;
            background:white;
            -webkit-overflow-scrolling:touch;
        }
        /* 消息样式（保留原有类名） */
        .msg{margin:10px 0;display:flex;max-width:85%}
        .user{margin-left:auto;justify-content:flex-end}
        .user .bubble{background:#0099ff;color:white;padding:12px 16px;border-radius:18px 18px 0 18px}
        .agent{margin-right:auto;justify-content:flex-start}
        .agent .bubble{background:#e5e5ea;color:#333;padding:12px 16px;border-radius:18px 18px 18px 0}
        /* 输入框：固定底部（移动端必备） */
        .input{
            display:flex;
            gap:10px;
            padding:10px;
            background:white;
            border-top:1px solid #eee;
        }
        input{
            flex:1;
            padding:14px 18px;
            border:1px solid #ddd;
            border-radius:25px;
            outline:none;
            font-size:16px;
        }
        button{
            padding:14px 26px;
            background:#0099ff;
            color:white;
            border:none;
            border-radius:25px;
            cursor:pointer;
            font-size:16px;
        }
        button:active{background:#0077cc}
    </style>
</head>
<body>
    <!-- 保留原有ID：chat -->
    <div class="chat" id="chat"></div>
    <div class="input">
        <!-- 保留原有ID：text -->
        <input id="text" placeholder="输入消息...">
        <!-- 保留原有onclick：send() -->
        <button onclick="send()">发送</button>
    </div>
    <script>
        // 保留原有函数名：addMsg
        function addMsg(role, text){
            let chat = document.getElementById('chat');
            let cls = role === 'user' ? 'user msg' : 'agent msg';
            let html = `<div class="${cls}"><div class="bubble">${text}</div></div>`;
            chat.innerHTML += html;
            chat.scrollTop = chat.scrollHeight;
        }
        // 保留原有函数名：send
        async function send(){
            let text = document.getElementById('text').value;
            if(!text) return;
            addMsg('user', text);
            document.getElementById('text').value = '';
            // 保留原有接口：/chat
            let res = await fetch('/chat', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({msg:text})
            });
            let data = await res.json();
            // 保留原有返回字段：data.reply
            addMsg('agent', data.reply);
        }
    </script>
</body>
</html>
"""
# 网页路由
@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

# 对话接口（对接你的Agent）
@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.json.get('msg')
    result = Agent.user_chat(user_msg)
    return jsonify(reply=f"{Agent.default_agent}：{result['agent_reply']}")

# 启动程序
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.244.0.0', 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    ip = get_local_ip()
    print(f"✅ 局域网访问地址：http://{ip}:5000")
    print(f"✅ 所有校园网设备（10.244开头）均可直接打开！")
    # 核心：host='0.0.0.0' 开放所有局域网IP
    app.run(host='0.0.0.0', port=5000, debug=False)