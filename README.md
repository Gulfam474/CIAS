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

- Self-service sign-up with optional email OTP verification
- Live form validation for email format and password strength
- Role-based access: **Super Admin**, **Admin**, **Staff**
- Identify who is an admin and assign or revoke access
- Campus setup wizard when buildings, floors, classrooms, or time slots are missing
- Optional product tour, started from the **Take a tour** button in the header
- Find empty classrooms by day, time, location, and capacity
- Timetable clash detection based on actual start and end times
- Times shown in 12-hour AM/PM format
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

Edit `.env` with your MySQL user and password (`USE_MYSQL=1`). The app creates the `cias` database if it does not exist. Set `USE_MYSQL=0` to use a local SQLite file (`cias.db`) instead.

### Email verification

New accounts can be required to confirm their email with a 6-digit code (OTP) before signing in. Codes expire after 10 minutes and can be resent from the verification page.

| Variable | Purpose |
| --- | --- |
| `USE_EMAIL_VERIFICATION` | `True` to require the OTP, `False` to activate accounts immediately |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS` | SMTP server settings |
| `MAIL_USERNAME`, `MAIL_PASSWORD` | SMTP login (for Gmail, use an [App Password](https://myaccount.google.com/apppasswords)) |
| `MAIL_FROM` | Sender address shown on the email |

If SMTP is not configured, set `USE_EMAIL_VERIFICATION=False`; otherwise sign-up fails because the code cannot be sent.

### Upgrading an existing MySQL database

Tables are created automatically, but new columns are not added to an existing `users` table. If you set up CIAS before sign-up was added, run once:

```sql
ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN otp_code VARCHAR(6) DEFAULT NULL;
ALTER TABLE users ADD COLUMN otp_expires_at DATETIME DEFAULT NULL;
```

### Dummy data for testing

```bash
python populate_dummy_data.py
```

This loads buildings, floors, classrooms, time slots, and timetable rows used in the project example (including Room 204 and Room 305). User accounts are not changed. To fill empty tables only:

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

## Accounts

There are no built-in demo accounts. Open **Create one here** on the sign-in page to register. New accounts get the **Staff** role.

To create the first Super Admin, register an account and promote it in the database:

```sql
UPDATE users SET role = 'super_admin' WHERE username = 'your-username';
```

After that, the Super Admin can assign Admin or Staff roles from **Users & Roles**.

| Role | Access |
| --- | --- |
| Super Admin | Full access, including assigning roles |
| Admin | Campus data, timetable, search, bookings, reports |
| Staff | Search, occupancy, own bookings |

## Timetable clash rules

A room cannot hold two classes at the same time on the same day. A class may start exactly when another ends. For a room with a class from 10:00 to 11:00 AM:

| New class | Result |
| --- | --- |
| 9:00 – 10:00 AM | Allowed (ends as the other starts) |
| 11:00 AM – 12:00 PM | Allowed (starts as the other ends) |
| 9:30 – 10:30 AM | Clash |
| 10:15 – 10:45 AM | Clash |
| Same time, different room or day | Allowed |

## How to try the main search

1. Sign in with an Admin or Super Admin account
2. Open **Find Classroom**
3. Day: Wednesday
4. Time: Period 5 (2:00 PM – 3:00 PM)
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
  templates/               HTML pages (including register.html and verify_email.html)
  static/css|js            Styles and UI
  project_desciption.txt   Original project brief
```
