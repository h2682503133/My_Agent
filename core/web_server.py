import socket
import json
import queue
from flask import Flask, render_template, request, session, redirect, url_for, Response, jsonify
from core.logger import gateway_log
from queue_manager import queue_and_retry, start_scheduler, queue_clients, MESSAGE_QUEUE

app = Flask(__name__)
app.secret_key = "123"

@app.route('/queue/stream')
def queue_stream():
    def gen():
        q = queue.Queue()
        queue_clients.add(q)
        try:
            while True:
                yield f"data: {q.get()}\n\n"
        except:
            queue_clients.remove(q)
    return Response(gen(), mimetype='text/event-stream')

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/do_login', methods=['POST'])
def do_login():
    session['user_id'] = request.form.get('user_id')
    return redirect(url_for('chat_page'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/chat')
def chat_page():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
@queue_and_retry
def chat(user_id, user_msg):
    from core.Agent import Agent
    result = Agent.user_chat(user_msg, user_id)
    return {"reply": f"{Agent.default_agent[user_id]}：{result['agent_reply']}"}

@app.route('/queue/status')
def queue_status():
    return jsonify(waiting=MESSAGE_QUEUE.qsize())

def get_local_ip():
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(('10.244.0.0',80))
        return s.getsockname()[0]
    except: return '127.0.0.1'

def start_web():
    ip=get_local_ip()
    gateway_log(f"WEB启动 http://{ip}:5000")
    app.run(host='0.0.0.0',port=5000,debug=False)