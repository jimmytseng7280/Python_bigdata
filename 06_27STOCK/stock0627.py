# 匯入所需套件
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('TkAgg')                     # 使用 Tkinter 後端
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
import re
import urllib3
import datetime
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設定中文字型（微軟正黑體）
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False

# 全域快取與預載資料
_CACHE = {}                                 # 存放爬取結果（中文名、市場別等）
_MARKET_SETS = {}                           # 存放各市場股票代碼集合
_NAME_MAP = {}                              # 存放中文名稱→股票代號對照
_MARKET_READY = False                       # 預載是否完成

def resolve_symbol(query):
    """將使用者輸入解析為 Yahoo Finance 可用的股票代號"""
    q = query.strip()
    if '.' in q:                            # 已包含後綴（如 2330.TW）
        return q.upper()
    if q.isdigit():                         # 純數字，直接回傳
        return q
    if q in _NAME_MAP:                      # 精確比對中文名
        return _NAME_MAP[q]
    for name, sym in _NAME_MAP.items():      # 模糊比對中文名
        if q in name:
            return sym
    return q

def fetch_chinese_name(symbol):
    """從 Yahoo 奇摩股市爬取股票中文名稱"""
    if symbol in _CACHE:
        return _CACHE[symbol]
    try:
        url = f'https://tw.stock.yahoo.com/quote/{symbol}'
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        r.encoding = 'utf-8'
        # 在頁面中尋找「中文名(代碼)」的 pattern
        m = re.search(r'([\u4e00-\u9fff]{2,10})\(?' + re.escape(symbol.split('.')[0]) + r'\)?', r.text)
        name = m.group(1) if m else ''
        _CACHE[symbol] = name
        return name
    except Exception:
        return ''

