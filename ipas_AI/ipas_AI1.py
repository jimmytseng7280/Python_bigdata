import os
import re
import json
import time
import sqlite3
import certifi
import urllib3
import requests
import pandas as pd

from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote, unquote
from pypdf import PdfReader


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ==========================
# 基本設定
# ==========================

OUTPUT_DIR = "ipas_AI應用規劃師初級_題庫資料庫"
PDF_DIR = os.path.join(OUTPUT_DIR, "pdf")
TXT_DIR = os.path.join(OUTPUT_DIR, "txt")

CSV_FILE = os.path.join(OUTPUT_DIR, "ipas_AI初級_題庫.csv")
JSON_FILE = os.path.join(OUTPUT_DIR, "ipas_AI初級_題庫.json")
DB_FILE = os.path.join(OUTPUT_DIR, "ipas_AI初級_題庫.sqlite")

OFFICIAL_PAGE = "https://ipd.nat.gov.tw/ipas/certification/AIAP/learning-resources"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}

SEARCH_KEYWORDS = [
    "iPAS AI應用規劃師 初級 題庫 解答 解析",
    "iPAS AI應用規劃師 初級 公告試題 答案",
    "AI應用規劃師 初級 人工智慧基礎概論 題目 答案",
    "AI應用規劃師 初級 生成式AI應用與規劃 題目 答案",
    "115年 第一次 初級 AI應用規劃師 公告試題 答案",
    "114年 第四次 初級 AI應用規劃師 公告試題 答案",
]

BLOCKED_KEYWORDS = [
    "login",
    "member",
    "cart",
    "checkout",
    "mosme",
    "books.com.tw",
    "tenlong",
    "eslite",
    "wunan",
    "pay",
    "paid",
    "app",
]


# ==========================
# 建立資料夾
# ==========================

def make_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(TXT_DIR, exist_ok=True)


# ==========================
# 檔名清理
# ==========================

def clean_filename(name: str) -> str:
    name = unquote(name)
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = name.replace("%", "_")
    return name.strip()


# ==========================
# 安全 GET
# ==========================

def get_response(url: str):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
            verify=certifi.where()
        )
        response.raise_for_status()
        return response

    except requests.exceptions.SSLError:
        print(f"SSL 驗證失敗，改用備援模式：{url}")

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
            verify=False
        )
        response.raise_for_status()
        return response

    except Exception as e:
        print(f"讀取失敗：{url}")
        print(f"原因：{e}")
        return None


# ==========================
# 取得 HTML
# ==========================

def get_html(url: str) -> str:
    response = get_response(url)

    if response is None:
        return ""

    response.encoding = response.apparent_encoding
    return response.text


# ==========================
# 下載 PDF
# ==========================

def download_pdf(url: str):
    response = get_response(url)

    if response is None:
        return None

    filename = clean_filename(url.split("/")[-1])

    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    filepath = os.path.join(PDF_DIR, filename)

    if os.path.exists(filepath):
        print(f"PDF 已存在：{filename}")
        return filepath

    with open(filepath, "wb") as f:
        f.write(response.content)

    print(f"PDF 下載完成：{filename}")
    time.sleep(1)

    return filepath


# ==========================
# 官方學習資源頁抓 PDF
# ==========================

