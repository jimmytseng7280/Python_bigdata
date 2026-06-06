"""
TP_PMT_attachment_crawler_2023_2026.py

台灣電力公司「亭置式變壓器」各容量規格得標資料爬蟲
版本：附件下載強化版

納入功能：
1. 多來源搜尋案件
   - taiwanbuying.com.tw
   - cf.ezbid.tw
   - web.pcc.gov.tw / pcc.gov.tw
   - DuckDuckGo / Bing 搜尋結果

2. 自動收集案號與候選網址

3. 自動嘗試抓明細頁
   - 品項名稱
   - 得標廠商
   - 預估需求數量
   - 原產地國別得標金額
   - 得標廠商原始投標金額

4. 自動下載附件
   - PDF
   - XLS / XLSX
   - ODS
   - CSV
   - TXT
   - DOC / DOCX 若有安裝 python-docx 可讀 DOCX

5. 解析附件中的容量規格
   - 25kVA
   - 37.5kVA
   - 50kVA
   - 75kVA
   - 100kVA
   - 167kVA
   - 250kVA
   - 333kVA
   - 500kVA

6. 輸出 Excel
   - 原始品項資料
   - 附件解析資料
   - 合併後資料庫
   - 指定容量單價
   - 容量規格統計
   - 年度容量平均單價
   - 廠商容量平均單價
   - 候選案件
   - 附件清單
   - 待人工確認
   - 執行紀錄

安裝基本套件：
pip install requests beautifulsoup4 pandas openpyxl lxml pdfplumber odfpy

建議加裝：
pip install python-docx

若要 OCR 圖片型 PDF：
1. 安裝 Tesseract OCR
2. 安裝 Poppler
3. pip install pytesseract pdf2image pillow

執行：
python TP_PMT_attachment_crawler_2023_2026.py
"""

import re
import time
import random
import hashlib
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse, parse_qs, unquote

import requests
import pandas as pd
from bs4 import BeautifulSoup


# ============================================================
# 基本設定
# ============================================================

YEARS = [2023, 2024, 2025, 2026]

KEYWORDS = [
    "亭置式變壓器",
    "亭置式 變壓器",
    "亭置變壓器",
    "台電 亭置式變壓器",
    "台灣電力 亭置式變壓器",
    "pad mounted transformer Taipower",
]

TARGET_CAPACITIES = [25, 37.5, 50, 75, 100, 167, 250, 333, 500]

TAIPOWER_ORG_ID = "2971"

EZBID_PATHS = [
    "3.13.31",
    "3.13.32",
    "3.13.33",
]

SEED_CASE_NOS = [
    "0081400078",
    "0081500019",
    "0081500027",
    "0081500032",
    "0081500037",
    "0141500021",
]

OUTPUT_DIR = Path("taipower_pmt_attachment_output")
ATTACH_DIR = OUTPUT_DIR / "attachments"
OUTPUT_DIR.mkdir(exist_ok=True)
ATTACH_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.7",
}

ATTACHMENT_EXTS = (
    ".pdf", ".xls", ".xlsx", ".ods", ".csv", ".txt", ".doc", ".docx"
)


# ============================================================
# 通用工具
# ============================================================

def polite_sleep(base=1.0):
    time.sleep(base + random.random())


def fetch_html(url, encoding=None, retry=3, timeout=35):
    last_error = ""
    for i in range(retry):
        try:
            print(f"爬取：{url}")
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
            if encoding:
                response.encoding = encoding
            else:
                response.encoding = response.apparent_encoding or "utf-8"
            return response.text, str(response.url), ""
        except Exception as e:
            last_error = str(e)
            print(f"失敗第 {i + 1} 次：{last_error}")
            time.sleep(2 + i)
    return "", url, last_error


def fetch_binary(url, retry=3, timeout=60):
    last_error = ""
    for i in range(retry):
        try:
            print(f"下載附件：{url}")
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
            return response.content, str(response.url), response.headers.get("content-type", ""), ""
        except Exception as e:
            last_error = str(e)
            print(f"附件下載失敗第 {i + 1} 次：{last_error}")
            time.sleep(2 + i)
    return b"", url, "", last_error


def html_to_soup_lines(html):
    soup = BeautifulSoup(html, "html.parser")
    lines = [x.strip() for x in soup.get_text("\n", strip=True).split("\n") if x.strip()]
    text = "\n".join(lines)
    return soup, lines, text


def unwrap_search_url(url):
    if not url:
        return ""
    url = unquote(url)
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "uddg" in qs and qs["uddg"]:
        return qs["uddg"][0]
    if "u" in qs and qs["u"]:
        return qs["u"][0]
    return url


def is_interesting_text(text):
    s = str(text)
    return (
        ("亭置式" in s and "變壓器" in s)
        or "亭置式變壓器" in s
        or "亭置變壓器" in s
        or "pad mounted transformer" in s.lower()
    )


def extract_case_no(text):
    m = re.search(r"\b\d{10}\b", str(text))
    return m.group(0) if m else ""


def extract_all_case_nos(text):
    return sorted(set(re.findall(r"\b\d{10}\b", str(text))))


