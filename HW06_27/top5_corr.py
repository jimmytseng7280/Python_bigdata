import sys
import yfinance as yf
import pandas as pd
import numpy as np

try:
    import twstock
    twstock.__update_codes()
    NAME_MAP = {}
    for code, info in twstock.codes.items():
        if getattr(info, 'type', '') == '股票' and getattr(info, 'name', '') and getattr(info, 'market', '') in ('上市', '上櫃'):
            suffix = '.TW' if info.market == '上市' else '.TWO'
            NAME_MAP[f"{code}{suffix}"] = f"{info.name}({code})"
except Exception:
    NAME_MAP = {}

def label_from_symbol(symbol: str) -> str:
    if symbol in NAME_MAP:
        return NAME_MAP[symbol]
    base = symbol.split('.')[0]
    if base in NAME_MAP:
        return NAME_MAP[base]
    return base

def main():
    print("資料來源: Yahoo Finance via yfinance")
    codes = [f"{i:04d}.TW" for i in range(1000, 2500)] + [f"{i:04d}.TWO" for i in range(6000, 7000)]

    try:
        data = yf.download(codes, start="2026-01-01", interval="1d", auto_adjust=True, progress=True, threads=True)
    except Exception as exc:
        print(f"下載失敗: {exc}")
        sys.exit(1)

    if data.empty:
        print("無法取得任何股票資料（可能無網路或資料庫尚未包含近期資料）")
        sys.exit(0)

    close = data.get('Close')
    if close is None or close.empty:
        print("無法取得收盤價欄位")
        sys.exit(0)

    if isinstance(close, pd.Series):
        close = close.to_frame()

    close = close.dropna(axis=1, how='all')
    if close.shape[1] < 2:
        print("可用股票數量不足，無法計算相關係數")
        sys.exit(0)

    returns = close.pct_change().replace([np.inf, -np.inf], np.nan).dropna(axis=1, how='all').dropna()

    if returns.shape[1] < 2:
        print("日報酬率欄位不足，無法計算相關係數")
        sys.exit(0)

    corr = returns.corr()

    pairs = []
    cols = corr.columns.tolist()
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            a, b = cols[i], cols[j]
            val = corr.loc[a, b]
            if pd.isna(val):
                continue
            label_a = label_from_symbol(a)
            label_b = label_from_symbol(b)
            pairs.append({
                'Stock1_Name': label_a.split('(')[0],
                'Stock1_Code': a.split('.')[0],
                'Stock2_Name': label_b.split('(')[0],
                'Stock2_Code': b.split('.')[0],
                'Correlation': float(val),
            })

    if not pairs:
        print("無法取得有效的股票配對相關係數")
        sys.exit(0)

    df = pd.DataFrame(pairs)
    df = df.sort_values(by='Correlation', ascending=False).reset_index(drop=True)

    print("\n===== 日報酬率相關係數 TOP 5（最接近 1）=====\n")
    top5 = df.head(5)
    for rank, row in top5.iterrows():
        print(f"{rank+1}. {row['Stock1_Name']}({row['Stock1_Code']}) 與 {row['Stock2_Name']}({row['Stock2_Code']})  相關係數={row['Correlation']:.4f}")

    print("\n===== 日報酬率相關係數 BOTTOM 5（最接近 -1）=====\n")
    bottom5 = df.tail(5).iloc[::-1]
    for rank, (_, row) in enumerate(bottom5.iterrows(), start=1):
        print(f"{rank}. {row['Stock1_Name']}({row['Stock1_Code']}) 與 {row['Stock2_Name']}({row['Stock2_Code']})  相關係數={row['Correlation']:.4f}")

    import os
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HW06_27")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "stock_daily_return_correlation_pairs.csv")
    try:
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n已將所有配對輸出至 {output_path}")
    except Exception as exc:
        print(f"輸出 CSV 失敗: {exc}")

if __name__ == "__main__":
    main()
