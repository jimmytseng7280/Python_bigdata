import csv
import requests
from datetime import datetime
from urllib.parse import quote_plus

START_YEAR = 2021
END_YEAR = 2026

CSV_FILE = "近五年台語_閩南語流行歌_YouTube清單.csv"

KEYWORDS = [
    "台語",
    "臺語",
    "閩南語",
    "台語流行",
    "臺語流行",
    "閩南語流行",
    "台語歌",
    "臺語歌",
    "閩南語歌",
    "Taiwanese Hokkien",
    "Hokkien song"
]

def search_itunes(keyword, limit=200):
    url = "https://itunes.apple.com/search"

    params = {
        "term": keyword,
        "country": "TW",
        "media": "music",
        "entity": "song",
        "limit": limit,
        "lang": "zh_tw"
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    return response.json().get("results", [])

def get_year(release_date):
    try:
        return datetime.fromisoformat(
            release_date.replace("Z", "+00:00")
        ).year
    except Exception:
        return None

def build_youtube_url(song_name, artist_name):
    keyword = f"{artist_name} {song_name} 官方 MV 台語"
    return f"https://www.youtube.com/results?search_query={quote_plus(keyword)}"

def main():
    records = []
    seen_track_ids = set()

    for keyword in KEYWORDS:
        print(f"搜尋關鍵字：{keyword}")

        try:
            songs = search_itunes(keyword)
        except Exception as e:
            print(f"搜尋失敗：{e}")
            continue

        for song in songs:
            track_id = song.get("trackId")

            if track_id in seen_track_ids:
                continue

            seen_track_ids.add(track_id)

            track_name = song.get("trackName", "")
            artist_name = song.get("artistName", "")
            album_name = song.get("collectionName", "")
            release_date = song.get("releaseDate", "")
            genre = song.get("primaryGenreName", "")

            year = get_year(release_date)

            if year is None:
                continue

            if year < START_YEAR or year > END_YEAR:
                continue

            youtube_url = build_youtube_url(track_name, artist_name)

            records.append({
                "搜尋關鍵字": keyword,
                "年份": year,
                "歌手": artist_name,
                "歌名": track_name,
                "專輯": album_name,
                "發行日期": release_date[:10],
                "類型": genre,
                "YouTube搜尋網址": youtube_url
            })

    records.sort(
        key=lambda x: (x["年份"], x["歌手"], x["歌名"]),
        reverse=True
    )

    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "搜尋關鍵字",
                "年份",
                "歌手",
                "歌名",
                "專輯",
                "發行日期",
                "類型",
                "YouTube搜尋網址"
            ]
        )

        writer.writeheader()
        writer.writerows(records)

    print("完成")
    print(f"共蒐集：{len(records)} 筆")
    print(f"輸出檔案：{CSV_FILE}")

if __name__ == "__main__":
    main()