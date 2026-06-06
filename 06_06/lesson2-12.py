import requests
import pandas as pd
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://data.ntpc.gov.tw/api/datasets/010e5b15-3823-4b20-b401-b1cf000550c5/json?page=0&size=10000"

data = requests.get(url, verify=False).json()

df = pd.DataFrame(data)

df.to_excel("youbike20新北市.xlsx", index=False)

print("已轉成 Excel")