def crawl_official_pdf_links():
    print("正在讀取 iPAS 官方學習資源頁...")

    html = get_html(OFFICIAL_PAGE)

    pdf_urls = []

    if html:
        soup = BeautifulSoup(html, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"]

            if ".pdf" in href.lower():
                full_url = urljoin(OFFICIAL_PAGE, href)

                if "AI" in full_url or "ai" in full_url:
                    pdf_urls.append(full_url)

    # 備援：直接加入目前常見官方 PDF
    backup_urls = [
        "https://www.ipas.org.tw/api/proxy/uploads/certification_resource/bf93f438f7be48d295c1b40a34d79f3d/115%E5%B9%B4%E7%AC%AC%E4%B8%80%E6%AC%A1%E5%88%9D%E7%B4%9AAI%E6%87%89%E7%94%A8%E8%A6%8F%E5%8A%83%E5%B8%AB_%E7%AC%AC%E4%B8%80%E7%A7%91_%E4%BA%BA%E5%B7%A5%E6%99%BA%E6%85%A7%E5%9F%BA%E7%A4%8E%E6%A6%82%E8%AB%96_%E5%85%AC%E5%91%8A%E8%A9%A6%E9%A1%8C_20260410164304.pdf",
        "https://www.ipas.org.tw/api/proxy/uploads/certification_resource/bf93f438f7be48d295c1b40a34d79f3d/115%E5%B9%B4%E7%AC%AC%E4%B8%80%E6%AC%A1%E5%88%9D%E7%B4%9AAI%E6%87%89%E7%94%A8%E8%A6%8F%E5%8A%83%E5%B8%AB_%E7%AC%AC%E4%BA%8C%E7%A7%91_%E7%94%9F%E6%88%90%E5%BC%8FAI%E6%87%89%E7%94%A8%E8%88%87%E8%A6%8F%E5%8A%83_%E5%85%AC%E5%91%8A%E8%A9%A6%E9%A1%8C_20260410164328.pdf",
    ]

    pdf_urls.extend(backup_urls)

    pdf_urls = list(dict.fromkeys(pdf_urls))

    print(f"找到官方 PDF 數量：{len(pdf_urls)}")

    return pdf_urls


# ==========================
# PDF 轉文字
# ==========================

def pdf_to_text(pdf_path: str) -> str:
    text = ""

    try:
        reader = PdfReader(pdf_path)

        for page in reader.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

        txt_name = clean_filename(os.path.basename(pdf_path)) + ".txt"
        txt_path = os.path.join(TXT_DIR, txt_name)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        return text

    except Exception as e:
        print(f"PDF 轉文字失敗：{pdf_path}")
        print(e)
        return ""


# ==========================
# DuckDuckGo 搜尋公開網頁
# ==========================

def search_duckduckgo(keyword: str, max_results: int = 10):
    print(f"搜尋：{keyword}")

    search_url = f"https://duckduckgo.com/html/?q={quote(keyword)}"
    html = get_html(search_url)

    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    urls = []

    for a in soup.select("a.result__a"):
        href = a.get("href")

        if href and href.startswith("http"):
            urls.append(href)

    urls = list(dict.fromkeys(urls))

    return urls[:max_results]


# ==========================
# 判斷是否略過
# ==========================

def should_skip_url(url: str) -> bool:
    lower_url = url.lower()

    for word in BLOCKED_KEYWORDS:
        if word in lower_url:
            return True

    return False


# ==========================
# 讀取公開網頁文字
# ==========================

def crawl_public_page_text(url: str) -> str:
    html = get_html(url)

    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    text = soup.get_text("\n")
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    time.sleep(1)

    return text


# ==========================
# 解析題目、選項、答案、解析
# ==========================

def parse_questions(text: str, source_name: str, source_url: str):
    results = []

    text = text.replace("（", "(").replace("）", ")")
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)

    blocks = re.split(r"(?=\n?\d{1,3}[\.、])", text)

    for block in blocks:
        block = block.strip()

        if len(block) < 30:
            continue

        number_match = re.match(r"(\d{1,3})[\.、]\s*", block)

        if not number_match:
            continue

        question_number = number_match.group(1)

        answer = ""
        explanation = ""

        answer_patterns = [
            r"答案[:：]\s*([ABCD])",
            r"解答[:：]\s*([ABCD])",
            r"正解[:：]\s*([ABCD])",
            r"^\s*([ABCD])\s+\d{1,3}[\.、]",
        ]

        for p in answer_patterns:
            m = re.search(p, block, flags=re.I | re.M)
            if m:
                answer = m.group(1).upper()
                break

        explanation_patterns = [
            r"解析[:：](.*)",
            r"詳解[:：](.*)",
            r"說明[:：](.*)",
        ]

        for p in explanation_patterns:
            m = re.search(p, block, flags=re.S)
            if m:
                explanation = m.group(1).strip()
                break

        options = {
            "A": "",
            "B": "",
            "C": "",
            "D": ""
        }

        option_matches = re.findall(
            r"\(([ABCD])\)\s*(.*?)(?=\([ABCD]\)|答案[:：]|解答[:：]|解析[:：]|詳解[:：]|說明[:：]|\Z)",
            block,
            flags=re.S | re.I
        )

        for opt, value in option_matches:
            opt = opt.upper()
            value = re.sub(r"\s+", " ", value).strip()
            options[opt] = value

        question_text = block

        question_text = re.sub(r"答案[:：]\s*[ABCD].*", "", question_text, flags=re.S | re.I)
        question_text = re.sub(r"解答[:：]\s*[ABCD].*", "", question_text, flags=re.S | re.I)
        question_text = re.sub(r"解析[:：].*", "", question_text, flags=re.S)
        question_text = re.sub(r"詳解[:：].*", "", question_text, flags=re.S)

        question_text = re.split(r"\(A\)", question_text)[0]
        question_text = re.sub(r"^\d{1,3}[\.、]\s*", "", question_text)
        question_text = re.sub(r"\s+", " ", question_text).strip()

        if len(question_text) < 10:
            continue

        results.append({
            "題號": question_number,
            "題目": question_text,
            "A": options["A"],
            "B": options["B"],
            "C": options["C"],
            "D": options["D"],
            "答案": answer,
            "解析": explanation,
            "來源名稱": source_name,
            "來源網址": source_url
        })

    return results


