"""Load demo college data for CIAS. Safe to run more than once."""

from app import app
from models import (
    Booking,
    Building,
    Classroom,
    Floor,
    TimeSlot,
    Timetable,
    User,
    db,
)


USERS = [
    {
        "username": "admin",
        "password": "admin123",
        "full_name": "System Administrator",
        "email": "admin@cias.college",
        "role": "super_admin",
        "department": "Administration",
    },
    {
        "username": "registrar",
        "password": "admin123",
        "full_name": "Priya Nair",
        "email": "registrar@cias.college",
        "role": "admin",
        "department": "Academic Office",
    },
    {
        "username": "hod.cs",
        "password": "admin123",
        "full_name": "Dr. Arun Mehta",
        "email": "hod.cs@cias.college",
        "role": "admin",
        "department": "Computer Science",
    },
    {
        "username": "faculty",
        "password": "staff123",
        "full_name": "Anita Deshmukh",
        "email": "anita@cias.college",
        "role": "staff",
        "department": "Computer Science",
    },
    {
        "username": "lab.assistant",
        "password": "staff123",
        "full_name": "Rahul Kulkarni",
        "email": "rahul@cias.college",
        "role": "staff",
        "department": "Science",
    },
]

SLOTS = [
    ("Period 1", "09:00", "10:00", 1, False),
    ("Period 2", "10:00", "11:00", 2, False),
    ("Period 3", "11:00", "12:00", 3, False),
    ("Period 4", "12:00", "13:00", 4, False),
    ("Lunch Break", "13:00", "14:00", 5, True),
    ("Period 5", "14:00", "15:00", 6, False),
    ("Period 6", "15:00", "16:00", 7, False),
    ("Period 7", "16:00", "17:00", 8, False),
]

BUILDINGS = [
    {
        "name": "Main Building",
        "code": "MAIN",
        "description": "Central academic block",
        "floors": [
            (1, "1st Floor", [("101", 40, "Lecture Hall", "Projector, Whiteboard"),
                              ("102", 40, "Lecture Hall", "Projector"),
                              ("103", 30, "Seminar Room", "Whiteboard"),
                              ("104", 80, "Lecture Hall", "Projector, Speakers")]),
            (2, "2nd Floor", [("201", 50, "Lecture Hall", "Projector, AC"),
                              ("202", 45, "Lecture Hall", "Projector"),
                              ("203", 35, "Seminar Room", "Smart board"),
                              ("204", 60, "Lecture Hall", "Projector, AC")]),
            (3, "3rd Floor", [("301", 40, "Lecture Hall", "Projector"),
                              ("302", 70, "Lecture Hall", "Projector, Speakers"),
                              ("303", 25, "Conference Room", "TV, Conference table")]),
        ],
    },
    {
        "name": "Science Building",
        "code": "SCI",
        "description": "Laboratories and science classrooms",
        "floors": [
            (1, "1st Floor", [("101", 40, "Laboratory", "Lab benches, Safety kit"),
                              ("102", 36, "Laboratory", "Lab benches"),
                              ("103", 48, "Lecture Hall", "Projector")]),
            (2, "2nd Floor", [("201", 42, "Laboratory", "Computers"),
                              ("202", 50, "Lecture Hall", "Projector, AC"),
                              ("203", 30, "Seminar Room", "Whiteboard")]),
            (3, "3rd Floor", [("301", 45, "Lecture Hall", "Projector"),
                              ("302", 55, "Lecture Hall", "Projector, AC"),
                              ("305", 50, "Lecture Hall", "Projector, AC")]),
        ],
    },
    {
        "name": "Library Block",
        "code": "LIB",
        "description": "Seminar and discussion rooms",
        "floors": [
            (1, "Ground Floor", [("G1", 20, "Seminar Room", "Whiteboard"),
                                 ("G2", 24, "Conference Room", "TV")]),
            (2, "1st Floor", [("201", 18, "Seminar Room", "Whiteboard"),
                              ("Hall", 120, "Auditorium", "Stage, Mic, Projector")]),
        ],
    },
]


def upsert_users():
    for item in USERS:
        user = User.query.filter_by(username=item["username"]).first()
        if not user:
            user = User(username=item["username"])
            db.session.add(user)
        user.full_name = item["full_name"]
        user.email = item["email"]
        user.role = item["role"]
        user.department = item["department"]
        user.is_active = True
        user.set_password(item["password"])


def seed_slots():
    if TimeSlot.query.count():
        return
    for name, start, end, order, is_break in SLOTS:
        db.session.add(
            TimeSlot(
                name=name,
                start_time=start,
                end_time=end,
                sort_order=order,
                is_break=is_break,
            )
        )


