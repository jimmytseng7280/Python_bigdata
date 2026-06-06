# 台電亭置式變壓器標案資料爬取
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://www.taiwanbuying.com.tw"
LIST_URL = "https://www.taiwanbuying.com.tw/ShowOrgYearClose.ASP?OrgID=2971&Y=2025"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def to_int(text):
    if not text:
        return None
    m = re.search(r"[\d,]+", text)
    return int(m.group().replace(",", "")) if m else None


def get_html(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    r.encoding = "big5" if "taiwanbuying" in url else "utf-8"
    return r.text


def extract_capacity(text):
    m = re.search(r"(\d+)\s*KVA", text, re.I)
    return f"{m.group(1)}kVA" if m else ""


def find_case_links():
    html = get_html(LIST_URL)
    soup = BeautifulSoup(html, "html.parser")

    links = []

    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        href = a["href"]

        if "亭置式變壓器" in title:
            full_url = urljoin(BASE, href)
            links.append({
                "標案名稱": title,
                "網址": full_url
            })

    # 去重
    seen = set()
    result = []
    for x in links:
        if x["網址"] not in seen:
            seen.add(x["網址"])
            result.append(x)

    return result


def parse_case(url):
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = [x.strip() for x in text.split("\n") if x.strip()]

    case_no = ""
    award_date = ""

    for i, line in enumerate(lines):
        if "標案案號" in line or "案號" == line:
            if i + 1 < len(lines):
                case_no = lines[i + 1]

        if "決標日期" in line or "決標日" in line:
            if i + 1 < len(lines):
                award_date = lines[i + 1]

    rows = []

    for i, line in enumerate(lines):
        if "品項名稱" in line:
            item_name = lines[i + 1] if i + 1 < len(lines) else ""

            qty = None
            amount = None
            vendor = ""

            for j in range(i, min(i + 60, len(lines))):
                if "得標廠商" in lines[j] and not vendor:
                    if j + 1 < len(lines):
                        vendor = lines[j + 1]

                if "預估需求數量" in lines[j] or "數量" == lines[j]:
                    if j + 1 < len(lines):
                        qty = to_int(lines[j + 1])

                if (
                    "得標廠商原始投標金額" in lines[j]
                    or "原產地國別得標金額" in lines[j]
                    or "決標金額" in lines[j]
                ):
                    if j + 1 < len(lines):
                        amount = to_int(lines[j + 1])

            if item_name and qty and amount:
                rows.append({
                    "案號": case_no,
                    "決標日期": award_date,
                    "標案網址": url,
                    "品項名稱": item_name,
                    "容量": extract_capacity(item_name),
                    "得標廠商": vendor,
                    "數量": qty,
                    "品項得標金額": amount,
                    "單一規格單價": round(amount / qty, 0)
                })

    return rows


def main():
    case_links = find_case_links()

    print(f"找到 {len(case_links)} 筆亭置式變壓器案件")

    all_rows = []

    for case in case_links:
        print("處理：", case["標案名稱"], case["網址"])

        try:
            rows = parse_case(case["網址"])
            all_rows.extend(rows)
            time.sleep(1)
        except Exception as e:
            print("失敗：", case["網址"], e)

    df = pd.DataFrame(all_rows)

    if df.empty:
        print("沒有抓到品項明細，可能該網站頁面未公開完整品項表。")
        return

    df = df.sort_values(["決標日期", "容量", "單一規格單價"])

    df.to_excel("台電亭置式變壓器_2025至今_單一規格得標單價.xlsx", index=False)
    df.to_csv("台電亭置式變壓器_2025至今_單一規格得標單價.csv", index=False, encoding="utf-8-sig")

    print(df)
    print("已輸出 Excel / CSV")


if __name__ == "__main__":
    main()