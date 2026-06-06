import requests
import pandas as pd

url = "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json"

data = requests.get(url).json()

df = pd.DataFrame(data)

df.to_excel("youbike.xlsx", index=False)

print("已轉成 Excel")