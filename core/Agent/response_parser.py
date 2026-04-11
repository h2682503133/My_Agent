import csv
import json
import time
from core.logger import debug_log,chat_log
def full_to_half(text: str) -> str:
    """
    全角转半角（万能版）
    字母、数字、空格、所有标点符号一次性转完
    """
    result = []
    for char in text:
        code = ord(char)
        if code == 0x3000:  # 全角空格
            result.append(chr(0x0020))
        elif 0xFF01 <= code <= 0xFF5E:  # 全角字符范围
            result.append(chr(code - 0xFEE0))
        else:
            result.append(char)
    return ''.join(result)
def parse_response(self,task):
    input_token=0
    output_token=0
    resp=task.consume_temp_dialog_output()
    
    try:
        data = resp.json()
        if "choices" in data:
            raw_response = data["choices"][0]["message"]["content"]
            input_token=int(data["usage"]["prompt_tokens"])
            output_token=int(data["usage"]["completion_tokens"])
        elif "message" in data:
            raw_response = data["message"]["content"]
            input_token=int(data['prompt_eval_count'])
            output_token=int(data['eval_count'])
        else:
            chat_log("此处进入了else分支")
            raw_response = str(data)
    except:
        raw_response = resp.text.strip()
    if input_token>0 and output_token>0:
        if "对话:"in raw_response:Type="call"
        elif "工具调用:" in raw_response:Type="tool"
        elif "询问:" in raw_response:Type="question"
        else :Type="other"
        chat_log(f"{self.id} [输入]{input_token}token [输出]{output_token}")
        debug_log(f"{self.id} [输入]{input_token}token [输出]{output_token}")
        with open("logs\\token.csv", "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([task.user.id, self.id, input_token, output_token,Type, time.strftime("%Y-%m-%d %H:%M", time.localtime())])
    task.set_temp_dialog_output(full_to_half(raw_response))


