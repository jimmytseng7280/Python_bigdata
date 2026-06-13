import tkinter as tk
from tkinter import messagebox
from threading import Thread
from pathlib import Path

import requests
from requests import Response
import pandas as pd
from pandas import DataFrame
import report20


def generate_report(output_file: Path, status_var: tk.StringVar) -> None:
    url: str = "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json"

    try:
        response: Response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data: list[dict] = response.json()
            df: DataFrame = pd.DataFrame(data=data)
            report20.export_to_pdf(df, output_file)
            status_var.set(f"PDF 已產生：{output_file}")
            messagebox.showinfo("完成", f"PDF 已產生：{output_file}")
        else:
            status_var.set("下載失敗")
            messagebox.showerror("錯誤", "下載失敗")
    except Exception as exc:
        status_var.set(f"發生錯誤：{exc}")
        messagebox.showerror("錯誤", str(exc))


def build_gui() -> None:
    root = tk.Tk()
    root.title("YouBike 即時報表")
    root.geometry("420x180")
    root.resizable(False, False)

    tk.Label(
        root,
        text="點擊按鈕下載 YouBike 即時資料並產生 PDF 報表",
        wraplength=360,
        justify="center",
    ).pack(pady=16)

    status_var = tk.StringVar(value="待執行")
    tk.Label(root, textvariable=status_var, fg="blue").pack(pady=(0, 10))

    def on_click() -> None:
        status_var.set("正在下載並生成報表...")
        output_file = Path(__file__).with_name("youbike_report20.pdf")
        thread = Thread(target=generate_report, args=(output_file, status_var), daemon=True)
        thread.start()

    tk.Button(root, text="產生報表", width=20, command=on_click).pack()

    root.mainloop()


if __name__ == "__main__":
    build_gui()