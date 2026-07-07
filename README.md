# SyncSlotNITT 🌌

SyncSlotNITT is a production-ready, database-backed university timetable management and attendance tracking platform built specifically with NIT Trichy's ecosystem in mind. It replaces chaotic paperwork and broken spreadsheet schedules with a unified, real-time coordination engine.

To make daily administrative tracking a bit more engaging, the entire platform is styled using a responsive, hardware-accelerated **Mystic Cosmic Fantasy Theme** (featuring visual tokens like Arcane Obsidian, Runic Violet, and Enchanted Solar Gold)[cite: 1].

---

## 🎯 The Core Gateways

The system splits into three isolated access portals, ensuring secure role separation[cite: 5]:

### 1. Curriculum Coordinator Management (CCM) Desk 🏛️
The central administrative command center[cite: 5]. 
* **Dynamic Grid Mapping:** Allows coordinators to publish master branch timetables across multiple departments and section configurations[cite: 2].
* **HTML5 Drag-and-Drop Palette:** Coordinators can forge quick-allocation subject/professor tokens and drag them directly into the timetable grid to auto-fill records instantly[cite: 2].
* **Collision Detection Engine:** The backend validates schedules automatically upon submission, flashing dynamic warnings if a professor is double-booked across different departments or sections at the same hour.

### 2. Faculty Track Portal 👨‍🏫
An isolated workspace for professors to manage their specific teaching schedules and roll calls[cite: 5].
* **Isolated Timetables:** Automatically filters and renders a customized view displaying only the slots allocated to that specific professor's User ID.
* **Digital Roll Call Registry:** A clean UI to log daily student attendance statuses (Present/Absent). Submitting the registry syncs records instantly across all connected databases.
* **On-Duty (OD) Leave Workspace:** A dedicated dashboard panel to review incoming student medical or OD leave applications, allowing professors to grant waivers with a single click.

### 3. Student Access Terminal 🎓
A centralized hub for students to track schedules and protect their academic eligibility[cite: 5].
* **Chart.js Analytics Rings:** Displays live, visual doughnut progress gauges for each subject. The ring dynamically turns a flashing crimson red if a student's attendance percentage dips below the mandatory **75% institutional eligibility threshold**.
* **iCalendar (.ics) Schedule Exporter:** Converts the student's live timetable matrix into a standard `.ics` calendar file with a single click, allowing them to import their class schedule seamlessly into Google Calendar, Outlook, or Apple Calendar.
* **Digital OD Application:** Allows students to digitally submit absence justifications (such as tech-fest coordination or medical leave) straight to their specific course professor's dashboard.

---

## ⚡ Key Architecture Upgrades

* **Persistent Relational Database:** Powered by a robust SQLite schema (`syncslot.db`), completely replacing volatile in-memory storage. Data stays perfectly synchronized and safe across reboots.
* **Live Magic Notification Feed:** Implements an automated trigger engine. Whenever a timetable is modified, attendance is logged, or an OD request is approved, target users receive an instant notification alert inside their navigation header bar[cite: 1].
* **Secure State Routing:** Uses cryptographic session cookies combined with password hashing via `werkzeug.security` to block unauthorized portal submersion or parameter spoofing.

---

## 🛠️ Tech Stack

* **Backend Framework:** Python 3.11 + Flask
* **Database Layer:** SQLite3 (Relational)
* **Production Web Server:** Gunicorn (WSGI)
* **Frontend Architecture:** Semantic HTML5, CSS3 Glassmorphism variables[cite: 1], Native JavaScript (ES6)
* **Data Visualization:** Chart.js (via CDN)
* **Containerization:** Docker

---

## 🚀 Local Quick-Start Guide

If you want to run this project locally on your development machine, follow these steps:

### Prerequisite Setup
Ensure you have Python 3.x and Git installed. Clone this repository and step into the project folder:
```bash
git clone [https://github.com/vikashdharsan245-byte/syncslot.git](https://github.com/vikashdharsan245-byte/syncslot.git)
cd syncslot