import requests
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://data.ntpc.gov.tw/api/datasets/010e5b15-3823-4b20-b401-b1cf000550c5/json?page=0&size=10000"

def main():
    print("下載新北市YOUBIKE即時資訊")

    response = requests.get(url, verify=False)

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