def make_ezbid_urls(case_no):
    if not case_no:
        return []
    return [f"https://cf.ezbid.tw/detail/{path}/{case_no}" for path in EZBID_PATHS]


def money_to_int(text):
    if text is None:
        return None
    s = str(text)
    s = s.replace("新臺幣", "").replace("新台幣", "")
    s = s.replace("台幣", "").replace("NT$", "")
    s = s.replace("$", "").replace("元", "")
    m = re.search(r"[\d,]+", s)
    if not m:
        return None
    return int(m.group().replace(",", ""))


def qty_to_float(text):
    if text is None:
        return None
    m = re.search(r"[\d,]+(?:\.\d+)?", str(text))
    if not m:
        return None
    return float(m.group().replace(",", ""))


def roc_date_to_ad(text):
    m = re.search(r"(\d{2,3})/(\d{1,2})/(\d{1,2})", str(text))
    if not m:
        return ""
    y, mo, d = map(int, m.groups())
    if y < 1911:
        y += 1911
    return f"{y:04d}/{mo:02d}/{d:02d}"


def extract_year(ad_date, roc_text=""):
    if ad_date:
        m = re.search(r"(\d{4})", str(ad_date))
        if m:
            return int(m.group(1))
    m = re.search(r"(\d{2,3})/(\d{1,2})/(\d{1,2})", str(roc_text))
    if m:
        y = int(m.group(1))
        if y < 1911:
            y += 1911
        return y
    return None


def normalize_item_name(text):
    s = str(text or "").strip()
    s = re.sub(r"\s+", " ", s)
    replace_map = {
        "ＫＶＡ": "kVA", "KVA": "kVA", "kva": "kVA",
        "ＫＶ": "kV", "KV": "kV", "kv": "kV",
        "仟伏安": "kVA",
    }
    for old, new in replace_map.items():
        s = s.replace(old, new)
    return s


def normalize_vendor(text):
    s = str(text or "").strip()
    s = re.sub(r"^.*得標廠商", "", s)
    s = re.sub(r"^.*廠商名稱", "", s)
    return s.strip(" ：:")


def extract_capacity_kva(text):
    s = normalize_item_name(text)
    patterns = [
        r"(\d+(?:\.\d+)?)\s*kVA",
        r"(\d+(?:\.\d+)?)\s*仟伏安",
    ]
    for p in patterns:
        m = re.search(p, s, re.I)
        if m:
            value = float(m.group(1))
            return int(value) if value.is_integer() else value
    return None


def extract_voltage(text):
    s = normalize_item_name(text)
    m = re.search(r"(\d+\.?\d*)\s*/\s*(\d+\.?\d*)\s*kV", s, re.I)
    if m:
        return f"{m.group(1)}/{m.group(2)}kV"
    m = re.search(r"(\d+\.?\d*)\s*kV", s, re.I)
    if m:
        return f"{m.group(1)}kV"
    return ""


def capacity_label(capacity):
    if capacity is None:
        return ""
    value = float(capacity)
    if value.is_integer():
        return f"{int(value)}kVA"
    return f"{value:g}kVA"


def hash_text(s):
    return hashlib.md5(str(s).encode("utf-8")).hexdigest()[:12]


# ============================================================
# 候選案件收集
# ============================================================

def add_candidate(candidates, source, url, case_no="", year="", original_page="", original_text=""):
    if not url or not str(url).startswith("http"):
        return
    candidates.append({
        "來源": source,
        "年度": year,
        "案號": case_no or extract_case_no(url + " " + str(original_text)),
        "候選網址": url,
        "原始頁": original_page,
        "原始文字": str(original_text)[:1500],
    })


def collect_taiwanbuying_year_lists():
    candidates, logs = [], []
    for year in YEARS:
        url = f"https://www.taiwanbuying.com.tw/ShowOrgYearClose.ASP?OrgID={TAIPOWER_ORG_ID}&Y={year}"
        html, final_url, err = fetch_html(url, encoding="big5")
        if err:
            logs.append({"來源": "taiwanbuying", "網址": url, "狀態": "失敗", "訊息": err})
            continue

        soup, lines, text = html_to_soup_lines(html)
        found = 0

        for tr in soup.find_all("tr"):
            row_text = tr.get_text(" ", strip=True)
            if not is_interesting_text(row_text):
                continue

            found += 1
            case_no = extract_case_no(row_text)

            if case_no:
                for ez_url in make_ezbid_urls(case_no):
                    add_candidate(candidates, "taiwanbuying_case_to_ezbid", ez_url, case_no, year, final_url, row_text)

            for a in tr.find_all("a", href=True):
                add_candidate(candidates, "taiwanbuying_detail_link", urljoin(final_url, a["href"]), case_no, year, final_url, row_text)

        for snippet in re.findall(r".{0,120}亭置.{0,80}變壓器.{0,200}", text):
            case_no = extract_case_no(snippet)
            if case_no:
                for ez_url in make_ezbid_urls(case_no):
                    add_candidate(candidates, "taiwanbuying_text_case_to_ezbid", ez_url, case_no, year, final_url, snippet)

        logs.append({"來源": "taiwanbuying", "網址": url, "狀態": "完成", "訊息": f"命中列數 {found}"})
        polite_sleep()

    return candidates, logs


