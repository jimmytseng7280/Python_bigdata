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
    # 若預載資料查不到，即時查詢 TWSE/TPEx API
    try:
        sym = _lookup_name_via_api(q)
        if sym:
            return sym
    except Exception:
        pass
    return q

def _lookup_name_via_api(name):
    """即時查詢 TWSE/TPEx API 將中文名稱轉為股票代號"""
    import requests as _req
    # 查上市
    try:
        r = _req.get('https://openapi.twse.com.tw/v1/opendata/t187ap03_L',
                     headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        for item in r.json():
            code = item[[k for k in item if '代號' in k][0]]
            for key in (k for k in item if '簡稱' in k or '名稱' in k):
                v = item[key].strip()
                if v and name in v:
                    _NAME_MAP[v] = f'{code}.TW'
                    return f'{code}.TW'
    except Exception:
        pass
    # 查上櫃
    try:
        r = _req.get('https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O',
                     headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, verify=False)
        for item in r.json():
            code = item['SecuritiesCompanyCode']
            for key in ('CompanyAbbreviation', 'CompanyName'):
                v = item[key].strip()
                if v and name in v:
                    _NAME_MAP[v] = f'{code}.TWO'
                    return f'{code}.TWO'
    except Exception:
        pass
    # 查興櫃
    try:
        r = _req.get('https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_R',
                     headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, verify=False)
        for item in r.json():
            code = item['SecuritiesCompanyCode']
            for key in ('CompanyAbbreviation', 'CompanyName'):
                v = item[key].strip()
                if v and name in v:
                    _NAME_MAP[v] = f'{code}.TWO'
                    return f'{code}.TWO'
    except Exception:
        pass
    return None

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
            # yfinance end 為 exclusive，加一天確保包含 end_date
            end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1)
            kwargs['end'] = end_dt.strftime('%Y-%m-%d')
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
            # 下載當日分鐘資料計算均價（每筆成交價的簡單平均）
            avg_price = None
            try:
                intraday = yf.download(sym, period='1d', interval='1m', progress=False, auto_adjust=True)
                if not intraday.empty:
                    if isinstance(intraday.columns, pd.MultiIndex):
                        intraday.columns = intraday.columns.droplevel(1)
                    avg_price = intraday['Close'].mean()
            except Exception:
                pass
            return sym, df, info, avg_price
    return symbol, pd.DataFrame(), {}, None


# ═══════════════════════════════════════════════════════════════
# 深度學習模型（純 numpy 實作，無需 PyTorch / TensorFlow）
# ═══════════════════════════════════════════════════════════════

def _dl_sigmoid(x):
    x = np.clip(x, -500, 500)
    return 1.0 / (1.0 + np.exp(-x))

def _dl_tanh(x):
    return np.tanh(np.clip(x, -500, 500))

def _dl_relu(x):
    return np.maximum(0, x)

def _dl_normalize(data):
    mu, sigma = np.mean(data), np.std(data)
    if sigma < 1e-8:
        sigma = 1.0
    return (data - mu) / sigma, mu, sigma

def _dl_create_sequences(data, seq_len):
    X, y = [], []
    for i in range(len(data) - seq_len):
        X.append(data[i:i+seq_len])
        y.append(data[i+seq_len])
    return np.array(X), np.array(y)


# ── LSTM ──

class _NpyLSTM:
    """純 numpy LSTM 單元"""
    def __init__(self, input_size, hidden_size):
        scale = np.sqrt(2.0 / (input_size + hidden_size))
        self.Wf = np.random.randn(hidden_size, input_size + hidden_size) * scale
        self.bf = np.zeros((hidden_size, 1))
        self.Wi = np.random.randn(hidden_size, input_size + hidden_size) * scale
        self.bi = np.zeros((hidden_size, 1))
        self.Wc = np.random.randn(hidden_size, input_size + hidden_size) * scale
        self.bc = np.zeros((hidden_size, 1))
        self.Wo = np.random.randn(hidden_size, input_size + hidden_size) * scale
        self.bo = np.zeros((hidden_size, 1))
        self.hidden_size = hidden_size

    def forward(self, x_seq):
        h = np.zeros((self.hidden_size, 1))
        c = np.zeros((self.hidden_size, 1))
        for t in range(x_seq.shape[1]):
            xt = x_seq[:, t:t+1]
            concat = np.vstack([h, xt])
            f = _dl_sigmoid(self.Wf @ concat + self.bf)
            i = _dl_sigmoid(self.Wi @ concat + self.bi)
            c_hat = _dl_tanh(self.Wc @ concat + self.bc)
            o = _dl_sigmoid(self.Wo @ concat + self.bo)
            c = f * c + i * c_hat
            h = o * _dl_tanh(c)
        return h, c


def _dl_train_lstm(close_arr, pred_days, seq_len=30, hidden=16, epochs=30, lr=0.005):
    """訓練 LSTM 並預測未來天數，回傳預測陣列"""
    norm, mu, sigma = _dl_normalize(close_arr)
    if len(norm) < seq_len + 5:
        return None
    X, y = _dl_create_sequences(norm, seq_len)
    if len(X) < 10:
        return None
    n_feat = 1
    lstm = _NpyLSTM(n_feat, hidden)
    # 輸出層
    Wo = np.random.randn(1, hidden) * np.sqrt(2.0 / hidden)
    bo = np.zeros((1, 1))

    for epoch in range(epochs):
        perm = np.random.permutation(len(X))
        total_loss = 0
        for idx in perm:
            xi = X[idx].reshape(n_feat, seq_len)
            yi = y[idx]
            h, c = lstm.forward(xi)
            pred_val = (Wo @ h + bo).item()
            loss = (pred_val - yi) ** 2
            total_loss += loss
            d_out = 2 * (pred_val - yi) / len(X)
            dWo = d_out * h.T
            dbo = np.array([[d_out]])
            # 簡化梯度更新（直接更新）
            Wo -= lr * dWo
            bo -= lr * dbo
        if epoch % 20 == 0:
            avg = total_loss / len(X)

    # 遞迴預測
    seq = list(norm[-seq_len:])
    preds = []
    for _ in range(pred_days):
        xi = np.array(seq[-seq_len:]).reshape(n_feat, seq_len)
        h, c = lstm.forward(xi)
        p = (Wo @ h + bo).item()
        preds.append(p)
        seq.append(p)
    preds = np.array(preds) * sigma + mu
    return preds


# ── GRU ──

class _NpyGRU:
    """純 numpy GRU 單元"""
    def __init__(self, input_size, hidden_size):
        scale = np.sqrt(2.0 / (input_size + hidden_size))
        self.Wz = np.random.randn(hidden_size, input_size + hidden_size) * scale
        self.bz = np.zeros((hidden_size, 1))
        self.Wr = np.random.randn(hidden_size, input_size + hidden_size) * scale
        self.br = np.zeros((hidden_size, 1))
        self.Wh = np.random.randn(hidden_size, input_size + hidden_size) * scale
        self.bh = np.zeros((hidden_size, 1))
        self.hidden_size = hidden_size

    def forward(self, x_seq):
        h = np.zeros((self.hidden_size, 1))
        for t in range(x_seq.shape[1]):
            xt = x_seq[:, t:t+1]
            concat = np.vstack([h, xt])
            z = _dl_sigmoid(self.Wz @ concat + self.bz)
            r = _dl_sigmoid(self.Wr @ concat + self.br)
            concat_r = np.vstack([r * h, xt])
            h_hat = _dl_tanh(self.Wh @ concat_r + self.bh)
            h = (1 - z) * h + z * h_hat
        return h


def _dl_train_gru(close_arr, pred_days, seq_len=30, hidden=16, epochs=30, lr=0.005):
    """訓練 GRU 並預測未來天數"""
    norm, mu, sigma = _dl_normalize(close_arr)
    if len(norm) < seq_len + 5:
        return None
    X, y = _dl_create_sequences(norm, seq_len)
    if len(X) < 10:
        return None
    n_feat = 1
    gru = _NpyGRU(n_feat, hidden)
    Wo = np.random.randn(1, hidden) * np.sqrt(2.0 / hidden)
    bo = np.zeros((1, 1))

    for epoch in range(epochs):
        perm = np.random.permutation(len(X))
        total_loss = 0
        for idx in perm:
            xi = X[idx].reshape(n_feat, seq_len)
            yi = y[idx]
            h = gru.forward(xi)
            pred_val = (Wo @ h + bo).item()
            loss = (pred_val - yi) ** 2
            total_loss += loss
            d_out = 2 * (pred_val - yi) / len(X)
            Wo -= lr * d_out * h.T
            bo -= lr * np.array([[d_out]])

    seq = list(norm[-seq_len:])
    preds = []
    for _ in range(pred_days):
        xi = np.array(seq[-seq_len:]).reshape(n_feat, seq_len)
        h = gru.forward(xi)
        p = (Wo @ h + bo).item()
        preds.append(p)
        seq.append(p)
    return np.array(preds) * sigma + mu


# ── Transformer（簡化版） ──

