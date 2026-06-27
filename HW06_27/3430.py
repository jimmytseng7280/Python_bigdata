import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

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

def resolve_symbol(query):
    q = query.strip()
    if q in STOCK_MAP:
        return STOCK_MAP[q]
    if '.' in q:
        return q.upper()
    return q

def fetch_data(symbol):
    candidates = [symbol]
    if '.' not in symbol:
        candidates += [f"{symbol}.TW", f"{symbol}.TWO"]
    for sym in candidates:
        df = yf.download(sym, period="2y", auto_adjust=True)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            return sym, df
    return symbol, pd.DataFrame()

query = input("請輸入股票代碼或股票名稱: ")
symbol = resolve_symbol(query)
symbol, df = fetch_data(symbol)

if df.empty:
    print(f"錯誤：股票 {query} 無資料，可能代碼錯誤或已下市。")
    exit()

close = df['Close']

print(f"\n股票代號: {symbol}")
print(f"資料期間: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}\n")

latest_date = df.index[-1]
print(f"最新交易日 ({latest_date.strftime('%Y-%m-%d')})")
print(f"  開盤價: {df['Open'].iloc[-1]:.2f}")
print(f"  最高價: {df['High'].iloc[-1]:.2f}")
print(f"  最低價: {df['Low'].iloc[-1]:.2f}")
print(f"  收盤價: {df['Close'].iloc[-1]:.2f}")
print()

df['日線'] = close
df['週線'] = close.rolling(5).mean()
df['月線'] = close.rolling(20).mean()
df['季線'] = close.rolling(60).mean()
df['半年線'] = close.rolling(120).mean()
df['年線'] = close.rolling(240).mean()

plt.figure(figsize=(18, 9))

plt.plot(df.index, df['日線'], color='black', linewidth=1, label='日線')
plt.plot(df.index, df['週線'], color='blue', linewidth=2, label='週線(5日)')
plt.plot(df.index, df['月線'], color='green', linewidth=2, label='月線(20日)')
plt.plot(df.index, df['季線'], color='orange', linewidth=2, label='季線(60日)')
plt.plot(df.index, df['半年線'], color='purple', linewidth=2, label='半年線(120日)')
plt.plot(df.index, df['年線'], color='red', linewidth=2, label='年線(240日)')

if not close.empty:
    h_idx = close.idxmax()
    l_idx = close.idxmin()
    plt.scatter(h_idx, close.loc[h_idx], color='red', s=70)
    plt.annotate(f'最高價 {close.loc[h_idx]:.2f}', xy=(h_idx, close.loc[h_idx]),
                 xytext=(30, 0), textcoords='offset points',
                 arrowprops=dict(arrowstyle='->', color='red'),
                 fontsize=11, color='red', va='center')
    plt.scatter(l_idx, close.loc[l_idx], color='blue', s=70)
    plt.annotate(f'最低價 {close.loc[l_idx]:.2f}', xy=(l_idx, close.loc[l_idx]),
                 xytext=(30, 0), textcoords='offset points',
                 arrowprops=dict(arrowstyle='->', color='blue'),
                 fontsize=11, color='blue', va='center')

plt.title(f"{symbol} 近二年股價走勢（日線、週線、月線、季線、半年線、年線）", fontsize=18)
plt.xlabel("日期", fontsize=13)
plt.ylabel("股價(元)", fontsize=13)
plt.grid(True, linestyle='--', alpha=0.4)
plt.legend(fontsize=12)
plt.tight_layout()
plt.show()