def preload_market_data():
    """預載三大市場（上市、上櫃、興櫃）股票代碼與中文名稱"""
    global _MARKET_READY

    # 從 TWSE 下載上市股票清單
    try:
        r = requests.get('https://openapi.twse.com.tw/v1/opendata/t187ap03_L',
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        twse = r.json()
        code_key = [k for k in twse[0] if '代號' in k][0]
        abbr_key = [k for k in twse[0] if '簡稱' in k][0]
        name_key = [k for k in twse[0] if '名稱' in k][0]
        _MARKET_SETS['上市'] = set()
        for item in twse:
            code = item[code_key]
            _MARKET_SETS['上市'].add(code)
            for k in (abbr_key, name_key):
                v = item[k].strip()
                if v and v not in _NAME_MAP:
                    _NAME_MAP[v] = f'{code}.TW'
    except Exception:
        _MARKET_SETS['上市'] = set()

    # 從 TPEx 下載上櫃股票清單
    try:
        r = requests.get('https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O',
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=15, verify=False)
        data = r.json()
        _MARKET_SETS['上櫃'] = set()
        for item in data:
            code = item['SecuritiesCompanyCode']
            _MARKET_SETS['上櫃'].add(code)
            for k in ('CompanyAbbreviation', 'CompanyName'):
                v = item[k].strip()
                if v and v not in _NAME_MAP:
                    _NAME_MAP[v] = f'{code}.TWO'
    except Exception:
        _MARKET_SETS['上櫃'] = set()

    # 從 TPEx 下載興櫃股票清單
    try:
        r = requests.get('https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_R',
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=15, verify=False)
        data = r.json()
        _MARKET_SETS['興櫃'] = set()
        for item in data:
            code = item['SecuritiesCompanyCode']
            _MARKET_SETS['興櫃'].add(code)
            for k in ('CompanyAbbreviation', 'CompanyName'):
                v = item[k].strip()
                if v and v not in _NAME_MAP:
                    _NAME_MAP[v] = f'{code}.TWO'
    except Exception:
        _MARKET_SETS['興櫃'] = set()

    _MARKET_READY = True

def get_market_type(code):
    """根據股票代碼回傳市場別（上市/上櫃/興櫃）"""
    for market in ('上市', '上櫃', '興櫃'):
        if code in _MARKET_SETS.get(market, set()):
            return market
    return '未知'

def fetch_data(symbol, start_date=None, end_date=None):
    """從 yfinance 下載股價資料，自動嘗試 .TW / .TWO 後綴"""
    candidates = [symbol]
    if '.' not in symbol:
        candidates += [f"{symbol}.TW", f"{symbol}.TWO"]
    for sym in candidates:
        kwargs = {'auto_adjust': True, 'progress': False}
        if start_date and end_date:
            kwargs['start'] = start_date
            kwargs['end'] = end_date
        else:
            kwargs['period'] = '2y'
        df = yf.download(sym, **kwargs)
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
    """臺灣股市查詢系統主視窗"""

    def __init__(self, root):
        self.root = root
        root.title("臺灣股市查詢系統")
        root.geometry("1200x800")

        # 上方：股票輸入列
        top = ttk.Frame(root)
        top.pack(fill=tk.X, padx=10, pady=(10, 0))

        ttk.Label(top, text="股票代碼或名稱:").pack(side=tk.LEFT)
        self.entry = ttk.Entry(top, width=20)
        self.entry.pack(side=tk.LEFT, padx=5)
        self.entry.bind('<Return>', lambda e: self.search())

        self.btn = ttk.Button(top, text="查詢", command=self.search)
        self.btn.pack(side=tk.LEFT, padx=5)

        self.status_var = tk.StringVar(value="正在載入上市/上櫃/興櫃資料...")
        self.status_label = ttk.Label(top, textvariable=self.status_var, foreground='gray')
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # 中間：日期輸入列
        date_frame = ttk.Frame(root)
        date_frame.pack(fill=tk.X, padx=10, pady=5)

        today = datetime.datetime.today()
        default_start = (today - datetime.timedelta(days=730)).strftime('%Y-%m-%d')
        default_end = today.strftime('%Y-%m-%d')

        ttk.Label(date_frame, text="開始日期:").pack(side=tk.LEFT)
        self.start_entry = ttk.Entry(date_frame, width=12)
        self.start_entry.pack(side=tk.LEFT, padx=(2, 10))
        self.start_entry.insert(0, default_start)

        ttk.Label(date_frame, text="結束日期:").pack(side=tk.LEFT)
        self.end_entry = ttk.Entry(date_frame, width=12)
        self.end_entry.pack(side=tk.LEFT, padx=(2, 5))
        self.end_entry.insert(0, default_end)

        ttk.Label(date_frame, text="(YYYY-MM-DD)", foreground='gray', font=('', 9)).pack(side=tk.LEFT)

        # 資訊區：顯示最新交易日資料
        self.info_frame = ttk.LabelFrame(root, text="最新交易日資訊")
        self.info_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.info_text = tk.StringVar()
        ttk.Label(self.info_frame, textvariable=self.info_text,
                  font=('Microsoft JhengHei', 11)).pack(padx=10, pady=8)

        # 圖表區：嵌入 matplotlib
        self.fig = plt.Figure(figsize=(10, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 背景執行預載
        threading.Thread(target=self.init_market_data, daemon=True).start()

    def init_market_data(self):
        """背景執行市場資料預載"""
        preload_market_data()
        self.root.after(0, self.on_market_ready)

    def on_market_ready(self):
        """預載完成後更新狀態列"""
        counts = []
        for m in ('上市', '上櫃', '興櫃'):
            n = len(_MARKET_SETS.get(m, set()))
            counts.append(f'{m}{n}檔')
        self.status_var.set(f'已載入 ' + ' '.join(counts))

    def search(self):
        """查詢按鈕點擊或按下 Enter 時觸發"""
        query = self.entry.get()
        if not query:
            return
        start_text = self.start_entry.get().strip()
        end_text = self.end_entry.get().strip()
        # 驗證日期格式
        try:
            if start_text and end_text:
                datetime.datetime.strptime(start_text, '%Y-%m-%d')
                datetime.datetime.strptime(end_text, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("錯誤", "日期格式錯誤，請使用 YYYY-MM-DD")
            return
        self.btn.config(state=tk.DISABLED, text="查詢中...")
        self.info_text.set("正在下載資料，請稍候...")
        self.ax.clear()
        self.canvas.draw()
        threading.Thread(target=self.worker, args=(query, start_text, end_text), daemon=True).start()

    def worker(self, query, start_date, end_date):
        """背景執行下載與資料處理"""
        try:
            symbol = resolve_symbol(query)
            symbol, df, info = fetch_data(symbol, start_date, end_date)
            self.root.after(0, self.display_result, query, symbol, df, info)
        except Exception as e:
            self.root.after(0, self.show_error, str(e))

    def display_result(self, query, symbol, df, info):
        """將查詢結果顯示在 GUI 上"""
        if df.empty:
            messagebox.showerror("錯誤", f"股票 {query} 無資料，可能代碼錯誤或已下市。")
            self.btn.config(state=tk.NORMAL, text="查詢")
            self.info_text.set("")
            return

        # 取得中文名稱與市場別
        name = fetch_chinese_name(symbol) or info.get('longName') or info.get('shortName') or ''
        code = symbol.split('.')[0]
        exchange = get_market_type(code)

        # 更新資訊區
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

        # 繪製均線圖
        self.ax.clear()
        self.ax.plot(df.index, close, color='black', linewidth=1, label='日線')
        self.ax.plot(df.index, close.rolling(5).mean(), color='blue', linewidth=1.5, label='週線(5日)')
        self.ax.plot(df.index, close.rolling(20).mean(), color='green', linewidth=1.5, label='月線(20日)')
        self.ax.plot(df.index, close.rolling(60).mean(), color='orange', linewidth=1.5, label='季線(60日)')
        self.ax.plot(df.index, close.rolling(120).mean(), color='purple', linewidth=1.5, label='半年線(120日)')
        self.ax.plot(df.index, close.rolling(240).mean(), color='red', linewidth=1.5, label='年線(240日)')

        # 標示最高點與最低點
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

        # 圖表格式設定
        start_str = df.index[0].strftime('%Y-%m-%d')
        end_str = df.index[-1].strftime('%Y-%m-%d')
        self.ax.set_title(f"{symbol} ({start_str} ~ {end_str})", fontsize=14)
        self.ax.set_xlabel("日期", fontsize=11)
        self.ax.set_ylabel("股價(元)", fontsize=11)
        self.ax.grid(True, linestyle='--', alpha=0.4)
        self.ax.legend(fontsize=10)
        self.fig.autofmt_xdate()
        self.fig.tight_layout()
        self.canvas.draw()
        self.btn.config(state=tk.NORMAL, text="查詢")

    def show_error(self, msg):
        """顯示錯誤訊息"""
        messagebox.showerror("錯誤", msg)
        self.btn.config(state=tk.NORMAL, text="查詢")
        self.info_text.set("")

if __name__ == '__main__':
    root = tk.Tk()
    app = StockApp(root)
    root.mainloop()
