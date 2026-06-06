# 導入requests庫用於發送HTTP請求
import requests
from requests import Response

# 定義主程式函數
def main():

    # 定義API的URL（YOUBIKE台北市即時資訊）
    url = "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json"

    # 輸出訊息到控制台
    print("下載台北市YOUBIKE即時資訊")

    # 使用requests發送GET請求
    # `:requests.Response` 是類型註解，表示response變數的型態應該是Response物件
    response:Response = requests.get(url)
    # 使用type()函數打印response物件的實際型態
    print(type(response))

    # 檢查HTTP狀態碼是否為200（200代表請求成功）
    if response.status_code == 200:
        # 呼叫.json()方法，將JSON格式的文本轉換為Python中的列表或字典
        data = response.json()
        # 輸出"下載成功"訊息
        print("下載成功")
        # 使用type()函數查看data的型態（通常是list列表）
        print(type(data))
        # 使用len()函數得到data列表中元素的個數
        print(len(data))        
        # 使用索引[0]取出data列表的第一個元素，並打印它
        print(data[0])
    else:  
        # 如果狀態碼不是200，輸出"下載失敗"訊息
        print("下載失敗")
        # 打印HTTP狀態碼
        print(response.status_code)

# 判斷這個檔案是否直接被執行（而不是被導入其他檔案）
if __name__ == '__main__':
    # 執行主程式函數
    main()