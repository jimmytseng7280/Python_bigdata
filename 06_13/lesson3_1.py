import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

CSV_FILE = "考試分數_3年6班.csv"
SUBJECTS = ["語文", "數學", "英語", "物理", "化學"]

df = pd.read_csv(CSV_FILE)
df["總分"] = df[SUBJECTS].sum(axis=1)
df["總排名"] = df["總分"].rank(method="min", ascending=False).astype(int)

# 配色方案
COLOR_BG = "#f0f5ff"
COLOR_FRAME_BG = "#ffffff"
COLOR_HEADER = "#4a90e4"
COLOR_HEADER_TEXT = "#ffffff"
COLOR_BTN_SEARCH = "#4a90e4"
COLOR_BTN_SEARCH_TEXT = "#ffffff"
COLOR_BTN_TOP = "#2ecc71"
COLOR_BTN_TOP_TEXT = "#ffffff"
COLOR_BTN_PLOT = "#ff8c4a"
COLOR_BTN_PLOT_TEXT = "#ffffff"
COLOR_ENTRY_BG = "#ffffff"
COLOR_ENTRY_FG = "#333333"

root = tk.Tk()
root.title("學生成績查詢系統")
root.geometry("1000x800")
root.configure(bg=COLOR_BG)

def clear_result():
    for item in tree.get_children():
        tree.delete(item)

def show_df(dataframe):
    clear_result()
    for _, row in dataframe.iterrows():
        tree.insert("", "end", values=tuple(row))

def search_student():
    name = entry_name.get().strip()
    if not name:
        messagebox.showwarning("提醒", "請輸入學生姓名")
        return
    result = df[df["學生姓名"] == name]
    if result.empty:
        messagebox.showinfo("結果", "找不到這位學生")
        clear_result()
        return
    show_df(result[["學生姓名"] + SUBJECTS + ["總分", "總排名"]])
    plot_student(name)

def top_students():
    try:
        n = int(entry_top_n.get().strip())
    except:
        messagebox.showwarning("提醒", "請輸入正確的名次數字")
        return
    result = df.sort_values(by=["總分", "學生姓名"], ascending=[False, True]).head(n)
    show_df(result[["學生姓名"] + SUBJECTS + ["總分", "總排名"]])

def top_subject():
    subject = combo_subject.get().strip()
    if subject not in SUBJECTS:
        messagebox.showwarning("提醒", "請選擇正確科目")
        return
    try:
        n = int(entry_subject_n.get().strip())
    except:
        messagebox.showwarning("提醒", "請輸入正確的名次數字")
        return
    result = df.sort_values(by=[subject, "學生姓名"], ascending=[False, True]).head(n).copy()
    result["該科排名"] = result[subject].rank(method="min", ascending=False).astype(int)
    show_df(result[["學生姓名", subject, "該科排名"]])

def plot_student(name):
    result = df[df["學生姓名"] == name]
    if result.empty:
        return
    scores = result.iloc[0][SUBJECTS]
    
    fig = Figure(figsize=(6, 4), dpi=100)
    ax = fig.add_subplot(121)
    ax.bar(scores.index, scores.values, color="#4a90e4")
    ax.set_title(f"{name} 各科成績", fontsize=12, fontweight="bold")
    ax.set_xlabel("科目", fontsize=10)
    ax.set_ylabel("分數", fontsize=10)
    ax.set_ylim(0, 100)
    for i, v in enumerate(scores.values):
        ax.text(i, v + 1, str(v), ha="center", va="bottom", fontsize=9)
    
    ax2 = fig.add_subplot(122)
    ax2.axis("off")
    table = ax2.table(
        cellText=[scores.values],
        colLabels=scores.index,
        rowLabels=[name],
        loc="center",
        cellLoc="center"
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.3)
    
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

