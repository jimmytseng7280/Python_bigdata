#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
lesson6.py - PyQtGraph 強大功能測試與演示儀表板
使用 PySide6 與 PyQtGraph 建立一個現代化、高效能且具高度互動性的科學數據視覺化應用程式。
此應用程式特別展示了 PyQtGraph 在高頻即時刷新、大數據量局部縮放、動態2D影像計算與散佈圖滑鼠互動等方面的卓越表現。

功能模組：
1. 即時多通道示波器 - 模擬雙通道正弦波即時顯示
2. 區間選取與縮放 - 大數據量的局部放大與雙向同步
3. 即時 2D 熱圖 - 動態波源干涉計算與渲染
4. 互動式散佈圖 - 高互動性散佈點與滑鼠事件處理
"""

# ==================== 匯入套件 ====================
import sys    # 系統功能，用於程式退出 sys.exit()
import os     # 作業系統功能（本範例未直接使用，保留供擴充）
import time   # 時間模組，用於 FPS 計算與隨機種子
import numpy as np  # 數值計算套件，處理矩陣運算與隨機數生成

# PySide6 - Qt for Python 的官方綁定
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QSlider, QCheckBox, QPushButton,
                               QTabWidget, QSplitter, QGroupBox, QFormLayout, QStatusBar,
                               QComboBox, QStackedWidget, QFrame, QScrollArea)
from PySide6.QtCore import QTimer, Qt, Slot, QPointF  # Qt 核心功能
from PySide6.QtGui import QFont, QColor  # Qt 圖形與字型功能

# PyQtGraph - 高效能科學繪圖套件，基於 Qt Graphics View Framework
import pyqtgraph as pg

# ==================== PyQtGraph 全域設定 ====================
# 注意：這些設定必須在建立任何 Widget 之前完成
pg.setConfigOption('background', '#fff5f7')  # 圖表背景色：淺玫瑰粉
pg.setConfigOption('foreground', '#4a3040')  # 圖表前景色（軸標籤、文字）：深玫瑰棕
pg.setConfigOptions(antialias=True)          # 啟用抗鋸齒，讓線條更平滑

# ==================== UI 樣式表 (QSS) ====================
# 使用類似 CSS 的語法來美化 Qt 介面
# 色彩主題：柔美淺粉紅風格
MODERN_STYLE = """
/* ==================== QSS 樣式表語法說明 ====================
 * QSS (Qt Style Sheets) 是 Qt 的樣式表語言，語法與 CSS 非常相似
 * 
 * 基本語法結構：
 * 選擇器 {
 *     屬性名稱: 屬性值;
 * }
 * 
 * 常見選擇器類型：
 * - QMainWindow：選擇所有 QMainWindow 實例
 * - QWidget：選擇所有 QWidget 及其子類
 * - QLabel：選擇所有 QLabel 標籤控件
 * - QPushButton：選擇所有 QPushButton 按鈕控件
 * - QGroupBox#objectName：選擇特定物件名稱的控件（# 後接物件名稱）
 * 
 * 本範例使用 "物件名稱選擇器" 來精確控制特定控件的樣式
 * 例如：QPushButton#playPauseBtn 只影響物件名稱為 playPauseBtn 的按鈕
 * ==================== QSS 樣式表語法說明 ==================== */

/* 主視窗背景色 */
QMainWindow {
    background-color: #fdf2f8;  /* 淺玫瑰粉底色，#ffffff 為純白，此處使用柔和的粉色 */
}

/* 中央主 Widget 背景色 */
QWidget#centralWidget {
    background-color: #fdf2f8;
}

/* 一般標籤文字樣式 */
QLabel {
    color: #5b3a52;  /* 深玫瑰棕文字 */
    font-family: ".AppleSystemUIFont", "Noto Sans TC", "Microsoft JhengHei", sans-serif;
    font-size: 13px;
}

/* 主標題樣式（側邊欄標題） */
QLabel#titleLabel {
    color: #be185d;  /* 玫瑰紅 */
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 4px;
}

/* 副標題樣式 */
QLabel#subTitleLabel {
    color: #9d7a9a;  /* 淡紫色調 */
    font-size: 12px;
    margin-bottom: 12px;
}

/* 群組框外框樣式 */
QGroupBox {
    border: 1px solid #f9a8d4;  /* 粉紅邊框 */
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #be185d;  /* 玫瑰紅標題 */
    font-family: ".AppleSystemUIFont", "Noto Sans TC", "Microsoft JhengHei", sans-serif;
}

/* 群組框標題位置 */
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 0 5px;
    background-color: #fdf2f8;
}

/* 主要按鈕樣式（玫瑰粉底色） */
QPushButton {
    background-color: #ec4899;  /* 玫瑰粉 */
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
    font-family: ".AppleSystemUIFont", "Noto Sans TC", "Microsoft JhengHei", sans-serif;
}

/* 按鈕滑鼠懸停效果 */
QPushButton:hover {
    background-color: #f472b6;  /* 淺粉紅 */
}

/* 按鈕按下效果 */
QPushButton:pressed {
    background-color: #db2777;  /* 深玫瑰 */
}

/* 播放/暫停按鈕特殊樣式（薰衣草紫） */
QPushButton#playPauseBtn {
    background-color: #a78bfa;  /* 薰衣草紫 */
}
QPushButton#playPauseBtn:hover {
    background-color: #c4b5fd;  /* 淺薰衣草 */
}
QPushButton#playPauseBtn:pressed {
    background-color: #8b5cf6;  /* 深薰衣草 */
}

/* 播放暫停按鈕：已選取（暫停狀態）時變為粉紅色 */
QPushButton#playPauseBtn[checked="true"] {
    background-color: #f472b6;  /* 粉紅色 */
}
QPushButton#playPauseBtn[checked="true"]:hover {
    background-color: #f9a8d4;
}
QPushButton#playPauseBtn[checked="true"]:pressed {
    background-color: #ec4899;
}

/* 動作按鈕樣式（淺粉底色，用於次要操作） */
QPushButton#actionBtn {
    background-color: #fce7f3;  /* 極淺粉 */
    color: #5b3a52;
    border: 1px solid #f9a8d4;
}
QPushButton#actionBtn:hover {
    background-color: #f9a8d4;
    color: #ffffff;
}
QPushButton#actionBtn:pressed {
    background-color: #f472b6;
    color: #ffffff;
}

/* 滑桿軌道樣式 */
QSlider::groove:horizontal {
    border: 1px solid #f9a8d4;
    height: 6px;
    background: #fce7f3;  /* 極淺粉 */
    border-radius: 3px;
}

/* 滑桿把手樣式 */
QSlider::handle:horizontal {
    background: #ec4899;  /* 玫瑰粉 */
    border: none;
    width: 14px;
    margin: -4px 0;
    border-radius: 7px;
}

/* 滑桿把手懸停效果 */
QSlider::handle:horizontal:hover {
    background: #f472b6;
}

