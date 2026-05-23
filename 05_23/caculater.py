import tkinter as tk
from tkinter import messagebox


def append_char(entry, char):
    entry.insert(tk.END, char)


def clear_entry(entry):
    entry.delete(0, tk.END)


def calculate(entry):
    expression = entry.get()
    try:
        result = eval(expression)
        entry.delete(0, tk.END)
        entry.insert(tk.END, str(result))
    except ZeroDivisionError:
        messagebox.showerror("錯誤", "不能除以零")
    except Exception:
        messagebox.showerror("錯誤", "無效的運算式")


def create_calculator():
    root = tk.Tk()
    root.title("簡易計算機")
    root.resizable(False, False)

    entry = tk.Entry(root, font=("Arial", 24), justify=tk.RIGHT, bd=5, relief=tk.RIDGE)
    entry.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky="we")

    buttons = [
        ("7", 1, 0), ("8", 1, 1), ("9", 1, 2), ("/", 1, 3),
        ("4", 2, 0), ("5", 2, 1), ("6", 2, 2), ("*", 2, 3),
        ("1", 3, 0), ("2", 3, 1), ("3", 3, 2), ("-", 3, 3),
        ("0", 4, 0), (".", 4, 1), ("=", 4, 2), ("+", 4, 3),
    ]

    for (text, row, col) in buttons:
        if text == "=":
            action = lambda e=entry: calculate(e)
        else:
            action = lambda char=text, e=entry: append_char(e, char)
        tk.Button(root, text=text, width=5, height=2, font=("Arial", 18), command=action).grid(row=row, column=col, padx=5, pady=5)

    tk.Button(root, text="C", width=5, height=2, font=("Arial", 18), command=lambda: clear_entry(entry)).grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky="we")
    tk.Button(root, text="()", width=5, height=2, font=("Arial", 18), command=lambda: append_char(entry, "()")).grid(row=5, column=2, padx=5, pady=5)
    tk.Button(root, text="^", width=5, height=2, font=("Arial", 18), command=lambda: append_char(entry, "**")).grid(row=5, column=3, padx=5, pady=5)

    root.mainloop()


if __name__ == "__main__":
    create_calculator()
