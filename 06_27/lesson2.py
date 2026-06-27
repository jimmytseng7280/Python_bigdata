import pandas as pd

dataFrame = pd.read_csv('各鄉鎮市區人口密度.csv')
dataFrame.columns = ['統計年', '區域別', '年底人口數', '土地面積', '人口密度']

df = dataFrame.drop(index=0)
df1 = df.dropna()
df2 = df1.drop('統計年', axis=1)

df3 = df2.copy()
df3['年底人口數'] = pd.to_numeric(df3['年底人口數'], errors='coerce')
df3['年底人口數'] = df3['年底人口數'].astype(int)

print(df3['年底人口數'].dtype)
print(df3)