def collect_search_engine_results():
    candidates, logs = [], []

    queries = []
    for year in YEARS:
        for kw in KEYWORDS:
            queries.extend([
                f'"{kw}" "台灣電力" "{year}"',
                f'"{kw}" "台電" "{year}"',
                f'"{kw}" "決標" "{year}"',
                f'site:taiwanbuying.com.tw "{kw}" "{year}"',
                f'site:cf.ezbid.tw/detail "{kw}" "{year}"',
                f'site:web.pcc.gov.tw "{kw}" "{year}"',
                f'site:pcc.gov.tw "{kw}" "{year}"',
            ])

    queries.extend([
        '"亭置式變壓器" "預估需求數量"',
        '"亭置式變壓器" "原產地國別得標金額"',
        '"亭置式變壓器" "得標廠商原始投標金額"',
        '"亭置式變壓器" "投標標價清單"',
        '"亭置式變壓器" "契約單價"',
        '"亭置式變壓器" "詳細價目表"',
        '"亭置式變壓器" "25KVA"',
        '"亭置式變壓器" "50KVA"',
        '"亭置式變壓器" "100KVA"',
        '"亭置式變壓器" "167KVA"',
    ])

    # 去重並限制數量，避免跑太久
    queries = list(dict.fromkeys(queries))[:80]

    for q in queries:
        search_urls = [
            f"https://duckduckgo.com/html/?q={quote(q)}",
            f"https://www.bing.com/search?q={quote(q)}&count=50",
        ]
        for search_url in search_urls:
            html, final_url, err = fetch_html(search_url, encoding="utf-8", retry=2, timeout=25)
            if err:
                logs.append({"來源": "search", "網址": search_url, "狀態": "失敗", "訊息": err})
                continue

            soup, lines, text = html_to_soup_lines(html)

            for case_no in extract_all_case_nos(text):
                for ez_url in make_ezbid_urls(case_no):
                    add_candidate(candidates, "search_case_to_ezbid", ez_url, case_no, "", final_url, q)

            for a in soup.find_all("a", href=True):
                href = unwrap_search_url(a["href"])
                full = urljoin(final_url, href)
                link_text = a.get_text(" ", strip=True)
                parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
                hit_text = " ".join([link_text, parent_text, full])

                if (
                    is_interesting_text(hit_text)
                    or "ezbid.tw/detail" in full
                    or "taiwanbuying.com.tw" in full
                    or "pcc.gov.tw" in full
                ):
                    case_no = extract_case_no(hit_text)
                    add_candidate(candidates, "search_result_link", full, case_no, "", final_url, hit_text)
                    if case_no:
                        for ez_url in make_ezbid_urls(case_no):
                            add_candidate(candidates, "search_result_case_to_ezbid", ez_url, case_no, "", final_url, hit_text)

            logs.append({"來源": "search", "網址": search_url, "狀態": "完成", "訊息": q})
            polite_sleep(1.5)

    return candidates, logs


def collect_ezbid_seed_related():
    candidates, logs = [], []
    for case_no in SEED_CASE_NOS:
        for url in make_ezbid_urls(case_no):
            html, final_url, err = fetch_html(url, encoding="utf-8", retry=2)
            if err:
                logs.append({"來源": "ezbid_seed", "網址": url, "狀態": "失敗", "訊息": err})
                continue

            soup, lines, text = html_to_soup_lines(html)

            if is_interesting_text(text):
                add_candidate(candidates, "ezbid_seed_hit", final_url, case_no, "", final_url, "")

            for found_case_no in extract_all_case_nos(text):
                for ez_url in make_ezbid_urls(found_case_no):
                    add_candidate(candidates, "ezbid_text_case_to_ezbid", ez_url, found_case_no, "", final_url, "")

            for a in soup.find_all("a", href=True):
                full = urljoin(final_url, a["href"])
                if "/detail/" in full or is_interesting_text(a.get_text(" ", strip=True)):
                    add_candidate(candidates, "ezbid_related_link", full, extract_case_no(full), "", final_url, a.get_text(" ", strip=True))

            logs.append({"來源": "ezbid_seed", "網址": url, "狀態": "完成", "訊息": "完成"})
            polite_sleep()

    return candidates, logs


def collect_pcc_entry_pages():
    candidates, logs = [], []
    urls = []
    for kw in KEYWORDS:
        urls.extend([
            f"https://web.pcc.gov.tw/prkms/tender/common/basic/readTenderBasic?querySentence={quote(kw)}",
            f"https://web.pcc.gov.tw/tps/QueryTender/query/searchTender?searchMode=common&searchType=basic&hid_1=1&querySentence={quote(kw)}",
            f"https://www.pcc.gov.tw/search?keyword={quote(kw)}",
        ])

    for url in urls:
        html, final_url, err = fetch_html(url, encoding="utf-8", retry=2)
        if err:
            logs.append({"來源": "pcc", "網址": url, "狀態": "失敗", "訊息": err})
            continue

        soup, lines, text = html_to_soup_lines(html)

        for case_no in extract_all_case_nos(text):
            for ez_url in make_ezbid_urls(case_no):
                add_candidate(candidates, "pcc_case_to_ezbid", ez_url, case_no, "", final_url, "")

        for a in soup.find_all("a", href=True):
            full = urljoin(final_url, a["href"])
            parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
            if is_interesting_text(parent_text + " " + full):
                case_no = extract_case_no(parent_text + " " + full)
                add_candidate(candidates, "pcc_link", full, case_no, "", final_url, parent_text)

        logs.append({"來源": "pcc", "網址": url, "狀態": "完成", "訊息": "完成"})
        polite_sleep()

    return candidates, logs


