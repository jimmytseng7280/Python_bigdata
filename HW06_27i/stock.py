# 匯入所需套件
import yfinance as yf
import pandas as pd
import numpy as np
import platform
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
import re
import urllib3
import datetime
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 跨平台中文字型設定
_IS_MAC = platform.system() == 'Darwin'
_CHINESE_FONT = 'PingFang TC' if _IS_MAC else 'Microsoft JhengHei'

# twstock 中文名稱對照
try:
    import twstock
    twstock.__update_codes()
    _TW_NAME = {}
    for code, info in twstock.codes.items():
        if getattr(info, 'type', '') == '股票' and getattr(info, 'name', '') and getattr(info, 'market', '') in ('上市', '上櫃'):
            suffix = '.TW' if info.market == '上市' else '.TWO'
            _TW_NAME[f"{code}{suffix}"] = f"{info.name}({code})"
except Exception:
    _TW_NAME = {}

def label_from_symbol(symbol):
    """從 twstock 或快取中取得中文標籤"""
    if symbol in _TW_NAME:
        return _TW_NAME[symbol]
    base = symbol.split('.')[0]
    if base in _TW_NAME:
        return _TW_NAME[base]
    name = fetch_chinese_name(symbol)
    return f"{name}({base})" if name else base

# 設定中文字型（微軟正黑體）
plt.rcParams['font.sans-serif'] = [_CHINESE_FONT, 'PingFang TC', 'Heiti TC', 'Microsoft JhengHei', 'Noto Sans CJK TC']
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

def calc_kd(df, n=9, k_smooth=3, d_smooth=3):
    """計算 KD 指標（隨機震盪指標）"""
    low_n = df['Low'].rolling(n).min()
    high_n = df['High'].rolling(n).max()
    rsv = (df['Close'] - low_n) / (high_n - low_n) * 100
    k = rsv.ewm(span=k_smooth, adjust=False).mean()
    d = k.ewm(span=d_smooth, adjust=False).mean()
    return k, d

