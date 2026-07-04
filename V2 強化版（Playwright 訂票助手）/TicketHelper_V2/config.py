
import json, os

CONFIG_PATH = "data/config.json"

def save_config(data):
    os.makedirs("data", exist_ok=True)
    with open(CONFIG_PATH,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH,"r",encoding="utf-8") as f:
        return json.load(f)
