# Classroom Information and Availability System (CIAS)

CIAS is an admin-based desktop application that helps college administrators find suitable empty classrooms for extra classes, replacement lectures, meetings, and other academic work.

The system stores buildings, floors, classrooms, student capacity, time slots, and timetable allocations. An administrator selects day, time slot, building or floor, and the number of students. CIAS checks the timetable and extra bookings, then lists rooms that are free and large enough.

Rooms that are already in use for that period are not shown as available.

## Project description

College staff often walk the timetable by hand to find a free room. CIAS replaces that work with a simple admin application:

- Organised information about buildings, floors, and classrooms
- Student capacity for each classroom
- Regular timetable allocations
- Occupied vs available rooms for a chosen day and time
- Suitable empty classrooms for a required class size

### Main workflow

Admin login → Dashboard → Find Empty Classroom → select day, time slot, building/floor, and student count → check timetable → display suitable unoccupied classrooms.

**Example:** Wednesday, 2:00 PM – 3:00 PM, 45 students.

The system can show:

- Room 204 — Main Building • 2nd Floor — Capacity 60  
- Room 305 — Science Building • 3rd Floor — Capacity 50  

### Technology

| Layer | Stack |
| --- | --- |
| Frontend | HTML, CSS, JavaScript |
| Backend | Python (Flask) |
| Database | MySQL (SQLite fallback if MySQL is not running) |
| Desktop window | pywebview |

## Features

- Role-based access: **Super Admin**, **Admin**, **Staff**
- Identify who is an admin and assign or revoke access
- Campus setup wizard when buildings, floors, classrooms, or time slots are missing
- Product tour after setup
- Find empty classrooms by day, time, location, and capacity
- Extra-class bookings that block a room like the timetable does
- Occupancy view and weekly utilization reports

## Setup

```bash
git clone https://github.com/Gulfam474/CIAS.git
cd CIAS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your MySQL user and password (`USE_MYSQL=1`). The app creates the `cias` database if it does not exist.

### Dummy data for testing

```bash
python populate_dummy_data.py
```

This loads buildings, floors, classrooms, time slots, and timetable rows used in the project example (including Room 204 and Room 305). Accounts are kept. To fill empty tables only:

```bash
python populate_dummy_data.py --keep
```

### Run

Browser:

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000)

Desktop window:

```bash
python run_desktop.py
```

## Demo accounts

| Username | Password | Role | Access |
| --- | --- | --- | --- |
| `admin` | `admin123` | Super Admin | Full access, including assigning roles |
| `registrar` | `admin123` | Admin | Campus data, timetable, search, bookings, reports |
| `hod.cs` | `admin123` | Admin | Same as Admin |
| `faculty` | `staff123` | Staff | Search, occupancy, own bookings |
| `lab.assistant` | `staff123` | Staff | Search, occupancy, own bookings |

Change these passwords after first login.

## How to try the main search

1. Sign in as `admin` / `admin123`
2. Open **Find Classroom**
3. Day: Wednesday
4. Time: Period 5 (14:00 – 15:00)
5. Students: 45

Suitable free rooms include **204** (Main Building, 2nd Floor, capacity 60) and **305** (Science Building, 3rd Floor, capacity 50). Occupied rooms for that period are not listed.

## Project layout

```
CIAS/
  app.py                   Flask app and APIs
  models.py                Database tables
  config.py                Roles and permissions
  populate_dummy_data.py   Dummy campus data for testing
  seed.py                  Seed helpers
  run_desktop.py           Desktop window
  templates/               HTML pages
  static/css|js            Styles and UI
  project_desciption.txt   Original project brief
```
