
import tkinter as tk
from tkinter import ttk, messagebox
import calendar
from datetime import datetime
from scheduler import wait_until
from config import save_config
from browser import open_and_prepare
from login import login
from booking import run_booking

AIRPORTS = [
    ("TSA", "台北松山"),
    ("TPE", "桃園國際"),
    ("KHH", "高雄小港"),
    ("RMQ", "台中清泉崗"),
    ("KNH", "金門尚義"),
    ("MZG", "馬公"),
    ("HUN", "花蓮"),
    ("TTT", "台東"),
    ("NRT", "東京成田"),
    ("HND", "東京羽田"),
    ("KIX", "大阪關西"),
    ("OKA", "沖繩那霸"),
    ("ICN", "首爾仁川"),
    ("BKK", "曼谷"),
    ("SIN", "新加坡"),
    ("HKG", "香港"),
]

AIRLINES = ["華信", "立榮"]
AIRPORT_DISPLAY = [f"{code} - {name}" for code, name in AIRPORTS]
TRIP_TYPES = ["單程", "來回程", "多目的地"]


class TicketGUI:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("訂票助手 V2（Playwright）")
        self.airline_vars = {}
        self.segments = []
        self.passenger_frame = None
        self.passenger_vars = []
        self.build()
        self._auto_resize()

    def build(self):

        row = 0
        ttk.Label(self.root, text="航空公司", font=("", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        frame_airline = ttk.Frame(self.root)
        frame_airline.grid(row=row, column=1, columnspan=5, sticky="w", padx=10, pady=5)
        for i, airline in enumerate(AIRLINES):
            var = tk.BooleanVar(value=(i == 0))
            self.airline_vars[airline] = var
            ttk.Checkbutton(frame_airline, text=airline, variable=var).pack(side="left", padx=8)

        row = 1
        ttk.Label(self.root, text="行程類型", font=("", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.trip_type = tk.StringVar(value="單程")
        frame_trip = ttk.Frame(self.root)
        frame_trip.grid(row=row, column=1, columnspan=5, sticky="w", padx=10, pady=5)
        for tt in TRIP_TYPES:
            ttk.Radiobutton(frame_trip, text=tt, variable=self.trip_type,
                             value=tt, command=self._on_trip_change).pack(side="left", padx=8)

        self.segment_frame = ttk.LabelFrame(self.root, text="航段資訊", padding=10)
        self.segment_frame.grid(row=2, column=0, columnspan=6, sticky="ew", padx=10, pady=5)
        self.root.grid_columnconfigure(0, weight=1)

        row = 3
        ttk.Label(self.root, text="人數", font=("", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.people = tk.IntVar(value=1)
        sp = ttk.Spinbox(self.root, from_=1, to=9, textvariable=self.people,
                     width=5, command=self._on_people_change)
        sp.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        self.people.trace_add("write", lambda *_: self._on_people_change())

        self.passenger_frame = ttk.LabelFrame(self.root, text="乘客資料", padding=10)
        self.passenger_frame.grid(row=4, column=0, columnspan=6, sticky="ew", padx=10, pady=5)
        self._build_passengers()

        row = 5
        ttk.Label(self.root, text="帳號", font=("", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.acc = tk.StringVar()
        ttk.Entry(self.root, textvariable=self.acc, width=30).grid(
            row=row, column=1, columnspan=3, sticky="w", padx=10, pady=5
        )

        row = 6
        ttk.Label(self.root, text="密碼", font=("", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.pwd = tk.StringVar()
        ttk.Entry(self.root, textvariable=self.pwd, show="*", width=30).grid(
            row=row, column=1, columnspan=3, sticky="w", padx=10, pady=5
        )

        row = 7
        ttk.Label(self.root, text="搶票開始時間", font=("", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.start_time = tk.StringVar(value="2026-07-04 13:30:00")
        start_frame = ttk.Frame(self.root)
        start_frame.grid(row=row, column=1, columnspan=3, sticky="w", padx=10, pady=5)
        ttk.Entry(start_frame, textvariable=self.start_time, width=20).pack(side="left")
        ttk.Button(start_frame, text="選擇", command=self.pick_start_time).pack(side="left", padx=5)

        row = 8
        btn_frame = ttk.Frame(self.root)
        btn_frame.grid(row=row, column=0, columnspan=6, pady=15)
        ttk.Button(btn_frame, text="儲存設定", command=self.save).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="開始搶票", command=self.start).pack(side="left", padx=10)

        self._on_trip_change()

    def _clear_segment_frame(self):
        for w in self.segment_frame.winfo_children():
            w.destroy()
        self.segments.clear()

    def _auto_resize(self):
        self.root.update_idletasks()
        self.root.geometry("")

    def _build_passengers(self):
        f = self.passenger_frame
        for w in f.winfo_children():
            w.destroy()
        self.passenger_vars.clear()

        n = self.people.get()
        ttk.Label(f, text="乘客", width=6, font=("", 9, "bold")).grid(row=0, column=0, padx=5)
        ttk.Label(f, text="姓名", width=15, font=("", 9, "bold")).grid(row=0, column=1, padx=5)
        ttk.Label(f, text="身分證號", width=15, font=("", 9, "bold")).grid(row=0, column=2, padx=5)

        for i in range(n):
            r = i + 1
            ttk.Label(f, text=f"乘客{i + 1}").grid(row=r, column=0, padx=5, pady=2)
            name_var = tk.StringVar()
            id_var = tk.StringVar()
            ttk.Entry(f, textvariable=name_var, width=18).grid(row=r, column=1, padx=5, pady=2)
            ttk.Entry(f, textvariable=id_var, width=18).grid(row=r, column=2, padx=5, pady=2)
            self.passenger_vars.append({"name": name_var, "id": id_var})

        self._auto_resize()

    def _on_people_change(self):
        try:
            n = self.people.get()
            if 1 <= n <= 9:
                self._build_passengers()
        except (tk.TclError, AttributeError):
            pass

    def _on_trip_change(self):
        self._clear_segment_frame()
        tt = self.trip_type.get()
        if tt == "單程":
            self._build_one_way()
        elif tt == "來回程":
            self._build_round_trip()
        else:
            self._build_multi_city()
        self._auto_resize()

    def _make_airport_combo(self, parent, default_idx=0):
        var = tk.StringVar(value=AIRPORT_DISPLAY[default_idx])
        combo = ttk.Combobox(parent, textvariable=var, values=AIRPORT_DISPLAY,
                              state="readonly", width=28)
        return var, combo

    def _make_date_entry(self, parent, default="2026-10-09"):
        var = tk.StringVar(value=default)
        frame = ttk.Frame(parent)
        ttk.Entry(frame, textvariable=var, width=12).pack(side="left")
        ttk.Button(frame, text="選擇", width=4,
                    command=lambda: self._pick_date_for(var)).pack(side="left", padx=2)
        return var, frame

    def _make_time_spinbox(self, parent, default_h="06", default_m="00"):
        h = tk.StringVar(value=default_h)
        m = tk.StringVar(value=default_m)
        frame = ttk.Frame(parent)
        ttk.Spinbox(frame, from_=0, to=23, width=3, format="%02.0f",
                     textvariable=h).pack(side="left")
        ttk.Label(frame, text=":").pack(side="left")
        ttk.Spinbox(frame, from_=0, to=59, width=3, format="%02.0f",
                     textvariable=m).pack(side="left")
        return h, m, frame

    def _build_one_way(self):
        f = self.segment_frame

        ttk.Label(f, text="出發地").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        dep_var, dep_combo = self._make_airport_combo(f, 0)
        dep_combo.grid(row=0, column=1, padx=5, pady=3)

        ttk.Label(f, text="目的地").grid(row=0, column=2, sticky="w", padx=5, pady=3)
        arr_var, arr_combo = self._make_airport_combo(f, 4)
        arr_combo.grid(row=0, column=3, padx=5, pady=3)

        ttk.Label(f, text="日期").grid(row=1, column=0, sticky="w", padx=5, pady=3)
        date_var, date_frame = self._make_date_entry(f)
        date_frame.grid(row=1, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(f, text="時間").grid(row=1, column=2, sticky="w", padx=5, pady=3)
        h, m, time_frame = self._make_time_spinbox(f)
        time_frame.grid(row=1, column=3, sticky="w", padx=5, pady=3)

        self.segments.append({
            "dep": dep_var, "arr": arr_var,
            "date": date_var, "hour": h, "minute": m
        })

    def _build_round_trip(self):
        f = self.segment_frame

        ttk.Label(f, text="出發地").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        dep_var, dep_combo = self._make_airport_combo(f, 0)
        dep_combo.grid(row=0, column=1, padx=5, pady=3)

        ttk.Label(f, text="目的地").grid(row=0, column=2, sticky="w", padx=5, pady=3)
        arr_var, arr_combo = self._make_airport_combo(f, 4)
        arr_combo.grid(row=0, column=3, padx=5, pady=3)

        ttk.Label(f, text="去程日期").grid(row=1, column=0, sticky="w", padx=5, pady=3)
        dep_date_var, dep_date_frame = self._make_date_entry(f)
        dep_date_frame.grid(row=1, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(f, text="回程日期").grid(row=1, column=2, sticky="w", padx=5, pady=3)
        ret_date_var, ret_date_frame = self._make_date_entry(f, "2026-10-16")
        ret_date_frame.grid(row=1, column=3, sticky="w", padx=5, pady=3)

        ttk.Label(f, text="去程時間").grid(row=2, column=0, sticky="w", padx=5, pady=3)
        h, m, time_frame = self._make_time_spinbox(f)
        time_frame.grid(row=2, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(f, text="回程時間").grid(row=2, column=2, sticky="w", padx=5, pady=3)
        rh, rm, ret_time_frame = self._make_time_spinbox(f, "18", "00")
        ret_time_frame.grid(row=2, column=3, sticky="w", padx=5, pady=3)

        self.segments.append({
            "dep": dep_var, "arr": arr_var,
            "dep_date": dep_date_var, "ret_date": ret_date_var,
            "hour": h, "minute": m,
            "ret_hour": rh, "ret_minute": rm
        })

    def _build_multi_city(self):
        f = self.segment_frame

        ttk.Button(f, text="+ 新增航段", command=self._add_segment).grid(
            row=0, column=0, columnspan=6, sticky="w", padx=5, pady=5
        )

        self._add_segment()

    def _add_segment(self):
        f = self.segment_frame
        idx = len(self.segments)
        row = idx + 1

        ttk.Label(f, text=f"航段 {idx + 1}").grid(row=row, column=0, sticky="w", padx=5, pady=2)

        dep_var, dep_combo = self._make_airport_combo(f, 0)
        dep_combo.grid(row=row, column=1, padx=3, pady=2)

        ttk.Label(f, text="→").grid(row=row, column=2, padx=2)
        arr_var, arr_combo = self._make_airport_combo(f, 4)
        arr_combo.grid(row=row, column=3, padx=3, pady=2)

        date_var, date_frame = self._make_date_entry(f)
        date_frame.grid(row=row, column=4, padx=3, pady=2)

        h, m, time_frame = self._make_time_spinbox(f)
        time_frame.grid(row=row, column=5, padx=3, pady=2)

        btn_del = ttk.Button(f, text="X", width=3,
                              command=lambda i=idx: self._remove_segment(i))
        btn_del.grid(row=row, column=6, padx=3, pady=2)

        self.segments.append({
            "dep": dep_var, "arr": arr_var,
            "date": date_var, "hour": h, "minute": m,
            "row": row, "del_btn": btn_del
        })
        self._auto_resize()

    def _remove_segment(self, idx):
        if len(self.segments) <= 1:
            messagebox.showwarning("警告", "至少保留一個航段")
            return

        seg = self.segments[idx]
        row = seg["row"]

        for w in self.segment_frame.grid_slaves(row=row):
            w.grid_forget()

        self.segments.pop(idx)

        for i, s in enumerate(self.segments):
            s["row"] = i + 1
        self._auto_resize()

    def _pick_date_for(self, date_var):
        top = tk.Toplevel(self.root)
        top.title("選擇日期")
        top.geometry("320x340")
        top.resizable(False, False)

        now = datetime.now()
        year = tk.IntVar(value=now.year)
        month = tk.IntVar(value=now.month)
        cal_frame = ttk.Frame(top)
        cal_frame.pack(fill="both", expand=True)

        def render():
            for w in cal_frame.winfo_children():
                w.destroy()

            ttk.Label(cal_frame, text=f"{year.get()} 年 {month.get()} 月",
                       font=("", 12, "bold")).grid(row=0, column=0, columnspan=7, pady=5)

            ttk.Button(cal_frame, text="<", width=3, command=prev).grid(row=1, column=0)
            ttk.Button(cal_frame, text=">", width=3, command=next_).grid(row=1, column=6)

            for i, d in enumerate(["一", "二", "三", "四", "五", "六", "日"]):
                ttk.Label(cal_frame, text=d, width=4, font=("", 9, "bold")).grid(row=2, column=i)

            cal = calendar.monthcalendar(year.get(), month.get())
            for r, week in enumerate(cal):
                for c, day in enumerate(week):
                    if day != 0:
                        ttk.Button(cal_frame, text=str(day), width=4,
                                    command=lambda d=day: select(d)).grid(row=r + 3, column=c)

        def prev():
            if month.get() == 1:
                month.set(12)
                year.set(year.get() - 1)
            else:
                month.set(month.get() - 1)
            render()

        def next_():
            if month.get() == 12:
                month.set(1)
                year.set(year.get() + 1)
            else:
                month.set(month.get() + 1)
            render()

        def select(day):
            date_var.set(f"{year.get():04d}-{month.get():02d}-{day:02d}")
            top.destroy()

        render()

    def pick_start_time(self):
        top = tk.Toplevel(self.root)
        top.title("選擇搶票開始時間")
        top.geometry("320x380")
        top.resizable(False, False)

        now = datetime.now()
        year = tk.IntVar(value=now.year)
        month = tk.IntVar(value=now.month)
        hour_var = tk.StringVar(value=f"{now.hour:02d}")
        min_var = tk.StringVar(value=f"{now.minute:02d}")

        time_frame = ttk.Frame(top)
        time_frame.pack(pady=5)
        ttk.Label(time_frame, text="時間: ").pack(side="left")
        ttk.Spinbox(time_frame, from_=0, to=23, width=3, format="%02.0f",
                     textvariable=hour_var).pack(side="left")
        ttk.Label(time_frame, text=" : ").pack(side="left")
        ttk.Spinbox(time_frame, from_=0, to=59, width=3, format="%02.0f",
                     textvariable=min_var).pack(side="left")

        cal_frame = ttk.Frame(top)
        cal_frame.pack(fill="both", expand=True)

        def render():
            for w in cal_frame.winfo_children():
                w.destroy()

            ttk.Label(cal_frame, text=f"{year.get()} 年 {month.get()} 月",
                       font=("", 12, "bold")).grid(row=0, column=0, columnspan=7, pady=5)

            ttk.Button(cal_frame, text="<", width=3, command=prev).grid(row=1, column=0)
            ttk.Button(cal_frame, text=">", width=3, command=next_).grid(row=1, column=6)

            for i, d in enumerate(["一", "二", "三", "四", "五", "六", "日"]):
                ttk.Label(cal_frame, text=d, width=4, font=("", 9, "bold")).grid(row=2, column=i)

            cal = calendar.monthcalendar(year.get(), month.get())
            for r, week in enumerate(cal):
                for c, day in enumerate(week):
                    if day != 0:
                        ttk.Button(cal_frame, text=str(day), width=4,
                                    command=lambda d=day: select(d)).grid(row=r + 3, column=c)

        def prev():
            if month.get() == 1:
                month.set(12)
                year.set(year.get() - 1)
            else:
                month.set(month.get() - 1)
            render()

        def next_():
            if month.get() == 12:
                month.set(1)
                year.set(year.get() + 1)
            else:
                month.set(month.get() + 1)
            render()

        def select(day):
            ts = f"{year.get():04d}-{month.get():02d}-{day:02d} {hour_var.get()}:{min_var.get()}:00"
            self.start_time.set(ts)
            top.destroy()

        render()

    def _get_airport_code(self, display_str):
        return display_str.split(" - ")[0].strip()

    def _get_airport_name(self, display_str):
        return display_str.split(" - ")[1].strip() if " - " in display_str else display_str

    def _collect_segments(self):
        tt = self.trip_type.get()
        result = []
        for seg in self.segments:
            dep_code = self._get_airport_code(seg["dep"].get())
            dep_name = self._get_airport_name(seg["dep"].get())
            arr_code = self._get_airport_code(seg["arr"].get())
            arr_name = self._get_airport_name(seg["arr"].get())
            h = seg["hour"].get()
            m = seg["minute"].get()

            if tt == "來回程":
                rh = seg["ret_hour"].get()
                rm = seg["ret_minute"].get()
                result.append({
                    "dep_code": dep_code, "dep_name": dep_name,
                    "arr_code": arr_code, "arr_name": arr_name,
                    "dep_date": seg["dep_date"].get(),
                    "ret_date": seg["ret_date"].get(),
                    "flight_time": f"{h}:{m}",
                    "ret_flight_time": f"{rh}:{rm}",
                })
            else:
                result.append({
                    "dep_code": dep_code, "dep_name": dep_name,
                    "arr_code": arr_code, "arr_name": arr_name,
                    "date": seg["date"].get(),
                    "flight_time": f"{h}:{m}",
                })
        return result

    def _collect_passengers(self):
        result = []
        for pv in self.passenger_vars:
            result.append({
                "name": pv["name"].get(),
                "id": pv["id"].get(),
            })
        return result

    def save(self):
        selected = [a for a, v in self.airline_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("警告", "請至少選擇一家航空公司")
            return
        save_config({
            "airlines": selected,
            "trip_type": self.trip_type.get(),
            "segments": self._collect_segments(),
            "people": self.people.get(),
            "passengers": self._collect_passengers(),
            "account": self.acc.get(),
        })
        messagebox.showinfo("OK", "已儲存")

    def start(self):
        selected = [a for a, v in self.airline_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("警告", "請至少選擇一家航空公司")
            return

        info = {
            "airlines": selected,
            "trip_type": self.trip_type.get(),
            "segments": self._collect_segments(),
            "people": self.people.get(),
            "passengers": self._collect_passengers(),
        }

        def job():
            import threading

            account = self.acc.get()
            password = self.pwd.get()

            def book_airline(airline):
                print(f"=== 啟動 {airline} 訂票 ===")
                login(account, password)
                airline_info = {**info, "company": airline}
                p, b, page = open_and_prepare(airline)
                run_booking(p, b, page, airline_info)

            threads = []
            for airline in selected:
                t = threading.Thread(target=book_airline, args=(airline,), daemon=True)
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            print("所有航空公司訂票流程結束")

        wait_until(self.start_time.get(), job)
        tt = self.trip_type.get()
        n_seg = len(self.segments)
        msg = (f"將在 {self.start_time.get()}\n"
               f"同時為 {len(selected)} 家航空公司搶票\n"
               f"行程類型: {tt}，共 {n_seg} 個航段")
        messagebox.showinfo("已啟動", msg)

    def run(self):
        self.root.mainloop()