# ==========================
# 存 CSV / JSON
# ==========================

def save_csv_json(rows):
    if not rows:
        print("沒有題目可存檔")
        return

    df = pd.DataFrame(rows)

    df.drop_duplicates(
        subset=["題目", "A", "B", "C", "D"],
        inplace=True
    )

    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(
            df.to_dict(orient="records"),
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"CSV 已存檔：{CSV_FILE}")
    print(f"JSON 已存檔：{JSON_FILE}")
    print(f"總題數：{len(df)}")


# ==========================
# 存 SQLite
# ==========================

def save_sqlite(rows):
    if not rows:
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_no TEXT,
            question TEXT,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            answer TEXT,
            explanation TEXT,
            source_name TEXT,
            source_url TEXT
        )
    """)

    cursor.execute("DELETE FROM questions")

    for row in rows:
        cursor.execute("""
            INSERT INTO questions (
                question_no,
                question,
                option_a,
                option_b,
                option_c,
                option_d,
                answer,
                explanation,
                source_name,
                source_url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.get("題號", ""),
            row.get("題目", ""),
            row.get("A", ""),
            row.get("B", ""),
            row.get("C", ""),
            row.get("D", ""),
            row.get("答案", ""),
            row.get("解析", ""),
            row.get("來源名稱", ""),
            row.get("來源網址", "")
        ))

    conn.commit()
    conn.close()

    print(f"SQLite 已存檔：{DB_FILE}")


# ==========================
# 主程式
# ==========================

def main():
    make_dirs()

    all_questions = []
    visited_urls = set()

    print("=" * 60)
    print("一、下載與解析 iPAS 官方 PDF")
    print("=" * 60)

    official_pdf_urls = crawl_official_pdf_links()

    for pdf_url in official_pdf_urls:
        pdf_path = download_pdf(pdf_url)

        if not pdf_path:
            continue

        text = pdf_to_text(pdf_path)

        questions = parse_questions(
            text=text,
            source_name=os.path.basename(pdf_path),
            source_url=pdf_url
        )

        print(f"解析題數：{len(questions)}")

        all_questions.extend(questions)

    print("=" * 60)
    print("二、搜尋公開網頁題庫、答案、解析")
    print("=" * 60)

    for keyword in SEARCH_KEYWORDS:
        urls = search_duckduckgo(keyword, max_results=10)

        for url in urls:
            if url in visited_urls:
                continue

            visited_urls.add(url)

            if should_skip_url(url):
                print(f"略過登入、付費或授權內容頁：{url}")
                continue

            print(f"讀取公開來源：{url}")

            if url.lower().endswith(".pdf"):
                pdf_path = download_pdf(url)

                if not pdf_path:
                    continue

                text = pdf_to_text(pdf_path)
                source_name = os.path.basename(pdf_path)

            else:
                text = crawl_public_page_text(url)
                source_name = "公開網頁"

            questions = parse_questions(
                text=text,
                source_name=source_name,
                source_url=url
            )

            print(f"解析題數：{len(questions)}")

            all_questions.extend(questions)

    print("=" * 60)
    print("三、存檔")
    print("=" * 60)

    save_csv_json(all_questions)
    save_sqlite(all_questions)

    print("=" * 60)
    print("完成")
    print("=" * 60)


if __name__ == "__main__":
    main()