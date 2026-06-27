import os
import pandas as pd
import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showinfo

# 取得目前腳本所在的目錄
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_data():
    """讀取 CSV 並進行資料清洗與預處理"""
    csv_path = os.path.join(BASE_DIR, '各鄉鎮市區人口密度.csv')
    df = pd.read_csv(csv_path)

    # 重新命名欄位為中文
    df.columns = ['統計年', '區域別', '年底人口數', '土地面積', '人口密度']

    # 移除第一列（原本的中文標題列）
    df = df.drop(index=0)

    # 移除最後 5 筆非資料內容（尾部說明資訊）
    df = df.drop(df.index[-5:])

    # 僅保留需要的欄位，並重新命名
    df = df[['區域別', '年底人口數', '土地面積']].copy()
    df = df.rename(columns={'年底人口數': '人口數'})

    # 轉換為數值型態，無法轉換者設為 NaN
    df['人口數'] = pd.to_numeric(df['人口數'], errors='coerce')
    df['土地面積'] = pd.to_numeric(df['土地面積'], errors='coerce')

    # 移除含有 NaN 的列
    df = df.dropna()

    # 新增人口密度欄位（人口數 / 土地面積）
    df['人口密度'] = df['人口數'] / df['土地面積']

    # 依人口數遞減排序
    df = df.sort_values('人口數', ascending=False).reset_index(drop=True)

    return df


def update_table(data):
    """清空表格並填入指定資料"""
    for row in tree.get_children():
        tree.delete(row)

    for _, row in data.iterrows():
        tree.insert('', 'end', values=(
            row['區域別'],
            int(row['人口數']),
            round(row['土地面積'], 4),
            round(row['人口密度'], 2),
        ))


def on_query():
    """查詢按鈕的回呼函式：根據關鍵字篩選區域別"""
    keyword = entry.get().strip()
    if keyword == '':
        update_table(df)
    else:
        mask = df['區域別'].str.contains(keyword, na=False)
        update_table(df[mask])


# === 主程式 ===

# 讀取資料
df = load_data()

# 建立主視窗
root = tk.Tk()
root.title('台灣鄉鎮市區人口密度查詢系統')
root.geometry('900x600')

# 上方控制區
control_frame = ttk.Frame(root, padding=10)
control_frame.pack(fill='x')

ttk.Label(control_frame, text='輸入區域名稱：').pack(side='left')
entry = ttk.Entry(control_frame, width=30)
entry.pack(side='left', padx=5)
entry.bind('<Return>', lambda e: on_query())

btn_query = ttk.Button(control_frame, text='查詢', command=on_query)
btn_query.pack(side='left')

# 下方表格區
table_frame = ttk.Frame(root)
table_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

columns = ('區域別', '人口數', '土地面積', '人口密度')
tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=20)

for col in columns:
    tree.heading(col, text=col, anchor='center')
    tree.column(col, width=180, anchor='center', minwidth=100)

# 加入垂直與水平捲軸
vsb = ttk.Scrollbar(table_frame, orient='vertical', command=tree.yview)
hsb = ttk.Scrollbar(table_frame, orient='horizontal', command=tree.xview)
tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

tree.grid(row=0, column=0, sticky='nsew')
vsb.grid(row=0, column=1, sticky='ns')
hsb.grid(row=1, column=0, sticky='ew')

table_frame.grid_rowconfigure(0, weight=1)
table_frame.grid_columnconfigure(0, weight=1)

# 預設顯示全部資料
update_table(df)

# 啟動主迴圈
root.mainloop()
