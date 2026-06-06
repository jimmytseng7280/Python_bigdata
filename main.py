import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from datetime import datetime


def create_text_report_pdf(filename="report.pdf", title="報告", content=""):
    """
    建立簡單的文字報告PDF
    
    參數：
        filename: PDF檔案名稱
        title: 報告標題
        content: 報告內容（字串）
    """
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # 自訂標題樣式
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=30,
        alignment=1  # 置中
    )
    
    # 建立內容
    elements = []
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(f"<b>產生時間：</b>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(content, styles['BodyText']))
    
    # 產生PDF
    doc.build(elements)
    print(f"✓ 已產生PDF報告：{filename}")


def create_dataframe_pdf(df, filename="data_report.pdf", title="資料統計報表"):
    """
    將DataFrame轉換為PDF報表
    
    參數：
        df: pandas DataFrame
        filename: PDF檔案名稱
        title: 報表標題
    """
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=20,
        alignment=1
    )
    
    elements = []
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 12))
    
    # 將DataFrame轉換為表格資料
    table_data = [list(df.columns)] + df.values.tolist()
    
    # 建立表格
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),  # 標題列背景色
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # 標題列文字色
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # 置中
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # 標題列加粗
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),  # 加入網格線
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),  # 行交替背景色
    ]))
    
    elements.append(table)
    
    # 產生PDF
    doc.build(elements)
    print(f"✓ 已產生DataFrame PDF報表：{filename}")


def main():
    print("Hello from python-bigdata!")
    
    # 示例1：建立簡單文字報告PDF
    sample_content = """
    <b>這是一個簡單的PDF報告示例。</b><br/><br/>
    您可以在此添加任何文字內容。<br/>
    支援HTML格式化。<br/><br/>
    <b>功能特色：</b><br/>
    • 支援中文文字<br/>
    • 靈活的樣式設定<br/>
    • 自動分頁
    """
    
    create_text_report_pdf(
        filename="sample_report.pdf",
        title="示例報告",
        content=sample_content
    )
    
    # 示例2：建立DataFrame PDF報表
    sample_df = pd.DataFrame({
        '項目': ['A', 'B', 'C', 'D'],
        '數量': [100, 200, 150, 300],
        '金額': [1000, 2000, 1500, 3000],
        '備註': ['合格', '優秀', '合格', '優秀']
    })
    
    create_dataframe_pdf(
        df=sample_df,
        filename="sample_data_report.pdf",
        title="銷售資料統計"
    )


if __name__ == "__main__":
    main()
