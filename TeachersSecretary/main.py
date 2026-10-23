import json
import os
import random
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

APP_NAME = "Teacher's Secretary"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "teacher_secretary.json")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MOTIVATION_MESSAGES = [
    "One more class completed. Your effort is making a difference!",
    "Progress happens one lecture at a time. Keep going!",
    "You showed up, taught, and helped someone learn. That matters.",
    "Another lecture done. Take a breath, then tackle the next one.",
    "Every topic you teach becomes an opportunity for someone to grow.",
    "Small steps, consistent effort, meaningful progress. Keep it up!"
]

MODULES = [
    ("Attendance", "attendance"),
    ("Marks Analyzer", "marks"),
    ("Assignment Tracker", "assignments"),
    ("Personal Diary", "diary"),
    ("Student Doubt Desk", "doubts"),
]


def load_data():
    """Load app data from JSON; use an empty structure if no file exists."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        return {"schedules": [], "next_schedule_id": 1}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("Data file must contain a JSON object.")
        data.setdefault("schedules", [])
        data.setdefault("next_schedule_id", 1)
        return data
    except (OSError, json.JSONDecodeError, ValueError) as error:
        messagebox.showwarning(
            "Data file issue",
            "The saved data could not be read. A fresh in-memory data set will be used.\n\n"
            f"Details: {error}\n\nYour original file has not been deleted."
        )
        return {"schedules": [], "next_schedule_id": 1}


def save_data(data):
    """Write to a temporary file first, then replace the main data file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_path = DATA_FILE + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
    os.replace(temp_path, DATA_FILE)


def parse_time(value):
    """Accept 12-hour times (09:30 AM) and legacy 24-hour times (09:30)."""
    value = value.strip().upper()
    for time_format in ("%I:%M %p", "%H:%M"):
        try:
            return datetime.strptime(value, time_format).time()
        except ValueError:
            continue
    raise ValueError("Enter a valid time such as 09:30 AM or 02:15 PM.")


def parse_user_time(value, ampm):
    """Parse typed 12-hour time; a bare hour such as '11' means '11:00'."""
    value = value.strip()
    if not value:
        raise ValueError("Enter a lecture time, such as 09:30 or 11.")
    if ":" not in value:
        if not value.isdigit():
            raise ValueError("Enter numbers only, for example 11 or 11:30.")
        value += ":00"
    parts = value.split(":")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise ValueError("Use a time such as 09:30, or just 11 for 11:00.")
    hour, minute = int(parts[0]), int(parts[1])
    if not 1 <= hour <= 12:
        raise ValueError("Hour must be between 1 and 12 when using AM/PM.")
    if not 0 <= minute <= 59:
        raise ValueError("Minutes must be between 00 and 59.")
    suffix = ampm.strip().upper()
    if suffix not in ("AM", "PM"):
        raise ValueError("Choose AM or PM.")
    if suffix == "AM":
        hour = 0 if hour == 12 else hour
    else:
        hour = 12 if hour == 12 else hour + 12
    return datetime(2000, 1, 1, hour, minute).time()


def time_choices():
    """Create 15-minute time choices in 12-hour AM/PM format."""
    choices = []
    for hour in range(24):
        for minute in (0, 15, 30, 45):
            choices.append(datetime(2000, 1, 1, hour, minute).strftime("%I:%M %p"))
    return choices


def display_time(value):
    return datetime.strptime(value, "%H:%M").strftime("%I:%M %p")


def today_string():
    return datetime.now().strftime("%Y-%m-%d")


def calculate_grade(obtained, maximum):
    percentage = (obtained / maximum) * 100 if maximum else 0
    if percentage >= 90: grade = "A+"
    elif percentage >= 80: grade = "A"
    elif percentage >= 70: grade = "B"
    elif percentage >= 60: grade = "C"
    elif percentage >= 40: grade = "D"
    else: grade = "F"
    return percentage, grade


def overlaps(lecture_a, lecture_b):
    if lecture_a["day"] != lecture_b["day"]:
        return False
    start_a, end_a = parse_time(lecture_a["start"]), parse_time(lecture_a["end"])
    start_b, end_b = parse_time(lecture_b["start"]), parse_time(lecture_b["end"])
    return start_a < end_b and start_b < end_a


class TeacherSecretaryApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1050x720")
        self.root.minsize(850, 600)
        self.data = load_data()
        self.selected_schedule_id = None
        self.reminder_jobs = []
        self._doubt_check_job = None
        self._configure_style()
        self.show_home()
        self.schedule_reminders()
        self.schedule_doubt_notifications()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _configure_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("Section.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Big.TButton", font=("Segoe UI", 12, "bold"), padding=12)
        style.configure("Treeview", rowheight=28)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def save(self):
        try:
            save_data(self.data)
        except OSError as error:
            messagebox.showerror("Save failed", f"Could not save your data:\n{error}")

    def show_home(self):
        self.clear_window()
        container = ttk.Frame(self.root, padding=28)
        container.pack(fill="both", expand=True)
        ttk.Label(container, text="Teacher's Secretary", style="Title.TLabel").pack(pady=(35, 8))
        ttk.Label(container, text="Your classes. Your schedule. Your progress.", style="Subtitle.TLabel").pack(pady=(0, 35))
        button_frame = ttk.Frame(container)
        button_frame.pack()
        ttk.Button(button_frame, text="＋  New Schedule", style="Big.TButton", command=self.new_schedule).grid(row=0, column=0, padx=12, pady=10, sticky="ew")
        ttk.Button(button_frame, text="▤  My Schedule", style="Big.TButton", command=self.show_schedules).grid(row=1, column=0, padx=12, pady=10, sticky="ew")
        ttk.Label(container, text=f"{len(self.data['schedules'])} saved schedule(s)", style="Subtitle.TLabel").pack(pady=20)
        ttk.Label(container, text="Data is stored locally in the data folder.", style="Subtitle.TLabel").pack(side="bottom", pady=10)

    def new_schedule(self):
        self.clear_window()
        outer = ttk.Frame(self.root, padding=24)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Create a New Schedule", style="Title.TLabel").pack(anchor="w", pady=(0, 18))
        form = ttk.Frame(outer)
        form.pack(fill="x")
        ttk.Label(form, text="Class name and division (e.g. FYCO-A)").grid(row=0, column=0, sticky="w", pady=8)
        class_var = tk.StringVar()
        ttk.Entry(form, textvariable=class_var, width=36).grid(row=0, column=1, sticky="w", padx=12, pady=8)
        ttk.Label(form, text="Subject / course (optional)").grid(row=1, column=0, sticky="w", pady=8)
        subject_var = tk.StringVar()
        ttk.Entry(form, textvariable=subject_var, width=36).grid(row=1, column=1, sticky="w", padx=12, pady=8)
        ttk.Label(form, text="Number of weekly lectures").grid(row=2, column=0, sticky="w", pady=8)
        count_var = tk.IntVar(value=1)
        ttk.Spinbox(form, from_=1, to=30, textvariable=count_var, width=8).grid(row=2, column=1, sticky="w", padx=12, pady=8)
        ttk.Label(outer, text="For each lecture, choose a day, type a time (e.g. 09:30 or 11), choose AM/PM, and optionally enter a topic.", style="Subtitle.TLabel").pack(anchor="w", pady=(20, 8))

        lecture_frame = ttk.Frame(outer)
        lecture_frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(lecture_frame, highlightthickness=0, height=250)
        scrollbar = ttk.Scrollbar(lecture_frame, orient="vertical", command=canvas.yview)
        rows_frame = ttk.Frame(canvas)
        rows_frame.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=rows_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        headers = ["Lecture", "Day", "Start time (AM/PM)", "End time (AM/PM)", "Topic (optional)"]
        lecture_rows = []

        def rebuild_rows(*_args):
            for widget in rows_frame.winfo_children():
                widget.destroy()
            lecture_rows.clear()
            for col, header in enumerate(headers):
                ttk.Label(rows_frame, text=header, font=("Segoe UI", 9, "bold")).grid(row=0, column=col, padx=5, pady=5, sticky="w")
            try:
                number = max(1, min(int(count_var.get()), 30))
            except (ValueError, tk.TclError):
                number = 1
            for index in range(number):
                day_var = tk.StringVar(value=DAYS[index % 5])
                start_var, end_var, topic_var = tk.StringVar(value="09:00"), tk.StringVar(value="10:00"), tk.StringVar()
                start_ampm, end_ampm = tk.StringVar(value="AM"), tk.StringVar(value="AM")
                ttk.Label(rows_frame, text=str(index + 1)).grid(row=index + 1, column=0, padx=5, pady=4)
                ttk.Combobox(rows_frame, textvariable=day_var, values=DAYS, state="readonly", width=13).grid(row=index + 1, column=1, padx=5, pady=4)
                numeric_time_validation = (self.root.register(self.validate_time_text), "%P")
                start_frame = ttk.Frame(rows_frame)
                start_frame.grid(row=index + 1, column=2, padx=5, pady=4, sticky="w")
                ttk.Entry(start_frame, textvariable=start_var, width=7, validate="key", validatecommand=numeric_time_validation).pack(side="left")
                ttk.Combobox(start_frame, textvariable=start_ampm, values=("AM", "PM"), state="readonly", width=4).pack(side="left", padx=(3, 0))
                end_frame = ttk.Frame(rows_frame)
                end_frame.grid(row=index + 1, column=3, padx=5, pady=4, sticky="w")
                ttk.Entry(end_frame, textvariable=end_var, width=7, validate="key", validatecommand=numeric_time_validation).pack(side="left")
                ttk.Combobox(end_frame, textvariable=end_ampm, values=("AM", "PM"), state="readonly", width=4).pack(side="left", padx=(3, 0))
                ttk.Entry(rows_frame, textvariable=topic_var, width=24).grid(row=index + 1, column=4, padx=5, pady=4)
                lecture_rows.append({"day": day_var, "start": start_var, "start_ampm": start_ampm, "end": end_var, "end_ampm": end_ampm, "topic": topic_var})

        count_var.trace_add("write", rebuild_rows)
        rebuild_rows()
        reminder_var, popup_var = tk.BooleanVar(value=True), tk.BooleanVar(value=True)
        options = ttk.Frame(outer)
        options.pack(fill="x", pady=12)
        ttk.Checkbutton(options, text="Enable lecture reminders", variable=reminder_var).pack(side="left", padx=(0, 18))
        ttk.Checkbutton(options, text="Show in-app pop-ups", variable=popup_var).pack(side="left")
        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Cancel", command=self.show_home).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="Save Schedule", command=lambda: self.save_new_schedule(class_var.get(), subject_var.get(), lecture_rows, reminder_var.get(), popup_var.get())).pack(side="right")

    def validate_time_text(self, proposed):
        return proposed == "" or (proposed.count(":") <= 1 and all(ch.isdigit() or ch == ":" for ch in proposed))

    def save_new_schedule(self, class_name, subject, lecture_rows, reminders, popups):
        class_name = class_name.strip()
        if not class_name:
            messagebox.showerror("Missing class", "Enter a class name and division, such as FYCO-A.")
            return
        lectures = []
        try:
            for row in lecture_rows:
                start = parse_user_time(row["start"].get(), row["start_ampm"].get())
                end = parse_user_time(row["end"].get(), row["end_ampm"].get())
                if start >= end:
                    raise ValueError("Each lecture's end time must be later than its start time.")
                lectures.append({"day": row["day"].get(), "start": start.strftime("%H:%M"), "end": end.strftime("%H:%M"), "topic": row["topic"].get().strip(), "topic_covered": False})
        except ValueError as error:
            messagebox.showerror("Invalid lecture time", f"Choose a valid time in AM/PM format, such as 09:30 AM or 02:15 PM.\n\n{error}")
            return

        conflicts = []
        for i in range(len(lectures)):
            for j in range(i + 1, len(lectures)):
                if overlaps(lectures[i], lectures[j]):
                    conflicts.append(f"{lectures[i]['day']} {lectures[i]['start']}-{lectures[i]['end']} overlaps {lectures[j]['start']}-{lectures[j]['end']}")
        if conflicts and not messagebox.askyesno("Schedule conflicts", "Some lectures overlap:\n\n" + "\n".join(conflicts) + "\n\nSave anyway? Conflicts will remain visible."):
            return

        schedule = {"id": self.data["next_schedule_id"], "name": class_name, "subject": subject.strip(), "lectures": lectures, "reminders_enabled": bool(reminders), "popups_enabled": bool(popups), "created_at": datetime.now().isoformat(timespec="seconds"), "syllabus_topics": [], "combined_from": [], "conflicts": conflicts}
        self.data["next_schedule_id"] += 1

        if not self.data["schedules"]:
            self.data["schedules"].append(schedule)
            self.save()
            messagebox.showinfo("Schedule created", "Your first schedule has been saved.")
            self.show_schedule_detail(schedule["id"])
            return

        choice = messagebox.askyesnocancel("Combine schedules?", "Combine this new schedule with an existing schedule?\n\nYes = choose a schedule to combine with\nNo = keep separate\nCancel = discard this new schedule")
        if choice is None:
            return
        if not choice:
            self.data["schedules"].append(schedule)
            self.save()
            messagebox.showinfo("Schedule created", "The new schedule is saved separately.")
            self.show_schedule_detail(schedule["id"])
            return

        selected = self.choose_schedule_dialog(list(self.data["schedules"]))
        if selected is None:
            return
        combined = self.combine_schedules(selected, schedule)
        self.data["schedules"].extend([schedule, combined])
        self.save()
        messagebox.showinfo("Schedules combined", "A combined overview was created. Original schedules remain saved separately.")
        self.show_schedule_detail(combined["id"])

    def choose_schedule_dialog(self, schedules):
        dialog = tk.Toplevel(self.root)
        dialog.title("Choose schedule to combine")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("420x300")
        ttk.Label(dialog, text="Combine the new schedule with:", style="Section.TLabel").pack(anchor="w", padx=16, pady=16)
        listbox = tk.Listbox(dialog, height=8, exportselection=False)
        listbox.pack(fill="both", expand=True, padx=16)
        for item in schedules:
            listbox.insert("end", f"#{item['id']}  {item['name']}")
        result = {"schedule": None}

        def choose():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Select a schedule", "Choose a schedule from the list.", parent=dialog)
                return
            result["schedule"] = schedules[selection[0]]
            dialog.destroy()

        ttk.Button(dialog, text="Combine", command=choose).pack(pady=12)
        self.root.wait_window(dialog)
        return result["schedule"]

    def combine_schedules(self, first, second):
        lectures = [dict(item) for item in first["lectures"]] + [dict(item) for item in second["lectures"]]
        conflicts = []
        for i in range(len(lectures)):
            for j in range(i + 1, len(lectures)):
                if overlaps(lectures[i], lectures[j]):
                    conflicts.append(f"{lectures[i]['day']} {lectures[i]['start']}-{lectures[i]['end']} conflicts with {lectures[j]['start']}-{lectures[j]['end']}")
        combined = {"id": self.data["next_schedule_id"], "name": f"{first['name']} + {second['name']} (Combined)", "subject": "Combined schedule overview", "lectures": lectures, "reminders_enabled": first["reminders_enabled"] or second["reminders_enabled"], "popups_enabled": first["popups_enabled"] or second["popups_enabled"], "created_at": datetime.now().isoformat(timespec="seconds"), "syllabus_topics": [], "combined_from": [first["id"], second["id"]], "conflicts": conflicts}
        self.data["next_schedule_id"] += 1
        return combined

    def show_schedules(self):
        self.clear_window()
        outer = ttk.Frame(self.root, padding=24)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="My Schedule", style="Title.TLabel").pack(anchor="w", pady=(0, 16))
        if not self.data["schedules"]:
            ttk.Label(outer, text="No schedules yet. Create your first schedule to get started.").pack(anchor="w", pady=12)
        else:
            tree = ttk.Treeview(outer, columns=("id", "name", "lectures", "reminders"), show="headings", selectmode="extended")
            for column, title, width in [("id", "ID", 60), ("name", "Schedule / Class", 440), ("lectures", "Lectures", 100), ("reminders", "Reminders", 120)]:
                tree.heading(column, text=title)
                tree.column(column, width=width, anchor="w")
            tree.pack(fill="both", expand=True)
            for schedule in self.data["schedules"]:
                tree.insert("", "end", iid=str(schedule["id"]), values=(schedule["id"], schedule["name"], len(schedule["lectures"]), "On" if schedule["reminders_enabled"] else "Off"))

            def open_selected(_event=None):
                selected = tree.selection()
                if selected:
                    self.show_schedule_detail(int(selected[0]))

            tree.bind("<Double-1>", open_selected)
            ttk.Label(outer, text="Double-click a schedule to open it.", style="Subtitle.TLabel").pack(anchor="w", pady=8)
            button_row = ttk.Frame(outer)
            button_row.pack(fill="x", pady=8)
            ttk.Button(button_row, text="Open Selected", command=open_selected).pack(side="left")
            ttk.Button(button_row, text="Combine Selected", command=lambda: self.combine_selected_schedules(tree)).pack(side="left", padx=8)
            ttk.Button(button_row, text="Keep Selected Separate", command=lambda: self.keep_selected_separate(tree)).pack(side="left", padx=8)
            ttk.Button(button_row, text="Delete Selected", command=lambda: self.delete_selected_schedule(tree)).pack(side="left", padx=8)
        ttk.Button(outer, text="← Home", command=self.show_home).pack(anchor="e", pady=8)

    def combine_selected_schedules(self, tree):
        """Let the teacher choose individual lectures from all saved schedules."""
        all_lectures = []
        for schedule in self.data["schedules"]:
            for lecture_index, lecture in enumerate(schedule.get("lectures", [])):
                all_lectures.append({"schedule": schedule, "lecture": lecture,
                                     "lecture_index": lecture_index, "source_name": schedule["name"]})

        if len(all_lectures) < 2:
            messagebox.showwarning("Not enough lectures", "You need at least 2 scheduled lectures before you can combine them.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Combine Scheduled Lectures")
        dialog.geometry("950x560")
        dialog.minsize(760, 420)
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Choose at least 2 lectures to be combined", style="Section.TLabel").pack(anchor="w", padx=18, pady=(18, 6))
        ttk.Label(dialog, text="Select individual lectures from any saved schedule. Original schedules will remain unchanged.", style="Subtitle.TLabel").pack(anchor="w", padx=18, pady=(0, 12))

        table_frame = ttk.Frame(dialog, padding=(18, 0, 18, 8))
        table_frame.pack(fill="both", expand=True)
        columns = ("class", "day", "start", "end", "topic")
        lecture_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")
        headings = {"class": ("Schedule / Class", 250), "day": ("Day", 120), "start": ("Start time", 145), "end": ("End time", 145), "topic": ("Topic", 260)}
        for column, (heading, width) in headings.items():
            lecture_tree.heading(column, text=heading)
            lecture_tree.column(column, width=width, anchor="w")
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=lecture_tree.yview)
        lecture_tree.configure(yscrollcommand=yscroll.set)
        lecture_tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        for row_id, item in enumerate(all_lectures):
            lecture = item["lecture"]
            lecture_tree.insert("", "end", iid=str(row_id), values=(item["source_name"], lecture["day"], display_time(lecture["start"]), display_time(lecture["end"]), lecture.get("topic") or "(topic not set)"))

        selection_label = ttk.Label(dialog, text="0 lectures selected")
        selection_label.pack(anchor="w", padx=18, pady=4)
        lecture_tree.bind("<<TreeviewSelect>>", lambda _event: selection_label.configure(text=f"{len(lecture_tree.selection())} lecture(s) selected"))

        # A normal click toggles a row, so users need not hold Ctrl or Shift.
        def toggle_lecture_selection(event):
            row_id = lecture_tree.identify_row(event.y)
            if not row_id:
                return
            if row_id in lecture_tree.selection():
                lecture_tree.selection_remove(row_id)
            else:
                lecture_tree.selection_add(row_id)
            selection_label.configure(text=f"{len(lecture_tree.selection())} lecture(s) selected")
            return "break"

        lecture_tree.bind("<Button-1>", toggle_lecture_selection)
        button_row = ttk.Frame(dialog, padding=18)
        button_row.pack(fill="x")

        def combine_chosen():
            selected_rows = lecture_tree.selection()
            if len(selected_rows) < 2:
                messagebox.showwarning("Choose at least 2 lectures", "Choose at least 2 lectures to be combined.", parent=dialog)
                return
            chosen, source_ids = [], []
            selected_items = [all_lectures[int(row)] for row in selected_rows]
            for item in selected_items:
                lecture_copy = dict(item["lecture"])
                lecture_copy["source_class"] = item["source_name"]
                chosen.append(lecture_copy)
                if item["schedule"]["id"] not in source_ids:
                    source_ids.append(item["schedule"]["id"])

            conflicts = []
            for i in range(len(chosen)):
                for j in range(i + 1, len(chosen)):
                    if overlaps(chosen[i], chosen[j]):
                        conflicts.append(f"{chosen[i]['day']} {display_time(chosen[i]['start'])}-{display_time(chosen[i]['end'])} overlaps with {chosen[j]['source_class']} at {display_time(chosen[j]['start'])}-{display_time(chosen[j]['end'])}")
            if conflicts and not messagebox.askyesno("Lecture conflicts detected", "Some selected lectures overlap:\n\n" + "\n".join(conflicts) + "\n\nCreate the combined schedule anyway?", parent=dialog):
                return

            combined = {
                "id": self.data["next_schedule_id"],
                "name": f"Combined Lectures ({len(chosen)})",
                "subject": "Combined lecture overview",
                "lectures": chosen,
                "reminders_enabled": any(item["schedule"].get("reminders_enabled", True) for item in selected_items),
                "popups_enabled": any(item["schedule"].get("popups_enabled", True) for item in selected_items),
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "syllabus_topics": [], "combined_from": source_ids, "conflicts": conflicts,
            }
            self.data["next_schedule_id"] += 1
            self.data["schedules"].append(combined)
            self.save()
            dialog.destroy()
            messagebox.showinfo("Lectures combined", f"A new combined schedule containing {len(chosen)} lectures has been created.\n\nAll original schedules remain unchanged.")
            self.show_schedule_detail(combined["id"])

        ttk.Button(button_row, text="Combine", command=combine_chosen).pack(side="right", padx=(8, 0))
        ttk.Button(button_row, text="Cancel", command=dialog.destroy).pack(side="right")

    def keep_selected_separate(self, tree):
        selected_ids = tree.selection()
        if not selected_ids:
            messagebox.showwarning("Select schedules", "Select one or more schedules first.")
            return
        messagebox.showinfo("Schedules kept separate", "The selected schedules remain independent. No data has been merged or changed.")

    def delete_selected_schedule(self, tree):
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select a schedule first.")
            return
        schedule_id = int(selected[0])
        schedule = self.get_schedule(schedule_id)
        if schedule and messagebox.askyesno("Delete schedule", f"Delete '{schedule['name']}'?\nThis cannot be undone."):
            self.data["schedules"] = [item for item in self.data["schedules"] if item["id"] != schedule_id]
            self.save()
            self.show_schedules()

    def get_schedule(self, schedule_id):
        return next((schedule for schedule in self.data["schedules"] if schedule["id"] == schedule_id), None)

    def show_schedule_detail(self, schedule_id):
        schedule = self.get_schedule(schedule_id)
        if schedule is None:
            messagebox.showerror("Schedule not found", "This schedule no longer exists.")
            self.show_schedules()
            return
        self.selected_schedule_id = schedule_id
        self.clear_window()
        outer = ttk.Frame(self.root, padding=22)
        outer.pack(fill="both", expand=True)
        top = ttk.Frame(outer)
        top.pack(fill="x", pady=(0, 12))
        ttk.Label(top, text=schedule["name"], style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="← My Schedule", command=self.show_schedules).pack(side="right")
        ttk.Label(outer, text=f"Subject: {schedule.get('subject') or 'Not specified'}   |   Weekly lectures: {len(schedule['lectures'])}", style="Subtitle.TLabel").pack(anchor="w", pady=(0, 12))

        tree = ttk.Treeview(outer, columns=("day", "start", "end", "topic", "covered"), show="headings", height=10)
        for col, title, width in [("day", "Day", 120), ("start", "Start (AM/PM)", 120), ("end", "End (AM/PM)", 120), ("topic", "Topic", 360), ("covered", "Lecture marked complete", 150)]:
            tree.heading(col, text=title)
            tree.column(col, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        ordered = sorted(schedule["lectures"], key=lambda item: (DAYS.index(item["day"]), item["start"]))
        for index, lecture in enumerate(ordered):
            tree.insert("", "end", iid=str(index), values=(lecture["day"], display_time(lecture["start"]), display_time(lecture["end"]), lecture.get("topic") or "(topic not set)", "Yes" if lecture.get("topic_covered") else "No"))

        if schedule.get("conflicts"):
            ttk.Label(outer, text=f"⚠ {len(schedule['conflicts'])} overlapping lecture pair(s) detected.", foreground="#b45309").pack(anchor="w", pady=6)
        self.update_progress_display(outer, schedule)
        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=12)
        ttk.Button(actions, text="Mark Lecture Completed", command=lambda: self.mark_lecture_completed(schedule, tree, ordered)).pack(side="left")
        ttk.Button(actions, text="Delete Selected Lecture", command=lambda: self.delete_lecture(schedule, tree, ordered)).pack(side="left", padx=8)
        ttk.Button(actions, text="Manage Syllabus Topics", command=lambda: self.manage_topics(schedule)).pack(side="left", padx=8)
        ttk.Button(actions, text="Open Five Modules", command=lambda: self.show_modules(schedule)).pack(side="left", padx=8)
        ttk.Button(actions, text="Edit Reminders", command=lambda: self.edit_reminders(schedule)).pack(side="left")

    def delete_lecture(self, schedule, tree, ordered):
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Select lecture", "Select the lecture you want to delete.")
            return
        try:
            lecture = ordered[int(selected[0])]
        except (ValueError, IndexError):
            messagebox.showerror("Selection error", "Please select a valid lecture and try again.")
            return
        description = f"{lecture['day']} {display_time(lecture['start'])}-{display_time(lecture['end'])}"
        if not messagebox.askyesno("Delete lecture", f"Delete this lecture?\n{description}\n\nThis cannot be undone."):
            return
        # Find the exact lecture by object identity, avoiding accidental deletion of a duplicate.
        for index, item in enumerate(schedule.get("lectures", [])):
            if item is lecture:
                del schedule["lectures"][index]
                break
        else:
            messagebox.showerror("Lecture not found", "This lecture could not be found in the saved schedule.")
            return
        self.save()
        self.show_schedule_detail(schedule["id"])
        messagebox.showinfo("Lecture deleted", "The selected lecture was deleted successfully.")

    def update_progress_display(self, parent, schedule):
        topics = schedule.get("syllabus_topics", [])
        total = len(topics)
        done = sum(1 for topic in topics if topic.get("covered"))
        percent = round(done / total * 100) if total else 0
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=4)
        ttk.Label(frame, text=f"Syllabus progress: {done}/{total} topics covered ({percent}%)").pack(anchor="w")
        ttk.Progressbar(frame, maximum=100, value=percent).pack(fill="x", pady=4)
        if not total:
            ttk.Label(frame, text="Add syllabus topics to calculate covered/uncovered progress.", style="Subtitle.TLabel").pack(anchor="w")

    def mark_lecture_completed(self, schedule, tree, ordered):
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Select lecture", "Select a lecture first.")
            return
        lecture = ordered[int(selected[0])]
        lecture["last_completed"] = datetime.now().isoformat(timespec="seconds")
        lecture["topic_covered"] = True
        self.save()
        messagebox.showinfo("Lecture completed", random.choice(MOTIVATION_MESSAGES))
        self.show_schedule_detail(schedule["id"])

    def manage_topics(self, schedule):
        dialog = tk.Toplevel(self.root)
        dialog.title("Syllabus Topics")
        dialog.geometry("500x430")
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Syllabus Topics", style="Section.TLabel").pack(anchor="w", padx=16, pady=12)
        entry_row = ttk.Frame(dialog)
        entry_row.pack(fill="x", padx=16)
        topic_var = tk.StringVar()
        ttk.Entry(entry_row, textvariable=topic_var).pack(side="left", fill="x", expand=True)
        listbox = tk.Listbox(dialog, height=12, selectmode="extended")
        listbox.pack(fill="both", expand=True, padx=16, pady=12)

        def refresh():
            listbox.delete(0, "end")
            for topic in schedule.get("syllabus_topics", []):
                listbox.insert("end", f"{'✓' if topic.get('covered') else '○'} {topic['name']}")

        def add_topic():
            name = topic_var.get().strip()
            if not name:
                messagebox.showwarning("Missing topic", "Enter a topic name.", parent=dialog)
                return
            schedule.setdefault("syllabus_topics", []).append({"name": name, "covered": False})
            topic_var.set("")
            self.save()
            refresh()

        def toggle_topics():
            selected = listbox.curselection()
            if not selected:
                messagebox.showwarning("Select topics", "Select one or more topics.", parent=dialog)
                return
            for index in selected:
                topic = schedule["syllabus_topics"][index]
                topic["covered"] = not topic.get("covered", False)
            self.save()
            refresh()

        buttons = ttk.Frame(dialog)
        buttons.pack(fill="x", padx=16, pady=(0, 12))
        ttk.Button(buttons, text="Add Topic", command=add_topic).pack(side="left")
        ttk.Button(buttons, text="Topic Covered", command=toggle_topics).pack(side="left", padx=8)
        ttk.Button(buttons, text="Close", command=lambda: (dialog.destroy(), self.show_schedule_detail(schedule["id"]))).pack(side="right")
        refresh()

    def edit_reminders(self, schedule):
        dialog = tk.Toplevel(self.root)
        dialog.title("Reminder Settings")
        dialog.geometry("380x200")
        dialog.transient(self.root)
        dialog.grab_set()
        reminder_var = tk.BooleanVar(value=schedule.get("reminders_enabled", True))
        popup_var = tk.BooleanVar(value=schedule.get("popups_enabled", True))
        ttk.Label(dialog, text="Schedule notifications", style="Section.TLabel").pack(anchor="w", padx=16, pady=14)
        ttk.Checkbutton(dialog, text="Enable lecture reminders", variable=reminder_var).pack(anchor="w", padx=16, pady=4)
        ttk.Checkbutton(dialog, text="Show in-app pop-ups", variable=popup_var).pack(anchor="w", padx=16, pady=4)

        def save_settings():
            schedule["reminders_enabled"] = reminder_var.get()
            schedule["popups_enabled"] = popup_var.get()
            self.save()
            dialog.destroy()
            self.schedule_reminders()
            self.show_schedule_detail(schedule["id"])

        ttk.Button(dialog, text="Save", command=save_settings).pack(pady=14)

    def show_modules(self, schedule):
        self.clear_window()
        outer = ttk.Frame(self.root, padding=24)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text=f"Modules: {schedule['name']}", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(outer, text="Choose a module. These starter pages reserve the navigation; full workflows come next.", style="Subtitle.TLabel").pack(anchor="w", pady=(0, 20))
        for title, key in MODULES:
            ttk.Button(outer, text=title, style="Big.TButton", command=lambda k=key, t=title: self.open_module(schedule, k, t)).pack(fill="x", pady=5)
        ttk.Button(outer, text="← Back to Schedule", command=lambda: self.show_schedule_detail(schedule["id"])).pack(anchor="e", pady=16)

    def open_module(self, schedule, module_key, module_title):
        if module_key == "attendance":
            self.show_attendance_module(schedule)
        elif module_key == "diary":
            self.manage_personal_diary(schedule)
        elif module_key == "doubts":
            self.show_doubt_desk(schedule)
        else:
            descriptions = {
                "marks": "Calculate averages, topper, second-highest distinct marks, fail list, and grade distribution.",
                "assignments": "Track assignments by class, due date, submitted work, pending work, and late submissions."
            }
            messagebox.showinfo(module_title, f"Class / schedule: {schedule['name']}\n\n{descriptions[module_key]}\n\nThis module will be implemented in a later development phase.")

    def manage_personal_diary(self, schedule):
        """Personal Diary uses the same simple topic-list interaction as Syllabus Topics."""
        schedule.setdefault("personal_diary_topics", [])
        dialog = tk.Toplevel(self.root)
        dialog.title("Personal Diary")
        dialog.geometry("1200x800")
        try:
            dialog.state("zoomed")
        except tk.TclError:
            pass
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Personal Diary", style="Section.TLabel").pack(anchor="w", padx=16, pady=12)
        entry_row = ttk.Frame(dialog)
        entry_row.pack(fill="x", padx=16)
        item_var = tk.StringVar()
        ttk.Entry(entry_row, textvariable=item_var).pack(side="left", fill="x", expand=True)
        listbox = tk.Listbox(dialog, height=12, selectmode="extended")
        listbox.pack(fill="both", expand=True, padx=16, pady=12)

        def refresh():
            listbox.delete(0, "end")
            for item in schedule.get("personal_diary_topics", []):
                listbox.insert("end", f"{'✓' if item.get('covered') else '○'} {item['name']}")

        def add_item():
            name = item_var.get().strip()
            if not name:
                messagebox.showwarning("Missing entry", "Enter a diary entry, task, meeting, note, or personal item.", parent=dialog)
                return
            schedule.setdefault("personal_diary_topics", []).append({"name": name, "covered": False, "created_at": datetime.now().isoformat(timespec="seconds")})
            item_var.set("")
            self.save()
            refresh()

        def mark_covered():
            selected = listbox.curselection()
            if not selected:
                messagebox.showwarning("Select entries", "Select one or more diary entries first.", parent=dialog)
                return
            for index in selected:
                item = schedule["personal_diary_topics"][index]
                item["covered"] = not item.get("covered", False)
            self.save()
            refresh()

        buttons = ttk.Frame(dialog)
        buttons.pack(fill="x", padx=16, pady=(0, 12))
        ttk.Button(buttons, text="Add Topic", command=add_item).pack(side="left")
        ttk.Button(buttons, text="Topic Covered", command=mark_covered).pack(side="left", padx=8)
        ttk.Button(buttons, text="Close", command=dialog.destroy).pack(side="right")
        refresh()

    def show_doubt_desk(self, schedule):
        """Show an inline empty state; unresolved doubts trigger hourly reminders."""
        schedule.setdefault("student_doubts", [])
        self.clear_window()
        outer = ttk.Frame(self.root, padding=24)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="Module 5: Student Doubt Desk", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="← Modules", command=lambda: self.show_modules(schedule)).pack(side="right")
        ttk.Label(outer, text=f"Class: {schedule['name']}", style="Subtitle.TLabel").pack(anchor="w", pady=(0, 12))

        unresolved = [d for d in schedule["student_doubts"] if not d.get("solved", False)]
        if not schedule["student_doubts"]:
            empty_text = "No doubts have been received yet.\n\n(If doubt is received then after every hour the user will get a notification from app to solve the doubt.\n\nThis notification will continue to come until the doubt is solved)"
            ttk.Label(outer, text=empty_text, justify="left", wraplength=850).pack(anchor="w", pady=18)
        else:
            ttk.Label(outer, text="Student doubts", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
            columns = ("student", "doubt", "status")
            tree = ttk.Treeview(outer, columns=columns, show="headings", height=12, selectmode="browse")
            tree.heading("student", text="Student")
            tree.heading("doubt", text="Doubt")
            tree.heading("status", text="Status")
            tree.column("student", width=180)
            tree.column("doubt", width=600)
            tree.column("status", width=120)
            tree.pack(fill="both", expand=True)
            for index, doubt in enumerate(schedule["student_doubts"]):
                tree.insert("", "end", iid=str(index), values=(doubt.get("student", "Unknown"), doubt.get("text", ""), "Solved" if doubt.get("solved") else "Unresolved"))

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=14)

        def mark_solved():
            tree_widget = next((w for w in outer.winfo_children() if isinstance(w, ttk.Treeview)), None)
            if tree_widget is None or not tree_widget.selection():
                messagebox.showwarning("Select a doubt", "Select a doubt to mark it solved.")
                return
            doubt = schedule["student_doubts"][int(tree_widget.selection()[0])]
            doubt["solved"] = True
            doubt["solved_at"] = datetime.now().isoformat(timespec="seconds")
            self.save()
            self.show_doubt_desk(schedule)

        if schedule["student_doubts"]:
            ttk.Button(actions, text="Mark Selected Solved", command=mark_solved).pack(side="left", padx=8)

    def schedule_doubt_notifications(self):
        """Check hourly and remind about unresolved doubts without interrupting empty desks."""
        if self._doubt_check_job is not None:
            try:
                self.root.after_cancel(self._doubt_check_job)
            except tk.TclError:
                pass
        self._doubt_check_job = self.root.after(60 * 60 * 1000, self.check_doubt_notifications)

    def check_doubt_notifications(self):
        now = datetime.now()
        due = []
        for schedule in self.data.get("schedules", []):
            for doubt in schedule.get("student_doubts", []):
                if doubt.get("solved", False):
                    continue
                last = doubt.get("last_notified") or doubt.get("created_at")
                try:
                    last_time = datetime.fromisoformat(last) if last else now
                except ValueError:
                    last_time = now
                if (now - last_time).total_seconds() >= 3600:
                    due.append((schedule, doubt))
                    doubt["last_notified"] = now.isoformat(timespec="seconds")
        if due:
            summary = "\n".join(f"• {schedule['name']}: {doubt.get('student', 'Student')} — {doubt.get('text', '')[:100]}" for schedule, doubt in due[:8])
            messagebox.showinfo("Unresolved student doubts", "These doubts still need attention:\n\n" + summary)
            self.save()
        self.schedule_doubt_notifications()

    def _ensure_class_records(self, schedule):
        schedule.setdefault("students", [])
        schedule.setdefault("attendance_records", [])
        schedule.setdefault("marks_records", [])
        schedule.setdefault("assignments", [])

    def show_attendance_module(self, schedule):
        self._ensure_class_records(schedule)
        # Add fields for older student records without discarding saved data.
        for student in schedule["students"]:
            student.setdefault("college_id", "")
            student.setdefault("roll", "")
            student.setdefault("name", "")

        self.clear_window()
        outer = ttk.Frame(self.root, padding=22)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="Module 1: Attendance", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="← Modules", command=lambda: self.show_modules(schedule)).pack(side="right")
        ttk.Label(outer, text=f"Class: {schedule['name']}  |  Student and attendance records are saved automatically", style="Subtitle.TLabel").pack(anchor="w", pady=(0, 8))

        # Three linked date selectors. All dates from 1 Jan 2025 through today are selectable.
        from calendar import monthrange
        start_date = datetime(2025, 1, 1).date()
        today_date = datetime.now().date()
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        date_bar = ttk.Frame(outer)
        date_bar.pack(fill="x", pady=(0, 8))
        ttk.Label(date_bar, text="Attendance date:").pack(side="left", padx=(0, 8))
        selected_day = tk.StringVar(value=str(today_date.day))
        selected_month = tk.StringVar(value=months[today_date.month - 1])
        selected_year = tk.StringVar(value=str(today_date.year))
        day_picker = ttk.Combobox(date_bar, textvariable=selected_day, state="readonly", width=4)
        month_picker = ttk.Combobox(date_bar, textvariable=selected_month, values=months, state="readonly", width=12)
        year_picker = ttk.Combobox(date_bar, textvariable=selected_year, values=["2025", "2026"], state="readonly", width=6)
        day_picker.pack(side="left", padx=(0, 5))
        month_picker.pack(side="left", padx=5)
        year_picker.pack(side="left", padx=5)
        ttk.Label(date_bar, text="Day / Month / Year  |  Dates available from 1 January 2025 through today.", style="Subtitle.TLabel").pack(side="left", padx=10)

        columns = ("college_id", "roll", "name", "attendance", "percentage")
        tree = ttk.Treeview(outer, columns=columns, show="headings", height=12, selectmode="browse")
        headers = [
            ("college_id", "College ID", 150),
            ("roll", "Roll no", 120),
            ("name", "Student Name", 300),
            ("attendance", "Attendance", 180),
            ("percentage", "Percentage", 130),
        ]
        for col, label, width in headers:
            tree.heading(col, text=label)
            tree.column(col, width=width, anchor="w")
        tree.pack(fill="both", expand=True)

        def selected_date_value():
            try:
                return datetime.strptime(f"{int(selected_day.get()):02d} {selected_month.get()} {selected_year.get()}", "%d %B %Y").date()
            except (ValueError, TypeError):
                return None

        def update_days(*_):
            try:
                month_num = months.index(selected_month.get()) + 1
                year_num = int(selected_year.get())
                # Hide future months for the current year; past years show all months.
                available_months = months if year_num < today_date.year else months[:today_date.month]
                month_picker.configure(values=available_months)
                if selected_month.get() not in available_months:
                    selected_month.set(available_months[-1])
                    month_num = months.index(selected_month.get()) + 1
                max_day = monthrange(year_num, month_num)[1]
                possible = []
                for day in range(1, max_day + 1):
                    d = datetime(year_num, month_num, day).date()
                    if start_date <= d <= today_date:
                        possible.append(str(day))
                day_picker.configure(values=possible)
                if selected_day.get() not in possible:
                    selected_day.set(possible[-1] if possible else "")
            except (ValueError, IndexError):
                day_picker.configure(values=[])
                selected_day.set("")
            refresh()

        def attendance_percentage(student):
            # The Percentage column follows the selected month, using the requested weighted score.
            chosen = selected_date_value()
            if chosen is None:
                return "—"
            records = [r for r in schedule["attendance_records"]
                       if r.get("student_id") == student["id"]
                       and str(r.get("date", "")).startswith(f"{chosen.year:04d}-{chosen.month:02d}-")]
            if not records:
                return "—"
            points = {"Present": 1.0, "Late": 0.5, "Excused": 0.5, "Absent": -1.0}
            score = sum(points.get(r.get("status"), 0.0) for r in records)
            pct = max(0.0, min(100.0, score / len(records) * 100.0))
            return f"{pct:.1f}%"

        def refresh(*_):
            tree.delete(*tree.get_children())
            chosen = selected_date_value()
            chosen_date = chosen.isoformat() if chosen else ""
            for student in schedule["students"]:
                attend = next((r.get("status", "Not recorded") for r in reversed(schedule["attendance_records"])
                               if r.get("student_id") == student["id"] and r.get("date") == chosen_date), "Not recorded")
                tree.insert("", "end", iid=str(student["id"]), values=(
                    student.get("college_id", ""), student.get("roll", ""), student.get("name", ""),
                    attend, attendance_percentage(student)))

        month_picker.bind("<<ComboboxSelected>>", update_days)
        year_picker.bind("<<ComboboxSelected>>", update_days)
        day_picker.bind("<<ComboboxSelected>>", refresh)

        def selected_student():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select student", "Select a student from the list first.", parent=self.root)
                return None
            student_id = int(sel[0])
            return next((st for st in schedule["students"] if st["id"] == student_id), None)

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=12)
        ttk.Button(actions, text="Add Student", command=lambda: self._add_student_dialog(schedule, refresh)).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Mark Attendance", command=lambda: self._attendance_dialog(schedule, selected_student(), refresh, selected_date_value().isoformat() if selected_date_value() else today_string())).pack(side="left", padx=6)
        ttk.Button(actions, text="Today's Report", command=lambda: self._daily_attendance_average(schedule)).pack(side="left", padx=6)
        ttk.Button(actions, text="Overall Attendance", command=lambda: self._overall_attendance_dialog(schedule)).pack(side="left", padx=6)
        ttk.Button(actions, text="Delete Student", command=lambda: self._delete_student(schedule, selected_student(), refresh)).pack(side="left", padx=6)
        ttk.Button(actions, text="Edit Student", command=lambda: self._edit_student_dialog(schedule, selected_student(), refresh)).pack(side="left", padx=6)
        ttk.Button(outer, text="← Back to Schedule", command=lambda: self.show_schedule_detail(schedule["id"])).pack(anchor="e")
        # Set initial day list without triggering a refresh before widgets exist.
        update_days()
        refresh()

    def _overall_attendance_dialog(self, schedule):
        self._ensure_class_records(schedule)
        if not schedule["students"]:
            messagebox.showinfo("Overall Attendance", "Add a student before calculating attendance.", parent=self.root)
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Overall Attendance")
        dialog.geometry("540x300")
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Overall Attendance", style="Section.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))
        student_var = tk.StringVar(value=schedule["students"][0]["name"])
        month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        from_var = tk.StringVar(value="July")
        to_var = tk.StringVar(value=datetime.now().strftime("%B"))
        from_year_var = tk.StringVar(value="2026")
        to_year_var = tk.StringVar(value=str(datetime.now().year))
        ttk.Label(frame, text="Student:").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=7)
        student_box = ttk.Combobox(frame, textvariable=student_var, values=[s["name"] for s in schedule["students"]], state="readonly", width=32)
        student_box.grid(row=1, column=1, sticky="ew", pady=7)
        ttk.Label(frame, text="From month:").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=7)
        ttk.Combobox(frame, textvariable=from_var, values=month_names, state="readonly", width=18).grid(row=2, column=1, sticky="w", pady=7)
        ttk.Label(frame, text="From year:").grid(row=3, column=0, sticky="w", padx=(0, 12), pady=7)
        ttk.Combobox(frame, textvariable=from_year_var, values=["2025", "2026"], state="readonly", width=18).grid(row=3, column=1, sticky="w", pady=7)
        ttk.Label(frame, text="To month:").grid(row=4, column=0, sticky="w", padx=(0, 12), pady=7)
        ttk.Combobox(frame, textvariable=to_var, values=month_names, state="readonly", width=18).grid(row=4, column=1, sticky="w", pady=7)
        ttk.Label(frame, text="To year:").grid(row=5, column=0, sticky="w", padx=(0, 12), pady=7)
        ttk.Combobox(frame, textvariable=to_year_var, values=["2025", "2026"], state="readonly", width=18).grid(row=5, column=1, sticky="w", pady=7)
        frame.columnconfigure(1, weight=1)

        def calculate():
            student = next((s for s in schedule["students"] if s["name"] == student_var.get()), None)
            if student is None:
                messagebox.showerror("Student not found", "Select a student.", parent=dialog)
                return
            start_month = month_names.index(from_var.get()) + 1
            end_month = month_names.index(to_var.get()) + 1
            start_year = int(from_year_var.get())
            end_year = int(to_year_var.get())
            start_key = start_year * 100 + start_month
            end_key = end_year * 100 + end_month
            if start_key > end_key:
                messagebox.showerror("Invalid range", "The starting month/year must be before or equal to the ending month/year.", parent=dialog)
                return
            now = datetime.now().date()
            records = []
            for record in schedule["attendance_records"]:
                if record.get("student_id") != student["id"]:
                    continue
                try:
                    record_date = datetime.strptime(record.get("date", ""), "%Y-%m-%d").date()
                except ValueError:
                    continue
                record_key = record_date.year * 100 + record_date.month
                if datetime(2025, 1, 1).date() <= record_date <= now and start_key <= record_key <= end_key:
                    records.append(record)
            points = {"Present": 1.0, "Late": 0.5, "Excused": 0.5, "Absent": -1.0}
            counts = {"Present": 0, "Absent": 0, "Late": 0, "Excused": 0}
            for record in records:
                status = record.get("status")
                if status in counts:
                    counts[status] += 1
            scores = [points[r.get("status")] for r in records if r.get("status") in points]
            if scores:
                percentage = max(0.0, min(100.0, sum(scores) / len(scores) * 100.0))
                result = (f"Student: {student['name']}\n"
                          f"Period: {from_var.get()} {start_year} to {to_var.get()} {end_year}\n"
                          f"Times marked present = {counts['Present']}\n"
                          f"Times marked absent = {counts['Absent']}\n"
                          f"Times marked late = {counts['Late']}\n"
                          f"Times marked excused = {counts['Excused']}\n"
                          f"Overall attendance: {percentage:.1f}%\n\n"
                          "Scoring: Present = +1, Late/Excused = +0.5, Absent = -1.")
            else:
                result = (f"Student: {student['name']}\n"
                          f"Period: {from_var.get()} to {to_var.get()} 2026\n"
                          "No attendance records found for this period.")
            messagebox.showinfo("Overall Attendance Result", result, parent=dialog)
        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=0, columnspan=2, sticky="e", pady=(18, 0))
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Calculate", command=calculate).pack(side="right")

    def _simple_form(self, title, fields, on_save, size="460x300"):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry(size)
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=title, style="Section.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))
        variables = {}
        for i, field in enumerate(fields, start=1):
            key, label, default = field[:3]
            kind = field[3] if len(field) > 3 else "entry"
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", padx=(0, 12), pady=6)
            var = tk.StringVar(value=default)
            variables[key] = var
            if kind == "status":
                widget = ttk.Combobox(frame, textvariable=var, values=["Present", "Absent", "Late", "Excused"], state="readonly", width=25)
            else:
                widget = ttk.Entry(frame, textvariable=var, width=28)
            widget.grid(row=i, column=1, sticky="ew", pady=6)
        frame.columnconfigure(1, weight=1)
        buttons = ttk.Frame(frame)
        buttons.grid(row=len(fields)+1, column=0, columnspan=2, sticky="e", pady=(16, 0))
        def save_and_close():
            try:
                if on_save({k: v.get().strip() for k, v in variables.items()}):
                    dialog.destroy()
            except (ValueError, TypeError) as error:
                messagebox.showerror("Invalid input", str(error), parent=dialog)
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Save", command=save_and_close).pack(side="right")
        return dialog

    def _add_student_dialog(self, schedule, refresh):
        def save(values):
            college_id, roll, name = values["college_id"], values["roll"], values["name"]
            if not college_id or not roll or not name:
                raise ValueError("Enter the College ID, Roll no, and student name.")
            if any(st.get("roll", "").casefold() == roll.casefold() for st in schedule["students"]):
                raise ValueError("That roll number already exists in this class.")
            if any(st.get("college_id", "").casefold() == college_id.casefold() for st in schedule["students"]):
                raise ValueError("That College ID already exists in this class.")
            next_id = max([st["id"] for st in schedule["students"]], default=0) + 1
            schedule["students"].append({"id": next_id, "college_id": college_id, "roll": roll, "name": name})
            self.save(); refresh(); return True
        self._simple_form("Add Student", [("college_id", "College ID", ""), ("roll", "Roll no", ""), ("name", "Student name", "")], save, "520x280")

    def _edit_student_dialog(self, schedule, student, refresh):
        if student is None:
            return
        student.setdefault("college_id", "")
        def save(values):
            college_id, roll, name = values["college_id"], values["roll"], values["name"]
            if not college_id or not roll or not name:
                raise ValueError("College ID, Roll no, and student name cannot be empty.")
            for other in schedule["students"]:
                if other["id"] != student["id"] and other.get("roll", "").casefold() == roll.casefold():
                    raise ValueError("That roll number is already used by another student.")
                if other["id"] != student["id"] and other.get("college_id", "").casefold() == college_id.casefold():
                    raise ValueError("That College ID is already used by another student.")
            student["college_id"], student["roll"], student["name"] = college_id, roll, name
            self.save(); refresh(); return True
        self._simple_form("Edit Student", [
            ("college_id", "College ID", student.get("college_id", "")),
            ("roll", "Roll no", student.get("roll", "")),
            ("name", "Student name", student.get("name", "")),
        ], save, "520x280")

    def _attendance_dialog(self, schedule, student, refresh, chosen_date=None):
        if student is None:
            return
        chosen_date = chosen_date or today_string()
        def save(values):
            date = values["date"] or chosen_date
            try:
                parsed = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Choose a valid date in YYYY-MM-DD format.")
            if parsed < datetime(2025, 1, 1).date() or parsed > datetime.now().date():
                raise ValueError("Attendance date must be between 2025-01-01 and today.")
            record = {"student_id": student["id"], "date": date, "status": values["status"]}
            old = next((r for r in schedule["attendance_records"] if r.get("student_id") == student["id"] and r.get("date") == date), None)
            if old:
                old["status"] = record["status"]
            else:
                schedule["attendance_records"].append(record)
            self.save(); refresh(); return True
        self._simple_form(f"Attendance: {student['name']}", [
            ("date", "Date (YYYY-MM-DD)", chosen_date),
            ("status", "Attendance status", "Present", "status")
        ], save, "520x230")

    def _daily_attendance_average(self, schedule):
        self._ensure_class_records(schedule)
        today = today_string()
        students = schedule["students"]
        records = {r.get("student_id"): r.get("status") for r in schedule["attendance_records"] if r.get("date") == today}
        points = {"Present": 1.0, "Late": 0.5, "Excused": 0.5, "Absent": -1.0}
        marked = [points[status] for status in records.values() if status in points]
        if not marked:
            average = 0.0
            message = "No attendance has been recorded for today yet."
        else:
            average = max(0.0, min(100.0, sum(marked) / len(marked) * 100.0))
            message = f"Today's attendance score average: {average:.1f}%\nStudents marked: {len(marked)} of {len(students)}"
        status_order = ["Present", "Absent", "Late", "Excused"]
        names_by_status = {status: [] for status in status_order}
        student_by_id = {student["id"]: student for student in students}
        for student_id, status in records.items():
            if status in names_by_status and student_id in student_by_id:
                st = student_by_id[student_id]
                names_by_status[status].append(f"{st.get('name', 'Unknown')} (Roll {st.get('roll', '')})")
        details = "\n".join(
            f"Students marked {status.lower()} = {', '.join(names_by_status[status]) if names_by_status[status] else 'None'}"
            for status in status_order
        )
        report = (f"Today's Attendance Report — {schedule['name']}\nDate: {today}\n\n{message}\n"
                  f"Students marked present = {len(names_by_status['Present'])}: {', '.join(names_by_status['Present']) if names_by_status['Present'] else 'None'}\n"
                  f"Students marked absent = {len(names_by_status['Absent'])}: {', '.join(names_by_status['Absent']) if names_by_status['Absent'] else 'None'}\n"
                  f"Students marked late = {len(names_by_status['Late'])}: {', '.join(names_by_status['Late']) if names_by_status['Late'] else 'None'}\n"
                  f"Students marked excused = {len(names_by_status['Excused'])}: {', '.join(names_by_status['Excused']) if names_by_status['Excused'] else 'None'}\n\n"
                  "Scoring: Present = +1, Late/Excused = +0.5, Absent = -1.")
        report_path = os.path.join(DATA_DIR, f"today_attendance_report_{schedule['id']}_{today}.txt")
        try:
            with open(report_path, "w", encoding="utf-8") as file:
                file.write(report)
        except OSError as error:
            messagebox.showerror("Report save failed", str(error))
            return
        messagebox.showinfo("Today's Report", report + f"\n\nSaved to: {report_path}")

    def _marks_dialog(self, schedule, student, refresh):
        if student is None: return
        def save(values):
            title = values["test"] or "Assessment"
            try:
                obtained, maximum = float(values["obtained"]), float(values["maximum"])
            except ValueError: raise ValueError("Marks must be numeric.")
            if maximum <= 0 or obtained < 0 or obtained > maximum:
                raise ValueError("Maximum marks must be positive, and obtained marks must be between 0 and maximum.")
            schedule["marks_records"].append({"student_id": student["id"], "date": today_string(), "test": title, "obtained": obtained, "maximum": maximum})
            self.save(); refresh()
            pct, grade = calculate_grade(obtained, maximum)
            messagebox.showinfo("Grade calculated", f"{student['name']}\nPercentage: {pct:.1f}%\nGrade: {grade}")
            return True
        self._simple_form(f"Enter Marks: {student['name']}", [("test", "Assessment / test", "Unit Test"), ("obtained", "Marks obtained", ""), ("maximum", "Maximum marks", "20")], save, "500x260")

    def _assignment_dialog(self, schedule, refresh):
        def save(values):
            title, due = values["title"], values["due"]
            if not title: raise ValueError("Enter an assignment title.")
            try: datetime.strptime(due, "%Y-%m-%d")
            except ValueError: raise ValueError("Deadline must use YYYY-MM-DD, for example 2026-10-22.")
            schedule["assignments"].append({"id": max([a["id"] for a in schedule["assignments"]], default=0)+1, "title": title, "due_date": due, "created_at": today_string(), "status": "Pending"})
            self.save(); refresh(); messagebox.showinfo("Assignment saved", f"'{title}' was added with deadline {due}.")
            return True
        self._simple_form("Add Assignment", [("title", "Assignment title", ""), ("due", "Deadline (YYYY-MM-DD)", today_string())], save, "520x220")

    def _show_assignments(self, schedule):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Assignments: {schedule['name']}")
        dialog.geometry("720x420")
        dialog.transient(self.root)
        frame = ttk.Frame(dialog, padding=16); frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Assignments and deadlines", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        tree = ttk.Treeview(frame, columns=("title", "due", "status"), show="headings")
        for c, label, width in [("title", "Assignment", 360), ("due", "Deadline", 160), ("status", "Status", 120)]:
            tree.heading(c, text=label); tree.column(c, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        for assignment in schedule["assignments"]:
            status = assignment.get("status", "Pending")
            if status == "Pending" and assignment["due_date"] < today_string(): status = "Overdue"
            tree.insert("", "end", iid=str(assignment["id"]), values=(assignment["title"], assignment["due_date"], status))
        def mark_done():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Select assignment", "Select an assignment first.", parent=dialog); return
            assignment = next(a for a in schedule["assignments"] if a["id"] == int(selection[0]))
            assignment["status"] = "Completed"; self.save()
            tree.item(selection[0], values=(assignment["title"], assignment["due_date"], "Completed"))
        ttk.Button(frame, text="Mark Selected Completed", command=mark_done).pack(anchor="w", pady=10)
        ttk.Button(frame, text="Close", command=dialog.destroy).pack(anchor="e")

    def _daily_report(self, schedule):
        self._ensure_class_records(schedule)
        today = today_string()
        attendance = [r for r in schedule["attendance_records"] if r["date"] == today]
        counts = {status: sum(1 for r in attendance if r["status"] == status) for status in ["Present", "Absent", "Late", "Excused"]}
        pending = [a for a in schedule["assignments"] if a.get("status", "Pending") == "Pending"]
        overdue = [a for a in pending if a["due_date"] < today]
        due_today = [a for a in pending if a["due_date"] == today]
        report = (
            f"Daily Attendance Report — {schedule['name']}\nDate: {today}\n\n"
            f"Students registered: {len(schedule['students'])}\n"
            f"Attendance records today: {len(attendance)}\n"
            f"Present: {counts['Present']} | Absent: {counts['Absent']} | Late: {counts['Late']} | Excused: {counts['Excused']}\n\n"
            f"Pending assignments: {len(pending)}\nDue today: {len(due_today)}\nOverdue: {len(overdue)}\n"
        )
        report_path = os.path.join(DATA_DIR, f"daily_report_{schedule['id']}_{today}.txt")
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)
        except OSError as error:
            messagebox.showerror("Report save failed", str(error))
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Daily Attendance Report")
        dialog.geometry("620x430")
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Daily Attendance Report", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        text_box = tk.Text(frame, wrap="word", height=16, width=70)
        text_box.pack(fill="both", expand=True)
        text_box.insert("1.0", report)
        text_box.configure(state="disabled")
        ttk.Label(frame, text=f"Report saved to: {report_path}", style="Subtitle.TLabel").pack(anchor="w", pady=6)
        ttk.Button(frame, text="Close", command=dialog.destroy).pack(anchor="e")

    def _delete_student(self, schedule, student, refresh):
        if student is None: return
        if not messagebox.askyesno("Delete student", f"Delete {student['name']} and their attendance records from this class? This cannot be undone."):
            return
        sid = student["id"]
        schedule["students"] = [st for st in schedule["students"] if st["id"] != sid]
        schedule["attendance_records"] = [r for r in schedule["attendance_records"] if r["student_id"] != sid]
        schedule["marks_records"] = [r for r in schedule["marks_records"] if r["student_id"] != sid]
        self.save(); refresh()

    def schedule_reminders(self):
        for job in self.reminder_jobs:
            try:
                self.root.after_cancel(job)
            except tk.TclError:
                pass
        self.reminder_jobs.clear()
        now = datetime.now()
        for schedule in self.data["schedules"]:
            if not schedule.get("reminders_enabled", True):
                continue
            for lecture in schedule.get("lectures", []):
                day_offset = (DAYS.index(lecture["day"]) - now.weekday()) % 7
                lecture_time = parse_time(lecture["start"])
                target = (now + timedelta(days=day_offset)).replace(hour=lecture_time.hour, minute=lecture_time.minute, second=0, microsecond=0)
                if target <= now:
                    target += timedelta(days=7)
                delay_ms = min(int((target - now).total_seconds() * 1000), 2_000_000_000)
                job = self.root.after(delay_ms, lambda s=schedule, l=lecture: self.fire_reminder(s, l))
                self.reminder_jobs.append(job)

    def fire_reminder(self, schedule, lecture):
        if schedule.get("popups_enabled", True):
            messagebox.showinfo("Upcoming lecture", f"{schedule['name']}\n{lecture['day']} {lecture['start']}-{lecture['end']}\n{lecture.get('topic') or 'Lecture'}")
        self.schedule_reminders()

    def on_close(self):
        self.save()
        self.root.destroy()


def main():
    root = tk.Tk()
    TeacherSecretaryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
