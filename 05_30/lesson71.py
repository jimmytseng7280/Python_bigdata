import csv

try:
    with open("lesson71_score.csv", "r", encoding="utf-8") as file:
        reader = csv.reader(file)

        for row in reader:
            print(row)

except:
    print("無法開啟檔案，請確認檔案存在且路徑正確。")