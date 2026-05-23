import tkinter as tk
import random

class GuessNumberGame:
    def __init__(self, root):
        self.root = root
        self.root.title("猜數字遊戲")
        self.root.geometry("430x380")
        self.root.resizable(False, False)
        self.root.configure(bg="#EAF4FF")

        self.answer = random.randint(1, 100)
        self.count = 0

        # 標題
        title = tk.Label(
            root,
            text="🎯 猜數字遊戲",
            font=("Microsoft JhengHei", 24, "bold"),
            bg="#EAF4FF",
            fg="#1F4E79"
        )
        title.pack(pady=20)

        # 白色卡片區
        card = tk.Frame(root, bg="white")
        card.pack(padx=30, pady=10, fill="both", expand=True)

        # 提示文字
        self.hint_label = tk.Label(
            card,
            text="請猜 1 到 100 的數字",
            font=("Microsoft JhengHei", 14),
            bg="white",
            fg="#333333"
        )
        self.hint_label.pack(pady=20)

        # 輸入框
        self.entry = tk.Entry(
            card,
            font=("Microsoft JhengHei", 24, "bold"),
            justify="center",
            width=8,
            bd=2,
            relief="solid"
        )
        self.entry.pack(pady=10)
        self.entry.bind("<Return>", lambda event: self.check_guess())

        # 結果顯示區
        self.result_label = tk.Label(
            card,
            text="開始遊戲吧！",
            font=("Microsoft JhengHei", 14, "bold"),
            bg="white",
            fg="#555555"
        )
        self.result_label.pack(pady=20)

        # 次數顯示
        self.count_label = tk.Label(
            card,
            text="猜測次數：0",
            font=("Microsoft JhengHei", 12),
            bg="white",
            fg="#666666"
        )
        self.count_label.pack()

        # 按鈕區
        button_frame = tk.Frame(card, bg="white")
        button_frame.pack(pady=25)

        # 猜測按鈕
        guess_button = tk.Button(
            button_frame,
            text="送出答案",
            font=("Microsoft JhengHei", 12, "bold"),
            bg="#2F80ED",
            fg="white",
            width=12,
            height=1,
            bd=0,
            cursor="hand2",
            activebackground="#1C5DB8",
            command=self.check_guess
        )
        guess_button.grid(row=0, column=0, padx=10)

        # 重新開始按鈕
        restart_button = tk.Button(
            button_frame,
            text="重新開始",
            font=("Microsoft JhengHei", 12, "bold"),
            bg="#27AE60",
            fg="white",
            width=12,
            height=1,
            bd=0,
            cursor="hand2",
            activebackground="#1E8449",
            command=self.restart_game
        )
        restart_button.grid(row=0, column=1, padx=10)

    def check_guess(self):
        value = self.entry.get()

        # 防呆
        if not value.isdigit():
            self.result_label.config(
                text="⚠️ 請輸入有效數字！",
                fg="#E74C3C"
            )
            return

        guess = int(value)

        if guess < 1 or guess > 100:
            self.result_label.config(
                text="⚠️ 請輸入 1~100",
                fg="#E74C3C"
            )
            return

        self.count += 1
        self.count_label.config(text=f"猜測次數：{self.count}")

        # 判斷答案
        if guess > self.answer:
            self.result_label.config(
                text="📉 太大了！",
                fg="#E67E22"
            )

        elif guess < self.answer:
            self.result_label.config(
                text="📈 太小了！",
                fg="#3498DB"
            )

        else:
            self.result_label.config(
                text=f"🎉 恭喜答對！答案是 {self.answer}",
                fg="#27AE60"
            )

        self.entry.delete(0, tk.END)

    def restart_game(self):
        self.answer = random.randint(1, 100)
        self.count = 0

        self.result_label.config(
            text="新遊戲開始！",
            fg="#555555"
        )

        self.count_label.config(
            text="猜測次數：0"
        )

        self.entry.delete(0, tk.END)


# 主程式
if __name__ == "__main__":
    root = tk.Tk()
    app = GuessNumberGame(root)
    root.mainloop()