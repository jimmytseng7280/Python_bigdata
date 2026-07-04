"""
台灣鄉鎮市區人口密度查詢系統
使用 pandas 處理資料，並以 tkinter/ttk 建立 GUI 介面
"""

import os
import pandas as pd
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False


def load_and_process_data(file_path: str) -> pd.DataFrame:
    """
    讀取 CSV 並進行資料整理，回處理後的 DataFrame。
    """
    # 讀取 CSV，使用第 2 列（index=1）作為欄位名稱
    df = pd.read_csv(file_path, header=1)

    # 移除最後 5 筆非資料內容（尾部說明資訊）
    df = df.iloc[:-5].reset_index(drop=True)

    # 僅保留需要的三個欄位：區域別、年底人口數、土地面積
    df = df[['區域別', '年底人口數', '土地面積']].copy()

    # 將年底人口數重新命名為人口數
    df.rename(columns={'年底人口數': '人口數'}, inplace=True)

    # 將人口數與土地面積轉換為數值型態
    df['人口數'] = pd.to_numeric(df['人口數'], errors='coerce')
    df['土地面積'] = pd.to_numeric(df['土地面積'], errors='coerce')

    # 移除含有空值的列
    df = df.dropna().reset_index(drop=True)

    # 新增人口密度欄位
    df['人口密度'] = df['人口數'] / df['土地面積']

    return df


class PopulationQueryApp:
    """台灣鄉鎮市區人口密度查詢系統的主視窗類別"""

    def __init__(self, root: tk.Tk, data: pd.DataFrame):
        self.root = root
        self.data = data

        # 提取縣市名稱（區域別前 3 字）
        self.data['縣市'] = self.data['區域別'].str[:3]
        self.counties = ['全部顯示'] + sorted(self.data['縣市'].unique())

        # 設定視窗標題與大小
        self.root.title('台灣鄉鎮市區人口密度查詢系統')
        self.root.geometry('1200x650')

        # 建立上方控制區
        control_frame = ttk.Frame(root)
        control_frame.pack(pady=10)

        label = ttk.Label(control_frame, text='輸入區域名稱：')
        label.pack(side=tk.LEFT, padx=(0, 5))

        self.keyword_entry = ttk.Entry(control_frame, width=30)
        self.keyword_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.keyword_entry.bind('<Return>', lambda e: self.query_data())

        query_button = ttk.Button(control_frame, text='查詢', command=self.query_data)
        query_button.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(control_frame, text='選擇縣市：').pack(side=tk.LEFT)
        self.combo = ttk.Combobox(
            control_frame, values=self.counties, state='readonly', width=12
        )
        self.combo.set('全部顯示')
        self.combo.pack(side=tk.LEFT, padx=5)
        self.combo.bind('<<ComboboxSelected>>', self.on_combo_select)

        # 主內容區：使用 PanedWindow 分隔表格與圖表
        paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        # --- 左側表格區 ---
        table_frame = ttk.Frame(paned)
        paned.add(table_frame, weight=2)

        columns = ('區域別', '人口數', '土地面積', '人口密度')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=25)

        for col in columns:
            self.tree.heading(col, text=col, anchor=tk.CENTER)
            self.tree.column(col, width=160, anchor=tk.CENTER, minwidth=100)

        v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # --- 右側圖表區 ---
        chart_frame = ttk.Frame(paned)
        paned.add(chart_frame, weight=1)

        self.fig, self.ax = plt.subplots(figsize=(4, 4.5))
        self.fig.tight_layout(pad=3)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 預設顯示所有資料
        self._current_data = self.data
        self.refresh_table(self.data)

    def refresh_table(self, df: pd.DataFrame) -> None:
        """
        清空表格並填入指定的 DataFrame 資料。
        人口密度四捨五入至小數點後兩位，人口數顯示為整數。
        """
        self._current_data = df

        # 清除現有資料
        for row in self.tree.get_children():
            self.tree.delete(row)

        # 逐筆插入資料
        for _, row in df.iterrows():
            self.tree.insert(
                '',
                tk.END,
                values=(
                    row['區域別'],
                    int(row['人口數']),
                    row['土地面積'],
                    round(row['人口密度'], 2),
                ),
            )

        self.update_chart(df)

    def update_chart(self, df: pd.DataFrame) -> None:
        """
        根據目前篩選結果繪製長條圖（顯示人口數前 10 名）。
        """
        self.ax.clear()

        top = df.nlargest(10, '人口數')

        self.ax.barh(top['區域別'], top['人口數'], color='steelblue')
        self.ax.set_xlabel('人口數')
        self.ax.set_title('人口數 TOP 10')
        self.ax.invert_yaxis()
        self.ax.tick_params(axis='y', labelsize=8)

        self.canvas.draw()

    def on_combo_select(self, event) -> None:
        """下拉選單選擇事件：根據選擇的縣市篩選區域別"""
        selected = self.combo.get()
        if selected == '全部顯示':
            self.refresh_table(self.data)
        else:
            mask = self.data['縣市'] == selected
            self.refresh_table(self.data[mask])

    def query_data(self) -> None:
        """
        根據使用者輸入的關鍵字篩選區域別，並更新表格。
        若關鍵字為空，則顯示所有資料。
        """
        self.combo.set('全部顯示')
        keyword = self.keyword_entry.get().strip()
        if keyword == '':
            filtered = self.data
        else:
            filtered = self.data[self.data['區域別'].str.contains(keyword, na=False)]
        self.refresh_table(filtered)


def main():
    """應用程式進入點"""
    # 以程式所在目錄為基準，建構 CSV 檔案路徑
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, '各鄉鎮市區人口密度.csv')

    # 讀取並處理資料
    data = load_and_process_data(csv_path)

    # 建立 GUI
    root = tk.Tk()
    app = PopulationQueryApp(root, data)
    root.mainloop()


if __name__ == '__main__':
    main()
