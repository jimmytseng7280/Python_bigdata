import tkinter as tk
from tkinter import messagebox
import random

class GuessNumberGame:
    def __init__(self, root):
        self.root = root
        self.root.title("猜數字遊戲")
        self.root.geometry("360x260")
        self.root.resizable(False, False)

        self.answer = random.randint(1, 100)
        self.count = 0

        tk.Label(root, text="猜數字遊戲", font=("Microsoft JhengHei", 20, "bold")).pack(pady=15)
        tk.Label(root, text="請猜 1 到 100 的數字", font=("Microsoft JhengHei", 12)).pack()

        self.entry = tk.Entry(root, font=("Microsoft JhengHei", 14), justify="center")
        self.entry.pack(pady=12)
        self.entry.bind("<Return>", lambda event: self.check_guess())

        tk.Button(
            root,
            text="送出答案",
            font=("Microsoft JhengHei", 12),
            command=self.check_guess
        ).pack(pady=5)

        self.result_label = tk.Label(root, text="請輸入數字開始遊戲", font=("Microsoft JhengHei", 12))
        self.result_label.pack(pady=10)

        tk.Button(
            root,
            text="重新開始",
            font=("Microsoft JhengHei", 11),
            command=self.restart_game
        ).pack()

    def check_guess(self):
        try:
            guess = int(self.entry.get())
        except ValueError:
            messagebox.showwarning("輸入錯誤", "請輸入有效的整數！")
            return

        if guess < 1 or guess > 100:
            messagebox.showwarning("範圍錯誤", "請輸入 1 到 100 之間的數字！")
            return

        self.count += 1

        if guess > self.answer:
            self.result_label.config(text=f"太大了！目前猜了 {self.count} 次")
        elif guess < self.answer:
            self.result_label.config(text=f"太小了！目前猜了 {self.count} 次")
        else:
            messagebox.showinfo("恭喜答對", f"答對了！答案是 {self.answer}\n你總共猜了 {self.count} 次")
            self.restart_game()

        self.entry.delete(0, tk.END)

    def restart_game(self):
        self.answer = random.randint(1, 100)
        self.count = 0
        self.result_label.config(text="新遊戲開始！請輸入數字")
        self.entry.delete(0, tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = GuessNumberGame(root)
    root.mainloop()