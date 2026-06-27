import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
import re

plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False

STOCK_MAP = {
    '奇鈦科': '3430.TWO',
    '台積電': '2330.TW',
    '鴻海': '2317.TW',
    '聯發科': '2454.TW',
    '台達電': '2308.TW',
    '中華電': '2412.TW',
    '富邦金': '2881.TW',
    '國泰金': '2882.TW',
    '中鋼': '2002.TW',
}

_CACHE = {}

def resolve_symbol(query):
    q = query.strip()
    if q in STOCK_MAP:
        return STOCK_MAP[q]
    if '.' in q:
        return q.upper()
    return q

def fetch_chinese_name(symbol):
    if symbol in _CACHE:
        return _CACHE[symbol]
    try:
        url = f'https://tw.stock.yahoo.com/quote/{symbol}'
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        r.encoding = 'utf-8'
        m = re.search(r'([\u4e00-\u9fff]{2,10})\(?' + re.escape(symbol.split('.')[0]) + r'\)?', r.text)
        name = m.group(1) if m else ''
        _CACHE[symbol] = name
        return name
    except Exception:
        return ''

EXCHANGE_MAP = {'TAI': '上市', 'TWO': '上櫃', 'ROC': '興櫃', 'OTC': '興櫃'}

def fetch_data(symbol):
    candidates = [symbol]
    if '.' not in symbol:
        candidates += [f"{symbol}.TW", f"{symbol}.TWO"]
    for sym in candidates:
        df = yf.download(sym, period="2y", auto_adjust=True, progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            try:
                info = yf.Ticker(sym).info
            except Exception:
                info = {}
            return sym, df, info
    return symbol, pd.DataFrame(), {}

class StockApp:
    def __init__(self, root):
        self.root = root
        root.title("臺灣股市查詢系統")
        root.geometry("1200x800")

        top = ttk.Frame(root)
        top.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(top, text="股票代碼或名稱:").pack(side=tk.LEFT)
        self.entry = ttk.Entry(top, width=20)
        self.entry.pack(side=tk.LEFT, padx=5)
        self.entry.bind('<Return>', lambda e: self.search())

        self.btn = ttk.Button(top, text="查詢", command=self.search)
        self.btn.pack(side=tk.LEFT, padx=5)

        self.info_frame = ttk.LabelFrame(root, text="最新交易日資訊")
        self.info_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.info_text = tk.StringVar()
        ttk.Label(self.info_frame, textvariable=self.info_text,
                  font=('Microsoft JhengHei', 11)).pack(padx=10, pady=8)

        self.fig = plt.Figure(figsize=(10, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def search(self):
        query = self.entry.get()
        if not query:
            return
        self.btn.config(state=tk.DISABLED, text="查詢中...")
        self.info_text.set("正在下載資料，請稍候...")
        self.ax.clear()
        self.canvas.draw()
        threading.Thread(target=self.worker, args=(query,), daemon=True).start()

    def worker(self, query):
        try:
            symbol = resolve_symbol(query)
            symbol, df, info = fetch_data(symbol)
            self.root.after(0, self.display_result, query, symbol, df, info)
        except Exception as e:
            self.root.after(0, self.show_error, str(e))

    def display_result(self, query, symbol, df, info):
        if df.empty:
            messagebox.showerror("錯誤", f"股票 {query} 無資料，可能代碼錯誤或已下市。")
            self.btn.config(state=tk.NORMAL, text="查詢")
            self.info_text.set("")
            return

        name = fetch_chinese_name(symbol) or info.get('longName') or info.get('shortName') or ''
        exchange_key = info.get('exchange', '')
        exchange = EXCHANGE_MAP.get(exchange_key, exchange_key)

        close = df['Close']
        latest_date = df.index[-1]
        info = (
            f"{name} ({symbol})    "
            f"市場: {exchange}    "
            f"期間: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}\n"
            f"最新交易日 ({latest_date.strftime('%Y-%m-%d')})    "
            f"開盤價: {df['Open'].iloc[-1]:.2f}    "
            f"最高價: {df['High'].iloc[-1]:.2f}    "
            f"最低價: {df['Low'].iloc[-1]:.2f}    "
            f"收盤價: {df['Close'].iloc[-1]:.2f}"
        )
        self.info_text.set(info)

        self.ax.clear()
        self.ax.plot(df.index, close, color='black', linewidth=1, label='日線')
        self.ax.plot(df.index, close.rolling(5).mean(), color='blue', linewidth=1.5, label='週線(5日)')
        self.ax.plot(df.index, close.rolling(20).mean(), color='green', linewidth=1.5, label='月線(20日)')
        self.ax.plot(df.index, close.rolling(60).mean(), color='orange', linewidth=1.5, label='季線(60日)')
        self.ax.plot(df.index, close.rolling(120).mean(), color='purple', linewidth=1.5, label='半年線(120日)')
        self.ax.plot(df.index, close.rolling(240).mean(), color='red', linewidth=1.5, label='年線(240日)')

        if not close.empty:
            h_idx = close.idxmax()
            l_idx = close.idxmin()
            self.ax.scatter(h_idx, close.loc[h_idx], color='red', s=50)
            self.ax.annotate(f'最高價 {close.loc[h_idx]:.2f}',
                             xy=(h_idx, close.loc[h_idx]),
                             xytext=(20, 0), textcoords='offset points',
                             arrowprops=dict(arrowstyle='->', color='red'),
                             fontsize=10, color='red', va='center')
            self.ax.scatter(l_idx, close.loc[l_idx], color='blue', s=50)
            self.ax.annotate(f'最低價 {close.loc[l_idx]:.2f}',
                             xy=(l_idx, close.loc[l_idx]),
                             xytext=(20, 0), textcoords='offset points',
                             arrowprops=dict(arrowstyle='->', color='blue'),
                             fontsize=10, color='blue', va='center')

        self.ax.set_title(f"{symbol} 近二年股價走勢", fontsize=14)
        self.ax.set_xlabel("日期", fontsize=11)
        self.ax.set_ylabel("股價(元)", fontsize=11)
        self.ax.grid(True, linestyle='--', alpha=0.4)
        self.ax.legend(fontsize=10)
        self.fig.autofmt_xdate()
        self.fig.tight_layout()
        self.canvas.draw()
        self.btn.config(state=tk.NORMAL, text="查詢")

    def show_error(self, msg):
        messagebox.showerror("錯誤", msg)
        self.btn.config(state=tk.NORMAL, text="查詢")
        self.info_text.set("")

if __name__ == '__main__':
    root = tk.Tk()
    app = StockApp(root)
    root.mainloop()
