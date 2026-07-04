
import threading, time
from datetime import datetime

def wait_until(ts, callback):
    target = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

    def loop():
        while True:
            if datetime.now() >= target:
                callback()
                return
            time.sleep(0.3)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
