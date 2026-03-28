import json
from core.logger import debug_log,chat_log
def parse_response(self, resp):
    try:
        data = resp.json()
        if "choices" in data:
            raw_response = data["choices"][0]["message"]["content"]
            chat_log(f"{self.agent_id} [输入]{data['usage']['prompt_tokens']}token [输出]{data['usage']['completion_tokens']}")
            debug_log(f"{self.agent_id} [输入]{data['usage']['prompt_tokens']}token [输出]{data['usage']['completion_tokens']}")
        elif "message" in data:
            raw_response = data["message"]["content"]
            chat_log(f"{self.agent_id} [输入]{data['usage']['prompt_tokens']}token [输出]{data['usage']['completion_tokens']}")
            debug_log(f"{self.agent_id} [输入]{data['usage']['prompt_tokens']}token [输出]{data['usage']['completion_tokens']}")
        else:
            raw_response = str(data)
    except:
        raw_response = resp.text.strip()

    return raw_response