def seed_campus():
    if Building.query.count():
        return
    for block in BUILDINGS:
        building = Building(
            name=block["name"],
            code=block["code"],
            description=block["description"],
            is_active=True,
        )
        db.session.add(building)
        db.session.flush()
        for number, name, rooms in block["floors"]:
            floor = Floor(
                building_id=building.id,
                floor_number=number,
                name=name,
                description=f"{name} of {block['name']}",
            )
            db.session.add(floor)
            db.session.flush()
            for room_number, capacity, room_type, facilities in rooms:
                db.session.add(
                    Classroom(
                        floor_id=floor.id,
                        room_number=room_number,
                        capacity=capacity,
                        room_type=room_type,
                        facilities=facilities,
                        description=f"Room {room_number} in {block['name']}",
                        is_active=True,
                    )
                )


def room(building_name, room_number):
    return (
        Classroom.query.join(Floor)
        .join(Building)
        .filter(Building.name == building_name, Classroom.room_number == room_number)
        .first()
    )


def slot_named(name):
    return TimeSlot.query.filter_by(name=name).first()


def seed_timetable():
    if Timetable.query.count():
        return
    allocations = [
        ("Main Building", "101", "Monday", "Period 1", "Engineering Mathematics", "Dr. Shah", "FE-A"),
        ("Main Building", "101", "Monday", "Period 2", "Engineering Mathematics", "Dr. Shah", "FE-A"),
        ("Main Building", "204", "Monday", "Period 5", "Data Structures", "Anita Deshmukh", "SE-CS"),
        ("Main Building", "204", "Wednesday", "Period 1", "Operating Systems", "Dr. Arun Mehta", "TE-CS"),
        ("Main Building", "204", "Friday", "Period 5", "Database Systems", "Priya Nair", "SE-CS"),
        ("Main Building", "302", "Tuesday", "Period 3", "Computer Networks", "Anita Deshmukh", "TE-CS"),
        ("Science Building", "305", "Monday", "Period 5", "Physics Lab Briefing", "Rahul Kulkarni", "FE-B"),
        ("Science Building", "305", "Thursday", "Period 2", "Chemistry", "Dr. Iyer", "FE-A"),
        ("Science Building", "202", "Wednesday", "Period 5", "Digital Electronics", "Dr. Joshi", "SE-EXTC"),
        ("Science Building", "101", "Tuesday", "Period 1", "Physics Laboratory", "Rahul Kulkarni", "FE-A"),
        ("Library Block", "Hall", "Friday", "Period 3", "Guest Lecture", "Registrar Office", "All Years"),
        ("Main Building", "104", "Thursday", "Period 6", "Workshop", "Industry Mentor", "BE-CS"),
        ("Main Building", "201", "Wednesday", "Period 2", "Software Engineering", "Anita Deshmukh", "TE-CS"),
        ("Main Building", "102", "Saturday", "Period 1", "Tutorial", "Dr. Shah", "FE-A"),
    ]
    for building, number, day, period, subject, teacher, group in allocations:
        classroom = room(building, number)
        timeslot = slot_named(period)
        if not classroom or not timeslot:
            continue
        db.session.add(
            Timetable(
                classroom_id=classroom.id,
                day_of_week=day,
                timeslot_id=timeslot.id,
                subject=subject,
                teacher_name=teacher,
                class_group=group,
                academic_year="2025-26",
            )
        )


def seed_bookings():
    if Booking.query.count():
        return
    faculty = User.query.filter_by(username="faculty").first()
    registrar = User.query.filter_by(username="registrar").first()
    classroom = room("Main Building", "203")
    timeslot = slot_named("Period 6")
    if faculty and classroom and timeslot:
        db.session.add(
            Booking(
                classroom_id=classroom.id,
                day_of_week="Wednesday",
                timeslot_id=timeslot.id,
                purpose="Replacement lecture — Software Engineering",
                booked_by_id=faculty.id,
                student_count=28,
                status="confirmed",
                notes="Original classroom under maintenance",
            )
        )
    hall = room("Library Block", "G2")
    p3 = slot_named("Period 3")
    if registrar and hall and p3:
        db.session.add(
            Booking(
                classroom_id=hall.id,
                day_of_week="Thursday",
                timeslot_id=p3.id,
                purpose="Department meeting",
                booked_by_id=registrar.id,
                student_count=12,
                status="confirmed",
            )
        )


def run():
    with app.app_context():
        db.create_all()
        upsert_users()
        seed_slots()
        seed_campus()
        db.session.commit()
        seed_timetable()
        seed_bookings()
        db.session.commit()
        print("CIAS demo data is ready.")
        print("  Super Admin : admin / admin123")
        print("  Admin       : registrar / admin123")
        print("  Staff       : faculty / staff123")
        print(f"  Buildings   : {Building.query.count()}")
        print(f"  Classrooms  : {Classroom.query.count()}")
        print(f"  Timetable   : {Timetable.query.count()}")


if __name__ == "__main__":
    run()
