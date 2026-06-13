import tkinter as tk
from tkinter import filedialog, scrolledtext, simpledialog
import pandas as pd

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# =====================
# 中文顯示修正
# =====================
matplotlib.rcParams["font.sans-serif"] = ["Microsoft JhengHei"]
matplotlib.rcParams["axes.unicode_minus"] = False


class ScoreApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📊 班級成績分析系統 Pro MAX")
        self.root.geometry("1300x800")

        # =====================
        # 上方按鈕
        # =====================
        top = tk.Frame(root)
        top.pack(pady=10)

        tk.Button(top, text="📂 選檔", command=self.load_file, width=12).grid(row=0, column=0, padx=5)
        tk.Button(top, text="📊 分析", command=self.analyze, width=12).grid(row=0, column=1, padx=5)
        tk.Button(top, text="🏆 前N名", command=self.top_n, width=12).grid(row=0, column=2, padx=5)
        tk.Button(top, text="🔍 查學生", command=self.search_student, width=12).grid(row=0, column=3, padx=5)

        # =====================
        # 主容器（左右滿版）
        # =====================
        container = tk.Frame(root)
        container.pack(fill=tk.BOTH, expand=True)

        container.columnconfigure(0, weight=4)  # 左 40%
        container.columnconfigure(1, weight=6)  # 右 60%
        container.rowconfigure(0, weight=1)

        # =====================
        # 左側文字區
        # =====================
        left = tk.Frame(container, bg="#f5f5f5")
        left.grid(row=0, column=0, sticky="nsew")

        self.text = scrolledtext.ScrolledText(left, font=("Microsoft JhengHei", 11))
        self.text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # =====================
        # 右側圖表區
        # =====================
        self.chart_frame = tk.Frame(container, bg="white")
        self.chart_frame.grid(row=0, column=1, sticky="nsew")

        self.df = None

    # =====================
    # 載入檔案
    # =====================
    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])

        if path:
            self.df = pd.read_csv(path, encoding="utf-8-sig")
            self.text.insert(tk.END, f"✔ 已載入：{path}\n\n")

    # =====================
    # 基本分析
    # =====================
    def analyze(self):
        if self.df is None:
            return

        df = self.df.copy()
        score_cols = df.columns[1:]

        df["總分"] = df[score_cols].sum(axis=1)
        df["平均"] = df[score_cols].mean(axis=1)

        self.df = df

        self.text.insert(tk.END, "\n===== 📊 班級分析 =====\n")
        self.text.insert(tk.END, f"👥 人數：{len(df)}\n")
        self.text.insert(tk.END, f"📌 平均總分：{df['總分'].mean():.2f}\n")

        self.draw_class_chart()

    # =====================
    # 前N名
    # =====================
    def top_n(self):
        if self.df is None:
            return

        n = simpledialog.askinteger("前N名", "輸入 N：", minvalue=1, maxvalue=100)

        top = self.df.sort_values("總分", ascending=False).head(n)

        self.text.insert(tk.END, f"\n🏆 前 {n} 名：\n")
        self.text.insert(tk.END, top[["學生姓名", "總分"]].to_string(index=False) + "\n")

    # =====================
    # 查學生
    # =====================
    def search_student(self):
        if self.df is None:
            return

        name = simpledialog.askstring("查詢", "輸入學生姓名：")

        if name not in self.df["學生姓名"].values:
            self.text.insert(tk.END, f"\n❌ 找不到 {name}\n")
            return

        stu = self.df[self.df["學生姓名"] == name].iloc[0]
        score_cols = self.df.columns[1:-2]

        self.text.insert(tk.END, f"\n🔍 {name} 成績：\n")
        self.text.insert(tk.END, stu.to_string() + "\n")

        self.draw_student_chart(name, stu, score_cols)

    # =====================
    # 班級圖表
    # =====================
    def draw_class_chart(self):
        for w in self.chart_frame.winfo_children():
            w.destroy()

        df = self.df
        score_cols = df.columns[1:-2]

        fig, axs = plt.subplots(1, 2, figsize=(10, 5))

        avg = df[score_cols].mean()
        axs[0].bar(avg.index, avg.values)
        axs[0].set_title("各科平均")
        axs[0].tick_params(axis='x', rotation=45)

        axs[1].hist(df["總分"], bins=8)
        axs[1].set_title("總分分布")

        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # =====================
    # 個人圖表
    # =====================
    def draw_student_chart(self, name, stu, cols):
        for w in self.chart_frame.winfo_children():
            w.destroy()

        fig, ax = plt.subplots(figsize=(6, 5))

        ax.bar(cols, stu[cols].values)
        ax.set_title(f"{name} 各科成績")
        ax.set_ylim(0, 100)
        ax.tick_params(axis='x', rotation=45)

        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


# =====================
# 啟動程式
# =====================
if __name__ == "__main__":
    root = tk.Tk()
    app = ScoreApp(root)
    root.mainloop()