import requests
import pandas as pd

URL = "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json"

def main():
    response = requests.get(URL, timeout=10)
    response.raise_for_status()

    data = response.json()

    df = pd.DataFrame(data)

    # 依行政區統計
    report = df.groupby("sarea").agg(
        站點數=("sno", "count"),
        可借車數=("available_rent_bikes", "sum"),
        可還空位數=("available_return_bikes", "sum"),
        總停車格數=("Quantity", "sum")
    ).reset_index()

    # 欄位改成中文
    report = report.rename(columns={
        "sarea": "行政區"
    })

    # 輸出 Excel
    file_name = "YouBike行政區統計報表.xlsx"

    with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="原始資料", index=False)
        report.to_excel(writer, sheet_name="行政區統計", index=False)

    print("統計報表產生完成")
    print(report)
    print(f"已輸出：{file_name}")

if __name__ == "__main__":
    main()