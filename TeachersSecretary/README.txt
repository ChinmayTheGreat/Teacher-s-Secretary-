TEACHER'S SECRETARY - v1.0

Run in VS Code:
    python main.py

Module 1: Attendance
- Add, edit, and delete students
- Store College ID, Roll no, and student name separately
- Select attendance date using Day, Month, and Year dropdowns
- Date dropdowns include all dates from 1 January 2025 through today; future dates are not available
- Record Present, Absent, Late, or Excused attendance for past or current dates
- The Percentage column shows the selected month's weighted attendance percentage
- Overall Attendance lets the teacher choose a student and inclusive start/end month/year range, and reports counts for Present, Absent, Late, and Excused
- Generate Today's Report with the current day's attendance score average, counts, and student names grouped by Present, Absent, Late, and Excused
- Attendance and student records save automatically

Module 4: Personal Diary
- Uses the same list-style interface as Syllabus Topics
- Add Topic adds a diary item, task, meeting, note, or personal reminder
- Topic Covered toggles the selected entries' covered status
- Diary entries are stored separately from syllabus topics for each schedule/class

Module 5: Student Doubt Desk
- Displays the requested empty-state message inline when no doubts have been received; it is not a popup
- Add Doubt records a student's question
- Unresolved doubts trigger an in-app reminder every hour while the app is running
- Mark Selected Solved stops reminders for that doubt

Attendance scoring used for percentages:
- Present = +1
- Late = +0.5
- Excused = +0.5
- Absent = -1
The displayed percentage is calculated as total score / number of recorded attendance entries * 100 and clamped to the 0%-100% range. Dates without a recorded status are not counted.

Schedule features include:
- Create and view schedules
- AM/PM time entry
- Delete lectures
- Combine selected lectures into a separate overview
- Syllabus progress tracking
- In-app lecture reminders while the app is running

Data is stored in data/teacher_secretary.json. Back up this file before replacing project files.