def _dl_train_transformer(close_arr, pred_days, seq_len=30, d_model=16, n_heads=4, epochs=30, lr=0.003):
    """純 numpy Transformer 預測模型"""
    norm, mu, sigma = _dl_normalize(close_arr)
    if len(norm) < seq_len + 5:
        return None
    X, y = _dl_create_sequences(norm, seq_len)
    if len(X) < 10:
        return None
    n_feat = 1
    head_dim = d_model // n_heads

    # 權重
    scale = np.sqrt(2.0 / (n_feat + d_model))
    Wq = np.random.randn(d_model, n_feat) * scale
    Wk = np.random.randn(d_model, n_feat) * scale
    Wv = np.random.randn(d_model, n_feat) * scale
    Wo_attn = np.random.randn(d_model, d_model) * scale
    # FFN
    W1 = np.random.randn(d_model * 4, d_model) * np.sqrt(2.0 / d_model)
    b1 = np.zeros((d_model * 4, 1))
    W2 = np.random.randn(d_model, d_model * 4) * np.sqrt(2.0 / (d_model * 4))
    b2 = np.zeros((d_model, 1))
    # 位置編碼
    pos_enc = np.random.randn(seq_len, d_model) * 0.02
    # 輸出
    Wout = np.random.randn(1, d_model) * np.sqrt(2.0 / d_model)
    bout = np.zeros((1, 1))

    def _forward(xi):
        seq = xi.T + pos_enc[:xi.shape[1]]  # (seq_len, n_feat) -> broadcast
        Q = Wq @ xi + pos_enc[:xi.shape[1]].T  # (d_model, seq_len)
        K = Wk @ xi + pos_enc[:xi.shape[1]].T
        V = Wv @ xi
        # 簡化注意力（不用分頭）
        scale_factor = np.sqrt(head_dim)
        attn = Q.T @ K / scale_factor  # (seq_len, seq_len)
        attn = np.exp(attn - np.max(attn, axis=-1, keepdims=True))
        attn = attn / (np.sum(attn, axis=-1, keepdims=True) + 1e-8)
        out = (attn @ V.T).T  # (d_model, seq_len)
        out = Wo_attn @ out
        out = _dl_relu(out)
        # 取最後一個時間步
        last = out[:, -1:]  # (d_model, 1)
        # FFN
        ff = _dl_relu(W1 @ last + b1)
        ff = W2 @ ff + b2
        last = last + ff  # residual
        return Wout @ last + bout

    for epoch in range(epochs):
        perm = np.random.permutation(len(X))
        for idx in perm:
            xi = X[idx].reshape(n_feat, seq_len)
            yi = y[idx]
            pred_val = _forward(xi).item()
            d_out = 2 * (pred_val - yi) / len(X) * lr
            # 簡化：直接微調輸出層
            Wout -= d_out * (_forward(xi).item() * 0.01)
            bout -= np.array([[d_out]])

    seq = list(norm[-seq_len:])
    preds = []
    for _ in range(pred_days):
        xi = np.array(seq[-seq_len:]).reshape(n_feat, seq_len)
        p = _forward(xi).item()
        preds.append(p)
        seq.append(p)
    return np.array(preds) * sigma + mu