def plot_class_total():
    fig = Figure(figsize=(8, 4), dpi=100)
    ax = fig.add_subplot(111)
    sorted_df = df.sort_values(by="總分", ascending=False)
    ax.bar(sorted_df["學生姓名"], sorted_df["總分"], color="#2ecc71")
    ax.set_title("全班總分分佈", fontsize=14, fontweight="bold")
    ax.set_xlabel("學生姓名", fontsize=11)
    ax.set_ylabel("總分", fontsize=11)
    ax.set_ylim(0, sorted_df["總分"].max() + 10)
    for i, v in enumerate(sorted_df["總分"]):
        ax.text(i, v + 1, str(v), ha="center", va="bottom", fontsize=9)
    ax.tick_params(axis="x", rotation=45)
    
    canvas = FigureCanvasTkAgg(fig, master=stat_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

def plot_subject_avg():
    fig = Figure(figsize=(8, 4), dpi=100)
    ax = fig.add_subplot(111)
    avg_scores = df[SUBJECTS].mean()
    ax.bar(avg_scores.index, avg_scores.values, color="#ff8c4a")
    ax.set_title("各科平均成績", fontsize=14, fontweight="bold")
    ax.set_xlabel("科目", fontsize=11)
    ax.set_ylabel("平均分數", fontsize=11)
    ax.set_ylim(0, avg_scores.max() + 5)
    for i, v in enumerate(avg_scores.values):
        ax.text(i, v + 1, f"{v:.1f}", ha="center", va="bottom", fontsize=9)
    
    canvas = FigureCanvasTkAgg(fig, master=stat_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

def create_labeled_frame(title):
    frame = tk.Frame(root, bg=COLOR_FRAME_BG, relief="flat")
    frame.pack(fill="x", padx=20, pady=(15, 5))

    header = tk.Label(
        frame,
        text=title,
        bg=COLOR_HEADER,
        fg=COLOR_HEADER_TEXT,
        font=("Microsoft YaHei UI", 12, "bold"),
        padx=10,
        pady=8
    )
    header.pack(fill="x")

    content = tk.Frame(frame, bg=COLOR_FRAME_BG)
    content.pack(fill="x", padx=10, pady=10)
    return content

frame1 = create_labeled_frame("1. 依學生姓名搜尋")
tk.Label(frame1, text="學生姓名：", bg=COLOR_FRAME_BG, font=("Microsoft YaHei UI", 11)).grid(row=0, column=0, sticky="w", padx=5, pady=8)
entry_name = tk.Entry(frame1, width=20, bg=COLOR_ENTRY_BG, fg=COLOR_ENTRY_FG, font=("Microsoft YaHei UI", 11), relief="flat", highlightthickness=2, highlightbackground="#d0e0f0")
entry_name.grid(row=0, column=1, padx=5, pady=8)
btn_search = tk.Button(frame1, text="搜尋", command=search_student, width=10,
                       bg=COLOR_BTN_SEARCH, fg=COLOR_BTN_SEARCH_TEXT, font=("Microsoft YaHei UI", 11, "bold"),
                       relief="flat", activebackground="#357abd", activeforeground="#ffffff")
btn_search.grid(row=0, column=2, padx=5, pady=8)
btn_plot = tk.Button(frame1, text="個人圖表", command=lambda: plot_student(entry_name.get().strip()), width=12,
                     bg=COLOR_BTN_PLOT, fg=COLOR_BTN_PLOT_TEXT, font=("Microsoft YaHei UI", 11, "bold"),
                     relief="flat", activebackground="#e57a3a", activeforeground="#ffffff")
btn_plot.grid(row=0, column=3, padx=5, pady=8)

frame2 = create_labeled_frame("2. 查詢全班前幾名")
tk.Label(frame2, text="前幾名：", bg=COLOR_FRAME_BG, font=("Microsoft YaHei UI", 11)).grid(row=0, column=0, sticky="w", padx=5, pady=8)
entry_top_n = tk.Entry(frame2, width=10, bg=COLOR_ENTRY_BG, fg=COLOR_ENTRY_FG, font=("Microsoft YaHei UI", 11), relief="flat", highlightthickness=2, highlightbackground="#d0e0f0")
entry_top_n.insert(0, "5")
entry_top_n.grid(row=0, column=1, padx=5, pady=8)
btn_top = tk.Button(frame2, text="查詢總分排名", command=top_students, width=14,
                    bg=COLOR_BTN_TOP, fg=COLOR_BTN_TOP_TEXT, font=("Microsoft YaHei UI", 11, "bold"),
                    relief="flat", activebackground="#25b85a", activeforeground="#ffffff")
btn_top.grid(row=0, column=2, padx=5, pady=8)

frame3 = create_labeled_frame("3. 查詢科目前幾名")
tk.Label(frame3, text="科目：", bg=COLOR_FRAME_BG, font=("Microsoft YaHei UI", 11)).grid(row=0, column=0, sticky="w", padx=5, pady=8)
combo_subject = ttk.Combobox(frame3, values=SUBJECTS, width=12, state="readonly")
combo_subject.current(0)
combo_subject.pack_forget()
combo_subject.grid(row=0, column=1, padx=5, pady=8)
tk.Label(frame3, text="前幾名：", bg=COLOR_FRAME_BG, font=("Microsoft YaHei UI", 11)).grid(row=0, column=2, sticky="w", padx=5, pady=8)
entry_subject_n = tk.Entry(frame3, width=10, bg=COLOR_ENTRY_BG, fg=COLOR_ENTRY_FG, font=("Microsoft YaHei UI", 11), relief="flat", highlightthickness=2, highlightbackground="#d0e0f0")
entry_subject_n.insert(0, "5")
entry_subject_n.grid(row=0, column=3, padx=5, pady=8)
btn_subject = tk.Button(frame3, text="查詢科目排名", command=top_subject, width=14,
                        bg=COLOR_BTN_TOP, fg=COLOR_BTN_TOP_TEXT, font=("Microsoft YaHei UI", 11, "bold"),
                        relief="flat", activebackground="#25b85a", activeforeground="#ffffff")
btn_subject.grid(row=0, column=4, padx=5, pady=8)

frame4 = tk.Frame(root, bg=COLOR_FRAME_BG)
frame4.pack(fill="both", expand=True, padx=20, pady=(10, 10))
title_label = tk.Label(frame4, text="查詢結果", bg=COLOR_FRAME_BG, fg=COLOR_HEADER, font=("Microsoft YaHei UI", 13, "bold"))
title_label.pack(anchor="w", pady=(0, 5))
columns = ["學生姓名"] + SUBJECTS + ["總分", "總排名"]
tree = ttk.Treeview(frame4, columns=columns, show="headings", height=15)
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=100, anchor="center")
style = ttk.Style()
style.configure("Treeview", font=("Microsoft YaHei UI", 11), rowheight=30)
style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 12, "bold"))
tree.pack(side="left", fill="both", expand=True)
scrollbar = ttk.Scrollbar(frame4, orient="vertical", command=tree.yview)
scrollbar.pack(side="right", fill="y")
tree.configure(yscrollcommand=scrollbar.set)