def expand_candidates_by_fetching_pages(candidate_df, limit=400):
    new_candidates, attachment_links = [], []

    sample = candidate_df.head(limit).copy()

    for _, row in sample.iterrows():
        url = row["候選網址"]
        if not str(url).startswith("http"):
            continue

        encoding = "big5" if "taiwanbuying.com.tw" in url else "utf-8"
        html, final_url, err = fetch_html(url, encoding=encoding, retry=1, timeout=25)
        if err:
            continue

        soup, lines, text = html_to_soup_lines(html)

        # 收集案號
        for case_no in extract_all_case_nos(text):
            for ez_url in make_ezbid_urls(case_no):
                add_candidate(new_candidates, "second_round_case_to_ezbid", ez_url, case_no, row.get("年度", ""), final_url, text[:1200])

        # 收集相關連結
        for a in soup.find_all("a", href=True):
            full = urljoin(final_url, a["href"])
            parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
            label = a.get_text(" ", strip=True)
            hit_text = " ".join([label, parent_text, full])

            if is_attachment_url(full) or looks_like_attachment_link(hit_text):
                attachment_links.append({
                    "來源頁": final_url,
                    "附件名稱": label or parent_text[:100],
                    "附件網址": full,
                    "案號": row.get("案號", ""),
                })

            if is_interesting_text(hit_text) or "/detail/" in full:
                add_candidate(new_candidates, "second_round_link", full, extract_case_no(hit_text), row.get("年度", ""), final_url, hit_text)

        polite_sleep(0.5)

    return pd.DataFrame(new_candidates), pd.DataFrame(attachment_links)


# ============================================================
# HTML 明細解析
# ============================================================

def parse_award_items_from_lines(lines, source_url):
    text = "\n".join(lines)
    rows, pending = [], []

    if not is_interesting_text(text):
        return rows, pending

    case_no = extract_case_no(text)

    award_date_roc = ""
    award_date_ad = ""
    for line in lines:
        if "決標日期" in line or "決標日" in line:
            award_date_roc = line
            award_date_ad = roc_date_to_ad(line)
            break

    award_year = extract_year(award_date_ad, award_date_roc)
    if award_year is not None and award_year not in YEARS:
        return rows, pending

    item_indices = [i for i, line in enumerate(lines) if "品項名稱" in line]

    # 備援：直接含品名與容量的列
    if not item_indices:
        for i, line in enumerate(lines):
            if is_interesting_text(line) and extract_capacity_kva(line) is not None:
                item_indices.append(i)

    for idx in item_indices:
        current_line = lines[idx]
        if "品項名稱" in current_line and is_interesting_text(current_line):
            item_name = re.sub(r"^.*品項名稱", "", current_line).strip(" ：:")
        elif "品項名稱" in current_line:
            item_name = lines[idx + 1] if idx + 1 < len(lines) else ""
        else:
            item_name = current_line

        item_name = normalize_item_name(item_name)
        if not is_interesting_text(item_name):
            continue

        capacity = extract_capacity_kva(item_name)
        block = lines[idx:idx + 350]

        vendor = ""
        quantity = None
        amount = None
        original_amount = None

        for j, line in enumerate(block):
            if "得標廠商" in line and "原始" not in line and not vendor:
                tmp = re.sub(r"^.*得標廠商", "", line).strip(" ：:")
                if tmp and "是否" not in tmp and "國別" not in tmp and "亭置" not in tmp:
                    vendor = tmp
                elif j + 1 < len(block):
                    vendor = block[j + 1]

            if not vendor and "廠商名稱" in line:
                tmp = re.sub(r"^.*廠商名稱", "", line).strip(" ：:")
                vendor = tmp or (block[j + 1] if j + 1 < len(block) else vendor)

            if "預估需求數量" in line:
                tmp = re.sub(r"^.*預估需求數量", "", line).strip(" ：:")
                quantity = qty_to_float(tmp) or (qty_to_float(block[j + 1]) if j + 1 < len(block) else quantity)

            if quantity is None and line.strip() in ["數量", "數 量"]:
                quantity = qty_to_float(block[j + 1]) if j + 1 < len(block) else quantity

            if "原產地國別得標金額" in line:
                tmp = re.sub(r"^.*原產地國別得標金額\d*", "", line).strip(" ：:")
                amount = money_to_int(tmp) or (money_to_int(block[j + 1]) if j + 1 < len(block) else amount)

            if amount is None and "品項得標金額" in line:
                tmp = re.sub(r"^.*品項得標金額", "", line).strip(" ：:")
                amount = money_to_int(tmp) or (money_to_int(block[j + 1]) if j + 1 < len(block) else amount)

            if "得標廠商原始投標金額" in line:
                tmp = re.sub(r"^.*得標廠商原始投標金額", "", line).strip(" ：:")
                original_amount = money_to_int(tmp) or (money_to_int(block[j + 1]) if j + 1 < len(block) else original_amount)

        if amount is None and original_amount is not None:
            amount = original_amount

        if quantity and amount:
            unit_price = round(amount / quantity, 0)
            rows.append(make_record(
                source="HTML",
                year=award_year,
                case_no=case_no,
                award_date_roc=award_date_roc,
                award_date_ad=award_date_ad,
                vendor=vendor,
                item_name=item_name,
                quantity=quantity,
                amount=amount,
                unit_price=unit_price,
                source_url=source_url
            ))
        else:
            pending.append({
                "案號": case_no,
                "決標日_西元": award_date_ad,
                "資料來源": source_url,
                "品項名稱": item_name,
                "抓到容量_kVA": capacity,
                "抓到廠商": vendor,
                "抓到數量": quantity,
                "抓到金額": amount,
                "原因": "HTML找到品項，但缺數量或金額",
                "摘要": " | ".join(block[:120]),
            })

    return rows, pending


