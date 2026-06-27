import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ==========================
# 中文設定
# ==========================
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False


# ==========================
# 標註函數（統一右側）
# ==========================
def right_annotate(ax, x, y, text, color="black"):

    ax.annotate(
        text,
        xy=(x, y),
        xytext=(40, 0),  # ⭐ 固定往右
        textcoords='offset points',
        arrowprops=dict(
            arrowstyle='->',
            lw=1,
            color=color
        ),
        fontsize=10,
        bbox=dict(
            boxstyle="round,pad=0.35",
            fc="white",
            ec="gray",
            alpha=0.95
        ),
        ha='left',
        va='center',
        zorder=10,
        clip_on=False
    )


# ==========================
# 下載資料
# ==========================
end_date = datetime.today()
start_date = end_date - timedelta(days=365 * 3)

print("下載 USD/TWD 匯率資料...")

df = yf.download(
    "TWD=X",
    start=start_date.strftime("%Y-%m-%d"),
    end=end_date.strftime("%Y-%m-%d"),
    progress=False
)

if df.empty:
    print("下載失敗")
    exit()

df = df[['Close']]
df.columns = ['日收盤匯率']

# 月 / 年
monthly = df.resample('ME').last()
monthly.columns = ['月收盤匯率']

yearly = df.resample('YE').last()
yearly.columns = ['年收盤匯率']


# ==========================
# CSV輸出
# ==========================
df.to_csv("USD_TWD_日.csv", encoding="utf-8-sig")
monthly.to_csv("USD_TWD_月.csv", encoding="utf-8-sig")
yearly.to_csv("USD_TWD_年.csv", encoding="utf-8-sig")


# ==========================
# 最高 / 最低
# ==========================
max_rate = df['日收盤匯率'].max()
min_rate = df['日收盤匯率'].min()

max_date = df['日收盤匯率'].idxmax()
min_date = df['日收盤匯率'].idxmin()


# ==========================
# 繪圖
# ==========================
fig, ax = plt.subplots(figsize=(16, 8))

# 日線
ax.plot(df.index, df['日收盤匯率'],
        color='blue', linewidth=1,
        label='日收盤匯率')

# 月線
ax.plot(monthly.index, monthly['月收盤匯率'],
        color='red', linewidth=2,
        marker='o', label='月收盤匯率')

# 年線
ax.plot(yearly.index, yearly['年收盤匯率'],
        color='green', linewidth=3,
        marker='s', label='年收盤匯率')


# ==========================
# 標記點
# ==========================
ax.scatter(max_date, max_rate, color='red', s=90, zorder=5)
ax.scatter(min_date, min_rate, color='green', s=90, zorder=5)

right_annotate(
    ax,
    max_date,
    max_rate,
    f"最高點 {max_rate:.4f}",
    color="red"
)

right_annotate(
    ax,
    min_date,
    min_rate,
    f"最低點 {min_rate:.4f}",
    color="green"
)


# ==========================
# 圖表設定
# ==========================
ax.set_title('近三年美元兌新台幣匯率走勢圖',
             fontsize=20, fontweight='bold')

ax.set_xlabel('日期')
ax.set_ylabel('匯率 (TWD/USD)')

ax.grid(True, linestyle='--', alpha=0.5)

ax.legend(title='資料類型')

ax.margins(x=0.02, y=0.1)

plt.tight_layout()
plt.show()


# ==========================
# 統計
# ==========================
print("\n===== 統計 =====")
print(f"最高：{max_rate:.4f} ({max_date.date()})")
print(f"最低：{min_rate:.4f} ({min_date.date()})")
print(f"最新：{df['日收盤匯率'].iloc[-1]:.4f}")
print(f"平均：{df['日收盤匯率'].mean():.4f}")