stat_frame = tk.Frame(root, bg=COLOR_FRAME_BG)
stat_frame.pack(fill="x", padx=20, pady=(10, 5))
stat_header = tk.Label(stat_frame, text="統計圖表", bg=COLOR_HEADER, fg=COLOR_HEADER_TEXT, font=("Microsoft YaHei UI", 13, "bold"), padx=10, pady=8)
stat_header.pack(fill="x")
stat_content = tk.Frame(stat_frame, bg=COLOR_FRAME_BG)
stat_content.pack(fill="x", padx=10, pady=10)
btn_total = tk.Button(stat_content, text="全班總分分佈", command=plot_class_total, width=15,
                      bg=COLOR_BTN_TOP, fg=COLOR_BTN_TOP_TEXT, font=("Microsoft YaHei UI", 11, "bold"),
                      relief="flat", activebackground="#25b85a", activeforeground="#ffffff")
btn_total.pack(side="left", padx=5)
btn_avg = tk.Button(stat_content, text="各科平均成績", command=plot_subject_avg, width=15,
                    bg=COLOR_BTN_PLOT, fg=COLOR_BTN_PLOT_TEXT, font=("Microsoft YaHei UI", 11, "bold"),
                    relief="flat", activebackground="#e57a3a", activeforeground="#ffffff")
btn_avg.pack(side="left", padx=5)

plot_frame = tk.Frame(root, bg=COLOR_FRAME_BG)
plot_frame.pack(fill="both", expand=True, padx=20, pady=(5, 20))
plot_header = tk.Label(plot_frame, text="個人成績圖表與表格", bg=COLOR_HEADER, fg=COLOR_HEADER_TEXT, font=("Microsoft YaHei UI", 13, "bold"), padx=10, pady=8)
plot_header.pack(fill="x")
plot_content = tk.Frame(plot_frame, bg=COLOR_FRAME_BG)
plot_content.pack(fill="both", expand=True, padx=10, pady=10)

show_df(df[["學生姓名"] + SUBJECTS + ["總分", "總排名"]])
root.mainloop() 