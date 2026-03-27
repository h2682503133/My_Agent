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

    return raw_response