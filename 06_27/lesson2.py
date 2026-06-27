import pandas as pd

# 1. 讀取內政部人口密度 CSV 檔案
dataFrame = pd.read_csv('各鄉鎮市區人口密度.csv')

# 2. 重新定義乾淨的欄位名稱（將原本的英文標題替換掉）
dataFrame.columns = ['統計年', '區域別', '年底人口數', '土地面積', '人口密度']

# 3. 刪除 index 為 0 的那列（因為該列包含重複的中文欄位名稱）
df = dataFrame.drop(index=0)

# 4. 移除包含空值（NaN）的行，確保資料基本完整性
df1 = df.dropna()

# 5. 刪除不需要分析的 '統計年' 欄位（axis=1 代表刪除整欄）
df2 = df1.drop('統計年', axis=1)

# 6. 複製一份 DataFrame，避免動到原始資料並防止 SettingWithCopyWarning 警告
df3 = df2.copy()

# 7. 將 '年底人口數' 轉換為數值型態，若有無法轉換的文字（如備註）會先變成 NaN
df3['年底人口數'] = pd.to_numeric(df3['年底人口數'], errors='coerce')

# 8. 再次移除因上一步轉換而產生的 NaN 空值（徹底清除尾端備註列）
df3 = df3.dropna()

# 9. 將各欄位轉換為正確的計算型態（人口數轉整數、面積與密度轉浮點數）
df3['年底人口數'] = df3['年底人口數'].astype(int)
df3['土地面積'] = df3['土地面積'].astype(float)
df3['人口密度'] = df3['人口密度'].astype(float)

# 10. 印出 DataFrame 的詳細資訊（包含欄位名稱、資料型態與非空值數量）
df3.info()

# 11. 在 Jupyter Notebook 中直接顯示清洗完成的精美資料表格
df3

# #print(df3.info)
# #print(df3['年底人口數'].dtype)
# #print(df3)