def make_record(source, year, case_no, award_date_roc, award_date_ad, vendor, item_name, quantity, amount, unit_price, source_url):
    item_name = normalize_item_name(item_name)
    capacity = extract_capacity_kva(item_name)
    return {
        "資料型態": source,
        "年度": year,
        "案號": case_no,
        "決標日_民國": award_date_roc,
        "決標日_西元": award_date_ad,
        "得標廠商": normalize_vendor(vendor),
        "品項名稱": item_name,
        "變壓器型式": "亭置式變壓器",
        "相數": "單相",
        "電壓": extract_voltage(item_name),
        "容量_kVA": capacity,
        "容量規格": capacity_label(capacity),
        "數量": quantity,
        "品項得標金額": amount,
        "每一規格得標單價": unit_price,
        "是否目標容量": capacity in TARGET_CAPACITIES,
        "資料來源": source_url,
    }


def parse_candidate_page(url):
    encoding = "big5" if "taiwanbuying.com.tw" in str(url) else "utf-8"
    html, final_url, err = fetch_html(url, encoding=encoding, retry=2, timeout=30)
    if err:
        return [], [{"資料來源": url, "原因": "網頁讀取失敗", "摘要": err}], []

    soup, lines, text = html_to_soup_lines(html)
    rows, pending = parse_award_items_from_lines(lines, final_url)
    attachments = collect_attachments_from_soup(soup, final_url)
    return rows, pending, attachments


# ============================================================
# 附件下載與解析
# ============================================================

def is_attachment_url(url):
    lower = str(url).lower().split("?")[0]
    return lower.endswith(ATTACHMENT_EXTS)


def looks_like_attachment_link(text):
    s = str(text)
    keywords = ["附件", "下載", "標價清單", "契約單價", "詳細價目", "價目表", "投標明細", "單價表", "pdf", "xls", "xlsx", "ods"]
    return any(k in s for k in keywords)


def collect_attachments_from_soup(soup, base_url):
    links = []
    for a in soup.find_all("a", href=True):
        full = urljoin(base_url, a["href"])
        label = a.get_text(" ", strip=True)
        parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
        hit_text = " ".join([label, parent_text, full])

        if is_attachment_url(full) or looks_like_attachment_link(hit_text):
            links.append({
                "來源頁": base_url,
                "附件名稱": label or parent_text[:100],
                "附件網址": full,
                "案號": extract_case_no(base_url + " " + parent_text),
            })

    return links


def save_attachment(att):
    url = att["附件網址"]
    content, final_url, content_type, err = fetch_binary(url)
    if err or not content:
        return None, final_url, content_type, err

    suffix = Path(urlparse(final_url).path).suffix.lower()
    if not suffix:
        if "pdf" in content_type.lower():
            suffix = ".pdf"
        elif "excel" in content_type.lower() or "spreadsheet" in content_type.lower():
            suffix = ".xlsx"
        else:
            suffix = ".bin"

    filename = f"{hash_text(final_url)}{suffix}"
    path = ATTACH_DIR / filename
    path.write_bytes(content)
    return path, final_url, content_type, ""


def read_pdf_text(path):
    try:
        import pdfplumber
        chunks = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                if txt.strip():
                    chunks.append(txt)
        return "\n".join(chunks)
    except Exception:
        return ""


def read_pdf_text_ocr_optional(path):
    try:
        import pytesseract
        from pdf2image import convert_from_path
        images = convert_from_path(str(path), dpi=200)
        chunks = []
        for img in images:
            txt = pytesseract.image_to_string(img, lang="chi_tra+eng")
            if txt.strip():
                chunks.append(txt)
        return "\n".join(chunks)
    except Exception:
        return ""


