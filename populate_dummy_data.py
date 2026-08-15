"""Populate dummy college data for CIAS testing.

Loads buildings, floors, classrooms, time slots, timetable and bookings
that match the project description example:

    Wednesday, 2:00 PM – 3:00 PM (Period 5), 45 students
    → Room 204 (Main Building, 2nd Floor, capacity 60)
    → Room 305 (Science Building, 3rd Floor, capacity 50)

Usage:
    python populate_dummy_data.py
    python populate_dummy_data.py --keep   # do not wipe existing campus rows
"""

import argparse

from app import app
from models import Booking, Building, Classroom, Floor, TimeSlot, Timetable, db
from seed import run as seed_run


def reset_campus():
    Booking.query.delete()
    Timetable.query.delete()
    Classroom.query.delete()
    Floor.query.delete()
    Building.query.delete()
    TimeSlot.query.delete()
    db.session.commit()


def verify_example():
    room_204 = (
        Classroom.query.join(Floor)
        .join(Building)
        .filter(Building.name == "Main Building", Classroom.room_number == "204")
        .first()
    )
    room_305 = (
        Classroom.query.join(Floor)
        .join(Building)
        .filter(Building.name == "Science Building", Classroom.room_number == "305")
        .first()
    )
    period_5 = TimeSlot.query.filter_by(name="Period 5").first()
    occupied = Timetable.query.filter_by(
        day_of_week="Wednesday", timeslot_id=period_5.id if period_5 else -1
    ).all()
    occupied_ids = {row.classroom_id for row in occupied}
    print("\nProject-description test case")
    print("  Day: Wednesday  |  Time: Period 5 (14:00 – 15:00)  |  Students: 45")
    if room_204:
        status = "occupied" if room_204.id in occupied_ids else "AVAILABLE"
        print(f"  Room 204  Main Building • 2nd Floor  Capacity {room_204.capacity}  → {status}")
    else:
        print("  Room 204 missing")
    if room_305:
        status = "occupied" if room_305.id in occupied_ids else "AVAILABLE"
        print(f"  Room 305  Science Building • 3rd Floor  Capacity {room_305.capacity}  → {status}")
    else:
        print("  Room 305 missing")


def main():
    parser = argparse.ArgumentParser(description="Load dummy CIAS data for testing")
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep existing buildings and slots (only fill empty tables)",
    )
    args = parser.parse_args()

    with app.app_context():
        db.create_all()
        if not args.keep:
            print("Clearing campus rows (users are kept)...")
            reset_campus()
        seed_run()
        verify_example()
        print("\nSign in: admin / admin123")
        print("Then open Find Classroom → Wednesday → Period 5 → 45 students.")


if __name__ == "__main__":
    main()
