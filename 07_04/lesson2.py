#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
lesson2.py - 台股相關係數分析工具 (全新版本)
功能: 搜尋選股 → 加入清單 → 自動下載資料 → 熱力圖 / 散佈圖矩陣 / 條件格式化表格
"""
import sys, re
import numpy as np
import pandas as pd
import yfinance as yf

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QCompleter, QProgressBar, QMessageBox,
    QStatusBar, QSizePolicy, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QColor

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams["font.family"] = "Microsoft JhengHei"
plt.rcParams["axes.unicode_minus"] = False

# ==================== 台股資料庫 ====================
TW_STOCKS = [
    ("1101","台泥","上市"),("1102","亞泥","上市"),("1103","嘉泥","上市"),
    ("1104","環泥","上市"),("1105","信大","上市"),("1107","新建","上市"),
    ("1108","幸福","上市"),("1110","東泥","上市"),
    ("1201","味全","上市"),("1203","味王","上市"),("1210","大成","上市"),
    ("1213","大飲","上市"),("1215","卜蜂","上市"),("1216","統一","上市"),
    ("1217","愛之味","上市"),("1218","泰山","上市"),("1219","福壽","上市"),
    ("1220","台榮","上市"),("1225","福懋油","上市"),("1227","佳格","上市"),
    ("1229","聯華","上市"),("1231","聯華食","上市"),
    ("1301","台塑","上市"),("1303","南亞","上市"),("1304","台聚","上市"),
    ("1305","華夏","上市"),("1307","三芳","上市"),("1308","亞聚","上市"),
    ("1309","台達化","上市"),("1310","台苯","上市"),("1312","國喬","上市"),
    ("1313","中石化","上市"),("1316","東陽","上市"),
    ("1402","遠東新","上市"),("1409","新纖","上市"),
    ("1590","亞德客-KY","上市"),("1597","直得","上市"),
    ("1605","華新","上市"),("1606","信邦","上市"),
    ("1701","中化","上市"),("1702","南僑","上市"),("1707","葡萄王","上市"),
    ("1710","東聯","上市"),("1711","永光","上市"),("1712","興農","上市"),
    ("1713","台肥","上市"),("1717","長春","上市"),("1718","中纖","上市"),
    ("1720","生達","上市"),("1723","士紙","上市"),("1724","台紙","上市"),
    ("1802","台玻","上市"),("1808","允強","上市"),
    ("2002","中鋼","上市"),("2006","東鋼","上市"),("2007","豐興","上市"),
    ("2008","榮剛","上市"),("2009","第一銅","上市"),("2010","春源","上市"),
    ("2012","中鴻","上市"),("2013","中鋼構","上市"),("2015","豐達科","上市"),
    ("2027","大成鋼","上市"),("2028","威致","上市"),("2029","盛餘","上市"),
    ("2031","新光鋼","上市"),
    ("2105","正新","上市"),("2108","南港","上市"),("2109","華豐","上市"),
    ("2114","建大","上市"),("2116","華固","上市"),("2117","台橡","上市"),
    ("2201","裕隆","上市"),("2204","中華","上市"),("2206","三陽","上市"),
    ("2207","和泰車","上市"),("2208","台船","上市"),
    ("2212","國產","上市"),
    ("2301","光寶科","上市"),("2302","麗正","上市"),("2303","聯電","上市"),
    ("2305","全友","上市"),("2307","欣興","上市"),("2308","台達電","上市"),
    ("2309","友達","上市"),("2311","日月光投控","上市"),
    ("2312","智邦","上市"),("2313","華通","上市"),
    ("2315","英業達","上市"),("2317","鴻海","上市"),
    ("2318","中華電","上市"),("2320","昆盈","上市"),
    ("2321","瑞昱","上市"),("2322","大同","上市"),("2323","中環","上市"),
    ("2324","仁寶","上市"),("2327","國巨","上市"),
    ("2329","華碩","上市"),("2330","台積電","上市"),("2331","精英","上市"),
    ("2332","友訊","上市"),("2337","旺宏","上市"),
    ("2340","台亞","上市"),("2344","華邦電","上市"),
    ("2348","鈊象","上市"),("2349","錸德","上市"),
    ("2350","凌陽","上市"),("2353","宏碁","上市"),("2354","鴻準","上市"),
    ("2357","華碩","上市"),("2359","所羅門","上市"),("2360","致茂","上市"),
    ("2363","矽統","上市"),("2365","昆盈","上市"),
    ("2367","義隆","上市"),("2368","金像電","上市"),
    ("2369","凌華","上市"),("2371","大同","上市"),
    ("2373","世芯-KY","上市"),("2374","佳能","上市"),
    ("2376","技嘉","上市"),("2377","微星","上市"),
    ("2379","瑞昱","上市"),("2382","廣達","上市"),("2383","台光電","上市"),
    ("2385","群光","上市"),("2388","威盛","上市"),("2390","研華","上市"),
    ("2391","啟碁","上市"),("2392","正崴","上市"),("2393","億光","上市"),
    ("2396","佳世達","上市"),("2397","友通","上市"),
    ("2399","智原","上市"),("2400","欣銓","上市"),
    ("2403","南亞科","上市"),("2404","漢唐","上市"),
    ("2408","南亞科","上市"),("2412","中華電","上市"),
    ("2418","力旺","上市"),("2421","建準","上市"),
    ("2428","景碩","上市"),("2430","鈺創","上市"),
    ("2431","聯昌","上市"),("2434","蘑菇科技","上市"),("2435","中磊","上市"),
    ("2439","美律","上市"),("2449","京元電子","上市"),
    ("2454","聯發科","上市"),("2456","奇力新","上市"),
    ("2460","建榮","上市"),("2465","麗臺","上市"),
    ("2474","鈊象","上市"),("2481","強茂","上市"),
    ("2492","華新科","上市"),
    ("2501","國建","上市"),("2505","華固","上市"),
    ("2511","太子","上市"),("2515","國揚","上市"),
    ("2520","冠德","上市"),("2534","宏盛","上市"),
    ("2542","興富發","上市"),("2548","夏都","上市"),
    ("2599","豐泰","上市"),
    ("2603","長榮","上市"),("2605","新興","上市"),("2606","裕民","上市"),
    ("2607","榮運","上市"),("2609","陽明","上市"),
    ("2610","萬海","上市"),("2615","台航","上市"),
    ("2617","台驊","上市"),("2618","長榮航","上市"),
    ("2637","慧洋-KY","上市"),
    ("2704","全家","上市"),("2705","六角","上市"),
    ("2707","晶華","上市"),("2712","豐邑","上市"),
    ("2715","宏全","上市"),("2718","台塑化","上市"),
    ("2723","美食-KY","上市"),("2724","王品","上市"),
    ("2729","瓦城","上市"),("2731","雄獅","上市"),
    ("2739","寒舍","上市"),("2743","全家便利商店","上市"),
    ("2747","富邦媒","上市"),("2753","八方雲集","上市"),
    ("2801","彰銀","上市"),("2809","京城銀","上市"),
    ("2811","第一金","上市"),("2812","高雄銀","上市"),
    ("2816","安泰銀","上市"),("2834","臺企銀","上市"),
    ("2845","遠東商銀","上市"),("2850","新產","上市"),
    ("2852","第一保","上市"),("2855","統一證","上市"),
    ("2856","元大金","上市"),("2861","兆豐金","上市"),
    ("2862","台新金","上市"),("2864","永豐金","上市"),
    ("2867","三商壽","上市"),("2870","中信金","上市"),
    ("2871","中信證","上市"),("2872","國泰金","上市"),
    ("2873","群益證","上市"),("2878","合庫金","上市"),
    ("2880","玉山金","上市"),("2881","富邦金","上市"),
    ("2882","國泰證","上市"),("2883","開發金","上市"),
    ("2884","玉山證","上市"),("2885","元大期","上市"),
    ("2886","兆豐證","上市"),("2887","台新證","上市"),
    ("2888","新光金","上市"),("2890","永豐金控","上市"),
    ("2897","元大投信","上市"),
    ("2901","欣欣","上市"),("2903","遠百","上市"),
    ("2904","震旦行","上市"),("2905","三商行","上市"),
    ("2910","統一超","上市"),("2912","統一超","上市"),
    ("2915","潤泰全","上市"),("2918","晶華酒店","上市"),
    ("2928","潤泰新","上市"),("2929","三商家購","上市"),
    ("2934","新美齊","上市"),("2935","台中銀","上市"),
    ("2938","旭隼","上市"),("2941","穩懋","上市"),
    ("2945","三瑞","上市"),
    ("3008","大立光","上市"),("3010","聯亞光","上市"),
    ("3011","今國光","上市"),("3014","聯陽","上市"),
    ("3015","勵勁-KY","上市"),("3016","嘉晶","上市"),
    ("3017","雙鴻","上市"),("3019","亞光","上市"),
    ("3023","信邦","上市"),("3024","崇友","上市"),
    ("3027","智易","上市"),("3029","零壹","上市"),
    ("3030","德律","上市"),("3034","聯詠","上市"),
    ("3035","智原","上市"),("3037","欣興","上市"),
    ("3039","宇瞻","上市"),("3042","晶技","上市"),
    ("3045","台灣大","上市"),("3049","和碩","上市"),
    ("3050","德微","上市"),("3052","凌巨","上市"),
    ("3060","安國","上市"),("3061","盛群","上市"),
    ("3062","建準","上市"),
    ("3069","宇連","上市"),
    ("3078","百佳泰","上市"),("3080","松翰","上市"),
    ("3081","聯亞","上市"),("3083","網龍","上市"),
    ("3085","新聚科","上市"),("3088","宏致","上市"),
    ("3091","成翔","上市"),("3094","連展","上市"),
    ("3098","聯茂","上市"),
    ("3105","穩懋","上市"),("3111","頎邦","上市"),
    ("3114","奇力新","上市"),("3117","通嘉","上市"),
    ("3121","新唐","上市"),("3122","笙泉","上市"),
    ("3123","穎崴","上市"),("3124","順達","上市"),
    ("3126","天鈺","上市"),("3128","昇達科","上市"),
    ("3130","一力","上市"),("3131","銀邦","上市"),("3132","立積","上市"),
    ("3134","聯陽","上市"),("3136","信紘科","上市"),
    ("3169","中信銀","上市"),("3176","基亞","上市"),
    ("3211","順達","上市"),("3217","優群","上市"),
    ("3227","原相","上市"),("3260","威剛","上市"),
    ("3269","展碁國際","上市"),
    ("3276","群聯","上市"),("3287","日月光","上市"),
    ("3305","昆聚","上市"),("3311","閎暉","上市"),
    ("3317","尼克森","上市"),("3323","加百裕","上市"),
    ("3324","雙鴻","上市"),("3329","東捷","上市"),
    ("3331","恩德","上市"),("3340","東貝","上市"),
    ("3343","中美晶","上市"),("3345","光磊","上市"),("3346","麗清","上市"),
    ("3349","倍微","上市"),("3350","聯鈞","上市"),
    ("3355","萊斯資訊","上市"),("3356","奇偶","上市"),
    ("3365","安勤","上市"),("3366","凌群","上市"),
    ("3373","健策","上市"),("3380","明泰","上市"),("3381","群創","上市"),
    ("3406","玉晶光","上市"),("3408","力旺","上市"),
    ("3413","聚鼎","上市"),("3426","台勝科","上市"),
    ("3447","展達","上市"),("3450","鈺太","上市"),
    ("3454","晶睿","上市"),("3458","鵬寶科技","上市"),
    ("3478","祥盟","上市"),("3480","宏致","上市"),
    ("3483","力致","上市"),("3492","晟銘電","上市"),
    ("3497","彩晶","上市"),
    ("3504","揚明光","上市"),("3508","位速","上市"),
    ("3510","凌陽","上市"),("3515","華立","上市"),
    ("3516","亞信","上市"),("3518","聯穎","上市"),
    ("3520","華盈","上市"),("3521","益通","上市"),
    ("3526","凡甲","上市"),("3527","世芯","上市"),
    ("3532","天鈺","上市"),("3533","嘉澤","上市"),
    ("3545","敦泰","上市"),("3546","宇瞻","上市"),
    ("3550","台達電","上市"),("3552","同致","上市"),
    ("3555","博城","上市"),("3556","虹堡","上市"),
    ("3558","安碁資訊","上市"),("3564","祥碩","上市"),
    ("3570","大市","上市"),("3578","有量","上市"),
    ("3583","辛耘","上市"),
    ("3589","永信","上市"),("3591","艾笛森","上市"),
    ("3596","智微","上市"),("3598","大眾控","上市"),
    ("3605","新世紀","上市"),("3606","裕民","上市"),
    ("3608","嘉澤","上市"),("3615","安可","上市"),
    ("3626","台星科","上市"),("3627","信紘科","上市"),
    ("3637","兆利","上市"),("3639","穎崴","上市"),
    ("3711","日月光投控","上市"),
    ("4104","DA Sekurit","上市"),("4106","雃博","上市"),
    ("4107","邦特","上市"),("4110","佳醫","上市"),
    ("4113","聯亞藥","上市"),("4116","明基醫","上市"),
    ("4120","金可-KY","上市"),("4123","承德","上市"),
    ("4126","太醫","上市"),("4128","中天","上市"),
    ("4137","麗豐-KY","上市"),("4139","馬光-KY","上市"),
    ("4142","國光生","上市"),("4151","智擎","上市"),
    ("4153","鈺緯","上市"),("4155","訊映","上市"),
    ("4158","安成藥","上市"),("4165","台耀","上市"),
    ("4167","松瑞藥","上市"),("4181","台耀","上市"),("4182","杏國","上市"),
]

# 顯示文字清單 (供 QCompleter 使用)
STOCK_DISPLAY = [f"{c} - {n} ({m})" for c, n, m in TW_STOCKS]
# 代碼 → 名稱
CODE_TO_NAME = {c: n for c, n, m in TW_STOCKS}

# ==================== 色彩 ====================
C = {
    "bg": "#ffffff", "card": "#f8f9fa", "input": "#ffffff",
    "primary": "#e94560", "primary_l": "#ff6b81",
    "text": "#1a1a2e", "dim": "#6b7280", "border": "#e5e7eb",
    "hi": "#ef4444", "md": "#f97316", "lo": "#eab308", "no": "#9ca3af", "self": "#10b981",
}

STYLE = f"""
* {{ font-family: "Microsoft JhengHei"; }}
QMainWindow {{ background: {C["bg"]}; }}
QWidget {{ background: transparent; color: {C["text"]}; }}
QLineEdit {{
    background: {C["input"]}; border: 2px solid {C["border"]};
    border-radius: 8px; padding: 12px 16px; font-size: 15px; color: {C["text"]};
}}
QLineEdit:focus {{ border-color: {C["primary"]}; }}
QPushButton {{
    background: {C["primary"]}; color: white; border: none;
    border-radius: 8px; padding: 12px 24px; font-size: 14px; font-weight: bold;
}}
QPushButton:hover {{ background: {C["primary_l"]}; }}
QPushButton:pressed {{ background: #c0392b; }}
QPushButton:disabled {{ background: {C["border"]}; color: {C["dim"]}; }}
QListWidget {{
    background: {C["card"]}; border: 2px solid {C["border"]};
    border-radius: 8px; padding: 4px; font-size: 14px; color: {C["text"]};
}}
QListWidget::item {{ padding: 10px 12px; border-bottom: 1px solid {C["border"]}; border-radius: 4px; }}
QListWidget::item:selected {{ background: {C["primary"]}; color: white; }}
QListWidget::item:hover {{ background: #f3f4f6; }}
QTabWidget::pane {{ border: 2px solid {C["border"]}; border-radius: 8px; background: {C["card"]}; padding: 0px; }}
QTabBar::tab {{
    background: {C["bg"]}; color: {C["dim"]}; border: 1px solid {C["border"]};
    border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px;
    padding: 10px 20px; margin-right: 4px; font-size: 13px; font-weight: bold;
}}
QTabBar::tab:selected {{ background: {C["card"]}; color: {C["primary"]}; }}
QTabBar::tab:hover:!selected {{ background: #f3f4f6; }}
QTableWidget {{
    background: {C["card"]}; border: 2px solid {C["border"]};
    border-radius: 8px; gridline-color: {C["border"]}; font-size: 13px;
    selection-background-color: {C["primary"]};
}}
QHeaderView::section {{
    background: {C["input"]}; color: {C["text"]}; border: none;
    border-bottom: 2px solid {C["border"]}; border-right: 1px solid {C["border"]};
    padding: 10px 8px; font-weight: bold; font-size: 13px;
}}
QProgressBar {{
    border: 2px solid {C["border"]}; border-radius: 8px;
    background: #f3f4f6; text-align: center; color: {C["text"]};
    font-size: 12px; font-weight: bold; height: 22px;
}}
QProgressBar::chunk {{ background: {C["primary"]}; border-radius: 6px; }}
QStatusBar {{ background: {C["card"]}; color: {C["dim"]}; border-top: 1px solid {C["border"]}; font-size: 13px; }}
QCompleter QAbstractItemView {{
    background: white; border: 2px solid {C["primary"]}; border-radius: 8px;
    selection-background-color: {C["primary"]}; selection-color: white; padding: 4px; outline: none;
}}
QScrollBar:vertical {{ background: {C["bg"]}; width: 10px; border-radius: 5px; }}
QScrollBar::handle:vertical {{ background: {C["border"]}; min-height: 30px; border-radius: 5px; }}
QScrollBar::handle:vertical:hover {{ background: {C["primary"]}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QLabel {{ color: {C["text"]}; background: transparent; }}
"""


# ==================== Canvas ====================
class MplCanvas(FigureCanvas):
    """Matplotlib 畫布，自動填滿容器"""
    def __init__(self, parent=None, dpi=100):
        self.fig = Figure(dpi=dpi, facecolor='none', constrained_layout=True)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(200, 200)
        self.axes.set_facecolor('none')
        self.fig.patch.set_facecolor('none')

    def resizeEvent(self, event):
        FigureCanvas.resizeEvent(self, event)
        if self.width() > 0 and self.height() > 0:
            self.fig.set_size_inches(self.width() / self.fig.dpi, self.height() / self.fig.dpi)


# ==================== 資料下載執行緒 ====================
class FetchThread(QThread):
    progress = Signal(int)
    finished = Signal(pd.DataFrame)
    error = Signal(str)

    def __init__(self, tickers: dict, start: str):
        super().__init__()
        self.tickers = tickers   # {"display": "code.TW"}
        self.start = start

    def run(self):
        try:
            self.progress.emit(10)
            data = yf.download(
                list(self.tickers.values()),
                start=self.start, interval="1d",
                auto_adjust=True, progress=False
            )
            self.progress.emit(80)
            close = data["Close"]
            rename = {v: k for k, v in self.tickers.items()}
            close = close.rename(columns=rename)
            self.progress.emit(100)
            self.finished.emit(close)
        except Exception as e:
            self.error.emit(str(e))


# ==================== 主視窗 ====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("台股相關係數分析")
        self.resize(1400, 900)
        self.setMinimumSize(1000, 600)
        self.setStyleSheet(STYLE)

        self.stocks = {}       # {display: ticker}
        self.stock_data = None
        self.returns = None
        self.corr = None

        self._build_ui()
        self.statusBar().showMessage("請搜尋並選取 2~4 檔股票，再點擊「開始分析」")

    # ---------- 建構 UI ----------
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        # 標題
        title = QLabel("📊 台股相關係數分析")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #e94560; border: none;")
        lay.addWidget(title)
        sub = QLabel("搜尋並選取 2 ~ 4 檔股票，自動計算日報酬率相關係數")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"font-size: 14px; color: {C['dim']}; border: none; margin-bottom: 8px;")
        lay.addWidget(sub)

        # 搜尋列
        srow = QHBoxLayout()
        srow.setSpacing(12)
        self.search = QLineEdit()
        self.search.setPlaceholderText("輸入股票代碼或名稱（例如: 2330、台積電）...")
        self.search.setMinimumHeight(48)
        self.completer = QCompleter(STOCK_DISPLAY)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setMaxVisibleItems(10)
        self.search.setCompleter(self.completer)
        self.search.returnPressed.connect(self._add)
        srow.addWidget(self.search, 1)

        btn_add = QPushButton("+ 加入")
        btn_add.setMinimumHeight(48)
        btn_add.setMinimumWidth(120)
        btn_add.clicked.connect(self._add)
        srow.addWidget(btn_add)
        lay.addLayout(srow)

        # 已選清單
        lbl = QLabel("📋 已選股票（2~4 檔）")
        lbl.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {C['primary']}; border: none;")
        lay.addWidget(lbl)

        list_row = QHBoxLayout()
        list_row.setSpacing(12)
        self.stock_list = QListWidget()
        self.stock_list.setMinimumHeight(100)
        self.stock_list.setMaximumHeight(200)
        list_row.addWidget(self.stock_list, 1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(8)
        btn_rm = QPushButton("✕ 移除")
        btn_rm.setMinimumHeight(40)
        btn_rm.setStyleSheet(f"""
            QPushButton {{ background: {C["card"]}; color: {C["primary"]}; border: 2px solid {C["primary"]}; }}
            QPushButton:hover {{ background: #fef2f2; }}
        """)
        btn_rm.clicked.connect(self._remove)
        btn_col.addWidget(btn_rm)
        btn_clr = QPushButton("清空")
        btn_clr.setMinimumHeight(40)
        btn_clr.setStyleSheet(f"""
            QPushButton {{ background: #f3f4f6; color: {C["primary"]}; border: 2px solid {C["primary"]}; }}
            QPushButton:hover {{ background: #fef2f2; }}
        """)
        btn_clr.clicked.connect(self._clear)
        btn_col.addWidget(btn_clr)
        btn_col.addStretch()
        list_row.addLayout(btn_col)
        lay.addLayout(list_row)

        # 分析按鈕 + 進度條
        arow = QHBoxLayout()
        arow.setSpacing(12)
        self.btn_analyze = QPushButton("🔍 開始分析（需至少 2 檔）")
        self.btn_analyze.setMinimumHeight(48)
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.clicked.connect(self._analyze)
        arow.addWidget(self.btn_analyze)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.progress.setMaximumHeight(50)
        arow.addWidget(self.progress, 1)
        lay.addLayout(arow)

        # 分頁
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 2px solid {C["border"]}; border-radius: 8px;
                background: {C["card"]}; padding: 0px;
            }}
        """)

        # 熱力圖分頁
        t1 = QWidget()
        l1 = QVBoxLayout(t1)
        l1.setContentsMargins(4, 4, 4, 4)
        self.heat_cv = MplCanvas(self, dpi=120)
        l1.addWidget(self.heat_cv)
        self.tabs.addTab(t1, "🔥 熱力圖")

        # 散佈圖矩陣分頁
        t2 = QWidget()
        l2 = QVBoxLayout(t2)
        l2.setContentsMargins(4, 4, 4, 4)
        self.scatter_cv = MplCanvas(self, dpi=120)
        l2.addWidget(self.scatter_cv)
        self.tabs.addTab(t2, "📊 散佈圖矩陣")

        # 條件格式化表格分頁
        t3 = QWidget()
        l3 = QVBoxLayout(t3)
        l3.setContentsMargins(4, 4, 4, 4)
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        l3.addWidget(self.table)
        self.tabs.addTab(t3, "📋 條件格式化表格")

        lay.addWidget(self.tabs, 1)

    # ---------- 股票操作 ----------
    def _add(self):
        text = self.search.text().strip()
        if not text:
            return
        info = self._find(text)
        if not info:
            QMessageBox.warning(self, "找不到", f"找不到「{text}」對應的股票")
            return
        display, ticker = info
        if len(self.stocks) >= 4:
            QMessageBox.warning(self, "已達上限", "最多只能選擇 4 檔股票")
            return
        if display in self.stocks:
            QMessageBox.information(self, "重複", f"已加入過「{display}」")
            return
        self.stocks[display] = ticker
        self.stock_list.addItem(display)
        self.search.clear()
        self._refresh_btn()

    def _remove(self):
        row = self.stock_list.currentRow()
        if row < 0:
            return
        item = self.stock_list.takeItem(row)
        self.stocks.pop(item.text(), None)
        self._refresh_btn()

    def _clear(self):
        self.stock_list.clear()
        self.stocks.clear()
        self._refresh_btn()

    def _find(self, text):
        """從輸入文字找到對應股票，回傳 (display, ticker) 或 None"""
        t = text.lower()
        # 1) 完整顯示格式 "2330 - 台積電 (上市)"
        m = re.match(r"(\d{4})", t)
        if m:
            code = m.group(1)
            for c, n, mk in TW_STOCKS:
                if c == code:
                    return (f"{c} - {n} ({mk})", f"{c}.TW")
        # 2) 精確比對
        for c, n, mk in TW_STOCKS:
            if t == c or t == n.lower():
                return (f"{c} - {n} ({mk})", f"{c}.TW")
        # 3) 模糊比對
        for c, n, mk in TW_STOCKS:
            if t in c or t in n.lower():
                return (f"{c} - {n} ({mk})", f"{c}.TW")
        return None

    def _refresh_btn(self):
        n = len(self.stocks)
        self.btn_analyze.setEnabled(n >= 2)
        if n < 2:
            self.btn_analyze.setText(f"🔍 開始分析（需至少 {2 - n} 檔）")
        else:
            self.btn_analyze.setText(f"🔍 開始分析（{n} 檔股票）")

    # ---------- 分析 ----------
    def _analyze(self):
        if len(self.stocks) < 2:
            return
        self.progress.setValue(0)
        self.btn_analyze.setEnabled(False)
        self.statusBar().showMessage("正在擷取資料...")

        self.thread = FetchThread(self.stocks, "2024-01-01")
        self.thread.progress.connect(lambda v: self.progress.setValue(v))
        self.thread.finished.connect(self._on_done)
        self.thread.error.connect(self._on_err)
        self.thread.start()

    def _on_done(self, data):
        self.stock_data = data
        self.returns = data.pct_change().dropna()
        self.corr = self.returns.corr()
        self._plot_heatmap()
        self._plot_scatter()
        self._fill_table()
        self.progress.setValue(100)
        self.btn_analyze.setEnabled(True)
        names = ", ".join(self.corr.columns.tolist())
        self.statusBar().showMessage(f"✅ 分析完成：{names}")

    def _on_err(self, msg):
        self.btn_analyze.setEnabled(True)
        self.progress.setValue(0)
        self.statusBar().showMessage(f"❌ 錯誤：{msg}")
        QMessageBox.critical(self, "擷取失敗", f"無法擷取股票資料：\n{msg}")

    # ---------- 熱力圖 ----------
    def _plot_heatmap(self):
        ax = self.heat_cv.axes
        ax.clear()
        sns.heatmap(
            self.corr, annot=True, fmt=".2f", cmap="RdYlBu_r",
            center=0, vmin=-1, vmax=1, square=True,
            linewidths=2, linecolor="white",
            cbar_kws={"shrink": 0.8, "label": "相關係數"},
            ax=ax, annot_kws={"size": 13, "weight": "bold", "color": "#1a1a2e"}
        )
        ax.set_title("股票日報酬率相關係數熱力圖", fontsize=15, fontweight="bold", color=C["text"], pad=15)
        self.heat_cv.draw()

    # ---------- 散佈圖矩陣 ----------
    def _plot_scatter(self):
        fig = self.scatter_cv.fig
        fig.clear()
        ret = self.returns
        n = len(ret.columns)
        axes = fig.subplots(n, n, squeeze=False)
        colors = ["#e94560", "#533483", "#0f3460", "#10b981", "#f59e0b", "#3b82f6"]

        for i in range(n):
            for j in range(n):
                ax = axes[i][j]
                ax.set_facecolor("white")
                if i == j:
                    ret.iloc[:, i].plot(kind="kde", ax=ax, color=colors[i % len(colors)], linewidth=2)
                    ax.set_title(ret.columns[i], fontsize=11, fontweight="bold", color=C["text"])
                    ax.set_ylabel("")
                else:
                    ax.scatter(ret.iloc[:, j], ret.iloc[:, i], alpha=0.5, s=12,
                               color=colors[i % len(colors)], edgecolors="#555", linewidth=0.3)
                    r = self.corr.iloc[i, j]
                    ax.text(0.5, 0.9, f"r={r:.2f}", transform=ax.transAxes,
                            ha="center", va="top", fontsize=10, fontweight="bold", color="#1a1a2e",
                            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9, edgecolor="#ccc"))
                if i == n - 1:
                    ax.set_xlabel(ret.columns[j], fontsize=9, color=C["dim"])
                else:
                    ax.set_xlabel("")
                if j == 0:
                    ax.set_ylabel(ret.columns[i], fontsize=9, color=C["dim"])
                else:
                    ax.set_ylabel("")
                ax.tick_params(labelsize=8, colors=C["dim"])
                for sp in ax.spines.values():
                    sp.set_color(C["border"])

        fig.suptitle("股票日報酬率散佈圖矩陣", fontsize=15, fontweight="bold", color=C["text"], y=1.01)
        self.scatter_cv.draw()

    # ---------- 條件格式化表格 ----------
    def _fill_table(self):
        corr = self.corr
        n = len(corr)
        self.table.setRowCount(n)
        self.table.setColumnCount(n)
        hdrs = corr.columns.tolist()
        self.table.setHorizontalHeaderLabels(hdrs)
        self.table.setVerticalHeaderLabels(hdrs)
        hfont = QFont("Microsoft JhengHei", 12, QFont.Bold)
        self.table.horizontalHeader().setFont(hfont)
        self.table.verticalHeader().setFont(hfont)

        for i in range(n):
            for j in range(n):
                v = corr.iloc[i, j]
                item = QTableWidgetItem(f"{v:.3f}")
                item.setTextAlignment(Qt.AlignCenter)
                if i == j:
                    bg, fg = QColor(C["self"]), QColor("white")
                elif abs(v) >= 0.7:
                    bg, fg = QColor(C["hi"]), QColor("white")
                elif abs(v) >= 0.5:
                    bg, fg = QColor(C["md"]), QColor("white")
                elif abs(v) >= 0.3:
                    bg, fg = QColor(C["lo"]), QColor("#1a1a2e")
                else:
                    bg, fg = QColor(C["no"]), QColor("white")
                item.setBackground(bg)
                item.setForeground(fg)
                item.setFont(QFont("Microsoft JhengHei", 13, QFont.Bold))
                self.table.setItem(i, j, item)


# ==================== 入口 ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft JhengHei", 10))
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
