import requests

url = "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json"

def main():
    print("下載台北市YOUBIKE即時資訊")

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        print("下載成功")
        print(type(data))
        print(len(data))
        print(data[0])
    else:
        print("下載失敗")
        print(response.status_code)

if __name__ == '__main__':
    main()