def read_excel_text(path):
    try:
        # 支援 xlsx/xls/ods；ods 需 odfpy
        dfs = pd.read_excel(path, sheet_name=None, dtype=str)
        chunks = []
        for sheet, df in dfs.items():
            chunks.append(f"--- sheet: {sheet} ---")
            chunks.append(df.fillna("").to_csv(index=False))
        return "\n".join(chunks)
    except Exception:
        return ""


def read_csv_text(path):
    for enc in ["utf-8-sig", "utf-8", "big5", "cp950"]:
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return ""


def read_docx_text(path):
    try:
        import docx
        doc = docx.Document(str(path))
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception:
        return ""


def read_attachment_text(path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = read_pdf_text(path)
        if not text.strip():
            text = read_pdf_text_ocr_optional(path)
        return text

    if suffix in [".xls", ".xlsx", ".ods"]:
        return read_excel_text(path)

    if suffix in [".csv", ".txt"]:
        return read_csv_text(path)

    if suffix == ".docx":
        return read_docx_text(path)

    return read_csv_text(path)


def parse_attachment_text(text, att):
    rows, pending = [], []

    if not text or not is_interesting_text(text):
        return rows, pending

    case_no = att.get("案號") or extract_case_no(text) or extract_case_no(att.get("來源頁", ""))
    source_url = att.get("附件網址", "")
    attachment_name = att.get("附件名稱", "")

    lines = [x.strip() for x in text.splitlines() if x.strip()]

    # 先用表格/文字列解析：找含亭置式與kVA的列，並讀附近列
    for i, line in enumerate(lines):
        if not (is_interesting_text(line) and extract_capacity_kva(line) is not None):
            continue

        block_lines = lines[max(0, i - 3): i + 12]
        block = " | ".join(block_lines)
        item_name = normalize_item_name(line)
        capacity = extract_capacity_kva(item_name)

        vendor = guess_vendor_from_block(block)
        quantity = guess_quantity_from_block(block)
        unit_price = guess_unit_price_from_block(block)
        amount = guess_amount_from_block(block)

        # 若只有金額與數量，算單價
        if unit_price is None and amount and quantity:
            unit_price = round(amount / quantity, 0)

        # 若只有單價與數量，算總價
        if amount is None and unit_price and quantity:
            amount = int(unit_price * quantity)

        if quantity and (unit_price or amount):
            rows.append(make_record(
                source=f"附件:{attachment_name}",
                year=None,
                case_no=case_no,
                award_date_roc="",
                award_date_ad="",
                vendor=vendor,
                item_name=item_name,
                quantity=quantity,
                amount=amount,
                unit_price=unit_price,
                source_url=source_url,
            ))
        else:
            pending.append({
                "案號": case_no,
                "資料來源": source_url,
                "品項名稱": item_name,
                "抓到容量_kVA": capacity,
                "抓到廠商": vendor,
                "抓到數量": quantity,
                "抓到單價": unit_price,
                "抓到金額": amount,
                "原因": "附件找到品項，但缺數量/單價/金額",
                "摘要": block[:1200],
            })

    # 第二種：整段用規則找「容量 + 數量 + 單價/金額」較寬鬆
    # 避免重複太多，只補 pending 中未找到的容量
    return rows, pending


def guess_vendor_from_block(block):
    m = re.search(r"(華城|士林|中興|三江|大同|東元|亞力|宏泰|中華電線|樂士|新桃電力|[\u4e00-\u9fff]{2,12}(?:股份有限公司|有限公司))", block)
    return m.group(1) if m else ""


def guess_quantity_from_block(block):
    patterns = [
        r"(?:數量|需求數量|預估需求數量)\D{0,15}([\d,]+(?:\.\d+)?)",
        r"([\d,]+(?:\.\d+)?)\s*(?:台|具|PC|PCS|EA)",
    ]
    for p in patterns:
        m = re.search(p, block, re.I)
        if m:
            return qty_to_float(m.group(1))
    return None


def guess_unit_price_from_block(block):
    patterns = [
        r"(?:單價|得標單價|契約單價)\D{0,20}([\d,]+)",
        r"([\d,]+)\s*(?:元/台|元／台|元每台)",
    ]
    for p in patterns:
        m = re.search(p, block)
        if m:
            value = money_to_int(m.group(1))
            # 單價通常不會是幾十億，做粗略過濾
            if value and 1000 <= value <= 5000000:
                return value
    return None


def guess_amount_from_block(block):
    patterns = [
        r"(?:金額|總價|複價|得標金額|標價)\D{0,20}([\d,]+)",
    ]
    for p in patterns:
        m = re.search(p, block)
        if m:
            return money_to_int(m.group(1))
    return None


def process_attachments(attachments_df):
    rows, pending, logs = [], [], []
    if attachments_df.empty:
        return rows, pending, logs

    attachments_df = attachments_df.drop_duplicates(subset=["附件網址"]).reset_index(drop=True)

    for idx, att in attachments_df.iterrows():
        att_dict = att.to_dict()
        path, final_url, content_type, err = save_attachment(att_dict)

        if err or path is None:
            pending.append({
                "案號": att_dict.get("案號", ""),
                "資料來源": att_dict.get("附件網址", ""),
                "原因": "附件下載失敗",
                "摘要": err,
            })
            logs.append({"來源": "attachment", "網址": att_dict.get("附件網址", ""), "狀態": "失敗", "訊息": err})
            continue

        text = read_attachment_text(path)
        if not text.strip():
            pending.append({
                "案號": att_dict.get("案號", ""),
                "資料來源": final_url,
                "原因": "附件無法讀取文字，可能是掃描PDF或不支援格式",
                "摘要": str(path),
            })
            logs.append({"來源": "attachment", "網址": final_url, "狀態": "無文字", "訊息": str(path)})
            continue

        r, p = parse_attachment_text(text, {**att_dict, "附件網址": final_url})
        rows.extend(r)
        pending.extend(p)
        logs.append({"來源": "attachment", "網址": final_url, "狀態": "完成", "訊息": str(path)})
        polite_sleep()

    return rows, pending, logs


# ============================================================
# 彙總表
# ============================================================

def build_target_capacity_table(df):
    base = pd.DataFrame({
        "容量_kVA": TARGET_CAPACITIES,
        "容量規格": [capacity_label(x) for x in TARGET_CAPACITIES],
    })

    if df.empty:
        return base

    x = df[df["容量_kVA"].isin(TARGET_CAPACITIES)].copy()
    if x.empty:
        return base

    summary = (
        x.groupby("容量_kVA")
        .agg(
            筆數=("每一規格得標單價", "count"),
            最低單價=("每一規格得標單價", "min"),
            平均單價=("每一規格得標單價", "mean"),
            最高單價=("每一規格得標單價", "max"),
            得標廠商清單=("得標廠商", lambda s: "、".join(sorted(set([str(v) for v in s if str(v).strip()])))),
            案號清單=("案號", lambda s: "、".join(sorted(set([str(v) for v in s if str(v).strip()])))),
        )
        .reset_index()
    )
    summary["平均單價"] = summary["平均單價"].round(0)
    return base.merge(summary, on="容量_kVA", how="left")


def build_capacity_summary(df):
    if df.empty:
        return pd.DataFrame()

    x = df[df["容量_kVA"].notna()].copy()
    if x.empty:
        return pd.DataFrame()

    summary = (
        x.groupby("容量_kVA")
        .agg(
            容量規格=("容量規格", "first"),
            筆數=("每一規格得標單價", "count"),
            最低單價=("每一規格得標單價", "min"),
            平均單價=("每一規格得標單價", "mean"),
            最高單價=("每一規格得標單價", "max"),
            最早年度=("年度", "min"),
            最新年度=("年度", "max"),
            得標廠商清單=("得標廠商", lambda s: "、".join(sorted(set([str(v) for v in s if str(v).strip()])))),
            案號清單=("案號", lambda s: "、".join(sorted(set([str(v) for v in s if str(v).strip()])))),
        )
        .reset_index()
    )
    summary["平均單價"] = summary["平均單價"].round(0)
    return summary.sort_values("容量_kVA")


def build_year_capacity_pivot(df):
    if df.empty:
        return pd.DataFrame()
    x = df[df["年度"].notna() & df["容量_kVA"].notna()].copy()
    if x.empty:
        return pd.DataFrame()
    pivot = pd.pivot_table(
        x,
        index="容量規格",
        columns="年度",
        values="每一規格得標單價",
        aggfunc="mean",
    )
    return pivot.round(0).reset_index()


def build_vendor_capacity_pivot(df):
    if df.empty:
        return pd.DataFrame()
    x = df[df["容量_kVA"].notna() & df["得標廠商"].notna()].copy()
    if x.empty:
        return pd.DataFrame()
    pivot = pd.pivot_table(
        x,
        index="得標廠商",
        columns="容量規格",
        values="每一規格得標單價",
        aggfunc="mean",
    )
    return pivot.round(0).reset_index()


# ============================================================
# 主程式
# ============================================================

def main():
    all_candidates, all_logs = [], []

    print("========== 來源1：taiwanbuying 年度清單 ==========")
    c, logs = collect_taiwanbuying_year_lists()
    all_candidates.extend(c)
    all_logs.extend(logs)

    print("========== 來源2：搜尋引擎 DuckDuckGo / Bing ==========")
    c, logs = collect_search_engine_results()
    all_candidates.extend(c)
    all_logs.extend(logs)

    print("========== 來源3：ezBid 種子延伸 ==========")
    c, logs = collect_ezbid_seed_related()
    all_candidates.extend(c)
    all_logs.extend(logs)

    print("========== 來源4：PCC 入口 ==========")
    c, logs = collect_pcc_entry_pages()
    all_candidates.extend(c)
    all_logs.extend(logs)

    for case_no in SEED_CASE_NOS:
        for ez_url in make_ezbid_urls(case_no):
            add_candidate(all_candidates, "manual_seed", ez_url, case_no, "", "", "")

    candidate_df = pd.DataFrame(all_candidates)

    if candidate_df.empty:
        print("沒有候選案件。")
        return

    candidate_df["候選網址"] = candidate_df["候選網址"].fillna("").astype(str)
    candidate_df = candidate_df[candidate_df["候選網址"].str.startswith("http")]
    candidate_df = candidate_df.drop_duplicates(subset=["候選網址"]).reset_index(drop=True)

    print(f"第一輪候選網址：{len(candidate_df)}")

    print("========== 第二輪：候選頁面擴充案號與附件 ==========")
    second_df, second_att_df = expand_candidates_by_fetching_pages(candidate_df, limit=400)

    if not second_df.empty:
        candidate_df = pd.concat([candidate_df, second_df], ignore_index=True)
        candidate_df = candidate_df.drop_duplicates(subset=["候選網址"]).reset_index(drop=True)

    print(f"總候選網址：{len(candidate_df)}")

    html_rows, html_pending, attachments = [], [], []

    for idx, row in candidate_df.iterrows():
        url = row["候選網址"]
        print(f"\n[{idx + 1}/{len(candidate_df)}] 解析HTML：{url}")

        try:
            rows, pending, atts = parse_candidate_page(url)
            html_rows.extend(rows)
            html_pending.extend(pending)
            for att in atts:
                if not att.get("案號"):
                    att["案號"] = row.get("案號", "")
                attachments.append(att)
        except Exception as e:
            html_pending.append({
                "資料來源": url,
                "原因": "HTML解析例外",
                "摘要": str(e),
            })

        polite_sleep(0.6)

    attachments_df = pd.DataFrame(attachments)
    if not second_att_df.empty:
        attachments_df = pd.concat([attachments_df, second_att_df], ignore_index=True)

    if attachments_df.empty:
        attachments_df = pd.DataFrame(columns=["來源頁", "附件名稱", "附件網址", "案號"])
    else:
        attachments_df = attachments_df.drop_duplicates(subset=["附件網址"]).reset_index(drop=True)

    print(f"\n========== 附件解析：共 {len(attachments_df)} 個候選附件 ==========")
    attachment_rows, attachment_pending, attachment_logs = process_attachments(attachments_df)
    all_logs.extend(attachment_logs)

    html_df = pd.DataFrame(html_rows)
    attachment_df = pd.DataFrame(attachment_rows)

    combined_df = pd.concat([html_df, attachment_df], ignore_index=True) if not html_df.empty or not attachment_df.empty else pd.DataFrame()

    if not combined_df.empty:
        combined_df = combined_df.drop_duplicates(
            subset=[
                "案號",
                "得標廠商",
                "品項名稱",
                "容量_kVA",
                "數量",
                "品項得標金額",
                "每一規格得標單價",
            ]
        )

        combined_df = combined_df.sort_values(
            ["年度", "案號", "容量_kVA", "得標廠商", "每一規格得標單價"],
            na_position="last",
        )

    pending_df = pd.DataFrame(html_pending + attachment_pending)
    logs_df = pd.DataFrame(all_logs)

    target_df = build_target_capacity_table(combined_df)
    summary_df = build_capacity_summary(combined_df)
    year_pivot_df = build_year_capacity_pivot(combined_df)
    vendor_pivot_df = build_vendor_capacity_pivot(combined_df)

    output_xlsx = OUTPUT_DIR / "台電_亭置式變壓器_2023_2026_附件強化版.xlsx"
    output_csv = OUTPUT_DIR / "台電_亭置式變壓器_2023_2026_合併資料庫.csv"

    with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
        combined_df.to_excel(writer, sheet_name="合併後資料庫", index=False)
        html_df.to_excel(writer, sheet_name="HTML解析資料", index=False)
        attachment_df.to_excel(writer, sheet_name="附件解析資料", index=False)
        target_df.to_excel(writer, sheet_name="指定容量單價", index=False)
        summary_df.to_excel(writer, sheet_name="容量規格統計", index=False)
        year_pivot_df.to_excel(writer, sheet_name="年度容量平均單價", index=False)
        vendor_pivot_df.to_excel(writer, sheet_name="廠商容量平均單價", index=False)
        candidate_df.to_excel(writer, sheet_name="候選案件", index=False)
        attachments_df.to_excel(writer, sheet_name="附件清單", index=False)

        if not pending_df.empty:
            pending_df.to_excel(writer, sheet_name="待人工確認", index=False)
        else:
            pd.DataFrame().to_excel(writer, sheet_name="待人工確認", index=False)

        if not logs_df.empty:
            logs_df.to_excel(writer, sheet_name="執行紀錄", index=False)
        else:
            pd.DataFrame().to_excel(writer, sheet_name="執行紀錄", index=False)

    if not combined_df.empty:
        combined_df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print("\n========== 完成 ==========")
    print(f"HTML資料筆數：{len(html_df)}")
    print(f"附件資料筆數：{len(attachment_df)}")
    print(f"合併資料筆數：{len(combined_df)}")
    print(f"候選案件筆數：{len(candidate_df)}")
    print(f"附件候選筆數：{len(attachments_df)}")
    print(f"待人工確認筆數：{len(pending_df)}")
    print(f"Excel：{output_xlsx}")
    print(f"CSV：{output_csv if not combined_df.empty else '無資料，未輸出 CSV'}")
    print("\n建議優先查看：")
    print("1. 指定容量單價")
    print("2. 容量規格統計")
    print("3. 附件清單")
    print("4. 待人工確認")


if __name__ == "__main__":
    main()
