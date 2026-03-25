import json
def parse_response(self, resp):
    try:
        data = resp.json()
        if "choices" in data:
            raw_response = data["choices"][0]["message"]["content"]
        elif "message" in data:
            raw_response = data["message"]["content"]
        else:
            raw_response = str(data)
    except:
        raw_response = resp.text.strip()

    self.history.append({"role": "test", "content": raw_response})

    try:
        with open("chat_log.json", "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    except:
        pass

    return raw_response