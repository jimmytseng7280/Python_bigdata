import requests
from requests import response #可加入此行(亦可不需要加)，讓 response 變成一個 typehint，方便以後看到資料型態
# Response灰色表示沒使用
def main():

    url = "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json"

    print("下載台北市YOUBIKE即時資訊")

    response = requests.get(url)
    #response:Response = requests.get(url)
    print(type(response))
    # typehint 是一個變數，裡面存放了 url 的資料型態
    # url:str = "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json"
    # 方便以後看到資料型態，typehint不一定要寫，但建議寫上去，讓程式碼更清楚

    if response.status_code == 200: # 200 代表是網址連結成功的意思
        #
        data = response.json()  # json() 是respones的實體方法，會把 response 轉成 json 格式的資料
                                # json(**kwargs.Any) -> Any，**表示沒有限定參數的型態，Any表示回傳的資料型態也沒有限定
        #data:list = response.json()
        print("下載成功")
        print(type(data))       # type(data)) 是一個內建函式，會回傳 data 的資料型態
                                # type() 是一個內建函式，會回傳資料的型態，data 是一個 list，所以 type(data) 會回傳 list
        print(len(data))        # len(data)) 是一個內建函式，會回傳 data 的長度
                                # len() 是一個內建函式，會回傳資料的長度，data 是一個 list，所以 len(data) 會回傳 list 的長度
        print(data[0])          # data[0] 是一個 list 的第一筆資料，因為 data 是一個 list，所以可以用 index 來取出資料
    else:                           # 其他狀態 或是 以404 代表網址連結失敗的意思
        print("下載失敗")
        print(response.status_code)

if __name__ == '__main__':
    main()