/* 下拉選擇框樣式 */
QComboBox {
    background-color: #ffffff;  /* 白色底 */
    border: 1px solid #f9a8d4;
    border-radius: 6px;
    padding: 6px 12px;
    color: #5b3a52;
    font-size: 13px;
    font-family: ".AppleSystemUIFont", "Noto Sans TC", sans-serif;
    min-width: 100px;
}

/* 下拉選擇框展開時邊框 */
QComboBox:on {
    border: 1px solid #ec4899;
}

/* 下拉選擇框的下拉選單樣式 */
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #f9a8d4;
    selection-background-color: #ec4899;  /* 選取項目的底色 */
    selection-color: #ffffff;
    color: #5b3a52;
}

/* 核取方塊樣式 */
QCheckBox {
    color: #5b3a52;
    spacing: 8px;
}

/* 核取方塊指示器（方框）樣式 */
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #f9a8d4;
    border-radius: 4px;
    background-color: #ffffff;
}

/* 核取方塊已勾選時的樣式 */
QCheckBox::indicator:checked {
    background-color: #ec4899;
    border: 1px solid #ec4899;
}

/* 分頁 Widget 面板樣式 */
QTabWidget::pane {
    border: 1px solid #f9a8d4;
    border-radius: 8px;
    background-color: #ffffff;  /* 白色底 */
    padding: 4px;
}

/* 分頁標籤樣式 */
QTabBar::tab {
    background-color: #fce7f3;  /* 極淺粉 */
    color: #9d7a9a;
    border: 1px solid #f9a8d4;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    margin-right: 4px;
    font-weight: 500;
    font-family: ".AppleSystemUIFont", "Noto Sans TC", sans-serif;
}

/* 已選取的分頁標籤 */
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #be185d;  /* 玫瑰紅 */
    border: 1px solid #f9a8d4;
    border-bottom: 1px solid #ffffff;  /* 與面板底色融合 */
    font-weight: 600;
}

/* 未選取分頁標籤的懸停效果 */
QTabBar::tab:hover:!selected {
    background-color: #f9a8d4;
    color: #ffffff;
}

