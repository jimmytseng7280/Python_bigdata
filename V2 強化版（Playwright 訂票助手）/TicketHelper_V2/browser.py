
from playwright.sync_api import sync_playwright
import time

AIRLINE_URLS = {
    "華信": "https://www.mandarin-airlines.com",
    "立榮": "https://www.uniair.com.tw/booking/flight-search",
}

AIRPORT_MAP = {
    "TSA": "TSA", "TPE": "TPE", "KHH": "KHH", "RMQ": "RMQ",
    "KNH": "KNH", "MZG": "MZG", "HUN": "HUN", "TTT": "TTT",
    "NRT": "NRT", "HND": "HND", "KIX": "KIX", "OKA": "OKA",
    "ICN": "ICN", "BKK": "BKK", "SIN": "SIN", "HKG": "HKG",
}


def open_and_prepare(company):
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    url = AIRLINE_URLS.get(company, "https://www.uniair.com.tw")
    page.goto(url)
    page.wait_for_load_state("networkidle")

    return p, browser, page


def _select_trip_type(page, trip_type):
    try:
        if trip_type == "單程":
            btn = page.locator("text=單程").first
            btn.click()
            print("  已選擇: 單程")
        elif trip_type == "來回程":
            btn = page.locator("text=來回").first
            btn.click()
            print("  已選擇: 來回")
        elif trip_type == "多目的地":
            btn = page.locator("text=多航段").first
            btn.click()
            print("  已選擇: 多航段/多個目的地")
        page.wait_for_timeout(500)
    except Exception as e:
        print(f"  選擇行程類型失敗: {e}")


def _select_airport(page, field_text, airport_code):
    try:
        field = page.locator(f"text={field_text}").first
        field.click()
        page.wait_for_timeout(300)

        option = page.locator(f"text={airport_code}").first
        option.click()
        page.wait_for_timeout(300)
        print(f"  {field_text}: {airport_code}")
    except Exception as e:
        print(f"  選擇{field_text}失敗: {e}")


def _set_date(page, date_str):
    try:
        date_input = page.locator("text=出發日期").first
        date_input.click()
        page.wait_for_timeout(300)

        parts = date_str.split("-")
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])

        page.wait_for_timeout(500)
        print(f"  日期: {date_str}")
    except Exception as e:
        print(f"  設定日期失敗: {e}")


def _set_passengers(page, people, infants=0):
    try:
        pax_field = page.locator("text=搭乘人數").first
        pax_field.click()
        page.wait_for_timeout(300)

        adult_input = page.locator("input[type='number']").first
        if adult_input:
            adult_input.fill(str(people))
            print(f"  旅客: {people} 人, 嬰兒: {infants} 人")
        page.wait_for_timeout(300)
    except Exception as e:
        print(f"  設定人數失敗: {e}")


def _handle_captcha(page):
    try:
        print("\n  請手動輸入驗證碼...")
        captcha_input = page.locator("text=請輸入驗證碼").first
        if captcha_input:
            captcha_input.click()

        for i in range(60):
            time.sleep(1)
            val = page.locator("input[placeholder*='驗證碼']").first
            if val and val.input_value():
                print(f"  驗證碼已輸入: {val.input_value()}")
                return True
        print("  驗證碼輸入超時")
        return False
    except Exception as e:
        print(f"  驗證碼處理失敗: {e}")
        return False


def fill_form(page, info):
    company = info.get("company", "未知")
    trip_type = info.get("trip_type", "單程")
    segments = info.get("segments", [])
    people = info.get("people", 1)
    passengers = info.get("passengers", [])

    print(f"\n=== {company} | 行程: {trip_type} ===")

    for i, seg in enumerate(segments, 1):
        dep = seg.get("dep_code", "")
        dep_name = seg.get("dep_name", "")
        arr = seg.get("arr_code", "")
        arr_name = seg.get("arr_name", "")

        if trip_type == "來回程":
            dep_date = seg.get("dep_date", "")
            ret_date = seg.get("ret_date", "")
            dep_time = seg.get("flight_time", "")
            ret_time = seg.get("ret_flight_time", "")
            print(f"  航段{i}: {dep}({dep_name}) → {arr}({arr_name})")
            print(f"         去程: {dep_date} {dep_time}  回程: {ret_date} {ret_time}")
        else:
            date = seg.get("date", "")
            time_ = seg.get("flight_time", "")
            print(f"  航段{i}: {dep}({dep_name}) → {arr}({arr_name})")
            print(f"         日期: {date}  時間: {time_}")

    print(f"  人數: {people}")
    for i, p in enumerate(passengers, 1):
        print(f"  乘客{i}: {p.get('name', '')} / {p.get('id', '')}")

    _select_trip_type(page, trip_type)

    if segments:
        seg = segments[0]
        _select_airport(page, "啟程地", seg["dep_code"])
        _select_airport(page, "目的地", seg["arr_code"])
        date_val = seg.get("dep_date") or seg.get("date", "")
        _set_date(page, date_val)

    _set_passengers(page, people)

    _handle_captcha(page)

    try:
        search_btn = page.locator("text=搜尋").first
        search_btn.click()
        print("  已點擊搜尋")
    except Exception as e:
        print(f"  點擊搜尋失敗: {e}")

    print(f"--- {company} 填寫完成 ---")
