import json
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

    resp=task.consume_temp_dialog_output()
    try:
        data = resp.json()
        if "choices" in data:
            raw_response = data["choices"][0]["message"]["content"]
            chat_log(f"{self.id} [输入]{data['usage']['prompt_tokens']}token [输出]{data['usage']['completion_tokens']}")
            debug_log(f"{self.id} [输入]{data['usage']['prompt_tokens']}token [输出]{data['usage']['completion_tokens']}")
        elif "message" in data:
            raw_response = data["message"]["content"]
            chat_log(f"{self.id} [输入]{data['prompt_eval_count']} token [输出]{data['eval_count']} token")
            debug_log(f"{self.id} [输入]{data['prompt_eval_count']} token [输出]{data['eval_count']} token")
        else:
            chat_log("此处进入了else分支")
            raw_response = str(data)
    except:
        raw_response = resp.text.strip()

    task.set_temp_dialog_output(full_to_half(raw_response))