def calc_dl_prediction(df, model_type='lstm', pred_days=20):
    """統一深度學習預測入口"""
    close = df['Close'].values.astype(float)
    if model_type == 'lstm':
        return _dl_train_lstm(close, pred_days)
    elif model_type == 'gru':
        return _dl_train_gru(close, pred_days)
    elif model_type == 'transformer':
        return _dl_train_transformer(close, pred_days)
    return None


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
        default_start = '2026-01-01'
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
        self.pred_days = tk.StringVar(value="20")
        pred_combo = ttk.Combobox(date_frame, textvariable=self.pred_days,
                                  values=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "15", "20", "30", "60", "90", "120"], width=5, state='readonly')
        pred_combo.pack(side=tk.LEFT, padx=2)
        ttk.Label(date_frame, text="(0=不預測)", foreground='gray', font=('', 9)).pack(side=tk.LEFT)

        ttk.Label(date_frame, text="    預測方法:").pack(side=tk.LEFT)
        self.pred_method = tk.StringVar(value="全部")
        method_combo = ttk.Combobox(date_frame, textvariable=self.pred_method,
                                    values=["全部", "AI預測", "XGBoost", "隨機森林", "LightGBM", "CatBoost", "GBoost", "ExtraTree", "Stacking", "線性", "多項式", "蒙地卡羅", "指數平滑", "MA交叉", "布林通道", "LSTM", "GRU", "Transformer"],
                                    width=8, state='readonly')
        method_combo.pack(side=tk.LEFT, padx=2)

        # 資訊區：顯示最新交易日資料
        self.info_frame = ttk.LabelFrame(root, text="最新交易日資訊")
        self.info_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        self.info_text = tk.StringVar()
        ttk.Label(self.info_frame, textvariable=self.info_text,
                  font=(_CHINESE_FONT, 11)).pack(padx=10, pady=8)

        # 預測值區：用 tk.Text 支援多色文字，依線圖顏色顯示
        self.pred_frame = ttk.Frame(root)
        self.pred_frame.pack(fill=tk.X, padx=10, pady=(0, 2))
        self.pred_text_widget = tk.Text(self.pred_frame, height=3, wrap=tk.WORD,
                                        bg='#ffffff', fg='#333333', font=(_CHINESE_FONT, 10),
                                        borderwidth=1, relief='solid', padx=8, pady=4)
        self.pred_text_widget.pack(fill=tk.X)
        self.pred_text_widget.insert('1.0', '查詢後自動預測...')
        self.pred_text_widget.config(state=tk.DISABLED)
        # 定義顏色標籤（與線圖顏色對應）
        self._pred_tag_colors = {
            'linear': '#888888', 'poly': '#ff9800', 'mc': '#bb86fc',
            'es': '#00bcd4', 'ma': '#4caf50', 'boll': '#e040fb',
            'xgb': '#2196f3', 'rf': '#ff5722', 'lgb': '#8bc34a',
            'cb': '#ff9800', 'gb': '#00897b', 'et': '#32cd32',
            'st': '#ff4500', 'lstm': '#00897b', 'gru': '#c2185b',
            'tf': '#5c6bc0',
        }

        # 「全部」模式預測狀態（背景執行緒 + 即時顯示用）
        self._pred_generation = 0       # 遞增計數器，使舊執行緒自動失效
        self._pred_spinner_running = False
        self._pred_spinner_idx = 0
        self._pred_done_count = 0
        self._pred_total_count = 0

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
        self._x_pos = None
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
        """左鍵：顯示該日收盤價及成交量；雙擊還原全範圍；拖曳平移"""
        if self._last_df is None:
            return
        if event.inaxes not in (self.ax, self.ax_vol, self.ax_kd):
            return
        if event.dblclick:
            # 重設為全範圍（含預測區域）
            total = len(self._date_index) if hasattr(self, '_date_index') else len(self._last_df)
            self._set_xlim_all(-0.5, total - 0.5)
            return
        if event.button == 1:
            self._dragging = True
            self._drag_start = event.xdata
            self._drag_xlim_start = self.ax.get_xlim()
            self._press_x = event.x
            self._press_y = event.y
            self._pressed_in_ax = event.inaxes
            self._show_click_popup(event)

    def _on_release(self, event):
        """滑鼠放開：結束拖曳"""
        self._dragging = False
        self._drag_start = None
        self._drag_xlim_start = None

    def _on_motion(self, event):
        """拖曳平移"""
        if not self._dragging or self._drag_start is None:
            return
        if event.xdata is None:
            return
        dx = event.xdata - self._drag_start
        xmin, xmax = self._drag_xlim_start
        self._set_xlim_all(xmin + dx, xmax + dx)
        self.canvas.draw_idle()

    def _show_click_popup(self, event):
        """點擊K線時在圖表上顯示該日收盤價及成交量"""
        if self._last_df is None or event.xdata is None:
            return
        df = self._last_df
        nearest = int(round(event.xdata))
        if nearest < 0 or nearest >= len(df):
            return
        row = df.iloc[nearest]
        day = df.index[nearest]

        # 清除舊的點擊標注
        if self._click_annotation is not None:
            try: self._click_annotation.remove()
            except Exception: pass
            self._click_annotation = None

        color = '#ef4444' if row['Close'] >= row['Open'] else '#22c55e'
        vol_text = f"{row['Volume']/1000:,.0f}張"

        day_str = day.strftime('%Y-%m-%d') if hasattr(day, 'strftime') else str(day)
        text = f"{day_str}\n收盤價: {row['Close']:.2f}\n成交量: {vol_text}"

        ax = event.inaxes
        if ax == self.ax:
            x, y = nearest, row['Close']
        elif ax == self.ax_vol:
            x, y = nearest, row['Volume']
        else:
            x, y = nearest, row['Close']

        self._click_annotation = ax.annotate(
            text, xy=(x, y),
            xytext=(15, 15), textcoords='offset points',
            fontsize=9, color='white', fontfamily=_CHINESE_FONT,
            bbox=dict(boxstyle='round,pad=0.4', facecolor=color, edgecolor='white', alpha=0.85),
            arrowprops=dict(arrowstyle='-', color='white', lw=0.5),
            zorder=30)
        self.canvas.draw_idle()

    def _apply_date_axis(self, xmin, xmax):
        """根據可見範圍自動調整X軸日期格式與刻度密度"""
        if self._last_df is None:
            return
        date_index = getattr(self, '_date_index', self._last_df.index)
        n = len(date_index)
        span = xmax - xmin
        # 根據可見範圍決定格式與步進
        if span <= 30:
            fmt_str = '%m/%d'
            step = max(1, int(span / 15))
        elif span <= 120:
            fmt_str = '%Y/%m/%d'
            step = max(1, int(span / 15))
        elif span <= 365:
            fmt_str = '%Y/%m'
            step = max(5, int(span / 15))
        else:
            fmt_str = '%Y/%m'
            step = max(20, int(span / 12))

        def fmt(x, pos):
            idx = int(round(x))
            if 0 <= idx < n:
                return date_index[idx].strftime(fmt_str)
            return ''
        loc = plt.MultipleLocator(step)
        for a in (self.ax, self.ax_vol, self.ax_kd):
            a.xaxis.set_major_locator(loc)
            a.xaxis.set_major_formatter(plt.FuncFormatter(fmt))

    def _on_xlim_change(self, ax):
        """縮放時自動調整刻度密度（不含 draw，由 scroll handler 處理）"""
        if getattr(self, '_in_xlim_change', False) or self._last_df is None:
            return
        self._in_xlim_change = True
        try:
            xmin, xmax = ax.get_xlim()
            self._apply_date_axis(xmin, xmax)
        finally:
            self._in_xlim_change = False

    def _update_pred_text(self, items, pred_days):
        """用 tk.Text 依線圖顏色顯示預測值
        items: [(name, value, color_hex), ...]
        """
        S0 = self._last_df['Close'].values[-1] if self._last_df is not None else 0
        self.pred_text_widget.config(state=tk.NORMAL, height=min(len(items) + 1, 6))
        self.pred_text_widget.delete('1.0', tk.END)

        header = f'目前股價: {S0:.2f}  |  預測{pred_days}日  |  方法: {self.pred_method.get()}\n'
        self.pred_text_widget.insert(tk.END, header)
        self.pred_text_widget.tag_add('header', '1.0', '1.end')
        self.pred_text_widget.tag_config('header', foreground='#333333', font=(_CHINESE_FONT, 10, 'bold'))

        for i, (name, val, clr) in enumerate(items):
            pct = (val - S0) / S0 * 100
            arrow = '▲' if pct > 0 else '▼' if pct < 0 else '─'
            tag = f'line_{i}'
            self.pred_text_widget.insert(tk.END, f'  {name}: {val:.2f}  ({arrow}{pct:+.2f}%)  ')
            self.pred_text_widget.tag_config(tag, foreground=clr, font=(_CHINESE_FONT, 10, 'bold'))
            # 把顏色套用到這一行
            line_start = self.pred_text_widget.index(f'end - 1c - {len(f"  {name}: {val:.2f}  ({arrow}{pct:+.2f}%)  ")}c')
            line_end = self.pred_text_widget.index('end - 1c')
            self.pred_text_widget.tag_add(tag, line_start, line_end)

        self.pred_text_widget.config(state=tk.DISABLED)

    def _init_pred_text_spinner(self, pred_days):
        """初始化預測文字框：標頭 + 底部旋轉動畫行"""
        S0 = self._last_df['Close'].values[-1] if self._last_df is not None else 0
        self.pred_text_widget.config(state=tk.NORMAL, height=3)
        self.pred_text_widget.delete('1.0', tk.END)
        header = f'目前股價: {S0:.2f}  |  預測{pred_days}日  |  方法: 全部\n'
        self.pred_text_widget.insert(tk.END, header)
        self.pred_text_widget.tag_add('header', '1.0', '1.end')
        self.pred_text_widget.tag_config('header', foreground='#333333', font=(_CHINESE_FONT, 10, 'bold'))
        # 旋轉動畫行（固定在最後一行）
        self.pred_text_widget.insert(tk.END, '  ⠋ 正在計算預測... 0/16\n')
        self.pred_text_widget.tag_config('spin', foreground='#888888', font=(_CHINESE_FONT, 9))
        self.pred_text_widget.tag_add('spin', 'end - 2l', 'end - 1c')
        self.pred_text_widget.config(state=tk.DISABLED)
        self._pred_spinner_running = True
        self._pred_spinner_idx = 0
        self._tick_pred_spinner()

    def _tick_pred_spinner(self):
        """每 100ms 更新旋轉動畫行（只替換最後一行的文字）"""
        if not self._pred_spinner_running:
            return
        ch = self._SPIN_FRAMES[self._pred_spinner_idx % len(self._SPIN_FRAMES)]
        done = self._pred_done_count
        total = self._pred_total_count
        spin_text = f'  {ch} 正在計算預測... {done}/{total}'
        self.pred_text_widget.config(state=tk.NORMAL)
        # 刪除舊的旋轉行（最後一行）
        self.pred_text_widget.delete('end - 2l', 'end - 1c')
        # 插入新的旋轉行
        self.pred_text_widget.insert(tk.END, spin_text + '\n')
        self.pred_text_widget.tag_config('spin', foreground='#888888', font=(_CHINESE_FONT, 9))
        self.pred_text_widget.tag_add('spin', 'end - 2l', 'end - 1c')
        self.pred_text_widget.config(state=tk.DISABLED)
        self._pred_spinner_idx += 1
        self.root.after(100, self._tick_pred_spinner)

    def _stop_pred_spinner(self):
        """停止旋轉動畫"""
        self._pred_spinner_running = False

    def _append_pred_text_item(self, name, val, color, S0):
        """在旋轉行之前插入一行彩色預測結果（即時顯示用）"""
        pct = (val - S0) / S0 * 100 if S0 else 0
        arrow = '▲' if pct > 0 else '▼' if pct < 0 else '─'
        line_text = f'  {name}: {val:.2f}  ({arrow}{pct:+.2f}%)\n'
        self.pred_text_widget.config(state=tk.NORMAL)
        # 在旋轉行（最後一行）之前插入
        insert_pos = 'end - 2c'
        cur_line = int(self.pred_text_widget.index(insert_pos).split('.')[0])
        tag = f'pred_{cur_line}'
        self.pred_text_widget.insert(insert_pos, line_text)
        self.pred_text_widget.tag_config(tag, foreground=color, font=(_CHINESE_FONT, 10, 'bold'))
        self.pred_text_widget.tag_add(tag, f'{cur_line}.0', f'{cur_line}.end - 1c')
        # 自動調整高度（上限 12 行）
        new_lines = int(self.pred_text_widget.index('end-1c').split('.')[0])
        self.pred_text_widget.config(height=min(max(new_lines, 3), 12))
        self.pred_text_widget.config(state=tk.DISABLED)

    def _finalize_pred_text(self, final_values, pred_days):
        """所有方法完成後，重建文字框並依價格排序顯示最終結果"""
        S0 = self._last_df['Close'].values[-1] if self._last_df is not None else 0
        self._stop_pred_spinner()
        final_values.sort(key=lambda x: x[1], reverse=True)
        self.pred_text_widget.config(state=tk.NORMAL, height=min(len(final_values) + 2, 12))
        self.pred_text_widget.delete('1.0', tk.END)
        header = f'目前股價: {S0:.2f}  |  預測{pred_days}日  |  方法: 全部\n'
        self.pred_text_widget.insert(tk.END, header)
        self.pred_text_widget.tag_add('header', '1.0', '1.end')
        self.pred_text_widget.tag_config('header', foreground='#333333', font=(_CHINESE_FONT, 10, 'bold'))
        for i, (name, val, clr) in enumerate(final_values):
            pct = (val - S0) / S0 * 100 if S0 else 0
            arrow = '▲' if pct > 0 else '▼' if pct < 0 else '─'
            tag = f'line_{i}'
            line_text = f'  {name}: {val:.2f}  ({arrow}{pct:+.2f}%)\n'
            self.pred_text_widget.insert(tk.END, line_text)
            self.pred_text_widget.tag_config(tag, foreground=clr, font=(_CHINESE_FONT, 10, 'bold'))
            line_no = i + 2
            self.pred_text_widget.tag_add(tag, f'{line_no}.0', f'{line_no}.end')
        self.pred_text_widget.config(state=tk.DISABLED)

    def _draw_prediction(self, df, close, pred_days):
        """根據選定方法預測未來走勢"""
        # 延伸日期索引以涵蓋預測天數
        last_date = df.index[-1]
        future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=pred_days)
        self._date_index = df.index.append(future_dates)

        # 自適應日期格式（含預測區域）
        total = len(self._date_index)
        self._apply_date_axis(-0.5, total - 0.5)

        method = self.pred_method.get()
        if method == "全部":
            self._pred_all(df, close, pred_days)
        elif method == "AI預測":
            self._pred_ai(df, close, pred_days)
        elif method == "XGBoost":
            self._pred_xgboost(df, close, pred_days)
        elif method == "隨機森林":
            self._pred_rf(df, close, pred_days)
        elif method == "LightGBM":
            self._pred_lgb(df, close, pred_days)
        elif method == "CatBoost":
            self._pred_cb(df, close, pred_days)
        elif method == "GBoost":
            self._pred_gb(df, close, pred_days)
        elif method == "ExtraTree":
            self._pred_et(df, close, pred_days)
        elif method == "Stacking":
            self._pred_stacking(df, close, pred_days)
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
        elif method == "LSTM":
            self._pred_lstm(df, close, pred_days)
        elif method == "GRU":
            self._pred_gru(df, close, pred_days)
        elif method == "Transformer":
            self._pred_transformer(df, close, pred_days)
        else:
            self._pred_bollinger(df, close, pred_days)

        # ===== 單一方法：從 legend 取值，依線圖顏色顯示 =====
        if method != "全部":
            method_color_map = {
                '線性': '#888888', '多項式': '#ff9800', '蒙地卡羅': '#bb86fc',
                '指數平滑': '#00bcd4', 'MA交叉': '#4caf50', '布林通道': '#e040fb',
                'XGBoost': '#ff6b6b', '隨機森林': '#4fc3f7', 'LightGBM': '#ffd700',
                'CatBoost': '#ff69b4', 'GBoost': '#00ffff', 'ExtraTree': '#32cd32',
                'Stacking': '#ff4500', 'LSTM': '#00897b', 'GRU': '#c2185b',
                'Transformer': '#5c6bc0', 'AI預測': '#ff6b6b',
            }
            S0 = close.values[-1]
            items = []
            legend = self.ax.get_legend()
            if legend is not None:
                for text in legend.get_texts():
                    lbl = text.get_text()
                    clr = method_color_map.get(method, '#e0e0e0')
                    # 從 legend 文字中提取數值
                    parts = lbl.split()
                    try:
                        val = float(parts[-1])
                    except ValueError:
                        val = S0
                    items.append((method, val, clr))
            if not items:
                items = [(method, S0, '#e0e0e0')]
            self._update_pred_text(items, pred_days)

    def _pred_all(self, df, close, pred_days):
        """全部預測：背景執行緒依序計算，每完成一個方法立即畫線並在文字框顯示"""
        from matplotlib.lines import Line2D
        n = len(close)
        x = np.arange(n)
        y = close.values.astype(float)
        future_x = np.arange(n, n + pred_days)
        S0 = y[-1]

        # 遞增 generation，使之前的舊執行緒自動失效
        gen = self._pred_generation
        self._pred_generation += 1

        # 啟動旋轉動畫
        self._pred_done_count = 0
        self._pred_total_count = 16
        self.root.after(0, self._init_pred_text_spinner, pred_days)

        # 畫預測區域底色
        def _draw_background():
            if self._pred_generation != gen:
                return
            self.ax.axvspan(n - 1, n - 1 + pred_days, alpha=0.03, color='#bb86fc')
            self.canvas.draw_idle()
        self.root.after(0, _draw_background)

        def _worker():
            """背景執行緒：依序計算 16 種方法，每完成一個就排程到主執行緒畫圖"""
            legend_handles = []
            final_values = []

            def _schedule_draw(val, color, label):
                """將計算結果排程到主執行緒畫圖"""
                if val is None:
                    self._pred_done_count += 1
                    return
                def _main():
                    if self._pred_generation != gen:
                        return
                    future_xx = np.arange(n, n + len(val))
                    self.ax.plot(future_xx, val, color=color, linewidth=1.5, linestyle='--', alpha=0.9)
                    h = Line2D([0], [0], color=color, linestyle='--', linewidth=1.5,
                               label=f'{label} {val[-1]:.2f}')
                    self._pred_done_count += 1
                    self._append_pred_text_item(label, val[-1], color, S0)
                    self.canvas.draw_idle()
                self.root.after(0, _main)
                legend_handles.append((label, val[-1], color))
                final_values.append((label, val[-1], color))

            # ═══════════ Phase 1：統計方法（快速） ═══════════

            # 1. 線性回歸（灰色）
            try:
                coeffs1 = np.polyfit(x, y, 1)
                trend1 = np.polyval(coeffs1, x)
                pred1 = np.polyval(coeffs1, future_x)
                std1 = np.std(y - trend1)
                _schedule_draw(pred1, '#888888', '線性')
                # 畫信賴區間
                def _fill_linear():
                    if self._pred_generation != gen:
                        return
                    self.ax.fill_between(future_x, pred1 - std1, pred1 + std1, alpha=0.04, color='#888888')
                self.root.after(0, _fill_linear)
            except Exception:
                self._pred_done_count += 1

            # 2. 多項式（橙色）
            try:
                c2 = np.polyfit(x, y, 2)
                c3 = np.polyfit(x, y, 3)
                pred2 = (np.polyval(c2, future_x) + np.polyval(c3, future_x)) / 2
                std2 = np.std(y - np.polyval(c2, x))
                _schedule_draw(pred2, '#ff9800', '多項式')
                def _fill_poly():
                    if self._pred_generation != gen:
                        return
                    self.ax.fill_between(future_x, pred2 - std2, pred2 + std2, alpha=0.04, color='#ff9800')
                self.root.after(0, _fill_poly)
            except Exception:
                self._pred_done_count += 1

            # 3. 蒙地卡羅（紫色）
            up_prob = 50.0
            mc_mean = None
            try:
                returns = np.diff(y) / y[:-1]
                mu, sigma = np.mean(returns), np.std(returns)
                sims = np.zeros((200, pred_days))
                for i in range(200):
                    prices = [S0]
                    for _ in range(pred_days):
                        prices.append(prices[-1] * np.exp((mu - 0.5 * sigma**2) + sigma * np.random.normal()))
                    sims[i, :] = prices[1:]
                mc_mean = np.mean(sims, axis=0)
                up_prob = np.mean(sims[:, -1] > S0) * 100
                mc_p5 = np.percentile(sims, 5, axis=0)
                mc_p95 = np.percentile(sims, 95, axis=0)

                def _draw_mc():
                    if self._pred_generation != gen:
                        return
                    for i in range(0, 200, 10):
                        self.ax.plot(future_x, sims[i], color='#bb86fc', linewidth=0.2, alpha=0.1)
                    self.ax.plot(future_x, mc_mean, color='#bb86fc', linewidth=1.5, linestyle='-')
                    self.ax.fill_between(future_x, mc_p5, mc_p95, alpha=0.06, color='#bb86fc')
                    # MC 機率文字
                    self.ax.text(0.02, 0.82,
                                 f'MC 上漲 {up_prob:.1f}% / 下跌 {100-up_prob:.1f}%　MA5/MA10 多頭',
                                 transform=self.ax.transAxes, fontsize=8, color='#e0e0e0',
                                 fontfamily=_CHINESE_FONT, verticalalignment='top',
                                 bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a1a2e', edgecolor='#555555'))
                    self.canvas.draw_idle()
                self.root.after(0, _draw_mc)
                _schedule_draw(mc_mean, '#bb86fc', 'MC均值')
            except Exception:
                self._pred_done_count += 1

            # 4. 指數平滑（青色）
            try:
                alpha_es, beta_es = 0.3, 0.1
                level = [y[0]]
                trend_v = [y[1] - y[0] if n > 1 else 0]
                for t in range(1, n):
                    new_level = alpha_es * y[t] + (1 - alpha_es) * (level[-1] + trend_v[-1])
                    new_trend = beta_es * (new_level - level[-1]) + (1 - beta_es) * trend_v[-1]
                    level.append(new_level)
                    trend_v.append(new_trend)
                pred4 = [level[-1] + (i + 1) * trend_v[-1] for i in range(pred_days)]
                _schedule_draw(np.array(pred4), '#00bcd4', '指數平滑')
            except Exception:
                self._pred_done_count += 1

            # 5. MA交叉（綠/紅）
            try:
                ma5 = np.convolve(y, np.ones(5)/5, mode='valid')
                ma10 = np.convolve(y, np.ones(10)/10, mode='valid')
                latest_diff = ma5[-1] - ma10[-1]
                if len(ma5) >= 5:
                    slope = np.polyfit(np.arange(5), ma5[-5:], 1)[0]
                else:
                    slope = latest_diff / max(len(ma5), 1)
                pred5 = np.array([S0 + slope * (i + 1) for i in range(pred_days)])
                color5 = '#22c55e' if latest_diff > 0 else '#f44336'
                direction = "多" if latest_diff > 0 else "空"
                _schedule_draw(pred5, color5, f'MA交叉({direction})')
            except Exception:
                self._pred_done_count += 1

            # 6. 布林通道（洋紅）
            try:
                ma20 = np.convolve(y, np.ones(20)/20, mode='valid')
                current_ma = ma20[-1]
                pred6 = np.array([current_ma + (S0 - current_ma) * (0.95 ** i) for i in range(1, pred_days + 1)])
                _schedule_draw(pred6, '#e040fb', '布林')
            except Exception:
                self._pred_done_count += 1

            # ═══════════ Phase 2：機器學習方法 ═══════════

            # 7. XGBoost（紅色）
            try:
                xgb_pred, _ = self._calc_ai_prediction(df, pred_days)
                _schedule_draw(xgb_pred, '#ff6b6b', 'XGBoost')
            except Exception:
                self._pred_done_count += 1

            # 8. 隨機森林（淺藍色）
            try:
                rf_pred, _ = self._calc_rf_prediction(df, pred_days)
                _schedule_draw(rf_pred, '#4fc3f7', '隨機森林')
            except Exception:
                self._pred_done_count += 1

            # 9. LightGBM（金色）
            try:
                lgb_pred, _ = self._calc_lgb_prediction(df, pred_days)
                _schedule_draw(lgb_pred, '#ffd700', 'LightGBM')
            except Exception:
                self._pred_done_count += 1

            # 10. CatBoost（粉紅）
            try:
                cb_pred, _ = self._calc_cb_prediction(df, pred_days)
                _schedule_draw(cb_pred, '#ff69b4', 'CatBoost')
            except Exception:
                self._pred_done_count += 1

            # 11. Gradient Boosting（青色）
            try:
                gb_pred, _ = self._calc_gb_prediction(df, pred_days)
                _schedule_draw(gb_pred, '#00ffff', 'GBoost')
            except Exception:
                self._pred_done_count += 1

            # 12. Extra Trees（萊姆綠）
            try:
                et_pred, _ = self._calc_et_prediction(df, pred_days)
                _schedule_draw(et_pred, '#32cd32', 'ExtraTree')
            except Exception:
                self._pred_done_count += 1

            # 13. Stacking Ensemble（橘紅）
            try:
                st_pred, _ = self._calc_stacking_prediction(df, pred_days)
                _schedule_draw(st_pred, '#ff4500', 'Stacking')
            except Exception:
                self._pred_done_count += 1

            # ═══════════ Phase 3：深度學習方法（最慢） ═══════════

            # 14. LSTM（深青色）
            try:
                lstm_pred = calc_dl_prediction(df, 'lstm', pred_days)
                _schedule_draw(lstm_pred, '#00897b', 'LSTM')
            except Exception:
                self._pred_done_count += 1

            # 15. GRU（玫紅色）
            try:
                gru_pred = calc_dl_prediction(df, 'gru', pred_days)
                _schedule_draw(gru_pred, '#c2185b', 'GRU')
            except Exception:
                self._pred_done_count += 1

            # 16. Transformer（寶石藍）
            try:
                tf_pred = calc_dl_prediction(df, 'transformer', pred_days)
                _schedule_draw(tf_pred, '#5c6bc0', 'Transformer')
            except Exception:
                self._pred_done_count += 1

            # ═══════════ 最終整理 ═══════════
            def _finalize():
                if self._pred_generation != gen:
                    return
                # 排序 legend
                legend_handles.sort(key=lambda h: h[1], reverse=True)
                handles = [Line2D([0], [0], color=h[2], linestyle='--', linewidth=1.5,
                                  label=f'{h[0]} {h[1]:.2f}') for h in legend_handles]
                self.ax.legend(handles=handles, fontsize=7, loc='lower right',
                               facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0', ncol=3)
                self._finalize_pred_text(final_values, pred_days)
                self.canvas.draw_idle()
            self.root.after(50, _finalize)

        threading.Thread(target=_worker, daemon=True).start()

    def _pred_linear(self, df, close, pred_days):
        """線性回歸預測"""
        n = len(close)
        x = np.arange(n)
        y = close.values.astype(float)
        coeffs = np.polyfit(x, y, 1)
        trend = np.polyval(coeffs, x)
        future_x = np.arange(n, n + pred_days)
        pred = np.polyval(coeffs, future_x)
        std_r = np.std(y - trend)

        self.ax.plot(self._x_pos, trend, color='#888888', linewidth=1, linestyle=':', alpha=0.5)
        self.ax.plot(future_x, pred, color='#888888', linewidth=2, linestyle='--')
        self.ax.fill_between(future_x, pred - std_r, pred + std_r, alpha=0.12, color='#888888')
        self.ax.fill_between(future_x, pred - 2*std_r, pred + 2*std_r, alpha=0.05, color='#888888')
        self.ax.scatter(future_x[-1], pred[-1], color='#888888', s=50, zorder=5,
                        edgecolors='white', linewidth=0.5)
        self.ax.annotate(f'  預測 {pred[-1]:.2f}', xy=(future_x[-1], pred[-1]),
                         xytext=(0, 15), textcoords='offset points',
                         fontsize=9, color='#888888', fontweight='bold', fontfamily=_CHINESE_FONT)
        self.ax.axvspan(n - 1, n - 1 + pred_days, alpha=0.04, color='#888888')
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color='#888888', linestyle='--', linewidth=2, label=f'線性預測 {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_polynomial(self, df, close, pred_days):
        """多項式回歸（二次+三次平均）"""
        n = len(close)
        x = np.arange(n)
        y = close.values.astype(float)
        future_x = np.arange(n, n + pred_days)
        c2 = np.polyfit(x, y, 2)
        c3 = np.polyfit(x, y, 3)
        trend = np.polyval(c2, x)
        pred = (np.polyval(c2, future_x) + np.polyval(c3, future_x)) / 2
        std_r = np.std(y - trend)

        self.ax.plot(self._x_pos, trend, color='#ff9800', linewidth=1, linestyle=':', alpha=0.5)
        self.ax.plot(future_x, pred, color='#ff9800', linewidth=2, linestyle='--')
        self.ax.fill_between(future_x, pred - std_r, pred + std_r, alpha=0.12, color='#ff9800')
        self.ax.fill_between(future_x, pred - 2*std_r, pred + 2*std_r, alpha=0.05, color='#ff9800')
        self.ax.scatter(future_x[-1], pred[-1], color='#ff9800', s=50, zorder=5,
                        edgecolors='white', linewidth=0.5)
        self.ax.annotate(f'  預測 {pred[-1]:.2f}', xy=(future_x[-1], pred[-1]),
                         xytext=(0, 15), textcoords='offset points',
                         fontsize=9, color='#ff9800', fontweight='bold', fontfamily=_CHINESE_FONT)
        self.ax.axvspan(n - 1, n - 1 + pred_days, alpha=0.04, color='#ff9800')
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color='#ff9800', linestyle='--', linewidth=2, label=f'多項式預測 {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_monte_carlo(self, df, close, pred_days):
        """蒙地卡羅模擬 (GBM, 200 paths)"""
        y = close.values.astype(float)
        n = len(y)
        future_x = np.arange(n, n + pred_days)
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
            self.ax.plot(future_x, sims[i], color='#bb86fc', linewidth=0.3, alpha=0.15)
        self.ax.plot(future_x, mc_mean, color='#bb86fc', linewidth=2, linestyle='-')
        self.ax.fill_between(future_x, mc_p25, mc_p75, alpha=0.2, color='#bb86fc')
        self.ax.fill_between(future_x, mc_p5, mc_p95, alpha=0.08, color='#bb86fc')
        self.ax.scatter(future_x[-1], mc_mean[-1], color='#bb86fc', s=50, zorder=5,
                        edgecolors='white', linewidth=0.5)
        self.ax.annotate(f'  均值 {mc_mean[-1]:.2f}', xy=(future_x[-1], mc_mean[-1]),
                         xytext=(0, 15), textcoords='offset points',
                         fontsize=9, color='#bb86fc', fontweight='bold', fontfamily=_CHINESE_FONT)
        self.ax.annotate(f'{mc_p95[-1]:.2f}', xy=(future_x[-1], mc_p95[-1]),
                         xytext=(0, 5), textcoords='offset points',
                         fontsize=7, color='#888888', fontfamily=_CHINESE_FONT)
        self.ax.annotate(f'{mc_p5[-1]:.2f}', xy=(future_x[-1], mc_p5[-1]),
                         xytext=(0, -10), textcoords='offset points',
                         fontsize=7, color='#888888', fontfamily=_CHINESE_FONT)
        up_prob = np.mean(sims[:, -1] > S0) * 100
        self.ax.text(0.02, 0.82,
                     f'上漲機率 {up_prob:.1f}%　下跌機率 {100-up_prob:.1f}%',
                     transform=self.ax.transAxes, fontsize=9, color='#e0e0e0',
                     fontfamily=_CHINESE_FONT, verticalalignment='top',
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a1a2e', edgecolor='#555555'))
        self.ax.axvspan(n - 1, n - 1 + pred_days, alpha=0.04, color='#bb86fc')
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color='#bb86fc', linewidth=2, label=f'MC均值 {mc_mean[-1]:.2f}'),
            Line2D([0], [0], color='#bb86fc', linewidth=8, alpha=0.25, label='50% 機率'),
            Line2D([0], [0], color='#bb86fc', linewidth=8, alpha=0.1, label='90% 機率'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_exp_smoothing(self, df, close, pred_days):
        """Holt-Winters 指數平滑法（趨勢 + 季節性）"""
        y = close.values.astype(float)
        n = len(y)
        future_x = np.arange(n, n + pred_days)

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
        self.ax.plot(self._x_pos, fitted, color='#00bcd4', linewidth=1, linestyle=':', alpha=0.5)

        # 未來預測
        last_level = level[-1]
        last_trend = trend_val[-1]
        pred = [last_level + (i + 1) * last_trend for i in range(pred_days)]

        # 誤差範圍
        residuals = y - np.array(fitted)
        std_r = np.std(residuals)
        expanding_std = np.array([std_r * np.sqrt(i + 1) for i in range(pred_days)])

        self.ax.plot(future_x, pred, color='#00bcd4', linewidth=2, linestyle='--')
        self.ax.fill_between(future_x, pred - expanding_std, pred + expanding_std,
                             alpha=0.12, color='#00bcd4')
        self.ax.fill_between(future_x, pred - 2*expanding_std, pred + 2*expanding_std,
                             alpha=0.05, color='#00bcd4')
        self.ax.scatter(future_x[-1], pred[-1], color='#00bcd4', s=50, zorder=5,
                        edgecolors='white', linewidth=0.5)
        self.ax.annotate(f'  預測 {pred[-1]:.2f}', xy=(future_x[-1], pred[-1]),
                         xytext=(0, 15), textcoords='offset points',
                         fontsize=9, color='#00bcd4', fontweight='bold', fontfamily=_CHINESE_FONT)
        self.ax.axvspan(n - 1, n - 1 + pred_days, alpha=0.04, color='#00bcd4')
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color='#00bcd4', linestyle='--', linewidth=2, label=f'指數平滑 {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_ma_cross(self, df, close, pred_days):
        """MA交叉預測法：以近期MA5/MA10交叉趨勢外推"""
        y = close.values.astype(float)
        n = len(y)
        future_x = np.arange(n, n + pred_days)

        # 計算 MA5 和 MA10
        ma5 = np.convolve(y, np.ones(5)/5, mode='valid')
        ma10 = np.convolve(y, np.ones(10)/10, mode='valid')
        offset = n - len(ma5)
        ma5_x = np.arange(offset, n)
        ma10_x = np.arange(n - len(ma10), n)

        # 歷史MA線
        self.ax.plot(self._x_pos[ma5_x], ma5, color='#22c55e', linewidth=1, linestyle=':', alpha=0.6)
        self.ax.plot(self._x_pos[ma10_x], ma10, color='#f44336', linewidth=1, linestyle=':', alpha=0.6)

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

        self.ax.plot(future_x, pred, color=color, linewidth=2, linestyle='--')
        self.ax.fill_between(future_x, pred - expanding_vol, pred + expanding_vol,
                             alpha=0.1, color=color)
        self.ax.fill_between(future_x, pred - 2*expanding_vol, pred + 2*expanding_vol,
                             alpha=0.04, color=color)
        self.ax.scatter(future_x[-1], pred[-1], color=color, s=50, zorder=5,
                        edgecolors='white', linewidth=0.5)
        self.ax.annotate(f'  預測 {pred[-1]:.2f}', xy=(future_x[-1], pred[-1]),
                         xytext=(0, 15), textcoords='offset points',
                         fontsize=9, color=color, fontweight='bold', fontfamily=_CHINESE_FONT)
        self.ax.text(0.02, 0.82,
                     f'MA5/MA10 {direction}　MA5={ma5[-1]:.2f} MA10={ma10[-1]:.2f}',
                     transform=self.ax.transAxes, fontsize=9, color='#e0e0e0',
                     fontfamily=_CHINESE_FONT, verticalalignment='top',
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a1a2e', edgecolor='#555555'))
        self.ax.axvspan(n - 1, n - 1 + pred_days, alpha=0.04, color=color)
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
        future_x = np.arange(n, n + pred_days)

        # 20日布林通道
        ma20 = np.convolve(y, np.ones(20)/20, mode='valid')
        offset = n - len(ma20)
        # 歷史布林帶
        hist_upper = ma20 + 2 * np.std(y[-len(ma20):])
        hist_lower = ma20 - 2 * np.std(y[-len(ma20):])
        self.ax.plot(self._x_pos[offset:], ma20, color='#e040fb', linewidth=1, linestyle=':', alpha=0.5)

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

        self.ax.plot(future_x, upper_pred, color='#e040fb', linewidth=0.8, linestyle=':', alpha=0.4)
        self.ax.plot(future_x, lower_pred, color='#e040fb', linewidth=0.8, linestyle=':', alpha=0.4)
        self.ax.fill_between(future_x, lower_pred, upper_pred, alpha=0.1, color='#e040fb')
        self.ax.plot(future_x, pred, color='#e040fb', linewidth=2, linestyle='--')
        self.ax.scatter(future_x[-1], pred[-1], color='#e040fb', s=50, zorder=5,
                        edgecolors='white', linewidth=0.5)
        self.ax.annotate(f'  預測 {pred[-1]:.2f}', xy=(future_x[-1], pred[-1]),
                         xytext=(0, 15), textcoords='offset points',
                         fontsize=9, color='#e040fb', fontweight='bold', fontfamily=_CHINESE_FONT)
        self.ax.text(0.02, 0.82,
                     f'布林通道　上軌 {upper_band:.2f}　MA20 {current_ma:.2f}　下軌 {lower_band:.2f}',
                     transform=self.ax.transAxes, fontsize=9, color='#e0e0e0',
                     fontfamily=_CHINESE_FONT, verticalalignment='top',
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a1a2e', edgecolor='#555555'))
        self.ax.axvspan(n - 1, n - 1 + pred_days, alpha=0.04, color='#e040fb')
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color='#e040fb', linestyle=':', linewidth=1, label='MA20'),
            Line2D([0], [0], color='#e040fb', linestyle='--', linewidth=2, label=f'布林預測 {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    # ── 專業技術指標特徵工程 ──

    def _tech_features(self, df):
        """建立專業技術指標特徵（RSI, MACD, Bollinger %B, 均線, 量價關係等）"""
        close = df['Close'].values.astype(float)
        volume = df['Volume'].values.astype(float)
        high = df['High'].values.astype(float)
        low = df['Low'].values.astype(float)
        n = len(close)

        features = {}
        # 滯後價格
        for lag in (1, 2, 3, 5, 10, 20):
            features[f'lag_{lag}'] = np.pad(close[:-lag] if lag < n else [],
                                            (lag, 0), constant_values=np.nan)[:n]

        # 日報酬率
        ret = np.diff(close) / close[:-1]
        features['return_1'] = np.pad(ret, (1, 0), constant_values=np.nan)
        features['return_5'] = np.pad(np.convolve(ret, np.ones(5)/5, mode='valid'),
                                      (5, 0), constant_values=np.nan)[:n]

        # 均線
        for ma_len in (5, 10, 20, 60):
            ma = np.convolve(close, np.ones(ma_len)/ma_len, mode='valid')
            features[f'ma_{ma_len}'] = np.pad(ma, (ma_len - 1, 0), constant_values=np.nan)[:n]
            # 價格與均線距離
            features[f'ma_{ma_len}_dist'] = (close - features[f'ma_{ma_len}']) / features[f'ma_{ma_len}']

        # RSI (14 日)
        gain = np.where(ret > 0, ret, 0)
        loss = np.where(ret < 0, -ret, 0)
        avg_gain = np.pad(np.convolve(gain, np.ones(14)/14, mode='valid'),
                          (14, 0), constant_values=np.nan)[:n]
        avg_loss = np.pad(np.convolve(loss, np.ones(14)/14, mode='valid'),
                          (14, 0), constant_values=np.nan)[:n]
        rs = avg_gain / np.where(avg_loss == 0, 1e-10, avg_loss)
        features['rsi'] = 100 - (100 / (1 + rs))

        # MACD (12, 26, 9)
        ema12 = close.copy().astype(float)
        ema26 = close.copy().astype(float)
        for i in range(1, n):
            ema12[i] = ema12[i-1] + (2/13) * (close[i] - ema12[i-1])
            ema26[i] = ema26[i-1] + (2/27) * (close[i] - ema26[i-1])
        macd = ema12 - ema26
        signal = macd.copy()
        for i in range(1, n):
            signal[i] = signal[i-1] + (2/10) * (macd[i] - signal[i-1])
        features['macd'] = macd
        features['macd_signal'] = signal
        features['macd_hist'] = macd - signal

        # Bollinger %B (20, 2)
        ma20 = features['ma_20'].copy()
        rolling_std = np.array([np.std(close[max(0, i-19):i+1]) for i in range(n)])
        upper = ma20 + 2 * rolling_std
        lower = ma20 - 2 * rolling_std
        features['bb_upper'] = upper
        features['bb_lower'] = lower
        features['bb_width'] = (upper - lower) / ma20
        features['bb_pct_b'] = np.where(upper != lower, (close - lower) / (upper - lower), 0.5)

        # 成交量特徵
        vol_ma5 = np.convolve(volume, np.ones(5)/5, mode='valid')
        features['vol_ma5'] = np.pad(vol_ma5, (4, 0), constant_values=np.nan)[:n]
        features['vol_ratio'] = volume / np.where(features['vol_ma5'] == 0, 1, features['vol_ma5'])

        # 波動率 (ATR-like)
        tr = np.maximum(high - low, np.abs(high - np.pad(close[:-1], (1, 0), constant_values=np.nan)))
        features['atr'] = np.pad(np.convolve(tr, np.ones(14)/14, mode='valid'),
                                 (14, 0), constant_values=np.nan)[:n]

        return pd.DataFrame(features, index=df.index)

    # ── 專業 AI 預測核心（XGBoost + 技術指標） ──

    def _calc_ai_prediction(self, df, pred_days):
        """使用 XGBoost 搭配技術指標進行專業多步預測，回傳 (預測陣列, 模型名稱) 或 (None, None)"""
        from xgboost import XGBRegressor
        from sklearn.preprocessing import StandardScaler
        close = df['Close'].values.astype(float)
        n = len(close)
        if n < 30:
            return None, None
        tech = self._tech_features(df)
        feature_cols = [c for c in tech.columns if c != 'bb_upper' and c != 'bb_lower']
        # 對齊 target：預測隔日收盤價
        X_all = tech[feature_cols].values
        y_all = close.copy()
        # 去除 NaN
        mask = ~np.isnan(X_all).any(axis=1)
        X_clean, y_clean = X_all[mask], y_all[mask]
        if len(X_clean) < 20:
            return None, None
        # 切分訓練/測試
        split = max(int(len(X_clean) * 0.85), len(X_clean) - 10)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_clean)
        model = XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.05,
                             random_state=42, n_jobs=-1, verbosity=0)
        model.fit(X_scaled[:split], y_clean[:split])
        # 遞迴多步預測（使用 raw 特徵空間避免縮放混亂）
        X_raw = X_clean.copy()
        last_idx = mask.sum() - 1
        preds = []
        try:
            for step in range(pred_days):
                feat = X_scaled[last_idx:last_idx+1].copy()
                p = model.predict(feat)[0]
                preds.append(p)
                new_raw = X_raw[-1:].copy()
                old_lag_1 = X_raw[-1, feature_cols.index('lag_1')]
                old_lag_2 = X_raw[-1, feature_cols.index('lag_2')]
                old_lag_3 = X_raw[-1, feature_cols.index('lag_3')]
                old_lag_5 = X_raw[-1, feature_cols.index('lag_5')]
                old_lag_10 = X_raw[-1, feature_cols.index('lag_10')]
                new_raw[0, feature_cols.index('lag_1')] = p
                new_raw[0, feature_cols.index('lag_2')] = old_lag_1
                new_raw[0, feature_cols.index('lag_3')] = old_lag_2
                new_raw[0, feature_cols.index('lag_5')] = old_lag_3
                new_raw[0, feature_cols.index('lag_10')] = old_lag_5
                new_raw[0, feature_cols.index('lag_20')] = old_lag_10
                X_raw = np.vstack([X_raw, new_raw])
                X_scaled = np.vstack([X_scaled, scaler.transform(new_raw)])
                last_idx += 1
        except Exception:
            return None, None
        return np.array(preds), 'XGBoost'

    def _calc_rf_prediction(self, df, pred_days, n_estimators=100):
        """使用隨機森林搭配技術指標進行多步預測"""
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.preprocessing import StandardScaler
        close = df['Close'].values.astype(float)
        n = len(close)
        if n < 30:
            return None, None
        tech = self._tech_features(df)
        feature_cols = [c for c in tech.columns if c != 'bb_upper' and c != 'bb_lower']
        X_all = tech[feature_cols].values
        y_all = close.copy()
        mask = ~np.isnan(X_all).any(axis=1)
        X_clean, y_clean = X_all[mask], y_all[mask]
        if len(X_clean) < 20:
            return None, None
        split = max(int(len(X_clean) * 0.85), len(X_clean) - 10)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_clean)
        model = RandomForestRegressor(n_estimators=n_estimators, max_depth=6,
                                      random_state=42, n_jobs=-1)
        model.fit(X_scaled[:split], y_clean[:split])
        X_raw = X_clean.copy()
        last_idx = mask.sum() - 1
        preds = []
        try:
            for step in range(pred_days):
                feat = X_scaled[last_idx:last_idx+1].copy()
                p = model.predict(feat)[0]
                preds.append(p)
                new_raw = X_raw[-1:].copy()
                old_lag_1 = X_raw[-1, feature_cols.index('lag_1')]
                old_lag_2 = X_raw[-1, feature_cols.index('lag_2')]
                old_lag_3 = X_raw[-1, feature_cols.index('lag_3')]
                old_lag_5 = X_raw[-1, feature_cols.index('lag_5')]
                old_lag_10 = X_raw[-1, feature_cols.index('lag_10')]
                new_raw[0, feature_cols.index('lag_1')] = p
                new_raw[0, feature_cols.index('lag_2')] = old_lag_1
                new_raw[0, feature_cols.index('lag_3')] = old_lag_2
                new_raw[0, feature_cols.index('lag_5')] = old_lag_3
                new_raw[0, feature_cols.index('lag_10')] = old_lag_5
                new_raw[0, feature_cols.index('lag_20')] = old_lag_10
                X_raw = np.vstack([X_raw, new_raw])
                X_scaled = np.vstack([X_scaled, scaler.transform(new_raw)])
                last_idx += 1
        except Exception:
            return None, None
        return np.array(preds), 'RF'

    def _calc_model_prediction(self, df, pred_days, model, model_name):
        """通用 AI 模型多步預測：特徵工程 → 標準化 → 訓練 → 遞迴預測"""
        from sklearn.preprocessing import StandardScaler
        close = df['Close'].values.astype(float)
        n = len(close)
        if n < 30:
            return None, None
        tech = self._tech_features(df)
        feature_cols = [c for c in tech.columns if c != 'bb_upper' and c != 'bb_lower']
        X_all = tech[feature_cols].values
        y_all = close.copy()
        mask = ~np.isnan(X_all).any(axis=1)
        X_clean, y_clean = X_all[mask], y_all[mask]
        if len(X_clean) < 20:
            return None, None
        split = max(int(len(X_clean) * 0.85), len(X_clean) - 10)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_clean)
        model.fit(X_scaled[:split], y_clean[:split])
        X_raw = X_clean.copy()
        last_idx = mask.sum() - 1
        preds = []
        try:
            for step in range(pred_days):
                feat = X_scaled[last_idx:last_idx+1].copy()
                p = model.predict(feat)[0]
                preds.append(p)
                new_raw = X_raw[-1:].copy()
                old_lag_1 = X_raw[-1, feature_cols.index('lag_1')]
                old_lag_2 = X_raw[-1, feature_cols.index('lag_2')]
                old_lag_3 = X_raw[-1, feature_cols.index('lag_3')]
                old_lag_5 = X_raw[-1, feature_cols.index('lag_5')]
                old_lag_10 = X_raw[-1, feature_cols.index('lag_10')]
                new_raw[0, feature_cols.index('lag_1')] = p
                new_raw[0, feature_cols.index('lag_2')] = old_lag_1
                new_raw[0, feature_cols.index('lag_3')] = old_lag_2
                new_raw[0, feature_cols.index('lag_5')] = old_lag_3
                new_raw[0, feature_cols.index('lag_10')] = old_lag_5
                new_raw[0, feature_cols.index('lag_20')] = old_lag_10
                X_raw = np.vstack([X_raw, new_raw])
                X_scaled = np.vstack([X_scaled, scaler.transform(new_raw)])
                last_idx += 1
        except Exception:
            return None, None
        return np.array(preds), model_name

    def _calc_lgb_prediction(self, df, pred_days):
        """LightGBM 預測"""
        from lightgbm import LGBMRegressor
        model = LGBMRegressor(n_estimators=100, max_depth=4, learning_rate=0.05,
                              random_state=42, n_jobs=-1, verbose=-1)
        return self._calc_model_prediction(df, pred_days, model, 'LightGBM')

    def _calc_cb_prediction(self, df, pred_days):
        """CatBoost 預測"""
        from catboost import CatBoostRegressor
        model = CatBoostRegressor(n_estimators=100, max_depth=4, learning_rate=0.05,
                                  random_state=42, verbose=0, allow_writing_files=False)
        return self._calc_model_prediction(df, pred_days, model, 'CatBoost')

    def _calc_gb_prediction(self, df, pred_days):
        """Gradient Boosting 預測"""
        from sklearn.ensemble import GradientBoostingRegressor
        model = GradientBoostingRegressor(n_estimators=100, max_depth=4, learning_rate=0.05,
                                          random_state=42)
        return self._calc_model_prediction(df, pred_days, model, 'GBoost')

    def _calc_et_prediction(self, df, pred_days):
        """Extra Trees 預測"""
        from sklearn.ensemble import ExtraTreesRegressor
        model = ExtraTreesRegressor(n_estimators=100, max_depth=6, random_state=42, n_jobs=-1)
        return self._calc_model_prediction(df, pred_days, model, 'ExtraTree')

    def _calc_stacking_prediction(self, df, pred_days):
        """Stacking Ensemble 預測（XGBoost + RF + LightGBM + CatBoost + GBoost）"""
        from sklearn.ensemble import StackingRegressor
        from sklearn.linear_model import Ridge
        from xgboost import XGBRegressor
        from lightgbm import LGBMRegressor
        from catboost import CatBoostRegressor
        from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
        estimators = [
            ('xgb', XGBRegressor(n_estimators=50, max_depth=3, random_state=42, verbosity=0)),
            ('rf', RandomForestRegressor(n_estimators=50, max_depth=4, random_state=42, n_jobs=-1)),
            ('lgb', LGBMRegressor(n_estimators=50, max_depth=3, random_state=42, verbose=-1)),
            ('cb', CatBoostRegressor(n_estimators=50, max_depth=3, random_state=42, verbose=0, allow_writing_files=False)),
            ('gb', GradientBoostingRegressor(n_estimators=50, max_depth=3, random_state=42)),
        ]
        model = StackingRegressor(estimators=estimators, final_estimator=Ridge(alpha=1.0), n_jobs=-1)
        return self._calc_model_prediction(df, pred_days, model, 'Stacking')

    def _draw_ai_prediction(self, future_x, pred, model_name, color):
        """共用繪圖：在圖表上畫出 AI 預測線與信賴區間"""
        std = np.std(np.diff(pred)) if len(pred) > 1 else 0
        upper = pred + 1.96 * std * np.sqrt(np.arange(1, len(pred) + 1))
        lower = pred - 1.96 * std * np.sqrt(np.arange(1, len(pred) + 1))
        lower = np.maximum(lower, 0)
        self.ax.plot(future_x, pred, color=color, linewidth=1.5, linestyle='--',
                     marker='o', markersize=3)
        self.ax.fill_between(future_x, lower, upper, color=color, alpha=0.08)
        self.ax.annotate(f'  {model_name} {pred[-1]:.2f}', xy=(future_x[-1], pred[-1]),
                         xytext=(0, 15), textcoords='offset points',
                         fontsize=9, color=color, fontweight='bold', fontfamily=_CHINESE_FONT)

    def _pred_ai(self, df, close, pred_days):
        """專業 AI 預測（預設使用 XGBoost + 技術指標）"""
        pred, model_name = self._calc_ai_prediction(df, pred_days)
        if pred is None:
            return
        n = len(close)
        future_x = np.arange(n, n + len(pred))
        color = '#00e676'
        self._draw_ai_prediction(future_x, pred, f'AI ({model_name})', color)
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color=color, linestyle='--', linewidth=2,
                   label=f'AI預測 ({model_name}) {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_xgboost(self, df, close, pred_days):
        """XGBoost + 技術指標預測"""
        pred, _ = self._calc_ai_prediction(df, pred_days)
        if pred is None:
            return
        n = len(close)
        future_x = np.arange(n, n + len(pred))
        color = '#ff6b6b'
        self._draw_ai_prediction(future_x, pred, 'XGBoost', color)
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color=color, linestyle='--', linewidth=2,
                   label=f'XGBoost {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_rf(self, df, close, pred_days):
        """隨機森林 + 技術指標預測"""
        pred, _ = self._calc_rf_prediction(df, pred_days)
        if pred is None:
            return
        n = len(close)
        future_x = np.arange(n, n + len(pred))
        color = '#4fc3f7'
        self._draw_ai_prediction(future_x, pred, 'RF', color)
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color=color, linestyle='--', linewidth=2,
                   label=f'隨機森林 {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_lgb(self, df, close, pred_days):
        """LightGBM + 技術指標預測"""
        pred, _ = self._calc_lgb_prediction(df, pred_days)
        if pred is None:
            return
        n = len(close)
        future_x = np.arange(n, n + len(pred))
        color = '#ffd700'
        self._draw_ai_prediction(future_x, pred, 'LightGBM', color)
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color=color, linestyle='--', linewidth=2,
                   label=f'LightGBM {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_cb(self, df, close, pred_days):
        """CatBoost + 技術指標預測"""
        pred, _ = self._calc_cb_prediction(df, pred_days)
        if pred is None:
            return
        n = len(close)
        future_x = np.arange(n, n + len(pred))
        color = '#ff69b4'
        self._draw_ai_prediction(future_x, pred, 'CatBoost', color)
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color=color, linestyle='--', linewidth=2,
                   label=f'CatBoost {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_gb(self, df, close, pred_days):
        """Gradient Boosting + 技術指標預測"""
        pred, _ = self._calc_gb_prediction(df, pred_days)
        if pred is None:
            return
        n = len(close)
        future_x = np.arange(n, n + len(pred))
        color = '#00ffff'
        self._draw_ai_prediction(future_x, pred, 'GBoost', color)
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color=color, linestyle='--', linewidth=2,
                   label=f'GBoost {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_et(self, df, close, pred_days):
        """Extra Trees + 技術指標預測"""
        pred, _ = self._calc_et_prediction(df, pred_days)
        if pred is None:
            return
        n = len(close)
        future_x = np.arange(n, n + len(pred))
        color = '#32cd32'
        self._draw_ai_prediction(future_x, pred, 'ExtraTree', color)
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color=color, linestyle='--', linewidth=2,
                   label=f'ExtraTree {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_stacking(self, df, close, pred_days):
        """Stacking Ensemble + 技術指標預測"""
        pred, _ = self._calc_stacking_prediction(df, pred_days)
        if pred is None:
            return
        n = len(close)
        future_x = np.arange(n, n + len(pred))
        color = '#ff4500'
        self._draw_ai_prediction(future_x, pred, 'Stacking', color)
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color=color, linestyle='--', linewidth=2,
                   label=f'Stacking {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_lstm(self, df, close, pred_days):
        """LSTM 深度學習預測"""
        pred = calc_dl_prediction(df, 'lstm', pred_days)
        if pred is None:
            return
        n = len(close)
        future_x = np.arange(n, n + len(pred))
        color = '#00897b'
        self._draw_ai_prediction(future_x, pred, 'LSTM', color)
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color=color, linestyle='--', linewidth=2,
                   label=f'LSTM {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_gru(self, df, close, pred_days):
        """GRU 深度學習預測"""
        pred = calc_dl_prediction(df, 'gru', pred_days)
        if pred is None:
            return
        n = len(close)
        future_x = np.arange(n, n + len(pred))
        color = '#c2185b'
        self._draw_ai_prediction(future_x, pred, 'GRU', color)
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color=color, linestyle='--', linewidth=2,
                   label=f'GRU {pred[-1]:.2f}'),
        ], fontsize=8, loc='upper right', facecolor='#0d1117', edgecolor='#555555', labelcolor='#e0e0e0')

    def _pred_transformer(self, df, close, pred_days):
        """Transformer 深度學習預測"""
        pred = calc_dl_prediction(df, 'transformer', pred_days)
        if pred is None:
            return
        n = len(close)
        future_x = np.arange(n, n + len(pred))
        color = '#5c6bc0'
        self._draw_ai_prediction(future_x, pred, 'Transformer', color)
        from matplotlib.lines import Line2D
        self.ax.legend(handles=[
            Line2D([0], [0], color=color, linestyle='--', linewidth=2,
                   label=f'Transformer {pred[-1]:.2f}'),
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
            symbol, df, info, avg_price = fetch_data(symbol, start_date, end_date)
            self.root.after(0, self.display_result, query, symbol, df, info, avg_price)
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

    def display_result(self, query, symbol, df, info, avg_price=None):
        """將查詢結果顯示在 GUI 上（深色主題、3子圖）"""
        if df.empty:
            messagebox.showerror("錯誤", f"股票 {query} 無資料，可能代碼錯誤或已下市。")
            self.btn.config(state=tk.NORMAL, text="查詢")
            self.info_text.set("")
            self.pred_text_widget.config(state=tk.NORMAL)
            self.pred_text_widget.delete('1.0', tk.END)
            self.pred_text_widget.insert('1.0', '查詢後自動預測...')
            self.pred_text_widget.config(state=tk.DISABLED)
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
        avg_str = f"均價: {avg_price:.2f}" if avg_price else ""
        latest_vol = df['Volume'].iloc[-1]
        close_series = df['Close']
        change = close_series.iloc[-1] - close_series.iloc[-2] if len(close_series) >= 2 else 0
        change_str = f"漲跌: {change:+.2f}" if change != 0 else "漲跌: 0.00"
        info_text = (
            f"{name} ({symbol})    "
            f"市場: {exchange}    "
            f"期間: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}\n"
            f"最新交易日 ({latest_date.strftime('%Y-%m-%d')})    "
            f"開盤價: {df['Open'].iloc[-1]:.2f}    "
            f"最高價: {df['High'].iloc[-1]:.2f}    "
            f"最低價: {df['Low'].iloc[-1]:.2f}    "
            f"收盤價: {df['Close'].iloc[-1]:.2f}    "
            f"{change_str}    "
            f"總量: {latest_vol/1000:,.1f}張    "
            f"{avg_str}    "
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
        self._x_pos = np.arange(len(df))
        self._date_index = df.index  # 初始化日期索引（供X軸刻度使用）
        self._click_annotation = None

        # ── K 線（蠟燭圖）──
        width = 0.6
        width2 = 0.05
        up = df[df['Close'] >= df['Open']]
        down = df[df['Close'] < df['Open']]
        up_idx = df.index.get_indexer(up.index)
        down_idx = df.index.get_indexer(down.index)
        self.ax.bar(up_idx, up['Close'] - up['Open'], width, bottom=up['Open'], color='#ef4444', edgecolor='#ef4444')
        self.ax.bar(up_idx, up['High'] - up['Close'], width2, bottom=up['Close'], color='#ef4444')
        self.ax.bar(up_idx, up['Low'] - up['Open'], width2, bottom=up['Open'], color='#ef4444')
        self.ax.bar(down_idx, down['Close'] - down['Open'], width, bottom=down['Open'], color='#22c55e', edgecolor='#22c55e')
        self.ax.bar(down_idx, down['High'] - down['Open'], width2, bottom=down['Open'], color='#22c55e')
        self.ax.bar(down_idx, down['Low'] - down['Close'], width2, bottom=down['Close'], color='#22c55e')

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
            self.ax.plot(self._x_pos, ma_series, color=color, linewidth=1, alpha=0.9, label=label)

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
        vol_up_idx = df.index.get_indexer(vol_up.index)
        vol_down_idx = df.index.get_indexer(vol_down.index)
        self.ax_vol.bar(vol_up_idx, vol_up['Volume'], width, color='#ef4444', alpha=0.7)
        self.ax_vol.bar(vol_down_idx, vol_down['Volume'], width, color='#22c55e', alpha=0.7)
        # 成交量均線
        vol_ma5 = volume.rolling(5).mean()
        vol_ma10 = volume.rolling(10).mean()
        self.ax_vol.plot(self._x_pos, vol_ma5, color='#00bcd4', linewidth=0.8, alpha=0.8)
        self.ax_vol.plot(self._x_pos, vol_ma10, color='#ffeb3b', linewidth=0.8, alpha=0.8)
        # VOL 數值（以張為單位，1張=1000股）
        v5 = vol_ma5.iloc[-1] if not vol_ma5.empty and not pd.isna(vol_ma5.iloc[-1]) else 0
        v10 = vol_ma10.iloc[-1] if not vol_ma10.empty and not pd.isna(vol_ma10.iloc[-1]) else 0
        vol_text = f"VOL  5T:{v5/1000:,.0f}張  10T:{v10/1000:,.0f}張"
        t = self.ax_vol.text(0.01, 0.95, vol_text, transform=self.ax_vol.transAxes,
                             fontsize=9, color='#e0e0e0', va='top', ha='left',
                             bbox=dict(boxstyle='round,pad=0.3', facecolor='#0d1117', alpha=0.8))
        self._ma_texts.append(t)
        self.ax_vol.set_ylabel("成交量(張)", fontsize=10, color=self._text_color)
        self.ax_vol.grid(True, linestyle='--', alpha=0.15, color=self._grid_color)
        self.ax_vol.yaxis.set_label_position('right')
        self.ax_vol.tick_params(labelleft=False, labelright=True)
        # 格式化成交量 Y 軸（以張為單位，1張=1000股）
        self.ax_vol.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:,.0f}張'))

        # ── KD 指標 ──
        self.ax_kd.plot(self._x_pos, k_val, color='#00bcd4', linewidth=1.2, label='K')
        self.ax_kd.plot(self._x_pos, d_val, color='#ffeb3b', linewidth=1.2, label='D')
        self.ax_kd.axhline(y=80, color='#555555', linestyle='--', linewidth=0.6)
        self.ax_kd.axhline(y=20, color='#555555', linestyle='--', linewidth=0.6)
        self.ax_kd.fill_between(self._x_pos, 80, 100, alpha=0.08, color='#ef4444')
        self.ax_kd.fill_between(self._x_pos, 0, 20, alpha=0.08, color='#22c55e')
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

        # X軸設定（數值位置，避免休市日空白，顯示日期）
        self.ax_kd.set_xlabel("日期", fontsize=10, color=self._text_color)
        self._set_xlim_all(-0.5, len(df) - 0.5)
        # 自適應日期格式
        self._apply_date_axis(-0.5, len(df) - 0.5)

        # 未來趨勢預測
        try:
            pred = int(self.pred_days.get())
        except Exception:
            pred = 20
        if pred <= 0:
            pred = 20
        if pred > 0 and len(close) > 10:
            self._draw_prediction(df, close, pred)  # method read from self.pred_method
            # 延伸X軸以顯示預測區域
            total = len(self._date_index)
            self._set_xlim_all(-0.5, total - 0.5)

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
