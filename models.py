from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default="staff")
    department = db.Column(db.String(80), default="")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role in ("super_admin", "admin")

    @property
    def is_super_admin(self):
        return self.role == "super_admin"

    @property
    def role_label(self):
        return {
            "super_admin": "Super Admin",
            "admin": "Admin",
            "staff": "Staff",
        }.get(self.role, self.role)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
            "role_label": self.role_label,
            "department": self.department or "",
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.strftime("%d %b %Y") if self.created_at else "",
            "last_login": self.last_login.strftime("%d %b %Y %H:%M") if self.last_login else "Never",
        }


class Building(db.Model):
    __tablename__ = "buildings"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.String(255), default="")
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    floors = db.relationship(
        "Floor", backref="building", cascade="all, delete-orphan", lazy="dynamic"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description or "",
            "is_active": self.is_active,
            "floor_count": self.floors.count(),
            "classroom_count": sum(f.classrooms.count() for f in self.floors),
        }


class Floor(db.Model):
    __tablename__ = "floors"

    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey("buildings.id"), nullable=False)
    floor_number = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), default="")

    classrooms = db.relationship(
        "Classroom", backref="floor", cascade="all, delete-orphan", lazy="dynamic"
    )

    __table_args__ = (
        db.UniqueConstraint("building_id", "floor_number", name="uq_building_floor"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "building_id": self.building_id,
            "building_name": self.building.name if self.building else "",
            "floor_number": self.floor_number,
            "name": self.name,
            "description": self.description or "",
            "classroom_count": self.classrooms.count(),
        }


class Classroom(db.Model):
    __tablename__ = "classrooms"

    id = db.Column(db.Integer, primary_key=True)
    floor_id = db.Column(db.Integer, db.ForeignKey("floors.id"), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    room_type = db.Column(db.String(40), default="Lecture Hall")
    facilities = db.Column(db.String(255), default="")
    description = db.Column(db.String(255), default="")
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    timetable_entries = db.relationship(
        "Timetable", backref="classroom", cascade="all, delete-orphan", lazy="dynamic"
    )
    bookings = db.relationship(
        "Booking", backref="classroom", cascade="all, delete-orphan", lazy="dynamic"
    )

    __table_args__ = (
        db.UniqueConstraint("floor_id", "room_number", name="uq_floor_room"),
    )

    @property
    def building(self):
        return self.floor.building if self.floor else None

    def location_label(self):
        if not self.floor:
            return self.room_number
        return f"{self.floor.building.name} • {self.floor.name}"

    def to_dict(self):
        building = self.building
        return {
            "id": self.id,
            "floor_id": self.floor_id,
            "room_number": self.room_number,
            "capacity": self.capacity,
            "room_type": self.room_type,
            "facilities": self.facilities or "",
            "description": self.description or "",
            "is_active": self.is_active,
            "building_id": building.id if building else None,
            "building_name": building.name if building else "",
            "floor_name": self.floor.name if self.floor else "",
            "floor_number": self.floor.floor_number if self.floor else None,
            "location": self.location_label(),
        }


class TimeSlot(db.Model):
    __tablename__ = "timeslots"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), nullable=False)
    start_time = db.Column(db.String(8), nullable=False)
    end_time = db.Column(db.String(8), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_break = db.Column(db.Boolean, default=False, nullable=False)

    def label(self):
        return f"{self.name} ({self.start_time} – {self.end_time})"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "sort_order": self.sort_order,
            "is_break": self.is_break,
            "label": self.label(),
        }


class Timetable(db.Model):
    __tablename__ = "timetable"

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey("classrooms.id"), nullable=False)
    day_of_week = db.Column(db.String(16), nullable=False)
    timeslot_id = db.Column(db.Integer, db.ForeignKey("timeslots.id"), nullable=False)
    subject = db.Column(db.String(120), nullable=False)
    teacher_name = db.Column(db.String(120), default="")
    class_group = db.Column(db.String(80), default="")
    academic_year = db.Column(db.String(20), default="")

    timeslot = db.relationship("TimeSlot")

    __table_args__ = (
        db.UniqueConstraint(
            "classroom_id", "day_of_week", "timeslot_id", name="uq_room_day_slot"
        ),
    )

    def to_dict(self):
        room = self.classroom
        slot = self.timeslot
        return {
            "id": self.id,
            "classroom_id": self.classroom_id,
            "day_of_week": self.day_of_week,
            "timeslot_id": self.timeslot_id,
            "subject": self.subject,
            "teacher_name": self.teacher_name or "",
            "class_group": self.class_group or "",
            "academic_year": self.academic_year or "",
            "room_number": room.room_number if room else "",
            "location": room.location_label() if room else "",
            "capacity": room.capacity if room else 0,
            "timeslot_label": slot.label() if slot else "",
        }


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey("classrooms.id"), nullable=False)
    day_of_week = db.Column(db.String(16), nullable=False)
    timeslot_id = db.Column(db.Integer, db.ForeignKey("timeslots.id"), nullable=False)
    purpose = db.Column(db.String(255), nullable=False)
    booked_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    student_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="confirmed")
    notes = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    timeslot = db.relationship("TimeSlot")
    booked_by = db.relationship("User")

    def to_dict(self):
        room = self.classroom
        slot = self.timeslot
        user = self.booked_by
        return {
            "id": self.id,
            "classroom_id": self.classroom_id,
            "day_of_week": self.day_of_week,
            "timeslot_id": self.timeslot_id,
            "purpose": self.purpose,
            "student_count": self.student_count or 0,
            "status": self.status,
            "notes": self.notes or "",
            "room_number": room.room_number if room else "",
            "location": room.location_label() if room else "",
            "capacity": room.capacity if room else 0,
            "timeslot_label": slot.label() if slot else "",
            "booked_by": user.full_name if user else "",
            "booked_by_role": user.role_label if user else "",
            "created_at": self.created_at.strftime("%d %b %Y %H:%M") if self.created_at else "",
        }