/* 垂直捲軸樣式 */
QScrollBar:vertical {
    background: #fdf2f8;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}

/* 垂直捲軸把手 */
QScrollBar::handle:vertical {
    background: #f9a8d4;
    min-height: 20px;
    border-radius: 5px;
}

/* 垂直捲軸把手懸停 */
QScrollBar::handle:vertical:hover {
    background: #f472b6;
}

/* 垂直捲軸上下箭頭（隱藏） */
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* 水平捲軸樣式 */
QScrollBar:horizontal {
    background: #fdf2f8;
    height: 10px;
    margin: 0px;
    border-radius: 5px;
}

/* 水平捲軸把手 */
QScrollBar::handle:horizontal {
    background: #f9a8d4;
    min-width: 20px;
    border-radius: 5px;
}

/* 水平捲軸把手懸停 */
QScrollBar::handle:horizontal:hover {
    background: #f472b6;
}

/* 水平捲軸左右箭頭（隱藏） */
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* 狀態列樣式 */
QStatusBar {
    background-color: #fdf2f8;
    color: #9d7a9a;
    border-top: 1px solid #f9a8d4;
    font-family: ".AppleSystemUIFont", "Noto Sans TC", sans-serif;
}
"""


# ==================== 主視窗類別 ====================
class PyQtGraphDemoApp(QMainWindow):
    """
    PyQtGraph 功能測試儀表板主視窗
    
    整個應用程式包含四個主要功能分頁：
    1. 即時多通道示波器：模擬雙通道正弦波即時顯示
    2. 區間選取與縮放：大數據量的局部放大與雙向同步
    3. 即時 2D 熱圖：動態波源干涉計算與渲染
    4. 互動式散佈圖：高互動性散佈點與滑鼠事件處理
    """

    def __init__(self):
        """初始化主視窗"""
        super().__init__()
        self.setWindowTitle("PyQtGraph 強大功能測試與展示儀表板")
        self.resize(1200, 800)
        # 套用預先定義的 CSS 樣式表到主視窗
        self.setStyleSheet(MODERN_STYLE)

        # ==================== 計時器與 FPS 統計 ====================
        # QTimer 用於定期觸發更新函數，實現即時動態效果
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_plots)  # 連接逾時信號到更新函數
        self.last_time = time.time()     # 記錄上次更新時間，用於計算 dt
        self.fps_buffer = []             # FPS 緩衝區，存放最近的 FPS 值以計算平均值
        self.time_offset = 0.0           # 時間偏移量，用於示波器波形相位移動

        # 初始化各功能模組的預設參數
        self._init_parameters()

        # 建立 UI 介面配置
        self._setup_ui()

        # 初始化資料與繪圖狀態
        self.regenerate_scatter_data()   # 生成散佈圖初始資料
        self.regenerate_zoom_data()      # 生成縮放圖初始資料
        
        # 啟動即時更新定時器（預設 60 FPS ≈ 16ms 間隔）
        self.fps_timer.start(16)

    def _init_parameters(self):
        """
        初始化各功能模組的預設數值
        
        包含三組參數：
        - 示波器：頻率、振幅、噪聲強度
        - 熱圖：演進速度、解析度、時間變數
        - 散佈圖：資料點數量
        """
        # 示波器設定
        self.oscilloscope_noise = 0.3    # 噪聲振幅（越大波形越不規則）
        self.oscilloscope_freq1 = 1.0    # 通道一頻率 (Hz)
        self.oscilloscope_freq2 = 2.0    # 通道二頻率 (Hz)
        self.oscilloscope_amp = 1.0      # 共用振幅

        # 熱圖設定
        self.heatmap_speed = 1.0         # 波動演進速度倍率
        self.heatmap_resolution = 128    # 運算網格解析度 (128x128)
        self.heatmap_t = 0.0             # 時間累積變數

        # 散佈圖設定
        self.scatter_count = 1000        # 預設散佈點數量

    def _setup_ui(self):
        """
        建立主要 UI 版面配置
        
        版面結構：
        ┌─────────────────────────────────────────────┐
        │  主視窗 (QMainWindow)                        │
        │  ┌──────────────┬──────────────────────────┐│
        │  │  側邊欄       │  主展示區 (QTabWidget)   ││
        │  │  (控制面板)   │  ┌────────────────────┐ ││
        │  │              │  │ 分頁一：示波器      │ ││
        │  │  全域控制     │  │ 分頁二：縮放        │ ││
        │  │  動態控制     │  │ 分頁三：熱圖        │ ││
        │  │  (Stacked)   │  │ 分頁四：散佈圖      │ ││
        │  │              │  └────────────────────┘ ││
        │  └──────────────┴──────────────────────────┘│
        │  ┌──────────────────────────────────────────┐│
        │  │  狀態列 (QStatusBar)                      ││
        │  └──────────────────────────────────────────┘│
        └─────────────────────────────────────────────┘
        """
        # 中央主 Widget（所有內容的根容器）
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")  # 設定物件名稱，供 QSS 選擇器使用
        self.setCentralWidget(central_widget)
        
        # 建立狀態列（提前建立，避免 TabWidget 新增 Tab 時觸發 on_tab_changed 報錯）
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 主水平佈局：分割左側控制區與右側展示區
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)  # 外邊距
        main_layout.setSpacing(16)  # 元素間距

        # QSplitter：可自由拖曳調整左右兩側寬度比例
        splitter = QSplitter(Qt.Horizontal)
        # 自訂 Splitter 分隔線樣式
        splitter.setStyleSheet("QSplitter::handle { background-color: #f9a8d4; width: 2px; }")

        # ================== 左側側邊欄：控制面板 ==================
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(12)

        # 側邊欄標題區域
        title_label = QLabel("PyQtGraph 測試面板")
        title_label.setObjectName("titleLabel")  # 對應 QSS 中的 QLabel#titleLabel
        sub_title = QLabel("即時、互動、高渲染效能")
        sub_title.setObjectName("subTitleLabel")
        sidebar_layout.addWidget(title_label)
        sidebar_layout.addWidget(sub_title)

        # ================== 1. 全域控制群組 ==================
        # 此群組的控制項適用於所有分頁
        global_group = QGroupBox("全域控制")
        global_layout = QFormLayout(global_group)  # 表單佈局：左邊標籤，右邊控件
        global_layout.setSpacing(10)

        # 播放/暫停按鈕（可切換狀態）
        self.play_pause_btn = QPushButton("暫停即時渲染")
        self.play_pause_btn.setObjectName("playPauseBtn")
        self.play_pause_btn.setCheckable(True)  # 設為可切換按鈕
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        global_layout.addRow(self.play_pause_btn)

        # 目標刷新率滑桿（5~120 FPS）
        self.fps_slider = QSlider(Qt.Horizontal)
        self.fps_slider.setRange(5, 120)
        self.fps_slider.setValue(60)
        self.fps_slider.valueChanged.connect(self.change_target_fps)
        self.fps_slider_label = QLabel("目標刷新率: 60 FPS")
        global_layout.addRow(self.fps_slider_label, self.fps_slider)

        # 實測 FPS 顯示標籤
        self.fps_display = QLabel("實測刷新率: 0.0 FPS")
        self.fps_display.setStyleSheet("color: #a78bfa; font-weight: bold;")  # 薰衣草紫
        global_layout.addRow("引擎狀態:", self.fps_display)

        # 抗鋸齒開關（全域設定，影響所有圖表線條品質）
        self.antialias_cb = QCheckBox("啟用全域抗鋸齒 (平滑線條)")
        self.antialias_cb.setChecked(True)
        self.antialias_cb.stateChanged.connect(self.toggle_antialias)
        global_layout.addRow(self.antialias_cb)

        sidebar_layout.addWidget(global_group)

        # ================== 2. 動態控制群組 ==================
        # 使用 QStackedWidget 實現「切頁效果」：
        # 根據右側分頁選擇，動態顯示對應的控制面板
        self.param_stack = QStackedWidget()
        
        # --- 分頁一控制面板：示波器參數設定 ---
        oscilloscope_widget = QWidget()
        osc_layout = QFormLayout(oscilloscope_widget)
        osc_layout.setContentsMargins(0, 0, 0, 0)
        
        osc_group = QGroupBox("即時示波器參數")
        osc_group_layout = QFormLayout(osc_group)

        # 通道一頻率滑桿（範圍 0.5Hz ~ 5.0Hz）
        self.osc_freq1_slider = QSlider(Qt.Horizontal)
        self.osc_freq1_slider.setRange(5, 50)  # 實際值 = 滑桿值 / 10
        self.osc_freq1_slider.setValue(10)
        self.osc_freq1_slider.valueChanged.connect(self.update_osc_params)
        self.osc_freq1_label = QLabel("通道一頻率: 1.0 Hz")
        osc_group_layout.addRow(self.osc_freq1_label, self.osc_freq1_slider)

        # 通道二頻率滑桿
        self.osc_freq2_slider = QSlider(Qt.Horizontal)
        self.osc_freq2_slider.setRange(5, 50)
        self.osc_freq2_slider.setValue(20)
        self.osc_freq2_slider.valueChanged.connect(self.update_osc_params)
        self.osc_freq2_label = QLabel("通道二頻率: 2.0 Hz")
        osc_group_layout.addRow(self.osc_freq2_label, self.osc_freq2_slider)

        # 噪聲強度滑桿（範圍 0.0 ~ 1.5）
        self.osc_noise_slider = QSlider(Qt.Horizontal)
        self.osc_noise_slider.setRange(0, 15)  # 實際值 = 滑桿值 / 10
        self.osc_noise_slider.setValue(3)
        self.osc_noise_slider.valueChanged.connect(self.update_osc_params)
        self.osc_noise_label = QLabel("通道二噪聲: 0.3")
        osc_group_layout.addRow(self.osc_noise_label, self.osc_noise_slider)

        # 顯示背景網格線開關
        self.osc_grid_cb = QCheckBox("顯示背景網格線")
        self.osc_grid_cb.setChecked(True)
        self.osc_grid_cb.stateChanged.connect(self.toggle_osc_grid)
        osc_group_layout.addRow(self.osc_grid_cb)

        # 啟用十字游標（滑鼠懸停時顯示座標）
        self.osc_crosshair_cb = QCheckBox("啟用游標座標讀取")
        self.osc_crosshair_cb.setChecked(True)
        self.osc_crosshair_cb.stateChanged.connect(self.toggle_osc_crosshair)
        osc_group_layout.addRow(self.osc_crosshair_cb)

        osc_layout.addRow(osc_group)
        self.param_stack.addWidget(oscilloscope_widget)  # 索引 0

        # --- 分頁二控制面板：區間縮放設定 ---
        zoom_widget = QWidget()
        zoom_layout = QFormLayout(zoom_widget)
        zoom_layout.setContentsMargins(0, 0, 0, 0)

        zoom_group = QGroupBox("大數據選取控制")
        zoom_group_layout = QVBoxLayout(zoom_group)
        
        # 互動操作說明標籤
        info_label = QLabel(
            "<b>互動提示：</b><br>"
            "1. 請拖曳上方圖表中的<b>半透明灰色區間</b>來變更局部放大範圍。<br>"
            "2. 可以在選取區間的<b>左右邊緣</b>拖曳以調整寬度。<br>"
            "3. 在下方圖表使用滑鼠滾輪縮放或右鍵拖曳時，上方選取框亦會<b>即時逆向同步</b>。"
        )
        info_label.setWordWrap(True)  # 自動換行
        info_label.setStyleSheet("color: #9d7a9a; line-height: 15px;")
        zoom_group_layout.addWidget(info_label)

        # 重新生成隨機走勢資料按鈕
        self.zoom_regen_btn = QPushButton("重新生成 random walk 趨勢線")
        self.zoom_regen_btn.setObjectName("actionBtn")
        self.zoom_regen_btn.clicked.connect(self.regenerate_zoom_data)
        zoom_group_layout.addWidget(self.zoom_regen_btn)

        zoom_layout.addRow(zoom_group)
        self.param_stack.addWidget(zoom_widget)  # 索引 1

        # --- 分頁三控制面板：2D 熱圖設定 ---
        heatmap_widget = QWidget()
        heatmap_layout = QFormLayout(heatmap_widget)
        heatmap_layout.setContentsMargins(0, 0, 0, 0)

        heatmap_group = QGroupBox("2D 熱圖運算參數")
        heatmap_group_layout = QFormLayout(heatmap_group)

        # 波動演進速度滑桿（0.1x ~ 3.0x）
        self.heat_speed_slider = QSlider(Qt.Horizontal)
        self.heat_speed_slider.setRange(1, 30)
        self.heat_speed_slider.setValue(10)
        self.heat_speed_slider.valueChanged.connect(self.update_heat_params)
        self.heat_speed_label = QLabel("波動演進速度: 1.0x")
        heatmap_group_layout.addRow(self.heat_speed_label, self.heat_speed_slider)

        # 色彩映射表選擇（影響熱圖外觀）
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(["viridis", "plasma", "magma", "inferno", "turbo", "cividis"])
        self.colormap_combo.currentTextChanged.connect(self.change_colormap)
        heatmap_group_layout.addRow("色彩地圖 (Colormap):", self.colormap_combo)

        # 運算解析度選擇（影響畫質與效能）
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItem("64 x 64 (極速)", 64)
        self.resolution_combo.addItem("128 x 128 (標準)", 128)
        self.resolution_combo.addItem("256 x 256 (高精細)", 256)
        self.resolution_combo.setCurrentIndex(1)
        self.resolution_combo.currentIndexChanged.connect(self.change_heatmap_resolution)
        heatmap_group_layout.addRow("運算網格解析度:", self.resolution_combo)

        # 色彩條操作提示
        info_heat = QLabel("提示：右側的色彩條 (Histogram) 可以直接用滑鼠拖曳上下界限來調整影像對比度。")
        info_heat.setWordWrap(True)
        info_heat.setStyleSheet("color: #9d7a9a; font-size: 11px;")
        heatmap_group_layout.addRow(info_heat)

        heatmap_layout.addRow(heatmap_group)
        self.param_stack.addWidget(heatmap_widget)  # 索引 2

        # --- 分頁四控制面板：散佈圖設定 ---
        scatter_widget = QWidget()
        scatter_layout = QFormLayout(scatter_widget)
        scatter_layout.setContentsMargins(0, 0, 0, 0)

        scatter_group = QGroupBox("隨機散佈點參數")
        scatter_group_layout = QFormLayout(scatter_group)

        # 資料點數量下拉選單
        self.scatter_count_combo = QComboBox()
        self.scatter_count_combo.addItem("500 點", 500)
        self.scatter_count_combo.addItem("1,000 點", 1000)
        self.scatter_count_combo.addItem("5,000 點 (效能測試)", 5000)
        self.scatter_count_combo.addItem("10,000 點 (極限效能)", 10000)
        self.scatter_count_combo.currentIndexChanged.connect(self.change_scatter_count)
        scatter_group_layout.addRow("資料點數 (Size):", self.scatter_count_combo)

        # 隨機重新生成資料按鈕
        self.scatter_regen_btn = QPushButton("隨機重新分佈資料點")
        self.scatter_regen_btn.setObjectName("actionBtn")
        self.scatter_regen_btn.clicked.connect(self.regenerate_scatter_data)
        scatter_group_layout.addRow(self.scatter_regen_btn)

        # 散佈圖互動操作說明
        info_scatter = QLabel(
            "<b>互動提示：</b><br>"
            "1. 滑鼠移到資料點上時，點會<b>自動高亮變紅</b>並在狀態列顯示座標。<br>"
            "2. 使用滑鼠<b>左鍵點擊</b>任一點，該點會被加上<b>紅色追蹤框</b>以標示選取。<br>"
            "3. 點選後，視窗底部狀態列將永久保留該點的資訊。"
        )
        info_scatter.setWordWrap(True)
        info_scatter.setStyleSheet("color: #9d7a9a; line-height: 15px;")
        scatter_group_layout.addRow(info_scatter)

        scatter_layout.addRow(scatter_group)
        self.param_stack.addWidget(scatter_widget)  # 索引 3

        # 將動態控制面板加入側邊欄
        sidebar_layout.addWidget(self.param_stack)
        sidebar_layout.addStretch()  # 在底部加入彈性空間

        # ================== 右側展示區：主分頁 Widget ==================
        self.main_tab = QTabWidget()
        self.main_tab.currentChanged.connect(self.on_tab_changed)  # 分頁切換時同步控制面板

        # 依序建立四個展示分頁
        self._create_tab_oscilloscope()  # 分頁一：即時示波器
        self._create_tab_zoom()          # 分頁二：區間縮放
        self._create_tab_heatmap()       # 分頁三：2D 熱圖
        self._create_tab_scatter()       # 分頁四：散佈圖

        # 將側邊欄與主要展示區加入 Splitter 容器
        sidebar_container = QWidget()
        sidebar_container.setLayout(sidebar_layout)
        sidebar_container.setMinimumWidth(260)  # 側邊欄最小寬度
        sidebar_container.setMaximumWidth(350)  # 側邊欄最大寬度
        
        splitter.addWidget(sidebar_container)
        splitter.addWidget(self.main_tab)
        
        # 設定 Splitter 初始分配比例（側邊欄 280px : 展示區 900px）
        splitter.setSizes([280, 900])

        # 主版面佈局加入 Splitter
        main_layout.addWidget(splitter)

        # 設定狀態列初始訊息
        self.status_bar.showMessage("系統就緒。當前分頁：即時示波器模式")

    # ==================== 分頁一：即時多通道示波器 ====================
    def _create_tab_oscilloscope(self):
        """
        建立即時多通道示波器分頁
        
        功能：
        - 顯示兩個同步的正弦波通道
        - 支援十字游標座標讀取
        - 兩通道 X 軸連動同步
        """
        # GraphicsLayoutWidget：PyQtGraph 的主要容器，支援多圖表佈局
        self.osc_widget = pg.GraphicsLayoutWidget()
        
        # 通道一：純正弦波
        self.p1 = self.osc_widget.addPlot(row=0, col=0, title="通道一：模擬正弦波 (CH1 Sine Wave)")
        self.p1.showGrid(x=True, y=True, alpha=0.25)  # 顯示網格，透明度 25%
        self.p1.setLabel('left', '振幅', units='V')    # Y 軸標籤
        self.p1.setLabel('bottom', '時間點', units='sample')  # X 軸標籤
        # 繪製曲線：玫瑰粉色、線寬 2
        self.curve1 = self.p1.plot(pen=pg.mkPen(color='#ec4899', width=2), name="CH1")

        # 通道二：含噪聲的正弦波
        self.p2 = self.osc_widget.addPlot(row=1, col=0, title="通道二：含噪聲波 (CH2 Sine + Noise)")
        self.p2.showGrid(x=True, y=True, alpha=0.25)
        self.p2.setLabel('left', '振幅', units='V')
        self.p2.setLabel('bottom', '時間點', units='sample')
        # 繪製曲線：薰衣草紫色、線寬 1.5
        self.curve2 = self.p2.plot(pen=pg.mkPen(color='#a78bfa', width=1.5), name="CH2")

        # X 軸連動：拖曳/縮放其中一個圖表時，另一個會同步
        self.p2.setXLink(self.p1)

        # ================== 十字游標（CH1） ==================
        # InfiniteLine：無限延伸的參考線，angle=90 為垂直線，angle=0 為水平線
        self.vLine1 = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#d4a0c0', width=1, style=Qt.DashLine))
        self.hLine1 = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#d4a0c0', width=1, style=Qt.DashLine))
        self.p1.addItem(self.vLine1, ignoreBounds=True)  # ignoreBounds=True 不影響自動縮放
        self.p1.addItem(self.hLine1, ignoreBounds=True)

        # ================== 十字游標（CH2） ==================
        self.vLine2 = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#d4a0c0', width=1, style=Qt.DashLine))
        self.hLine2 = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#d4a0c0', width=1, style=Qt.DashLine))
        self.p2.addItem(self.vLine2, ignoreBounds=True)
        self.p2.addItem(self.hLine2, ignoreBounds=True)

        # 座標文字標籤（顯示滑鼠位置的 X, Y 值）
        self.coord_label1 = pg.TextItem(anchor=(1, 0), color='#ec4899')  # 玫瑰粉
        self.coord_label2 = pg.TextItem(anchor=(1, 0), color='#a78bfa')  # 薰衣草紫
        self.p1.addItem(self.coord_label1)
        self.p2.addItem(self.coord_label2)

        # 滑鼠事件 Proxy：限流在 60Hz，避免密集觸發造成效能問題
        self.osc_mouse_proxy = pg.SignalProxy(
            self.osc_widget.scene().sigMouseMoved, 
            rateLimit=60, 
            slot=self.on_osc_mouse_moved
        )

        # 將此圖表容器加入分頁
        self.main_tab.addTab(self.osc_widget, "即時多通道示波器")

    def on_osc_mouse_moved(self, evt):
        """
        處理示波器分頁的滑鼠滑過事件
        
        功能：
        - 移動十字游標到滑鼠位置
        - 同步更新另一通道的垂直線
        - 在圖表右上角顯示座標數值
        """
        if not self.osc_crosshair_cb.isChecked():
            return  # 如果十字游標已關閉，直接返回
            
        pos = evt[0]  # 取得滑鼠位置（scene 座標）
        
        # 判斷滑鼠在哪個圖表的範圍內
        if self.p1.sceneBoundingRect().contains(pos):
            # 將場景座標轉換為圖表資料座標
            mouse_point = self.p1.vb.mapSceneToView(pos)
            x_val, y_val = mouse_point.x(), mouse_point.y()
            
            # 更新 CH1 十字線位置
            self.vLine1.setPos(x_val)
            self.hLine1.setPos(y_val)
            # 同步更新 CH2 的垂直線（因為 X 軸已鎖定連動）
            self.vLine2.setPos(x_val)
            
            # 更新座標顯示文字
            self.coord_label1.setText(f"X: {x_val:.1f}\nY: {y_val:.3f}")
            # 將文字定位在目前可見範圍的右上角
            x_range, y_range = self.p1.viewRange()
            self.coord_label1.setPos(x_range[1], y_range[1])
            
        elif self.p2.sceneBoundingRect().contains(pos):
            mouse_point = self.p2.vb.mapSceneToView(pos)
            x_val, y_val = mouse_point.x(), mouse_point.y()
            
            # 更新 CH2 十字線位置
            self.vLine2.setPos(x_val)
            self.hLine2.setPos(y_val)
            # 同步更新 CH1 的垂直線
            self.vLine1.setPos(x_val)
            
            # 更新座標顯示文字
            self.coord_label2.setText(f"X: {x_val:.1f}\nY: {y_val:.3f}")
            x_range, y_range = self.p2.viewRange()
            self.coord_label2.setPos(x_range[1], y_range[1])

    # ==================== 分頁二：互動式區間縮放 ====================
    def _create_tab_zoom(self):
        """
        建立互動式區間縮放分頁
        
        功能：
        - 上方：全局概覽圖，帶有可拖曳的半透明選取區間
        - 下方：局部放大圖，顯示選取範圍的詳細內容
        - 雙向同步：拖曳上方選取框 → 下方更新；縮放下方 → 上方選取框同步
        """
        self.zoom_widget = pg.GraphicsLayoutWidget()
        
        # 上方全局概覽圖
        self.p_overview = self.zoom_widget.addPlot(row=0, col=0, title="全局走勢 (請調整灰色半透明區間)")
        self.p_overview.showGrid(x=True, y=True, alpha=0.15)
        self.p_overview.setFixedHeight(180)  # 固定高度，避免視窗調整時變形
        
        # 下方局部放大圖
        self.p_detail = self.zoom_widget.addPlot(row=1, col=0, title="選取範圍局部放大 (雙向同步)")
        self.p_detail.showGrid(x=True, y=True, alpha=0.25)
        # 自訂 X 軸刻度線顏色
        self.p_detail.getAxis('bottom').setPen(pg.mkPen('#ec4899', width=1))

        # LinearRegionItem：可拖曳的半透明區域選擇器
        self.region = pg.LinearRegionItem([3000, 5000])  # 初始選取範圍
        self.region.setZValue(10)  # 設定 Z 軸層級，確保繪製在曲線上方
        self.p_overview.addItem(self.region)

        # 雙向同步信號綁定
        # 1. 上方選取區間改變 → 更新下方圖表 X 軸範圍
        self.region.sigRegionChanged.connect(self.sync_zoom_detail_plot)
        # 2. 下方圖表 X 軸範圍改變 → 反向更新上方選取區間
        self.p_detail.sigXRangeChanged.connect(self.sync_zoom_region_box)

        # 防止無限循環的鎖（sync_detail → region_changed → sync_region → detail_changed → ...）
        self.zoom_updating_lock = False

        self.main_tab.addTab(self.zoom_widget, "區間選取與縮放")

    def regenerate_zoom_data(self):
        """
        生成並重新繪製隨機走勢 (Random Walk) 趨勢線
        
        Random Walk 原理：
        - 每一步的位移服從常態分佈 N(0, 0.2)
        - 使用 cumsum() 累加得到隨機走勢路徑
        """
        # 使用當前時間作為隨機種子，確保每次生成不同
        np.random.seed(int(time.time()))
        steps = np.random.normal(0, 0.2, 10000)  # 10,000 個步進值
        self.zoom_data = steps.cumsum() + 50  # 累加並偏移到 50 附近

        # 清除舊的繪圖內容
        self.p_overview.clear()
        self.p_detail.clear()
        
        # 重新加入區域選擇器（clear() 會移除所有項目）
        self.p_overview.addItem(self.region)

        # 繪製新曲線
        self.p_overview.plot(self.zoom_data, pen=pg.mkPen('#d4a0c0', width=1))   # 概覽圖：淡玫瑰
        self.p_detail.plot(self.zoom_data, pen=pg.mkPen('#a78bfa', width=1.8))   # 放大圖：薰衣草紫
        
        # 重設選取範圍與顯示範圍
        self.region.setRegion([3000, 5000])
        self.sync_zoom_detail_plot()

    def sync_zoom_detail_plot(self):
        """
        將上方的 LinearRegionItem 位置同步到下方的詳細 Plot
        
        當使用者拖曳上方的半透明選取框時，下方圖表會自動縮放到對應範圍
        """
        if self.zoom_updating_lock:
            return  # 如果鎖已啟用，跳過以防止循環
        self.zoom_updating_lock = True
        min_x, max_x = self.region.getRegion()
        # 更新下方 X 軸範圍（padding=0 表示精確對齊）
        self.p_detail.setXRange(min_x, max_x, padding=0)
        self.zoom_updating_lock = False

    def sync_zoom_region_box(self):
        """
        當下方詳細 Plot 變更範圍時，逆向更新上方 LinearRegionItem 區間
        
        當使用者在下方圖表使用滾輪縮放或右鍵拖曳時，
        上方的半透明選取框會自動調整到對應位置
        """
        if self.zoom_updating_lock:
            return
        self.zoom_updating_lock = True
        # 取得下方 Plot 目前可見的 X 軸範圍
        min_x, max_x = self.p_detail.viewRange()[0]
        # 限制範圍不超出數據長度（避免索引越界）
        min_x = max(0, min_x)
        max_x = min(len(self.zoom_data), max_x)
        self.region.setRegion([min_x, max_x])
        self.zoom_updating_lock = False

    # ==================== 分頁三：即時 2D 漣漪干涉熱圖 ====================
    def _create_tab_heatmap(self):
        """
        建立即時 2D 熱圖分頁
        
        功能：
        - 模擬兩個點電荷波源的干涉圖樣
        - 即時計算並渲染 2D 強度矩陣
        - 支援色彩映射表切換與解析度調整
        - 右側 HistogramLUT 可即時調整對比度
        """
        self.heat_widget = pg.GraphicsLayoutWidget()
        
        # 建立 Plot 外框（用於放置 ImageItem）
        self.p_image = self.heat_widget.addPlot(row=0, col=0, title="波源干涉即時干涉圖 (2D ImageItem)")
        # 隱藏軸刻度，讓影像佔滿整個繪圖區
        self.p_image.showAxis('left', False)
        self.p_image.showAxis('bottom', False)

        # ImageItem：PyQtGraph 用於高效渲染 2D 陣列的核心物件
        self.image_item = pg.ImageItem()
        self.p_image.addItem(self.image_item)

        # HistogramLUTItem：右側的色彩條與強度調整器
        # 可以直接用滑鼠拖曳來調整影像對比度
        self.lut_item = pg.HistogramLUTItem()
        self.lut_item.setImageItem(self.image_item)  # 綁定到 ImageItem
        self.heat_widget.addItem(self.lut_item)

        # 預設使用 viridis 色彩映射表
        self.change_colormap("viridis")

        self.main_tab.addTab(self.heat_widget, "即時 2D 熱圖")

    def update_heatmap_grid(self):
        """
        根據解析度重新計算 2D 網格座標矩陣
        
        使用 np.meshgrid 產生 X, Y 座標矩陣，
        後續可用於計算每個網格點與波源的距離
        """
        res = self.heatmap_resolution
        # 在 [-15, 15] 範圍內生成解析度個均勻分佈點
        x = np.linspace(-15, 15, res)
        y = np.linspace(-15, 15, res)
        # meshgrid 回傳兩個 (res x res) 的矩陣
        self.heat_X, self.heat_Y = np.meshgrid(x, y)

    def change_colormap(self, name):
        """
        更換熱圖的色彩映射表
        
        支援的色彩映射表：
        - viridis: 綠黃漸變（預設，視覺友善）
        - plasma: 紅黃紫漸變
        - magma: 黑紅黃漸變
        - inferno: 黑紅黃漸變（更強烈）
        - turbo: 彩虹色
        - cividis: 藍黃漸變（色盲友善）
        """
        try:
            cmap = pg.colormap.get(name)
            self.lut_item.gradient.setColorMap(cmap)
        except Exception as e:
            print(f"更換色彩映射表失敗: {e}")

    def change_heatmap_resolution(self, index):
        """
        更換熱圖運算的解析度
        
        解析度越高 → 畫面越精細，但計算量越大
        """
        self.heatmap_resolution = self.resolution_combo.currentData()
        self.update_heatmap_grid()  # 重新計算網格
        self.status_bar.showMessage(f"解析度變更為: {self.heatmap_resolution} x {self.heatmap_resolution}")

    # ==================== 分頁四：互動式散佈圖 ====================
    def _create_tab_scatter(self):
        """
        建立互動式散佈圖分頁
        
        功能：
        - 顯示大量隨機分佈的散佈點
        - 滑鼠懸停時自動高亮最近的點
        - 點擊可鎖定特定點並顯示座標
        """
        self.scatter_widget = pg.GraphicsLayoutWidget()
        self.p_scatter = self.scatter_widget.addPlot(title="互動式散佈圖 (1,000隨機常態分佈點)")
        self.p_scatter.showGrid(x=True, y=True, alpha=0.2)
        
        # 點擊標記圈：用於標示使用者選取的點
        self.clicked_marker = pg.ScatterPlotItem(
            size=18, 
            pen=pg.mkPen('#e11d48', width=2),  # 玫瑰紅邊框
            brush=pg.mkBrush(None),              # 透明填充
            symbol='o'                           # 圓形符號
        )
        self.p_scatter.addItem(self.clicked_marker)
        self.clicked_marker.setVisible(False)  # 初始隱藏
        self.selected_point_idx = None         # 記錄目前選取的點索引

        # 滑鼠事件 Proxy：限流在 60Hz，偵測最近的點
        self.scatter_mouse_proxy = pg.SignalProxy(
            self.scatter_widget.scene().sigMouseMoved, 
            rateLimit=60, 
            slot=self.on_scatter_mouse_moved
        )

        self.main_tab.addTab(self.scatter_widget, "互動式散佈圖")

    def regenerate_scatter_data(self):
        """
        重新生成散佈圖數據
        
        使用常態分佈 (Gaussian Distribution) 生成隨機座標，
        預設中心在 (0,0)，標準差為 1.0
        """
        # 清除舊的繪圖內容
        self.p_scatter.clear()
        
        # 重新加入點選標記圈
        self.clicked_marker.setVisible(False)
        self.p_scatter.addItem(self.clicked_marker)
        self.selected_point_idx = None

        # 使用時間戳取模作為隨機種子，確保每次生成不同
        np.random.seed(int(time.time() * 100) % 10000)
        self.scatter_x = np.random.normal(0, 1.0, self.scatter_count)
        self.scatter_y = np.random.normal(0, 1.0, self.scatter_count)

        # ================== 建立高互動性 ScatterPlotItem ==================
        # 預設顏色：半透明粉紅
        s_color = pg.mkColor('#f472b6')
        s_color.setAlpha(150)  # 設定透明度 (0=全透明, 255=不透明)
        
        # 懸停時顏色：較不透明的玫瑰粉
        h_color = pg.mkColor('#ec4899')
        h_color.setAlpha(220)

        # hoverable=True：滑鼠移過時自動觸發 hover 事件
        # 並自動切換為 hoverBrush / hoverPen 的外觀
        self.scatter_item = pg.ScatterPlotItem(
            size=10, 
            pen=pg.mkPen('#ffffff', width=0.5),  # 白色細邊框
            brush=pg.mkBrush(s_color),
            hoverable=True,
            hoverBrush=pg.mkBrush(h_color),      # 懸停時的填充色
            hoverPen=pg.mkPen('#be185d', width=1.5)  # 懸停時的邊框色
        )
        
        # 封裝每個點的座標與索引資訊
        spots = [{'pos': (self.scatter_x[i], self.scatter_y[i]), 'data': i} for i in range(self.scatter_count)]
        self.scatter_item.addPoints(spots)
        
        # 綁定點擊事件：當任一點被點擊時觸發 on_scatter_clicked
        self.scatter_item.sigClicked.connect(self.on_scatter_clicked)
        
        self.p_scatter.addItem(self.scatter_item)
        self.p_scatter.setTitle(f"互動式散佈圖 (共 {self.scatter_count:,} 點)")

    def change_scatter_count(self, index):
        """切換散佈圖點的數量並重新生成資料"""
        self.scatter_count = self.scatter_count_combo.currentData()
        self.regenerate_scatter_data()
        self.status_bar.showMessage(f"已隨機生成 {self.scatter_count:,} 個常態分佈點，已備妥以測試效能！")

    def on_scatter_clicked(self, item, points):
        """
        當使用者點選散佈圖的任一點時
        
        功能：
        - 在該點位置顯示紅色環狀標記圈
        - 在狀態列永久顯示該點的座標資訊
        """
        if not points:
            return
        
        # 取得點擊到的第一個點資訊
        point = points[0]
        pos = point.pos()    # 取得座標 (QPointF)
        idx = point.data()   # 取得索引（在 regenerate_scatter_data 中設定）
        
        self.selected_point_idx = idx
        
        # 在該點位置顯示紅色標記圈
        self.clicked_marker.setData(x=[pos.x()], y=[pos.y()])
        self.clicked_marker.setVisible(True)
        
        # 在狀態列顯示選取資訊
        msg = f"選取點編號: {idx} | 座標: ({pos.x():.4f}, {pos.y():.4f})"
        self.status_bar.showMessage(msg)

    def on_scatter_mouse_moved(self, evt):
        """
        偵測滑鼠位置並提示最近點的座標
        
        使用 numpy 向量化運算快速計算歐氏距離，
        當滑鼠足夠靠近某點時（距離 < 0.18），顯示該點資訊
        """
        pos = evt[0]
        if self.p_scatter.sceneBoundingRect().contains(pos):
            mouse_point = self.p_scatter.vb.mapSceneToView(pos)
            
            # 向量化計算：一次算出滑鼠到所有點的距離平方
            distances = (self.scatter_x - mouse_point.x())**2 + (self.scatter_y - mouse_point.y())**2
            nearest_idx = np.argmin(distances)  # 找出最近的點索引
            min_dist = np.sqrt(distances[nearest_idx])  # 計算實際距離
            
            # 滑鼠必須足夠靠近該點（在 0.18 單位內）
            if min_dist < 0.18:
                x_val = self.scatter_x[nearest_idx]
                y_val = self.scatter_y[nearest_idx]
                
                # 如果該點就是已選取的點，就不重複更新
                if self.selected_point_idx == nearest_idx:
                    return
                self.status_bar.showMessage(f"懸停點編號: {nearest_idx} | 座標: ({x_val:.4f}, {y_val:.4f})")
            else:
                # 滑鼠移開時，恢復顯示已選取的點或一般提示
                if self.selected_point_idx is not None:
                    pos_x = self.scatter_x[self.selected_point_idx]
                    pos_y = self.scatter_y[self.selected_point_idx]
                    self.status_bar.showMessage(f"選取點編號: {self.selected_point_idx} | 座標: ({pos_x:.4f}, {pos_y:.4f})")
                else:
                    self.status_bar.showMessage("互動式散佈圖：滑鼠懸停顯示最近點，左鍵點擊可鎖定點。")

    # ==================== 動態更新核心 ====================
    def update_plots(self):
        """
        定時更新圖表（核心主迴圈）
        
        此函數由 QTimer 每 16ms（60 FPS）觸發一次，
        根據當前作用中的分頁，更新對應的圖表數據
        
        效能關鍵：
        - 使用 setData() 而非重繪，實現高效更新
        - 只更新當前可見的分頁，節省 CPU 資源
        """
        # ================== FPS 計算 ==================
        current_time = time.time()
        dt = current_time - self.last_time  # 計算時間差（秒）
        self.last_time = current_time
        
        if dt > 0:
            self.fps_buffer.append(1.0 / dt)  # 計算瞬時 FPS
            if len(self.fps_buffer) > 40:     # 保留最近 40 筆
                self.fps_buffer.pop(0)
            avg_fps = sum(self.fps_buffer) / len(self.fps_buffer)  # 計算平均 FPS
            self.fps_display.setText(f"實測刷新率: {avg_fps:.1f} FPS")

        # 如果暫停按鈕已按下，跳過數據更新（但 FPS 計算仍繼續）
        if self.play_pause_btn.isChecked():
            return

        # 取得當前作用中的分頁索引
        active_tab = self.main_tab.currentIndex()

        # ================== 分頁一：即時示波器更新 ==================
        if active_tab == 0:
            self.time_offset += 0.05  # 時間累加，控制波形移動速度
            
            # 生成 500 個點的時間軸
            x = np.arange(500)
            
            # 通道一：純正弦波 y = A * sin(x * w + phi)
            # phi 隨時間增加，實現波形向右移動的效果
            phi1 = self.time_offset * self.oscilloscope_freq1
            y1 = self.oscilloscope_amp * np.sin(x * 0.05 + phi1)
            
            # 通道二：正弦波 + 高斯噪聲
            phi2 = self.time_offset * self.oscilloscope_freq2
            noise = np.random.normal(0, self.oscilloscope_noise, size=len(x))
            y2 = self.oscilloscope_amp * np.sin(x * 0.04 + phi2) + noise
            
            # setData() 是 PyQtGraph 的高效更新方法
            # 相比 matplotlib 的重繪機制，速度提升數十倍
            self.curve1.setData(x, y1)
            self.curve2.setData(x, y2)

        # ================== 分頁三：即時 2D 熱圖更新 ==================
        elif active_tab == 2:
            self.heatmap_t += 0.12 * self.heatmap_speed  # 時間累加
            
            # 建立兩個動態旋轉的點電荷波源
            # 波源位置隨時間做圓周運動
            x1 = 5.0 * np.sin(self.heatmap_t * 0.7)
            y1 = 5.0 * np.cos(self.heatmap_t * 0.4)
            x2 = -5.0 * np.sin(self.heatmap_t * 0.5)
            y2 = -5.0 * np.cos(self.heatmap_t * 0.8)
            
            # 計算每個網格點到兩個波源的歐式距離
            dist1 = np.sqrt((self.heat_X - x1)**2 + (self.heat_Y - y1)**2)
            dist2 = np.sqrt((self.heat_X - x2)**2 + (self.heat_Y - y2)**2)
            
            # 波的疊加方程式：
            # wave = sin(k * r - omega * t) / (r + damping)
            # k=1.8: 波數（控制波長）
            # r + 1.2: 距離衰減項（避免除以零）
            wave1 = np.sin(1.8 * dist1 - self.heatmap_t) / (dist1 + 1.2)
            wave2 = np.sin(1.8 * dist2 - self.heatmap_t) / (dist2 + 1.2)
            z = wave1 + wave2  # 雙波源疊加（干涉）
            
            # setImage()：高效渲染 2D 矩陣為影像
            self.image_item.setImage(z)

    # ==================== 控制面板信號處理 ==================
    @Slot(int)
    def on_tab_changed(self, index):
        """
        當主要展示分頁切換時，同步切換左側控制面板
        
        使用 QStackedWidget 的 setCurrentIndex() 實現
        控制面板與展示分頁的對應關係
        """
        self.param_stack.setCurrentIndex(index)
        
        # 更新狀態列顯示
        tab_names = ["即時示波器模式", "區間選取與縮放模式", "即時 2D 熱圖模式", "互動式散佈圖模式"]
        self.status_bar.showMessage(f"切換至: {tab_names[index]}")

        # 切換到熱圖分頁時，確認網格已初始化
        if index == 2:
            if not hasattr(self, 'heat_X'):
                self.update_heatmap_grid()

    @Slot()
    def toggle_play_pause(self):
        """
        暫停/恢復即時動畫更新
        
        暫停時：Timer 繼續運行（FPS 計算與滑鼠互動仍正常），
        但跳過波形數據更新
        """
        paused = self.play_pause_btn.isChecked()
        if paused:
            self.play_pause_btn.setText("恢復即時渲染")
            self.status_bar.showMessage("已暫停即時繪圖更新")
        else:
            self.play_pause_btn.setText("暫停即時渲染")
            self.status_bar.showMessage("已恢復即時繪圖更新")
            self.last_time = time.time()  # 重設時間基準，避免 dt 過大

    @Slot(int)
    def change_target_fps(self, value):
        """
        調整 QTimer 觸發頻率以改變目標 FPS
        
        interval_ms = 1000 / value
        例如：60 FPS → 16ms, 30 FPS → 33ms
        """
        self.fps_slider_label.setText(f"目標刷新率: {value} FPS")
        interval_ms = int(1000 / value)
        self.fps_timer.setInterval(interval_ms)
        self.status_bar.showMessage(f"已調整目標刷新率為: {value} Hz (~{interval_ms} 毫秒間隔)")

    @Slot(int)
    def toggle_antialias(self, state):
        """
        開關全域抗鋸齒
        
        抗鋸齒可讓線條更平滑，但在某些顯卡上可能影響效能
        """
        enabled = (state == Qt.Checked.value)
        pg.setConfigOptions(antialias=enabled)
        self.status_bar.showMessage(f"全域抗鋸齒選項已變更為: {enabled}")

    @Slot()
    def update_osc_params(self):
        """同步示波器控制面板的滑桿數值到內部變數"""
        # 滑桿值除以 10 得到實際頻率
        self.oscilloscope_freq1 = self.osc_freq1_slider.value() / 10.0
        self.oscilloscope_freq2 = self.osc_freq2_slider.value() / 10.0
        self.oscilloscope_noise = self.osc_noise_slider.value() / 10.0
        
        # 更新標籤文字顯示
        self.osc_freq1_label.setText(f"通道一頻率: {self.oscilloscope_freq1:.1f} Hz")
        self.osc_freq2_label.setText(f"通道二頻率: {self.oscilloscope_freq2:.1f} Hz")
        self.osc_noise_label.setText(f"通道二噪聲: {self.oscilloscope_noise:.1f}")

    @Slot(int)
    def toggle_osc_grid(self, state):
        """開關示波器的背景格線"""
        show = (state == Qt.Checked.value)
        self.p1.showGrid(x=show, y=show, alpha=0.25 if show else 0)
        self.p2.showGrid(x=show, y=show, alpha=0.25 if show else 0)
        self.status_bar.showMessage(f"顯示格線: {show}")

    @Slot(int)
    def toggle_osc_crosshair(self, state):
        """隱藏或顯示示波器的十字游標與座標標籤"""
        show = (state == Qt.Checked.value)
        self.vLine1.setVisible(show)
        self.hLine1.setVisible(show)
        self.vLine2.setVisible(show)
        self.hLine2.setVisible(show)
        self.coord_label1.setVisible(show)
        self.coord_label2.setVisible(show)
        
        if not show:
            self.status_bar.showMessage("已隱藏十字坐標游標")
        else:
            self.status_bar.showMessage("已啟用十字坐標游標（滑鼠移入波形圖即可顯示座標）")

    @Slot()
    def update_heat_params(self):
        """同步熱圖控制面板的滑桿數值到內部變數"""
        self.heatmap_speed = self.heat_speed_slider.value() / 10.0
        self.heat_speed_label.setText(f"波動演進速度: {self.heatmap_speed:.1f}x")


# ==================== 程式進入點 ====================
def main():
    """
    主程式啟動入口
    
    建立 QApplication → 設定字型 → 建立並顯示主視窗 → 進入事件迴圈
    """
    # 建立 Qt 應用程式實例（每個 Qt 程式只能有一個 QApplication）
    app = QApplication(sys.argv)
    
    # 設定全域預設字型
    # 使用系統預設無襯線字體，解決高 DPI 螢幕字型鋸齒問題
    font = QFont(".AppleSystemUIFont", 10)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)

    # 建立主視窗並顯示
    window = PyQtGraphDemoApp()
    window.show()
    
    # 進入 Qt 事件迴圈，等待使用者互動
    # sys.exit() 確保程式正確退出並釋放資源
    sys.exit(app.exec())


# 確保直接執行此檔案時才呼叫 main()
# 如果是被其他模組 import，則不自動執行
if __name__ == "__main__":
    main()