def calc_correlation(target_symbol, start_date=None, end_date=None):
    """計算目標股票與全部上市/上櫃股票的日報酬率相關係數，回傳前5名
    使用範圍式下載（已被 top5_corr.py 驗證可運作）"""
    import warnings
    import numpy as _np
    warnings.filterwarnings('ignore')

    target_code = target_symbol.split('.')[0]
    if '.' not in target_symbol:
        target = f"{target_code}.TW"
    else:
        target = target_symbol

    # 範圍式代碼（與 top5_corr.py 一致）
    all_tickers = [f"{i:04d}.TW" for i in range(1000, 2500)] + \
                  [f"{i:04d}.TWO" for i in range(6000, 7000)]
    if target not in all_tickers:
        all_tickers.insert(0, target)

    total = len(all_tickers)
    if total == 0:
        yield 0, 0, []
        return

    batch_size = 500
    all_close = {}
    for i in range(0, total, batch_size):
        batch = all_tickers[i:i + batch_size]
        try:
            kwargs = {'auto_adjust': True, 'progress': False, 'threads': True}
            if start_date and end_date:
                kwargs['start'] = start_date
                kwargs['end'] = end_date
            else:
                kwargs['period'] = '2y'
            df_batch = yf.download(batch, **kwargs)
            if df_batch.empty:
                yield min(i + batch_size, total), total, []
                continue
            if isinstance(df_batch.columns, pd.MultiIndex):
                close_cols = df_batch['Close']
                for ticker in batch:
                    if ticker in close_cols.columns:
                        s = close_cols[ticker].dropna()
                        if len(s) >= 30:
                            all_close[ticker] = s
            elif not df_batch.empty and len(batch) == 1:
                s = df_batch['Close'].dropna()
                if len(s) >= 30:
                    all_close[batch[0]] = s
        except Exception:
            pass
        yield min(i + batch_size, total), total, []

    if not all_close:
        yield total, total, []
        return

    # 組合成 DataFrame，一次計算相關係數
    close_df = pd.DataFrame(all_close)

    # 確認目標存在
    target_col = None
    for col in close_df.columns:
        if col == target or col.split('.')[0] == target_code:
            target_col = col
            break
    if target_col is None:
        yield total, total, []
        return

    # 計算日報酬率
    returns = close_df.pct_change().replace([_np.inf, -_np.inf], _np.nan).dropna(axis=0, how='all')
    if target_col not in returns.columns:
        yield total, total, []
        return

    target_ret = returns[target_col].dropna()

    # 計算與目標的相關係數
    results = []
    for col in returns.columns:
        if col == target_col:
            continue
        other_ret = returns[col].dropna()
        common = target_ret.index.intersection(other_ret.index)
        if len(common) < 30:
            continue
        corr_val = target_ret.loc[common].corr(other_ret.loc[common])
        if pd.isna(corr_val):
            continue
        code = col.split('.')[0]
        name = label_from_symbol(col)
        results.append((col, name, float(corr_val)))

    results.sort(key=lambda x: abs(x[2]), reverse=True)
    yield total, total, results[:5]

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
        root.geometry("1400x900")
        root.protocol("WM_DELETE_WINDOW", self._on_close)

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

        ttk.Label(date_frame, text="    預測天數:").pack(side=tk.LEFT)
        self.pred_days = tk.StringVar(value="30")
        pred_combo = ttk.Combobox(date_frame, textvariable=self.pred_days,
                                  values=["0", "5", "10", "15", "20", "30", "60", "90", "120"], width=5, state='readonly')
        pred_combo.pack(side=tk.LEFT, padx=2)
        ttk.Label(date_frame, text="(0=不預測)", foreground='gray', font=('', 9)).pack(side=tk.LEFT)

        ttk.Label(date_frame, text="    預測方法:").pack(side=tk.LEFT)
        self.pred_method = tk.StringVar(value="多項式")
        method_combo = ttk.Combobox(date_frame, textvariable=self.pred_method,
                                    values=["全部", "線性", "多項式", "蒙地卡羅", "指數平滑", "MA交叉", "布林通道"],
                                    width=8, state='readonly')
        method_combo.pack(side=tk.LEFT, padx=2)

        # 資訊區：顯示最新交易日資料
        self.info_frame = ttk.LabelFrame(root, text="最新交易日資訊")
        self.info_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        self.info_text = tk.StringVar()
        ttk.Label(self.info_frame, textvariable=self.info_text,
                  font=(_CHINESE_FONT, 11)).pack(padx=10, pady=8)

        # 相關係數區：顯示前五名高相關股票
        self.corr_frame = ttk.LabelFrame(root, text="日報酬率相關係數 Top 5")
        self.corr_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        self.corr_text = tk.StringVar(value="查詢後自動計算...")
        ttk.Label(self.corr_frame, textvariable=self.corr_text,
                  font=(_CHINESE_FONT, 10), justify=tk.LEFT).pack(padx=10, pady=6, anchor=tk.W)

        # 旋轉動畫狀態
        self._spinner_running = False
        self._spinner_idx = 0
        self._corr_generation = 0  # 用來取消舊的相關係數查詢

        # 深色主題色彩
        self._bg_color = '#1a1a2e'
        self._ax_color = '#16213e'
        self._grid_color = '#333333'
        self._text_color = '#e0e0e0'

        # 圖表區：3個子圖（K線、成交量、KD），共用X軸
        self.fig, (self.ax, self.ax_vol, self.ax_kd) = plt.subplots(
            3, 1, figsize=(13, 8.5), dpi=100,
            gridspec_kw={'height_ratios': [4, 1, 1.2]},
            sharex=True)
        self.fig.set_facecolor(self._bg_color)
        self.fig.subplots_adjust(hspace=0.04, left=0.06, right=0.93, top=0.99, bottom=0.04)
        for ax in (self.ax, self.ax_vol, self.ax_kd):
            ax.set_facecolor(self._ax_color)
            ax.tick_params(colors=self._text_color)
            ax.xaxis.label.set_color(self._text_color)
            ax.yaxis.label.set_color(self._text_color)
            for spine in ax.spines.values():
                spine.set_color(self._grid_color)
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 0))
        self.canvas.draw()

        # 圖表互動：滾輪縮放、拖曳平移、點擊/hover 顯示資訊、雙擊還原
        self.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.canvas.mpl_connect('button_press_event', self._on_press)
        self.canvas.mpl_connect('button_release_event', self._on_release)
        self.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self.canvas.mpl_connect('motion_notify_event', self._on_hover)
        self._dragging = False
        self._drag_start = None
        self._drag_xlim_start = None
        self._press_x = None
        self._press_y = None
        self._pressed_in_ax = None
        self._click_annotation = None
        self._vline = None
        self._in_xlim_change = False
        self._last_df = None
        self._last_symbol = None
        # 十字準線元件
        self._crosshair_hline = None
        self._crosshair_vline = None
        self._crosshair_price_label = None
        self._crosshair_date_label = None
        self._ma_texts = []  # MA數值標注

        # 刻度自動調整
        self.ax.callbacks.connect('xlim_changed', self._on_xlim_change)

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

    # ── 旋轉動畫 ──
    _SPIN_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    def _start_spinner(self, msg="正在搜尋"):
        """啟動旋轉動畫"""
        self._spinner_running = True
        self._spinner_idx = 0
        self._spinner_msg = msg
        self._tick_spinner()

    def _tick_spinner(self):
        """每 80ms 切換一次符號"""
        if not self._spinner_running:
            return
        ch = self._SPIN_FRAMES[self._spinner_idx % len(self._SPIN_FRAMES)]
        self.corr_text.set(f"{ch} {self._spinner_msg}...")
        self._spinner_idx += 1
        self.root.after(80, self._tick_spinner)

    def _stop_spinner(self):
        """停止旋轉動畫"""
        self._spinner_running = False

    # ── 圖表互動 ──
    def _set_xlim_all(self, xmin, xmax):
        """同步設定3個子圖的X軸範圍（不觸發 draw）"""
        self.ax.set_xlim(xmin, xmax)
        self.ax_vol.set_xlim(xmin, xmax)
        self.ax_kd.set_xlim(xmin, xmax)

    def _on_scroll(self, event):
        """滾輪縮放：以滑鼠位置為中心，延遲重繪"""
        if self._last_df is None:
            return
        if event.inaxes not in (self.ax, self.ax_vol, self.ax_kd):
            return
        xmin, xmax = self.ax.get_xlim()
        span = xmax - xmin
        ratio = (event.xdata - xmin) / span if span > 0 else 0.5
        factor = 0.8 if event.button == 'up' else 1.25
        new_span = max(5, min(span * factor, span * 2))
        center = xmin + ratio * span
        self._set_xlim_all(center - ratio * new_span, center + (1 - ratio) * new_span)
        # 延遲重繪，避免滾動時過多 redraw
        if getattr(self, '_scroll_timer', None):
            self.root.after_cancel(self._scroll_timer)
        self._scroll_timer = self.root.after(30, self._do_scroll_redraw)

    def _do_scroll_redraw(self):
        """執行實際重繪"""
        self._scroll_timer = None
        self.canvas.draw_idle()

    def _on_press(self, event):
        """左鍵：無拖曳時顯示浮動視窗、拖曳平移；雙擊還原"""
        if self._last_df is None:
            return
        if event.inaxes not in (self.ax, self.ax_vol, self.ax_kd):
            return
        if event.dblclick:
            self._set_xlim_all(self._last_df.index[0], self._last_df.index[-1])
            return
        if event.button == 1:
            self._dragging = True
            self._drag_start = event.xdata
            self._drag_xlim_start = self.ax.get_xlim()
            self._press_x = event.x
            self._press_y = event.y
            self._pressed_in_ax = event.inaxes

    def _on_release(self, event):
        """滑鼠放開：若無明顯移動則顯示浮動視窗"""
        was_dragging = self._dragging
        self._dragging = False
        self._drag_start = None
        self._drag_xlim_start = None
        # 判斷是否為「點擊」（滑鼠移動 < 5 像素）
        if was_dragging and hasattr(self, '_press_x') and event.x is not None:
            dx = abs(event.x - self._press_x)
            dy = abs(event.y - self._press_y)
            if dx < 5 and dy < 5 and self._last_df is not None:
                # 只要 xdata 有效就在 K 線圖上顯示
                if event.inaxes == self.ax or event.xdata is not None:
                    self._show_click_popup(event)

    def _on_motion(self, event):
        """拖曳平移"""
        if not self._dragging or self._drag_start is None:
            return
        if event.xdata is None:
            return
        dx = event.xdata - self._drag_start
        xmin, xmax = self._drag_xlim_start
        self._set_xlim_all(xmin + dx, xmax + dx)

    def _show_click_popup(self, event):
        """點擊K線時顯示浮動視窗，顯示當天完整交易資料"""
        if self._last_df is None or event.xdata is None:
            return
        df = self._last_df
        ts = pd.Timestamp(mdates.num2date(event.xdata))
        nearest = df.index.get_indexer([ts], method='nearest')[0]
        if nearest < 0 or nearest >= len(df):
            return
        day = df.index[nearest]
        row = df.iloc[nearest]

        # KD 值
        k_val, d_val = calc_kd(df)
        k_now = k_val.iloc[nearest]
        d_now = d_val.iloc[nearest]

        # 建立浮動視窗
        popup = tk.Toplevel(self.root)
        popup.title(f"{day.strftime('%Y-%m-%d')} 交易資料")
        popup.geometry("320x280")
        popup.configure(bg='#1a1a2e')
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()

        # 視窗居中
        popup.update_idletasks()
        px = self.root.winfo_x() + (self.root.winfo_width() - 320) // 2
        py = self.root.winfo_y() + (self.root.winfo_height() - 280) // 2
        popup.geometry(f"+{px}+{py}")

        title_color = '#e0e0e0'
        bg = '#1a1a2e'
        row_bg = '#16213e'

        # 標題
        tk.Label(popup, text=f"  {day.strftime('%Y-%m-%d')} ({day.strftime('%A')})",
                 font=(_CHINESE_FONT, 12, 'bold'), fg='#00bcd4', bg=bg).pack(fill=tk.X, pady=(10, 5))

        # 資料表格
        data = [
            ("開盤價", f"{row['Open']:.2f}", '#ef4444' if row['Close'] >= row['Open'] else '#22c55e'),
            ("最高價", f"{row['High']:.2f}", '#ef4444' if row['Close'] >= row['Open'] else '#22c55e'),
            ("最低價", f"{row['Low']:.2f}", '#ef4444' if row['Close'] >= row['Open'] else '#22c55e'),
            ("收盤價", f"{row['Close']:.2f}", '#ef4444' if row['Close'] >= row['Open'] else '#22c55e'),
            ("成交量", f"{row['Volume']:,.0f}", '#e0e0e0'),
            ("漲跌", f"{row['Close'] - row['Open']:+.2f}",
             '#ef4444' if row['Close'] >= row['Open'] else '#22c55e'),
            ("K 值", f"{k_now:.2f}", '#00bcd4'),
            ("D 值", f"{d_now:.2f}", '#ffeb3b'),
        ]

        table_frame = tk.Frame(popup, bg=bg)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        table_frame.columnconfigure(1, weight=1)

        for i, (label, value, color) in enumerate(data):
            r_bg = row_bg if i % 2 == 0 else bg
            tk.Label(table_frame, text=label, font=(_CHINESE_FONT, 10),
                     fg='#aaaaaa', bg=r_bg, anchor='w').grid(row=i, column=0, sticky='w', padx=(10, 5), pady=4)
            tk.Label(table_frame, text=value, font=(_CHINESE_FONT, 10, 'bold'),
                     fg=color, bg=r_bg, anchor='e').grid(row=i, column=1, sticky='e', padx=(5, 10), pady=4)

        # 關閉按鈕
        tk.Button(popup, text="關閉", command=popup.destroy, font=(_CHINESE_FONT, 10),
                  bg='#333333', fg='white', activebackground='#555555', relief=tk.FLAT,
                  padx=20, pady=5).pack(pady=(5, 10))

    def _on_xlim_change(self, ax):
        """縮放時自動調整刻度密度（不含 draw，由 scroll handler 處理）"""
        if getattr(self, '_in_xlim_change', False):
            return
        self._in_xlim_change = True
        try:
            xmin, xmax = ax.get_xlim()
            span = xmax - xmin
            if span <= 30:
                loc = mdates.DayLocator()
                fmt = mdates.DateFormatter('%m/%d')
            elif span <= 90:
                loc = mdates.WeekdayLocator(interval=1)
                fmt = mdates.DateFormatter('%m/%d')
            elif span <= 365:
                loc = mdates.MonthLocator()
                fmt = mdates.DateFormatter('%Y-%m')
            else:
                loc = mdates.MonthLocator(interval=3)
                fmt = mdates.DateFormatter('%Y-%m')
            for a in (self.ax, self.ax_vol, self.ax_kd):
                a.xaxis.set_major_locator(loc)
                a.xaxis.set_major_formatter(fmt)
        finally:
            self._in_xlim_change = False

    def _clear_crosshair(self):
        """清除十字準線"""
        for artist in (self._crosshair_hline, self._crosshair_vline, self._crosshair_price_label):
            if artist is not None:
                try: artist.remove()
                except Exception: pass
        self._crosshair_hline = None
        self._crosshair_vline = None
        self._crosshair_price_label = None

    def _on_hover(self, event):
        """十字準線 + 右側價格標籤"""
        if self._last_df is None:
            return
        if self._dragging:
            return
        if event.inaxes != self.ax and event.inaxes != self.ax_vol and event.inaxes != self.ax_kd:
            self._clear_crosshair()
            self.canvas.draw_idle()
            return
        if event.xdata is None or event.ydata is None:
            return

        df = self._last_df
        ts = pd.Timestamp(mdates.num2date(event.xdata))
        nearest = df.index.get_indexer([ts], method='nearest')[0]
        if nearest < 0 or nearest >= len(df):
            return
        day = df.index[nearest]
        price = df['Close'].iloc[nearest]

        self._clear_crosshair()

        # 垂直線（貫穿所有子圖）
        for a in (self.ax, self.ax_vol, self.ax_kd):
            pass
        self._crosshair_vline = self.ax.axvline(x=day, color='#555555', linestyle='-', linewidth=0.7, alpha=0.8)
        self.ax_vol.axvline(x=day, color='#555555', linestyle='-', linewidth=0.7, alpha=0.8)
        self.ax_kd.axvline(x=day, color='#555555', linestyle='-', linewidth=0.7, alpha=0.8)

        # 水平線（在K線圖上）
        self._crosshair_hline = self.ax.axhline(y=event.ydata, color='#555555', linestyle='-', linewidth=0.7, alpha=0.8)

        # 右側價格標籤
        xlim = self.ax.get_xlim()
        self._crosshair_price_label = self.ax.text(
            xlim[1], event.ydata, f' {price:.2f} ',
            fontsize=9, color='white', fontweight='bold',
            ha='left', va='center',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#333333', edgecolor='#555555'),
            clip_on=False, zorder=10)

        # 延遲重繪
        if getattr(self, '_hover_timer', None):
            self.root.after_cancel(self._hover_timer)
        self._hover_timer = self.root.after(20, self._do_hover_redraw)

    def _do_hover_redraw(self):
        self._hover_timer = None
        self.canvas.draw_idle()

    def _draw_prediction(self, df, close, pred_days):
        """根據選定方法預測未來走勢"""
        method = self.pred_method.get()
        if method == "全部":
            self._pred_all(df, close, pred_days)
        elif method == "線性":
            self._pred_linear(df, close, pred_days)
        elif method == "多項式":
            self._pred_polynomial(df, close, pred_days)
        elif method == "蒙地卡羅":
            self._pred_monte_carlo(df, close, pred_days)
        elif method == "指數平滑":
            self._pred_exp_smoothing(df, close, pred_days)
        elif method == "MA交叉":
            self._pred_ma_cross(df, close, pred_days)
        else:
            self._pred_bollinger(df, close, pred_days)

    def _pred_all(self, df, close, pred_days):
        """同時顯示全部預測方法"""
        from matplotlib.lines import Line2D
        n = len(close)
        x = np.arange(n)
        y = close.values.astype(float)
        last_date = df.index[-1]
        future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=pred_days)
        future_x = np.arange(n, n + pred_days)
        legend_handles = []

        # 1. 線性（灰色）
        coeffs1 = np.polyfit(x, y, 1)
        trend1 = np.polyval(coeffs1, x)
        pred1 = np.polyval(coeffs1, future_x)
        std1 = np.std(y - trend1)
        self.ax.plot(future_dates, pred1, color='#888888', linewidth=1.2, linestyle='--', alpha=0.8)
        self.ax.fill_between(future_dates, pred1 - std1, pred1 + std1, alpha=0.04, color='#888888')
        legend_handles.append(Line2D([0], [0], color='#888888', linestyle='--', linewidth=1.2,
                                     label=f'線性 {pred1[-1]:.2f}'))

        # 2. 多項式（橙色）
        c2 = np.polyfit(x, y, 2)
        c3 = np.polyfit(x, y, 3)
        pred2 = (np.polyval(c2, future_x) + np.polyval(c3, future_x)) / 2
        std2 = np.std(y - np.polyval(c2, x))
        self.ax.plot(future_dates, pred2, color='#ff9800', linewidth=1.2, linestyle='--', alpha=0.8)
        self.ax.fill_between(future_dates, pred2 - std2, pred2 + std2, alpha=0.04, color='#ff9800')
        legend_handles.append(Line2D([0], [0], color='#ff9800', linestyle='--', linewidth=1.2,
                                     label=f'多項式 {pred2[-1]:.2f}'))

        # 3. 蒙地卡羅（紫色）
        returns = np.diff(y) / y[:-1]
        mu, sigma = np.mean(returns), np.std(returns)
        S0 = y[-1]
        sims = np.zeros((200, pred_days))
        for i in range(200):
            prices = [S0]
            for _ in range(pred_days):
                prices.append(prices[-1] * np.exp((mu - 0.5 * sigma**2) + sigma * np.random.normal()))
            sims[i, :] = prices[1:]
        mc_mean = np.mean(sims, axis=0)
        for i in range(0, 200, 10):
            self.ax.plot(future_dates, sims[i], color='#bb86fc', linewidth=0.2, alpha=0.1)
        self.ax.plot(future_dates, mc_mean, color='#bb86fc', linewidth=1.5, linestyle='-')
        mc_p5 = np.percentile(sims, 5, axis=0)
        mc_p95 = np.percentile(sims, 95, axis=0)
        self.ax.fill_between(future_dates, mc_p5, mc_p95, alpha=0.06, color='#bb86fc')
        up_prob = np.mean(sims[:, -1] > S0) * 100
        legend_handles.append(Line2D([0], [0], color='#bb86fc', linewidth=1.5,
                                     label=f'MC均值 {mc_mean[-1]:.2f}'))

        # 4. 指數平滑（青色）
        alpha_es, beta_es = 0.3, 0.1
        level = [y[0]]
        trend_v = [y[1] - y[0] if n > 1 else 0]
        for t in range(1, n):
            new_level = alpha_es * y[t] + (1 - alpha_es) * (level[-1] + trend_v[-1])
            new_trend = beta_es * (new_level - level[-1]) + (1 - beta_es) * trend_v[-1]
            level.append(new_level)
            trend_v.append(new_trend)
        pred4 = [level[-1] + (i + 1) * trend_v[-1] for i in range(pred_days)]
        self.ax.plot(future_dates, pred4, color='#00bcd4', linewidth=1.2, linestyle='--', alpha=0.8)
        legend_handles.append(Line2D([0], [0], color='#00bcd4', linestyle='--', linewidth=1.2,
                                     label=f'指數平滑 {pred4[-1]:.2f}'))

        # 5. MA交叉（綠/紅）
        ma5 = np.convolve(y, np.ones(5)/5, mode='valid')
        ma10 = np.convolve(y, np.ones(10)/10, mode='valid')
        latest_diff = ma5[-1] - ma10[-1]
        if len(ma5) >= 5:
            slope = np.polyfit(np.arange(5), ma5[-5:], 1)[0]
        else:
            slope = latest_diff / max(len(ma5), 1)
        pred5 = [S0 + slope * (i + 1) for i in range(pred_days)]
        color5 = '#22c55e' if latest_diff > 0 else '#f44336'
        self.ax.plot(future_dates, pred5, color=color5, linewidth=1.2, linestyle='--', alpha=0.8)
        direction = "多" if latest_diff > 0 else "空"
        legend_handles.append(Line2D([0], [0], color=color5, linestyle='--', linewidth=1.2,
                                     label=f'MA交叉({direction}) {pred5[-1]:.2f}'))

        # 6. 布林通道（洋紅）
        ma20 = np.convolve(y, np.ones(20)/20, mode='valid')
        current_ma = ma20[-1]
        current_std = np.std(y[-20:])
        pred6 = []
        for i in range(1, pred_days + 1):
            decay = 0.95 ** i
            pred6.append(current_ma + (S0 - current_ma) * decay)
        self.ax.plot(future_dates, pred6, color='#e040fb', linewidth=1.2, linestyle='--', alpha=0.8)
        legend_handles.append(Line2D([0], [0], color='#e040fb', linestyle='--', linewidth=1.2,
                                     label=f'布林 {pred6[-1]:.2f}'))

        self.ax.axvspan(df.index[-1], future_dates[-1], alpha=0.03, color='#bb86fc')

        # 機率文字
        self.ax.text(0.02, 0.82,
                     f'MC 上漲 {up_prob:.1f}% / 下跌 {100-up_prob:.1f}%　MA5/MA10 {direction}頭',
                     transform=self.ax.transAxes, fontsize=8, color='#e0e0e0',
                     fontfamily=_CHINESE_FONT, verticalalignment='top',
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a1a2e', edgecolor='#555555'))

        self.ax.legend(handles=legend_handles, fontsize=7, loc='lower right',
                       facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0', ncol=3)

    def _pred_linear(self, df, close, pred_days):
        """線性回歸預測"""
        n = len(close)
        x = np.arange(n)
        y = close.values.astype(float)
        coeffs = np.polyfit(x, y, 1)
        trend = np.polyval(coeffs, x)
        last_date = df.index[-1]
        future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=pred_days)
        future_x = np.arange(n, n + pred_days)
        pred = np.polyval(coeffs, future_x)
        std_r = np.std(y - trend)

        self.ax.plot(df.index, trend, color='#888888', linewidth=1, linestyle=':', alpha=0.5)
        self.ax.plot(future_dates, pred, color='#888888', linewidth=2, linestyle='--')
        self.ax.fill_between(future_dates, pred - std_r, pred + std_r, alpha=0.12, color='#888888')
        self.ax.fill_between(future_dates, pred - 2*std_r, pred + 2*std_r, alpha=0.05, color='#888888')
        self.ax.scatter(future_dates[-1], pred[-1], color='#888888', s=50, zorder=5,
                        edgecolors='white', linewidth=0.5)
        self.ax.annotate(f'  預測 {pred[-1]:.2f}', xy=(future_dates[-1], pred[-1]),
                         xytext=(0, 15), textcoords='offset points',
                         fontsize=9, color='#888888', fontweight='bold', fontfamily=_CHINESE_FONT)
        self.ax.axvspan(df.index[-1], future_dates[-1], alpha=0.04, color='#888888')
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color='#888888', linestyle='--', linewidth=2, label=f'線性預測 {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_polynomial(self, df, close, pred_days):
        """多項式回歸（二次+三次平均）"""
        n = len(close)
        x = np.arange(n)
        y = close.values.astype(float)
        last_date = df.index[-1]
        future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=pred_days)
        future_x = np.arange(n, n + pred_days)
        c2 = np.polyfit(x, y, 2)
        c3 = np.polyfit(x, y, 3)
        trend = np.polyval(c2, x)
        pred = (np.polyval(c2, future_x) + np.polyval(c3, future_x)) / 2
        std_r = np.std(y - trend)

        self.ax.plot(df.index, trend, color='#ff9800', linewidth=1, linestyle=':', alpha=0.5)
        self.ax.plot(future_dates, pred, color='#ff9800', linewidth=2, linestyle='--')
        self.ax.fill_between(future_dates, pred - std_r, pred + std_r, alpha=0.12, color='#ff9800')
        self.ax.fill_between(future_dates, pred - 2*std_r, pred + 2*std_r, alpha=0.05, color='#ff9800')
        self.ax.scatter(future_dates[-1], pred[-1], color='#ff9800', s=50, zorder=5,
                        edgecolors='white', linewidth=0.5)
        self.ax.annotate(f'  預測 {pred[-1]:.2f}', xy=(future_dates[-1], pred[-1]),
                         xytext=(0, 15), textcoords='offset points',
                         fontsize=9, color='#ff9800', fontweight='bold', fontfamily=_CHINESE_FONT)
        self.ax.axvspan(df.index[-1], future_dates[-1], alpha=0.04, color='#ff9800')
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color='#ff9800', linestyle='--', linewidth=2, label=f'多項式預測 {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_monte_carlo(self, df, close, pred_days):
        """蒙地卡羅模擬 (GBM, 200 paths)"""
        y = close.values.astype(float)
        last_date = df.index[-1]
        future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=pred_days)
        returns = np.diff(y) / y[:-1]
        mu, sigma = np.mean(returns), np.std(returns)
        S0 = y[-1]
        sims = np.zeros((200, pred_days))
        for i in range(200):
            prices = [S0]
            for _ in range(pred_days):
                prices.append(prices[-1] * np.exp((mu - 0.5 * sigma**2) + sigma * np.random.normal()))
            sims[i, :] = prices[1:]
        mc_mean = np.mean(sims, axis=0)
        mc_p25 = np.percentile(sims, 25, axis=0)
        mc_p75 = np.percentile(sims, 75, axis=0)
        mc_p5 = np.percentile(sims, 5, axis=0)
        mc_p95 = np.percentile(sims, 95, axis=0)

        for i in range(0, 200, 5):
            self.ax.plot(future_dates, sims[i], color='#bb86fc', linewidth=0.3, alpha=0.15)
        self.ax.plot(future_dates, mc_mean, color='#bb86fc', linewidth=2, linestyle='-')
        self.ax.fill_between(future_dates, mc_p25, mc_p75, alpha=0.2, color='#bb86fc')
        self.ax.fill_between(future_dates, mc_p5, mc_p95, alpha=0.08, color='#bb86fc')
        self.ax.scatter(future_dates[-1], mc_mean[-1], color='#bb86fc', s=50, zorder=5,
                        edgecolors='white', linewidth=0.5)
        self.ax.annotate(f'  均值 {mc_mean[-1]:.2f}', xy=(future_dates[-1], mc_mean[-1]),
                         xytext=(0, 15), textcoords='offset points',
                         fontsize=9, color='#bb86fc', fontweight='bold', fontfamily=_CHINESE_FONT)
        self.ax.annotate(f'{mc_p95[-1]:.2f}', xy=(future_dates[-1], mc_p95[-1]),
                         xytext=(0, 5), textcoords='offset points',
                         fontsize=7, color='#888888', fontfamily=_CHINESE_FONT)
        self.ax.annotate(f'{mc_p5[-1]:.2f}', xy=(future_dates[-1], mc_p5[-1]),
                         xytext=(0, -10), textcoords='offset points',
                         fontsize=7, color='#888888', fontfamily=_CHINESE_FONT)
        up_prob = np.mean(sims[:, -1] > S0) * 100
        self.ax.text(0.02, 0.82,
                     f'上漲機率 {up_prob:.1f}%　下跌機率 {100-up_prob:.1f}%',
                     transform=self.ax.transAxes, fontsize=9, color='#e0e0e0',
                     fontfamily=_CHINESE_FONT, verticalalignment='top',
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a1a2e', edgecolor='#555555'))
        self.ax.axvspan(df.index[-1], future_dates[-1], alpha=0.04, color='#bb86fc')
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color='#bb86fc', linewidth=2, label=f'MC均值 {mc_mean[-1]:.2f}'),
            Line2D([0], [0], color='#bb86fc', linewidth=8, alpha=0.25, label='50% 機率'),
            Line2D([0], [0], color='#bb86fc', linewidth=8, alpha=0.1, label='90% 機率'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_exp_smoothing(self, df, close, pred_days):
        """Holt-Winters 指數平滑法（趨勢 + 季節性）"""
        y = close.values.astype(float)
        last_date = df.index[-1]
        future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=pred_days)
        n = len(y)

        # 手動實作雙指數平滑 (Holt's linear)
        alpha, beta = 0.3, 0.1
        level = [y[0]]
        trend_val = [y[1] - y[0] if n > 1 else 0]
        for t in range(1, n):
            new_level = alpha * y[t] + (1 - alpha) * (level[-1] + trend_val[-1])
            new_trend = beta * (new_level - level[-1]) + (1 - beta) * trend_val[-1]
            level.append(new_level)
            trend_val.append(new_trend)

        # 歷史擬合
        fitted = [level[i] + trend_val[i] for i in range(n)]
        self.ax.plot(df.index, fitted, color='#00bcd4', linewidth=1, linestyle=':', alpha=0.5)

        # 未來預測
        last_level = level[-1]
        last_trend = trend_val[-1]
        pred = [last_level + (i + 1) * last_trend for i in range(pred_days)]

        # 誤差範圍
        residuals = y - np.array(fitted)
        std_r = np.std(residuals)
        expanding_std = np.array([std_r * np.sqrt(i + 1) for i in range(pred_days)])

        self.ax.plot(future_dates, pred, color='#00bcd4', linewidth=2, linestyle='--')
        self.ax.fill_between(future_dates, pred - expanding_std, pred + expanding_std,
                             alpha=0.12, color='#00bcd4')
        self.ax.fill_between(future_dates, pred - 2*expanding_std, pred + 2*expanding_std,
                             alpha=0.05, color='#00bcd4')
        self.ax.scatter(future_dates[-1], pred[-1], color='#00bcd4', s=50, zorder=5,
                        edgecolors='white', linewidth=0.5)
        self.ax.annotate(f'  預測 {pred[-1]:.2f}', xy=(future_dates[-1], pred[-1]),
                         xytext=(0, 15), textcoords='offset points',
                         fontsize=9, color='#00bcd4', fontweight='bold', fontfamily=_CHINESE_FONT)
        self.ax.axvspan(df.index[-1], future_dates[-1], alpha=0.04, color='#00bcd4')
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color='#00bcd4', linestyle='--', linewidth=2, label=f'指數平滑 {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_ma_cross(self, df, close, pred_days):
        """MA交叉預測法：以近期MA5/MA10交叉趨勢外推"""
        y = close.values.astype(float)
        n = len(y)
        last_date = df.index[-1]
        future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=pred_days)

        # 計算 MA5 和 MA10
        ma5 = np.convolve(y, np.ones(5)/5, mode='valid')
        ma10 = np.convolve(y, np.ones(10)/10, mode='valid')
        offset = n - len(ma5)
        ma5_x = np.arange(offset, n)
        ma10_x = np.arange(n - len(ma10), n)

        # 歷史MA線
        self.ax.plot(df.index[ma5_x], ma5, color='#22c55e', linewidth=1, linestyle=':', alpha=0.6)
        self.ax.plot(df.index[ma10_x], ma10, color='#f44336', linewidth=1, linestyle=':', alpha=0.6)

        # 交叉判斷：MA5在MA10上方=多頭，下方=空頭
        latest_diff = ma5[-1] - ma10[-1]
        # 趨勢斜率（最近5天MA5的線性回歸斜率）
        if len(ma5) >= 5:
            slope = np.polyfit(np.arange(5), ma5[-5:], 1)[0]
        else:
            slope = latest_diff / max(len(ma5), 1)

        # 外推預測
        S0 = y[-1]
        pred = []
        for i in range(1, pred_days + 1):
            pred.append(S0 + slope * i)

        # 信心區間：用歷史波動率
        daily_vol = np.std(np.diff(y) / y[:-1]) * S0
        expanding_vol = np.array([daily_vol * np.sqrt(i + 1) for i in range(pred_days)])

        direction = "多頭" if latest_diff > 0 else "空頭"
        color = '#22c55e' if latest_diff > 0 else '#f44336'

        self.ax.plot(future_dates, pred, color=color, linewidth=2, linestyle='--')
        self.ax.fill_between(future_dates, pred - expanding_vol, pred + expanding_vol,
                             alpha=0.1, color=color)
        self.ax.fill_between(future_dates, pred - 2*expanding_vol, pred + 2*expanding_vol,
                             alpha=0.04, color=color)
        self.ax.scatter(future_dates[-1], pred[-1], color=color, s=50, zorder=5,
                        edgecolors='white', linewidth=0.5)
        self.ax.annotate(f'  預測 {pred[-1]:.2f}', xy=(future_dates[-1], pred[-1]),
                         xytext=(0, 15), textcoords='offset points',
                         fontsize=9, color=color, fontweight='bold', fontfamily=_CHINESE_FONT)
        self.ax.text(0.02, 0.82,
                     f'MA5/MA10 {direction}　MA5={ma5[-1]:.2f} MA10={ma10[-1]:.2f}',
                     transform=self.ax.transAxes, fontsize=9, color='#e0e0e0',
                     fontfamily=_CHINESE_FONT, verticalalignment='top',
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a1a2e', edgecolor='#555555'))
        self.ax.axvspan(df.index[-1], future_dates[-1], alpha=0.04, color=color)
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color='#22c55e', linestyle=':', linewidth=1, label='MA5'),
            Line2D([0], [0], color='#f44336', linestyle=':', linewidth=1, label='MA10'),
            Line2D([0], [0], color=color, linestyle='--', linewidth=2, label=f'MA預測 {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_bollinger(self, df, close, pred_days):
        """布林通道預測法：以均值回歸為基礎外推"""
        y = close.values.astype(float)
        n = len(y)
        last_date = df.index[-1]
        future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=pred_days)

        # 20日布林通道
        ma20 = np.convolve(y, np.ones(20)/20, mode='valid')
        offset = n - len(ma20)
        # 歷史布林帶
        hist_upper = ma20 + 2 * np.std(y[-len(ma20):])
        hist_lower = ma20 - 2 * np.std(y[-len(ma20):])
        self.ax.plot(df.index[offset:], ma20, color='#e040fb', linewidth=1, linestyle=':', alpha=0.5)

        # 最新布林通道參數
        current_ma = ma20[-1]
        current_std = np.std(y[-20:])
        upper_band = current_ma + 2 * current_std
        lower_band = current_ma - 2 * current_std

        # 均值回歸預測：價格向MA20收斂
        S0 = y[-1]
        pred = []
        for i in range(1, pred_days + 1):
            # 指數衰減回歸到MA20（延伸方向）
            decay = 0.95 ** i
            pred.append(current_ma + (S0 - current_ma) * decay)

        # 通道外推（帶狀區域）
        expanding_std = np.array([current_std * np.sqrt(i + 1) * 0.5 for i in range(pred_days)])
        upper_pred = [p + expanding_std[i] for i, p in enumerate(pred)]
        lower_pred = [p - expanding_std[i] for i, p in enumerate(pred)]

        self.ax.plot(future_dates, upper_pred, color='#e040fb', linewidth=0.8, linestyle=':', alpha=0.4)
        self.ax.plot(future_dates, lower_pred, color='#e040fb', linewidth=0.8, linestyle=':', alpha=0.4)
        self.ax.fill_between(future_dates, lower_pred, upper_pred, alpha=0.1, color='#e040fb')
        self.ax.plot(future_dates, pred, color='#e040fb', linewidth=2, linestyle='--')
        self.ax.scatter(future_dates[-1], pred[-1], color='#e040fb', s=50, zorder=5,
                        edgecolors='white', linewidth=0.5)
        self.ax.annotate(f'  預測 {pred[-1]:.2f}', xy=(future_dates[-1], pred[-1]),
                         xytext=(0, 15), textcoords='offset points',
                         fontsize=9, color='#e040fb', fontweight='bold', fontfamily=_CHINESE_FONT)
        self.ax.text(0.02, 0.82,
                     f'布林通道　上軌 {upper_band:.2f}　MA20 {current_ma:.2f}　下軌 {lower_band:.2f}',
                     transform=self.ax.transAxes, fontsize=9, color='#e0e0e0',
                     fontfamily=_CHINESE_FONT, verticalalignment='top',
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a1a2e', edgecolor='#555555'))
        self.ax.axvspan(df.index[-1], future_dates[-1], alpha=0.04, color='#e040fb')
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color='#e040fb', linestyle=':', linewidth=1, label='MA20'),
            Line2D([0], [0], color='#e040fb', linestyle='--', linewidth=2, label=f'布林預測 {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

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
        self.corr_text.set("查詢後自動計算...")
        self._corr_generation += 1  # 使舊的 corr_worker 失效
        self.ax.clear()
        self.ax_vol.clear()
        self.ax_kd.clear()
        self.canvas.draw()
        threading.Thread(target=self.worker, args=(query, start_text, end_text), daemon=True).start()

    def worker(self, query, start_date, end_date):
        """背景執行下載與資料處理"""
        try:
            symbol = resolve_symbol(query)
            symbol, df, info = fetch_data(symbol, start_date, end_date)
            self.root.after(0, self.display_result, query, symbol, df, info)
            # 背景計算相關係數（帶入 generation）
            gen = self._corr_generation
            threading.Thread(target=self.corr_worker, args=(symbol, start_date, end_date, gen), daemon=True).start()
        except Exception as e:
            self.root.after(0, self.show_error, str(e))

    def corr_worker(self, symbol, start_date, end_date, generation):
        """背景計算日報酬率相關係數"""
        code = symbol.split('.')[0]
        self.root.after(0, self._start_spinner, f"正在比較 {code} 與全部股票")
        try:
            for done, total, partial in calc_correlation(symbol, start_date, end_date):
                # 如果已有更新的查詢，直接放棄
                if self._corr_generation != generation:
                    return
                if done < total:
                    ch = self._SPIN_FRAMES[self._spinner_idx % len(self._SPIN_FRAMES)]
                    self.root.after(0, self.corr_text.set,
                                    f"{ch} 正在比較 {code} 與全部股票... {done}/{total}")
                else:
                    self.root.after(0, self._stop_spinner)
                    self.root.after(10, self.show_correlation, symbol, partial)
        except Exception as e:
            if self._corr_generation == generation:
                self.root.after(0, self._stop_spinner)
                self.root.after(10, self.corr_text.set, f"計算失敗: {e}")

    def show_correlation(self, symbol, results):
        """顯示相關係數結果"""
        if not results:
            self.corr_text.set("無足夠資料計算相關係數")
            return
        target_name = label_from_symbol(symbol)
        lines = [f"與 {target_name} 日報酬率相關度最高的股票：\n"]
        for i, (sym, name, corr) in enumerate(results, 1):
            bar_len = int(abs(corr) * 20)
            bar = '█' * bar_len + '░' * (20 - bar_len)
            lines.append(f"  {i}. {name}  相關係數: {corr:+.4f}  {bar}")
        self.corr_text.set('\n'.join(lines))

    def display_result(self, query, symbol, df, info):
        """將查詢結果顯示在 GUI 上（深色主題、3子圖）"""
        if df.empty:
            messagebox.showerror("錯誤", f"股票 {query} 無資料，可能代碼錯誤或已下市。")
            self.btn.config(state=tk.NORMAL, text="查詢")
            self.info_text.set("")
            return

        name = fetch_chinese_name(symbol) or info.get('longName') or info.get('shortName') or ''
        code = symbol.split('.')[0]
        exchange = get_market_type(code)
        close = df['Close']
        volume = df['Volume']
        latest_date = df.index[-1]
        k_val, d_val = calc_kd(df)
        latest_k = k_val.iloc[-1]
        latest_d = d_val.iloc[-1]

        # 更新資訊區
        info_text = (
            f"{name} ({symbol})    "
            f"市場: {exchange}    "
            f"期間: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}\n"
            f"最新交易日 ({latest_date.strftime('%Y-%m-%d')})    "
            f"開盤價: {df['Open'].iloc[-1]:.2f}    "
            f"最高價: {df['High'].iloc[-1]:.2f}    "
            f"最低價: {df['Low'].iloc[-1]:.2f}    "
            f"收盤價: {df['Close'].iloc[-1]:.2f}    "
            f"K: {latest_k:.2f}    D: {latest_d:.2f}"
        )
        self.info_text.set(info_text)

        # 清除舊圖
        for ax in (self.ax, self.ax_vol, self.ax_kd):
            ax.clear()
            ax.set_facecolor(self._ax_color)
            ax.tick_params(colors=self._text_color)
            for spine in ax.spines.values():
                spine.set_color(self._grid_color)
        for t in self._ma_texts:
            try: t.remove()
            except Exception: pass
        self._ma_texts.clear()
        self._last_df = df
        self._last_symbol = symbol
        self._click_annotation = None
        self._vline = None
        self._crosshair_hline = None
        self._crosshair_vline = None
        self._crosshair_price_label = None

        # ── K 線（蠟燭圖）──
        width = 0.6
        width2 = 0.05
        up = df[df['Close'] >= df['Open']]
        down = df[df['Close'] < df['Open']]
        self.ax.bar(up.index, up['Close'] - up['Open'], width, bottom=up['Open'], color='#ef4444', edgecolor='#ef4444')
        self.ax.bar(up.index, up['High'] - up['Close'], width2, bottom=up['Close'], color='#ef4444')
        self.ax.bar(up.index, up['Low'] - up['Open'], width2, bottom=up['Open'], color='#ef4444')
        self.ax.bar(down.index, down['Close'] - down['Open'], width, bottom=down['Open'], color='#22c55e', edgecolor='#22c55e')
        self.ax.bar(down.index, down['High'] - down['Open'], width2, bottom=down['Open'], color='#22c55e')
        self.ax.bar(down.index, down['Low'] - down['Close'], width2, bottom=down['Close'], color='#22c55e')

        # 均線（5T週線、10T雙週線、20T月線、60T季線、120T半年線、240T年線）
        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        ma120 = close.rolling(120).mean()
        ma240 = close.rolling(240).mean()
        ma_cfg = [
            (ma5,   '#00bcd4', '5T(週)'),
            (ma10,  '#ffeb3b', '10T(雙週)'),
            (ma20,  '#e040fb', '20T(月)'),
            (ma60,  '#ff9800', '60T(季)'),
            (ma120, '#4caf50', '120T(半年)'),
            (ma240, '#f44336', '240T(年)'),
        ]
        for ma_series, color, label in ma_cfg:
            self.ax.plot(df.index, ma_series, color=color, linewidth=1, alpha=0.9, label=label)

        # MA 數值顯示（左上角，每段用對應顏色）
        def _mv(ma):
            v = ma.iloc[-1] if not ma.empty and not pd.isna(ma.iloc[-1]) else None
            if v is None or len(ma) < 2 or pd.isna(ma.iloc[-2]):
                return f"---", False
            arrow = '↑' if v > ma.iloc[-2] else '↓'
            return f"{v:.2f}{arrow}", True

        for i, (ma_series, color, label) in enumerate(ma_cfg):
            val_str, _ = _mv(ma_series)
            line_idx = 0 if i < 3 else 1
            col_idx = i % 3
            x_pos = 0.01 + col_idx * 0.31
            y_pos = 0.97 - line_idx * 0.06
            txt = self.ax.text(x_pos, y_pos, f"MA{label}:{val_str}",
                               transform=self.ax.transAxes,
                               fontsize=7.5, color=color, fontweight='bold',
                               va='top', ha='left', zorder=20,
                               fontfamily=_CHINESE_FONT)
            self._ma_texts.append(txt)

        # K線圖格式
        self.ax.set_ylabel("股價", fontsize=10, color=self._text_color)
        self.ax.grid(True, linestyle='--', alpha=0.15, color=self._grid_color)
        self.ax.yaxis.set_label_position('right')
        self.ax.tick_params(labelleft=False, labelright=True)

        # ── 成交量柱狀圖 ──
        vol_up = df[volume.index.isin(up.index)]
        vol_down = df[volume.index.isin(down.index)]
        self.ax_vol.bar(vol_up.index, vol_up['Volume'], width, color='#ef4444', alpha=0.7)
        self.ax_vol.bar(vol_down.index, vol_down['Volume'], width, color='#22c55e', alpha=0.7)
        # 成交量均線
        vol_ma5 = volume.rolling(5).mean()
        vol_ma10 = volume.rolling(10).mean()
        self.ax_vol.plot(df.index, vol_ma5, color='#00bcd4', linewidth=0.8, alpha=0.8)
        self.ax_vol.plot(df.index, vol_ma10, color='#ffeb3b', linewidth=0.8, alpha=0.8)
        # VOL 數值
        v5 = vol_ma5.iloc[-1] if not vol_ma5.empty and not pd.isna(vol_ma5.iloc[-1]) else 0
        v10 = vol_ma10.iloc[-1] if not vol_ma10.empty and not pd.isna(vol_ma10.iloc[-1]) else 0
        vol_text = f"VOL  5T:{v5:,.0f}  10T:{v10:,.0f}"
        t = self.ax_vol.text(0.01, 0.95, vol_text, transform=self.ax_vol.transAxes,
                             fontsize=9, color='#e0e0e0', va='top', ha='left',
                             bbox=dict(boxstyle='round,pad=0.3', facecolor='#0d1117', alpha=0.8))
        self._ma_texts.append(t)
        self.ax_vol.set_ylabel("成交量", fontsize=10, color=self._text_color)
        self.ax_vol.grid(True, linestyle='--', alpha=0.15, color=self._grid_color)
        self.ax_vol.yaxis.set_label_position('right')
        self.ax_vol.tick_params(labelleft=False, labelright=True)
        # 格式化成交量 Y 軸（用萬為單位）
        self.ax_vol.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/10000:.0f}萬' if x >= 10000 else f'{x:,.0f}'))

        # ── KD 指標 ──
        self.ax_kd.plot(df.index, k_val, color='#00bcd4', linewidth=1.2, label='K')
        self.ax_kd.plot(df.index, d_val, color='#ffeb3b', linewidth=1.2, label='D')
        self.ax_kd.axhline(y=80, color='#555555', linestyle='--', linewidth=0.6)
        self.ax_kd.axhline(y=20, color='#555555', linestyle='--', linewidth=0.6)
        self.ax_kd.fill_between(df.index, 80, 100, alpha=0.08, color='#ef4444')
        self.ax_kd.fill_between(df.index, 0, 20, alpha=0.08, color='#22c55e')
        self.ax_kd.set_ylim(0, 100)
        self.ax_kd.set_ylabel("KD", fontsize=10, color=self._text_color)
        self.ax_kd.grid(True, linestyle='--', alpha=0.15, color=self._grid_color)
        self.ax_kd.yaxis.set_label_position('right')
        self.ax_kd.tick_params(labelleft=False, labelright=True)
        # KD 數值顯示
        kd_text = f"KD  9K:{latest_k:.2f}  9D:{latest_d:.2f}"
        t = self.ax_kd.text(0.01, 0.95, kd_text, transform=self.ax_kd.transAxes,
                            fontsize=9, color='#e0e0e0', va='top', ha='left',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='#0d1117', alpha=0.8))
        self._ma_texts.append(t)
        self.ax_kd.legend(fontsize=9, loc='upper right', facecolor='#0d1117',
                          edgecolor='#555555', labelcolor=self._text_color)

        # X軸日期格式
        self.ax_kd.set_xlabel("日期", fontsize=10, color=self._text_color)
        self.ax_kd.xaxis.set_major_locator(mdates.MonthLocator())
        self.ax_kd.xaxis.set_major_formatter(mdates.DateFormatter('%m'))
        self.fig.autofmt_xdate(rotation=0)

        # 未來趨勢預測
        try:
            pred = int(self.pred_days.get())
        except Exception:
            pred = 0
        if pred > 0 and len(close) > 10:
            self._draw_prediction(df, close, pred)  # method read from self.pred_method

        self.canvas.draw()
        self.btn.config(state=tk.NORMAL, text="查詢")

    def show_error(self, msg):
        """顯示錯誤訊息"""
        messagebox.showerror("錯誤", msg)
        self.btn.config(state=tk.NORMAL, text="查詢")
        self.info_text.set("")

    def _on_close(self):
        """關閉視窗時強制結束所有執行緒"""
        import os
        self.root.destroy()
        os._exit(0)

if __name__ == '__main__':
    root = tk.Tk()
    app = StockApp(root)
    root.mainloop()
