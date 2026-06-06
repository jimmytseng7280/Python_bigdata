# 台電亭置式變壓器標案資料爬取
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {"User-Agent": "Mozilla/5.0"}

SEED_URLS = [
    "https://cf.ezbid.tw/detail/3.13.31/0081400078",
]

YEARS_ROC = ["112", "113", "114", "115"]  # 2023~2026
KEYWORD = "亭置式變壓器"


def fetch(url, timeout=30, retry=3):
    for i in range(retry):
        try:
            print("正在爬取：", url)
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            r.encoding = "utf-8"
            return r.text
        except requests.exceptions.Timeout:
            print(f"連線超時，重試第 {i + 1} 次")
            time.sleep(2 + i)
        except Exception as e:
            print("錯誤：", e)
            return ""
    return ""


def lines_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    return [x.strip() for x in soup.get_text("\n", strip=True).split("\n") if x.strip()], soup


def money_to_int(text):
    if not text:
        return None
    m = re.search(r"[\d,]+", str(text))
    return int(m.group().replace(",", "")) if m else None


def roc_date_to_ad(text):
    m = re.search(r"(\d{3})/(\d{1,2})/(\d{1,2})", text)
    if not m:
        return ""
    y, mth, d = map(int, m.groups())
    return f"{y + 1911:04d}/{mth:02d}/{d:02d}"


def extract_capacity(text):
    m = re.search(r"(\d+)\s*kVA", text, re.I)
    return f"{m.group(1)}kVA" if m else ""


def extract_phase(text):
    if "單相" in text:
        return "單相"
    if "三相" in text:
        return "三相"
    return ""


def extract_voltage(text):
    m = re.search(r"(\d+\.?\d*)\s*/\s*(\d+\.?\d*)\s*kV", text, re.I)
    return m.group(0).replace(" ", "") if m else ""


def discover_case_urls(seed_urls):
    """
    從已知案子的頁面往外找同類型案號。
    ezBid 明細頁常會有相關案號連結。
    """
    urls = set(seed_urls)

    for seed in seed_urls:
        html = fetch(seed)
        if not html:
            continue

        lines, soup = lines_from_html(html)
        text = "\n".join(lines)

        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = urljoin(seed, href)

            if "/detail/3.13.31/" in full:
                urls.add(full)

        # 從文字中抓可能案號
        for case_no in re.findall(r"\b\d{10}\b", text):
            urls.add(f"https://cf.ezbid.tw/detail/3.13.31/{case_no}")

    return sorted(urls)


def parse_case(url):
    html = fetch(url)
    if not html:
        return []

    lines, soup = lines_from_html(html)
    text = "\n".join(lines)

    if KEYWORD not in text:
        return []

    case_no = ""
    m = re.search(r"\b\d{10}\b", text)
    if m:
        case_no = m.group()

    award_date_roc = ""
    award_date_ad = ""

    for line in lines:
        if "決標日" in line or "決標日期" in line:
            award_date_roc = line.replace("決標日：", "").replace("其他:決標日期", "").strip()
            award_date_ad = roc_date_to_ad(line)
            break

    # 只保留 2023~2026
    if award_date_ad:
        year = int(award_date_ad[:4])
        if year < 2023 or year > 2026:
            return []

    rows = []

    for i, line in enumerate(lines):
        if "品項名稱" not in line:
            continue

        item_name = lines[i + 1] if i + 1 < len(lines) else ""

        if KEYWORD not in item_name:
            continue

        block = lines[i:i + 180]

        vendor = ""
        qty = None
        amount = None

        for j, b in enumerate(block):
            if "得標廠商" in b and "原始" not in b and not vendor and j + 1 < len(block):
                vendor = block[j + 1]

            if "預估需求數量" in b and j + 1 < len(block):
                qty = money_to_int(block[j + 1])

            # 優先抓真正得標金額
            if "原產地國別得標金額" in b and j + 1 < len(block):
                amount = money_to_int(block[j + 1])

            # 備援
            if amount is None and "得標廠商原始投標金額" in b and j + 1 < len(block):
                amount = money_to_int(block[j + 1])

        if item_name and vendor and qty and amount:
            rows.append({
                "案號": case_no,
                "決標日_民國": award_date_roc,
                "決標日_西元": award_date_ad,
                "得標廠商": vendor,
                "品項名稱": item_name,
                "相數": extract_phase(item_name),
                "電壓": extract_voltage(item_name),
                "容量": extract_capacity(item_name),
                "數量": qty,
                "品項得標金額": amount,
                "單一規格得標單價": round(amount / qty, 0),
                "資料來源": url
            })

    return rows


def main():
    case_urls = discover_case_urls(SEED_URLS)

    # 你之前程式已找到的案號，直接補進來
    extra_urls = [
        "https://cf.ezbid.tw/detail/3.13.31/0081500019",
        "https://cf.ezbid.tw/detail/3.13.31/0081500027",
        "https://cf.ezbid.tw/detail/3.13.31/0081500032",
        "https://cf.ezbid.tw/detail/3.13.31/0081500037",
        "https://cf.ezbid.tw/detail/3.13.31/0141500021",
    ]

    case_urls = sorted(set(case_urls + extra_urls))

    print(f"找到候選案件：{len(case_urls)} 筆")

    all_rows = []

    for url in case_urls:
        rows = parse_case(url)
        all_rows.extend(rows)
        time.sleep(1)

    df = pd.DataFrame(all_rows)

    if df.empty:
        print("沒有抓到資料。")
        return

    df = df.drop_duplicates(
        subset=["案號", "得標廠商", "品項名稱", "數量", "品項得標金額"]
    )

    df = df.sort_values(
        ["決標日_西元", "案號", "得標廠商", "容量", "單一規格得標單價"]
    )

    output_xlsx = "台電_亭置式變壓器_所有廠商_2023_2026_得標單價.xlsx"
    output_csv = "台電_亭置式變壓器_所有廠商_2023_2026_得標單價.csv"

    df.to_excel(output_xlsx, index=False)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print(df)
    print("完成輸出：")
    print(output_xlsx)
    print(output_csv)


if __name__ == "__main__":
    main()