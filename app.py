import os
import random
import re
import string
from datetime import datetime, timedelta
from functools import wraps

from dotenv import load_dotenv

# Load environment variables before importing config
load_dotenv()

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_mail import Mail, Message
from sqlalchemy import create_engine, inspect, or_, text

from config import Config
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

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
ROOM_TYPES = ["Lecture Hall", "Laboratory", "Seminar Room", "Conference Room", "Auditorium"]
BOOKING_STATUSES = ["confirmed", "cancelled"]

login_manager = LoginManager()
login_manager.login_view = "login"
mail = Mail()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    _configure_database(app)
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/"):
            return json_error("Please sign in.", 401)
        return redirect(url_for("login"))

    with app.app_context():
        db.create_all()
        _ensure_schema()

    register_routes(app)
    return app


def _configure_database(app):
    if not app.config.get("USE_MYSQL"):
        app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLITE_URI"]
        return

    uri = app.config["MYSQL_URI"]
    try:
        _ensure_mysql_database(uri)
        engine = create_engine(uri, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        app.config["SQLALCHEMY_DATABASE_URI"] = uri
    except Exception as exc:
        print(f"[CIAS] MySQL not available ({exc}). Using SQLite fallback.")
        app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLITE_URI"]
        app.config["USE_MYSQL"] = False


def _ensure_mysql_database(uri):
    db_name = os.getenv("MYSQL_DATABASE", "cias")
    root_uri = uri.rsplit("/", 1)[0]
    engine = create_engine(root_uri, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
        conn.commit()


def _ensure_schema():
    inspector = inspect(db.engine)
    wanted = {
        "floors": ("description", "VARCHAR(255) DEFAULT ''"),
        "classrooms": ("description", "VARCHAR(255) DEFAULT ''"),
    }
    for table, (column, ddl) in wanted.items():
        if table not in inspector.get_table_names():
            continue
        columns = {col["name"] for col in inspector.get_columns(table)}
        if column not in columns:
            db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
            db.session.commit()


def _generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def _send_otp_email(user_email, otp_code):
    try:
        msg = Message(
            subject="Verify your email - CIAS",
            recipients=[user_email],
            body=f"""
Welcome to CIAS!

Your OTP verification code is: {otp_code}

This code will expire in 10 minutes.

If you didn't request this, please ignore this email.
            """.strip(),
            html=f"""
<h2>Welcome to CIAS!</h2>
<p>Your OTP verification code is:</p>
<h1 style="color: #2563eb; font-size: 32px; letter-spacing: 4px;">{otp_code}</h1>
<p>This code will expire in 10 minutes.</p>
<p>If you didn't request this, please ignore this email.</p>
            """.strip()
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send OTP email: {e}")
        return False


def _validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def permission_required(module):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            allowed = Config.PERMISSIONS.get(module, ())
            if current_user.role not in allowed:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"ok": False, "error": "Access denied"}), 403
                flash("You do not have access to this section.", "error")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def admin_required(view):
    return permission_required("buildings")(view)


def json_error(message, status=400):
    return jsonify({"ok": False, "error": message}), status


def json_ok(data=None, **extra):
    payload = {"ok": True}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return jsonify(payload)


def campus_setup():
    buildings = Building.query.count()
    floors = Floor.query.count()
    classrooms = Classroom.query.count()
    timeslots = TimeSlot.query.filter_by(is_break=False).count()
    missing = []
    if not buildings:
        missing.append("building")
    if not floors:
        missing.append("floor")
    if not classrooms:
        missing.append("classroom")
    if not timeslots:
        missing.append("timeslot")
    if not buildings:
        step = 1
    elif not floors:
        step = 2
    elif not classrooms:
        step = 3
    elif not timeslots:
        step = 4
    else:
        step = 5
    return {
        "complete": not missing,
        "missing": missing,
        "step": step,
        "counts": {
            "buildings": buildings,
            "floors": floors,
            "classrooms": classrooms,
            "timeslots": timeslots,
        },
    }


def occupied_classroom_ids(day, timeslot_id, exclude_booking_id=None):
    timetable_ids = {
        row[0]
        for row in db.session.query(Timetable.classroom_id)
        .filter_by(day_of_week=day, timeslot_id=timeslot_id)
        .all()
    }
    booking_q = Booking.query.filter(
        Booking.day_of_week == day,
        Booking.timeslot_id == timeslot_id,
        Booking.status == "confirmed",
    )
    if exclude_booking_id:
        booking_q = booking_q.filter(Booking.id != exclude_booking_id)
    booking_ids = {row.classroom_id for row in booking_q.all()}
    return timetable_ids | booking_ids


def classroom_query(building_id=None, floor_id=None, min_capacity=0, active_only=True):
    q = Classroom.query.join(Floor).join(Building)
    if active_only:
        q = q.filter(Classroom.is_active.is_(True), Building.is_active.is_(True))
    if building_id:
        q = q.filter(Floor.building_id == int(building_id))
    if floor_id:
        q = q.filter(Classroom.floor_id == int(floor_id))
    if min_capacity:
        q = q.filter(Classroom.capacity >= int(min_capacity))
    return q.order_by(Building.name, Floor.floor_number, Classroom.room_number)


def register_routes(app):
    @app.context_processor
    def inject_globals():
        role = current_user.role if current_user.is_authenticated else None
        return {
            "DAYS": DAYS,
            "ROOM_TYPES": ROOM_TYPES,
            "ROLE_LABELS": Config.ROLE_LABELS,
            "can": lambda module: role in Config.PERMISSIONS.get(module, ()),
            "db_engine": "MySQL" if app.config.get("USE_MYSQL") else "SQLite",
            "campus": campus_setup() if current_user.is_authenticated else None,
        }

    # ---------- Auth ----------
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            user = User.query.filter_by(username=username).first()
            if not user or not user.check_password(password):
                flash("Invalid username or password.", "error")
                return render_template("login.html")
            if Config.USE_EMAIL_VERIFICATION and not user.email_verified:
                flash("Please verify your email before signing in.", "warning")
                return redirect(url_for("verify_email", user_id=user.id))
            if not user.is_active:
                flash("This account has been deactivated. Contact a Super Admin.", "error")
                return render_template("login.html")
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            flash(f"Welcome back, {user.full_name}. You are signed in as {user.role_label}.", "success")
            return redirect(url_for("dashboard"))
        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            full_name = (request.form.get("full_name") or "").strip()
            password = request.form.get("password") or ""
            confirm_password = request.form.get("confirm_password") or ""

            if not all([username, email, full_name, password]):
                flash("All fields are required.", "error")
                return render_template("register.html")

            if not _validate_email(email):
                flash("Please enter a valid email address (e.g., user@example.com).", "error")
                return render_template("register.html")

            if len(password) < 6:
                flash("Password must be at least 6 characters.", "error")
                return render_template("register.html")

            if password != confirm_password:
                flash("Passwords do not match.", "error")
                return render_template("register.html")

            if User.query.filter_by(username=username).first():
                flash("Username already exists.", "error")
                return render_template("register.html")

            if User.query.filter_by(email=email).first():
                flash("Email already registered.", "error")
                return render_template("register.html")

            user = User(
                username=username,
                full_name=full_name,
                email=email,
                role="staff",
                email_verified=not Config.USE_EMAIL_VERIFICATION,
                is_active=not Config.USE_EMAIL_VERIFICATION,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            if Config.USE_EMAIL_VERIFICATION:
                otp_code = _generate_otp()
                user.otp_code = otp_code
                user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
                db.session.commit()

                if _send_otp_email(user.email, otp_code):
                    flash("Account created! Check your email for the OTP.", "success")
                    return redirect(url_for("verify_email", user_id=user.id))
                else:
                    db.session.delete(user)
                    db.session.commit()
                    flash("Failed to send verification email. Please try again.", "error")
                    return render_template("register.html")
            else:
                flash("Account created successfully! You can now sign in.", "success")
                return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/verify-email/<int:user_id>", methods=["GET", "POST"])
    def verify_email(user_id):
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if not Config.USE_EMAIL_VERIFICATION:
            flash("Email verification is disabled.", "error")
            return redirect(url_for("login"))

        user = User.query.get(user_id)
        if not user:
            flash("Invalid verification link.", "error")
            return redirect(url_for("register"))

        if request.method == "POST":
            otp_code = (request.form.get("otp_code") or "").strip()

            if not otp_code:
                flash("OTP is required.", "error")
                return render_template("verify_email.html", user_id=user_id)

            if user.otp_expires_at and datetime.utcnow() > user.otp_expires_at:
                flash("OTP has expired. Please request a new one.", "error")
                return render_template("verify_email.html", user_id=user_id)

            if user.otp_code != otp_code:
                flash("Invalid OTP. Please try again.", "error")
                return render_template("verify_email.html", user_id=user_id)

            user.email_verified = True
            user.is_active = True
            user.otp_code = None
            user.otp_expires_at = None
            db.session.commit()

            flash("Email verified successfully! You can now sign in.", "success")
            return redirect(url_for("login"))

        return render_template("verify_email.html", user_id=user_id, email=user.email)

    @app.route("/api/resend-otp/<int:user_id>", methods=["POST"])
    def resend_otp(user_id):
        if not Config.USE_EMAIL_VERIFICATION:
            return json_error("Email verification is disabled", 400)

        user = User.query.get(user_id)
        if not user:
            return json_error("User not found", 404)

        if user.email_verified:
            return json_error("Email already verified", 400)

        otp_code = _generate_otp()
        user.otp_code = otp_code
        user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        db.session.commit()

        if _send_otp_email(user.email, otp_code):
            return json_ok(message="OTP sent to your email")
        else:
            return json_error("Failed to send OTP", 500)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been signed out.", "success")
        return redirect(url_for("login"))

    # ---------- Pages ----------
    @app.route("/")
    @login_required
    def dashboard():
        today = datetime.utcnow().strftime("%A")
        if today not in DAYS:
            today = "Monday"
        slots = TimeSlot.query.order_by(TimeSlot.sort_order).all()
        current_slot = _current_timeslot(slots)

        stats = {
            "buildings": Building.query.filter_by(is_active=True).count(),
            "classrooms": Classroom.query.filter_by(is_active=True).count(),
            "users": User.query.filter_by(is_active=True).count(),
            "admins": User.query.filter(User.role.in_(["super_admin", "admin"]), User.is_active.is_(True)).count(),
            "timetable": Timetable.query.count(),
            "bookings": Booking.query.filter_by(status="confirmed").count(),
        }

        occupancy = []
        if current_slot:
            occupied = occupied_classroom_ids(today, current_slot.id)
            total = Classroom.query.filter_by(is_active=True).count()
            occupancy = {
                "day": today,
                "slot": current_slot.label(),
                "occupied": len(occupied),
                "available": max(total - len(occupied), 0),
                "total": total,
            }

        recent_bookings = (
            Booking.query.order_by(Booking.created_at.desc()).limit(6).all()
        )
        return render_template(
            "dashboard.html",
            stats=stats,
            occupancy=occupancy,
            recent_bookings=recent_bookings,
            current_slot=current_slot,
            today=today,
        )

    @app.route("/search")
    @permission_required("search")
    def search_page():
        return render_template(
            "search.html",
            buildings=Building.query.filter_by(is_active=True).order_by(Building.name).all(),
            timeslots=TimeSlot.query.order_by(TimeSlot.sort_order).all(),
        )

    @app.route("/setup")
    @permission_required("setup")
    def setup_page():
        return redirect(url_for("dashboard"))

    @app.route("/api/setup/status")
    @permission_required("setup")
    def api_setup_status():
        status = campus_setup()
        status["buildings"] = [b.to_dict() for b in Building.query.order_by(Building.name)]
        status["floors"] = [
            f.to_dict() for f in Floor.query.order_by(Floor.building_id, Floor.floor_number)
        ]
        status["classrooms"] = [c.to_dict() for c in Classroom.query.order_by(Classroom.room_number)]
        status["timeslots"] = [
            t.to_dict() for t in TimeSlot.query.order_by(TimeSlot.sort_order)
        ]
        return json_ok(status)

    @app.route("/buildings")
    @permission_required("buildings")
    def buildings_page():
        return render_template("buildings.html")

    @app.route("/classrooms")
    @permission_required("classrooms")
    def classrooms_page():
        return render_template(
            "classrooms.html",
            buildings=Building.query.order_by(Building.name).all(),
        )

    @app.route("/timeslots")
    @permission_required("timeslots")
    def timeslots_page():
        return render_template("timeslots.html")

    @app.route("/timetable")
    @permission_required("timetable")
    def timetable_page():
        return render_template(
            "timetable.html",
            buildings=Building.query.filter_by(is_active=True).order_by(Building.name).all(),
            timeslots=TimeSlot.query.order_by(TimeSlot.sort_order).all(),
            classrooms=classroom_query().all(),
        )

    @app.route("/bookings")
    @permission_required("bookings")
    def bookings_page():
        return render_template(
            "bookings.html",
            buildings=Building.query.filter_by(is_active=True).order_by(Building.name).all(),
            timeslots=TimeSlot.query.order_by(TimeSlot.sort_order).all(),
            classrooms=classroom_query().all(),
        )

    @app.route("/occupancy")
    @permission_required("occupancy")
    def occupancy_page():
        return render_template(
            "occupancy.html",
            buildings=Building.query.filter_by(is_active=True).order_by(Building.name).all(),
            timeslots=TimeSlot.query.order_by(TimeSlot.sort_order).all(),
        )

    @app.route("/users")
    @permission_required("users")
    def users_page():
        return render_template("users.html")

    @app.route("/reports")
    @permission_required("reports")
    def reports_page():
        return render_template(
            "reports.html",
            timeslots=TimeSlot.query.order_by(TimeSlot.sort_order).all(),
        )

    @app.route("/profile", methods=["GET", "POST"])
    @permission_required("profile")
    def profile():
        if request.method == "POST":
            full_name = (request.form.get("full_name") or "").strip()
            email = (request.form.get("email") or "").strip()
            department = (request.form.get("department") or "").strip()
            if not full_name or not email:
                flash("Name and email are required.", "error")
                return redirect(url_for("profile"))
            existing = User.query.filter(User.email == email, User.id != current_user.id).first()
            if existing:
                flash("That email is already in use.", "error")
                return redirect(url_for("profile"))
            current_user.full_name = full_name
            current_user.email = email
            current_user.department = department
            current_password = request.form.get("current_password") or ""
            new_password = request.form.get("new_password") or ""
            if new_password:
                if not current_user.check_password(current_password):
                    flash("Current password is incorrect.", "error")
                    return redirect(url_for("profile"))
                if len(new_password) < 6:
                    flash("New password must be at least 6 characters.", "error")
                    return redirect(url_for("profile"))
                current_user.set_password(new_password)
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("profile"))
        return render_template("profile.html")

    # ---------- Lookups ----------
    @app.route("/api/lookups")
    @login_required
    def api_lookups():
        return json_ok(
            {
                "days": DAYS,
                "room_types": ROOM_TYPES,
                "roles": [
                    {"id": key, "label": label}
                    for key, label in Config.ROLE_LABELS.items()
                ],
                "buildings": [b.to_dict() for b in Building.query.order_by(Building.name)],
                "floors": [f.to_dict() for f in Floor.query.order_by(Floor.floor_number)],
                "timeslots": [
                    t.to_dict()
                    for t in TimeSlot.query.order_by(TimeSlot.sort_order)
                ],
                "classrooms": [c.to_dict() for c in classroom_query().all()],
            }
        )

    @app.route("/api/floors")
    @login_required
    def api_floors_by_building():
        building_id = request.args.get("building_id")
        q = Floor.query
        if building_id:
            q = q.filter_by(building_id=int(building_id))
        floors = q.order_by(Floor.floor_number).all()
        return json_ok([f.to_dict() for f in floors])

    @app.route("/api/classrooms/options")
    @login_required
    def api_classroom_options():
        rooms = classroom_query(
            building_id=request.args.get("building_id"),
            floor_id=request.args.get("floor_id"),
        ).all()
        return json_ok([c.to_dict() for c in rooms])

    # ---------- Search ----------
    @app.route("/api/search", methods=["POST"])
    @permission_required("search")
    def api_search():
        data = request.get_json(force=True, silent=True) or {}
        day = data.get("day")
        timeslot_id = data.get("timeslot_id")
        capacity = int(data.get("capacity") or 0)
        if day not in DAYS:
            return json_error("Please select a valid day.")
        if not timeslot_id:
            return json_error("Please select a time slot.")
        slot = db.session.get(TimeSlot, int(timeslot_id))
        if not slot:
            return json_error("Time slot not found.")
        if slot.is_break:
            return json_error("That period is a break. Choose a teaching slot.")

        occupied = occupied_classroom_ids(day, slot.id)
        candidates = classroom_query(
            building_id=data.get("building_id") or None,
            floor_id=data.get("floor_id") or None,
            min_capacity=capacity,
        ).all()
        available = []
        all_matching = classroom_query(
            building_id=data.get("building_id") or None,
            floor_id=data.get("floor_id") or None,
        ).all()
        occupied_rooms = []
        for room in all_matching:
            if room.id in occupied:
                reason = _occupation_reason(room.id, day, slot.id)
                occupied_rooms.append({**room.to_dict(), "reason": reason})

        for room in candidates:
            item = room.to_dict()
            item["spare_seats"] = room.capacity - capacity
            available.append(item)

        available = [r for r in available if r["id"] not in occupied]
        return json_ok(
            {
                "filters": {
                    "day": day,
                    "timeslot": slot.label(),
                    "capacity": capacity,
                },
                "available": available,
                "occupied": occupied_rooms,
                "counts": {
                    "available": len(available),
                    "occupied": len(occupied_rooms),
                    "checked": len(all_matching),
                },
            }
        )

    # ---------- Buildings & floors ----------
    @app.route("/api/buildings", methods=["GET", "POST"])
    @permission_required("buildings")
    def api_buildings():
        if request.method == "GET":
            return json_ok([b.to_dict() for b in Building.query.order_by(Building.name)])
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get("name") or "").strip()
        code = (data.get("code") or "").strip().upper()
        if not name or not code:
            return json_error("Building name and code are required.")
        if Building.query.filter(or_(Building.name == name, Building.code == code)).first():
            return json_error("A building with that name or code already exists.")
        building = Building(
            name=name,
            code=code,
            description=(data.get("description") or "").strip(),
            is_active=bool(data.get("is_active", True)),
        )
        db.session.add(building)
        db.session.commit()
        return json_ok(building.to_dict())

    @app.route("/api/buildings/<int:item_id>", methods=["PUT", "DELETE"])
    @permission_required("buildings")
    def api_building_item(item_id):
        building = db.session.get(Building, item_id)
        if not building:
            return json_error("Building not found.", 404)
        if request.method == "DELETE":
            db.session.delete(building)
            db.session.commit()
            return json_ok({"deleted": True})
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get("name") or "").strip()
        code = (data.get("code") or "").strip().upper()
        if not name or not code:
            return json_error("Building name and code are required.")
        clash = Building.query.filter(
            Building.id != item_id, or_(Building.name == name, Building.code == code)
        ).first()
        if clash:
            return json_error("A building with that name or code already exists.")
        building.name = name
        building.code = code
        building.description = (data.get("description") or "").strip()
        building.is_active = bool(data.get("is_active", True))
        db.session.commit()
        return json_ok(building.to_dict())

    @app.route("/api/floors", methods=["GET", "POST"])
    @permission_required("buildings")
    def api_floors():
        if request.method == "GET":
            return json_ok(
                [f.to_dict() for f in Floor.query.order_by(Floor.building_id, Floor.floor_number)]
            )
        data = request.get_json(force=True, silent=True) or {}
        try:
            building_id = int(data.get("building_id"))
            floor_number = int(data.get("floor_number"))
        except (TypeError, ValueError):
            return json_error("Building and floor number are required.")
        name = (data.get("name") or "").strip()
        if not name:
            return json_error("Floor name is required.")
        if not db.session.get(Building, building_id):
            return json_error("Building not found.")
        if Floor.query.filter_by(building_id=building_id, floor_number=floor_number).first():
            return json_error("That floor already exists in this building.")
        floor = Floor(
            building_id=building_id,
            floor_number=floor_number,
            name=name,
            description=(data.get("description") or "").strip(),
        )
        db.session.add(floor)
        db.session.commit()
        return json_ok(floor.to_dict())

    @app.route("/api/floors/<int:item_id>", methods=["PUT", "DELETE"])
    @permission_required("buildings")
    def api_floor_item(item_id):
        floor = db.session.get(Floor, item_id)
        if not floor:
            return json_error("Floor not found.", 404)
        if request.method == "DELETE":
            db.session.delete(floor)
            db.session.commit()
            return json_ok({"deleted": True})
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get("name") or "").strip()
        try:
            floor_number = int(data.get("floor_number"))
        except (TypeError, ValueError):
            return json_error("Floor number is required.")
        if not name:
            return json_error("Floor name is required.")
        clash = Floor.query.filter(
            Floor.building_id == floor.building_id,
            Floor.floor_number == floor_number,
            Floor.id != item_id,
        ).first()
        if clash:
            return json_error("That floor already exists in this building.")
        floor.name = name
        floor.floor_number = floor_number
        floor.description = (data.get("description") or "").strip()
        db.session.commit()
        return json_ok(floor.to_dict())

    # ---------- Classrooms ----------
    @app.route("/api/classrooms", methods=["GET", "POST"])
    @permission_required("classrooms")
    def api_classrooms():
        if request.method == "GET":
            rooms = classroom_query(
                building_id=request.args.get("building_id"),
                floor_id=request.args.get("floor_id"),
                active_only=False,
            ).all()
            return json_ok([c.to_dict() for c in rooms])
        data = request.get_json(force=True, silent=True) or {}
        try:
            floor_id = int(data.get("floor_id"))
            capacity = int(data.get("capacity"))
        except (TypeError, ValueError):
            return json_error("Floor and capacity are required.")
        room_number = (data.get("room_number") or "").strip()
        if not room_number or capacity <= 0:
            return json_error("Room number and a positive capacity are required.")
        if not db.session.get(Floor, floor_id):
            return json_error("Floor not found.")
        if Classroom.query.filter_by(floor_id=floor_id, room_number=room_number).first():
            return json_error("That room number already exists on this floor.")
        room = Classroom(
            floor_id=floor_id,
            room_number=room_number,
            capacity=capacity,
            room_type=data.get("room_type") or "Lecture Hall",
            facilities=(data.get("facilities") or "").strip(),
            description=(data.get("description") or "").strip(),
            is_active=bool(data.get("is_active", True)),
        )
        db.session.add(room)
        db.session.commit()
        return json_ok(room.to_dict())

    @app.route("/api/classrooms/<int:item_id>", methods=["PUT", "DELETE"])
    @permission_required("classrooms")
    def api_classroom_item(item_id):
        room = db.session.get(Classroom, item_id)
        if not room:
            return json_error("Classroom not found.", 404)
        if request.method == "DELETE":
            db.session.delete(room)
            db.session.commit()
            return json_ok({"deleted": True})
        data = request.get_json(force=True, silent=True) or {}
        try:
            floor_id = int(data.get("floor_id"))
            capacity = int(data.get("capacity"))
        except (TypeError, ValueError):
            return json_error("Floor and capacity are required.")
        room_number = (data.get("room_number") or "").strip()
        if not room_number or capacity <= 0:
            return json_error("Room number and a positive capacity are required.")
        clash = Classroom.query.filter(
            Classroom.floor_id == floor_id,
            Classroom.room_number == room_number,
            Classroom.id != item_id,
        ).first()
        if clash:
            return json_error("That room number already exists on this floor.")
        room.floor_id = floor_id
        room.room_number = room_number
        room.capacity = capacity
        room.room_type = data.get("room_type") or room.room_type
        room.facilities = (data.get("facilities") or "").strip()
        room.description = (data.get("description") or "").strip()
        room.is_active = bool(data.get("is_active", True))
        db.session.commit()
        return json_ok(room.to_dict())

    # ---------- Time slots ----------
    @app.route("/api/timeslots", methods=["GET", "POST"])
    @permission_required("timeslots")
    def api_timeslots():
        if request.method == "GET":
            return json_ok([t.to_dict() for t in TimeSlot.query.order_by(TimeSlot.sort_order)])
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get("name") or "").strip()
        start_time = (data.get("start_time") or "").strip()
        end_time = (data.get("end_time") or "").strip()
        if not name or not start_time or not end_time:
            return json_error("Name, start time and end time are required.")
        slot = TimeSlot(
            name=name,
            start_time=_normalize_time(start_time),
            end_time=_normalize_time(end_time),
            sort_order=int(data.get("sort_order") or 0),
            is_break=bool(data.get("is_break")),
        )
        db.session.add(slot)
        db.session.commit()
        return json_ok(slot.to_dict())

    @app.route("/api/timeslots/<int:item_id>", methods=["PUT", "DELETE"])
    @permission_required("timeslots")
    def api_timeslot_item(item_id):
        slot = db.session.get(TimeSlot, item_id)
        if not slot:
            return json_error("Time slot not found.", 404)
        if request.method == "DELETE":
            db.session.delete(slot)
            db.session.commit()
            return json_ok({"deleted": True})
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get("name") or "").strip()
        start_time = (data.get("start_time") or "").strip()
        end_time = (data.get("end_time") or "").strip()
        if not name or not start_time or not end_time:
            return json_error("Name, start time and end time are required.")
        slot.name = name
        slot.start_time = _normalize_time(start_time)
        slot.end_time = _normalize_time(end_time)
        slot.sort_order = int(data.get("sort_order") or 0)
        slot.is_break = bool(data.get("is_break"))
        db.session.commit()
        return json_ok(slot.to_dict())

    # ---------- Timetable ----------
    @app.route("/api/timetable", methods=["GET", "POST"])
    @permission_required("timetable")
    def api_timetable():
        if request.method == "GET":
            q = Timetable.query
            if request.args.get("day"):
                q = q.filter_by(day_of_week=request.args.get("day"))
            if request.args.get("timeslot_id"):
                q = q.filter_by(timeslot_id=int(request.args.get("timeslot_id")))
            if request.args.get("classroom_id"):
                q = q.filter_by(classroom_id=int(request.args.get("classroom_id")))
            rows = q.order_by(Timetable.day_of_week, Timetable.timeslot_id).all()
            return json_ok([r.to_dict() for r in rows])
        data = request.get_json(force=True, silent=True) or {}
        error = _validate_allocation(data)
        if error:
            return json_error(error)
        clash = _find_timetable_clash(
            int(data["classroom_id"]), data["day_of_week"], int(data["timeslot_id"])
        )
        if clash:
            return json_error(_clash_message(clash))
        booking = Booking.query.filter_by(
            classroom_id=int(data["classroom_id"]),
            day_of_week=data["day_of_week"],
            timeslot_id=int(data["timeslot_id"]),
            status="confirmed",
        ).first()
        if booking:
            return json_error("This classroom already has a confirmed extra-class booking.")
        row = Timetable(
            classroom_id=int(data["classroom_id"]),
            day_of_week=data["day_of_week"],
            timeslot_id=int(data["timeslot_id"]),
            subject=(data.get("subject") or "").strip(),
            teacher_name=(data.get("teacher_name") or "").strip(),
            class_group=(data.get("class_group") or "").strip(),
            academic_year=(data.get("academic_year") or "").strip(),
        )
        db.session.add(row)
        db.session.commit()
        return json_ok(row.to_dict())

    @app.route("/api/timetable/<int:item_id>", methods=["PUT", "DELETE"])
    @permission_required("timetable")
    def api_timetable_item(item_id):
        row = db.session.get(Timetable, item_id)
        if not row:
            return json_error("Timetable entry not found.", 404)
        if request.method == "DELETE":
            db.session.delete(row)
            db.session.commit()
            return json_ok({"deleted": True})
        data = request.get_json(force=True, silent=True) or {}
        error = _validate_allocation(data)
        if error:
            return json_error(error)
        clash = _find_timetable_clash(
            int(data["classroom_id"]),
            data["day_of_week"],
            int(data["timeslot_id"]),
            exclude_id=item_id,
        )
        if clash:
            return json_error(_clash_message(clash))
        row.classroom_id = int(data["classroom_id"])
        row.day_of_week = data["day_of_week"]
        row.timeslot_id = int(data["timeslot_id"])
        row.subject = (data.get("subject") or "").strip()
        row.teacher_name = (data.get("teacher_name") or "").strip()
        row.class_group = (data.get("class_group") or "").strip()
        row.academic_year = (data.get("academic_year") or "").strip()
        db.session.commit()
        return json_ok(row.to_dict())

    # ---------- Bookings ----------
    @app.route("/api/bookings", methods=["GET", "POST"])
    @permission_required("bookings")
    def api_bookings():
        if request.method == "GET":
            q = Booking.query
            if request.args.get("status"):
                q = q.filter_by(status=request.args.get("status"))
            if request.args.get("day"):
                q = q.filter_by(day_of_week=request.args.get("day"))
            if not current_user.is_admin:
                q = q.filter_by(booked_by_id=current_user.id)
            rows = q.order_by(Booking.created_at.desc()).all()
            return json_ok([r.to_dict() for r in rows])
        data = request.get_json(force=True, silent=True) or {}
        error = _validate_allocation(data, require_subject=False)
        if error:
            return json_error(error)
        purpose = (data.get("purpose") or "").strip()
        if not purpose:
            return json_error("Purpose is required.")
        classroom_id = int(data["classroom_id"])
        day = data["day_of_week"]
        timeslot_id = int(data["timeslot_id"])
        occupied = occupied_classroom_ids(day, timeslot_id)
        if classroom_id in occupied:
            return json_error("This classroom is already occupied for that day and time.")
        room = db.session.get(Classroom, classroom_id)
        student_count = int(data.get("student_count") or 0)
        if student_count and room and student_count > room.capacity:
            return json_error("Student count exceeds classroom capacity.")
        row = Booking(
            classroom_id=classroom_id,
            day_of_week=day,
            timeslot_id=timeslot_id,
            purpose=purpose,
            booked_by_id=current_user.id,
            student_count=student_count,
            status="confirmed",
            notes=(data.get("notes") or "").strip(),
        )
        db.session.add(row)
        db.session.commit()
        return json_ok(row.to_dict())

    @app.route("/api/bookings/<int:item_id>", methods=["PUT", "DELETE"])
    @permission_required("bookings")
    def api_booking_item(item_id):
        row = db.session.get(Booking, item_id)
        if not row:
            return json_error("Booking not found.", 404)
        if not current_user.is_admin and row.booked_by_id != current_user.id:
            return json_error("You can only manage your own bookings.", 403)
        if request.method == "DELETE":
            db.session.delete(row)
            db.session.commit()
            return json_ok({"deleted": True})
        data = request.get_json(force=True, silent=True) or {}
        if data.get("status") == "cancelled":
            row.status = "cancelled"
            db.session.commit()
            return json_ok(row.to_dict())
        error = _validate_allocation(data, require_subject=False)
        if error:
            return json_error(error)
        purpose = (data.get("purpose") or "").strip()
        if not purpose:
            return json_error("Purpose is required.")
        occupied = occupied_classroom_ids(
            data["day_of_week"], int(data["timeslot_id"]), exclude_booking_id=row.id
        )
        if int(data["classroom_id"]) in occupied:
            return json_error("This classroom is already occupied for that day and time.")
        row.classroom_id = int(data["classroom_id"])
        row.day_of_week = data["day_of_week"]
        row.timeslot_id = int(data["timeslot_id"])
        row.purpose = purpose
        row.student_count = int(data.get("student_count") or 0)
        row.notes = (data.get("notes") or "").strip()
        row.status = data.get("status") or row.status
        db.session.commit()
        return json_ok(row.to_dict())

    # ---------- Occupancy & reports ----------
    @app.route("/api/occupancy")
    @permission_required("occupancy")
    def api_occupancy():
        day = request.args.get("day") or datetime.utcnow().strftime("%A")
        if day not in DAYS:
            day = "Monday"
        timeslot_id = request.args.get("timeslot_id")
        slot = db.session.get(TimeSlot, int(timeslot_id)) if timeslot_id else _current_timeslot(
            TimeSlot.query.order_by(TimeSlot.sort_order).all()
        )
        if not slot:
            return json_error("No time slot available.")
        occupied_ids = occupied_classroom_ids(day, slot.id)
        rooms = classroom_query(
            building_id=request.args.get("building_id"),
            floor_id=request.args.get("floor_id"),
        ).all()
        result = []
        for room in rooms:
            item = room.to_dict()
            item["status"] = "occupied" if room.id in occupied_ids else "available"
            item["reason"] = _occupation_reason(room.id, day, slot.id) if room.id in occupied_ids else ""
            result.append(item)
        return json_ok(
            {
                "day": day,
                "timeslot": slot.to_dict(),
                "rooms": result,
                "counts": {
                    "available": sum(1 for r in result if r["status"] == "available"),
                    "occupied": sum(1 for r in result if r["status"] == "occupied"),
                    "total": len(result),
                },
            }
        )

    @app.route("/api/reports/summary")
    @permission_required("reports")
    def api_reports():
        summary = []
        rooms = Classroom.query.filter_by(is_active=True).all()
        slots = TimeSlot.query.filter_by(is_break=False).order_by(TimeSlot.sort_order).all()
        for day in DAYS:
            occupied_total = 0
            slots_checked = 0
            for slot in slots:
                occupied_total += len(occupied_classroom_ids(day, slot.id))
                slots_checked += 1
            capacity = len(rooms) * max(slots_checked, 1)
            summary.append(
                {
                    "day": day,
                    "occupied_slots": occupied_total,
                    "total_slots": len(rooms) * slots_checked,
                    "utilization": round((occupied_total / capacity) * 100, 1) if capacity else 0,
                }
            )
        by_building = []
        for building in Building.query.filter_by(is_active=True):
            room_ids = [c.id for f in building.floors for c in f.classrooms if c.is_active]
            by_building.append(
                {
                    "building": building.name,
                    "classrooms": len(room_ids),
                    "total_capacity": sum(
                        c.capacity for f in building.floors for c in f.classrooms if c.is_active
                    ),
                }
            )
        return json_ok({"by_day": summary, "by_building": by_building})

    # ---------- Users & access ----------
    @app.route("/api/users", methods=["GET", "POST"])
    @permission_required("users")
    def api_users():
        if request.method == "GET":
            role = request.args.get("role")
            q = User.query
            if role:
                q = q.filter_by(role=role)
            if request.args.get("admins") == "1":
                q = q.filter(User.role.in_(["super_admin", "admin"]))
            users = q.order_by(User.role, User.full_name).all()
            return json_ok([u.to_dict() for u in users])
        data = request.get_json(force=True, silent=True) or {}
        username = (data.get("username") or "").strip().lower()
        full_name = (data.get("full_name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        role = data.get("role") or "staff"
        password = data.get("password") or ""
        if role not in Config.ALL_ROLES:
            return json_error("Invalid role.")
        if not username or not full_name or not email or not password:
            return json_error("Username, name, email and password are required.")
        if len(password) < 6:
            return json_error("Password must be at least 6 characters.")
        if User.query.filter(or_(User.username == username, User.email == email)).first():
            return json_error("Username or email already exists.")
        user = User(
            username=username,
            full_name=full_name,
            email=email,
            role=role,
            department=(data.get("department") or "").strip(),
            is_active=bool(data.get("is_active", True)),
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return json_ok(user.to_dict())

    @app.route("/api/users/<int:item_id>", methods=["PUT", "DELETE"])
    @permission_required("users")
    def api_user_item(item_id):
        user = db.session.get(User, item_id)
        if not user:
            return json_error("User not found.", 404)
        if request.method == "DELETE":
            if user.id == current_user.id:
                return json_error("You cannot delete your own account.")
            if user.role == "super_admin" and User.query.filter_by(role="super_admin").count() <= 1:
                return json_error("At least one Super Admin must remain.")
            db.session.delete(user)
            db.session.commit()
            return json_ok({"deleted": True})
        data = request.get_json(force=True, silent=True) or {}
        full_name = (data.get("full_name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        role = data.get("role") or user.role
        if role not in Config.ALL_ROLES:
            return json_error("Invalid role.")
        if user.id == current_user.id and role != user.role:
            return json_error("You cannot change your own role.")
        if (
            user.role == "super_admin"
            and role != "super_admin"
            and User.query.filter_by(role="super_admin").count() <= 1
        ):
            return json_error("At least one Super Admin must remain.")
        if not full_name or not email:
            return json_error("Name and email are required.")
        clash = User.query.filter(User.email == email, User.id != item_id).first()
        if clash:
            return json_error("That email is already in use.")
        user.full_name = full_name
        user.email = email
        user.role = role
        user.department = (data.get("department") or "").strip()
        user.is_active = bool(data.get("is_active", True))
        if user.id == current_user.id:
            user.is_active = True
        password = data.get("password") or ""
        if password:
            if len(password) < 6:
                return json_error("Password must be at least 6 characters.")
            user.set_password(password)
        db.session.commit()
        return json_ok(user.to_dict())

    @app.errorhandler(404)
    def not_found(_e):
        if request.path.startswith("/api/"):
            return json_error("Not found.", 404)
        return render_template("login.html") if not current_user.is_authenticated else redirect(url_for("dashboard"))

    @app.errorhandler(500)
    def server_error(_e):
        if request.path.startswith("/api/"):
            return json_error("Server error.", 500)
        flash("Something went wrong. Please try again.", "error")
        return redirect(url_for("dashboard") if current_user.is_authenticated else url_for("login"))


def _normalize_time(value):
    value = value.strip()
    if len(value) == 5:
        return value
    try:
        parsed = datetime.strptime(value, "%H:%M:%S")
        return parsed.strftime("%H:%M")
    except ValueError:
        return value


def _find_timetable_clash(classroom_id, day, timeslot_id, exclude_id=None):
    slot = db.session.get(TimeSlot, timeslot_id)
    if not slot:
        return None
    overlapping_ids = [
        s.id
        for s in TimeSlot.query.filter(
            TimeSlot.start_time < slot.end_time, TimeSlot.end_time > slot.start_time
        )
    ]
    q = Timetable.query.filter(
        Timetable.classroom_id == classroom_id,
        Timetable.day_of_week == day,
        Timetable.timeslot_id.in_(overlapping_ids),
    )
    if exclude_id:
        q = q.filter(Timetable.id != exclude_id)
    return q.first()


def _clash_message(clash):
    return (
        f"Clash: Room {clash.classroom.room_number} already has "
        f"'{clash.subject}' on {clash.day_of_week}, {clash.timeslot.label()}."
    )


def _current_timeslot(slots):
    now = datetime.now().strftime("%H:%M")
    for slot in slots:
        if slot.start_time <= now < slot.end_time:
            return slot
    teaching = [s for s in slots if not s.is_break]
    return teaching[0] if teaching else (slots[0] if slots else None)


def _occupation_reason(classroom_id, day, timeslot_id):
    entry = Timetable.query.filter_by(
        classroom_id=classroom_id, day_of_week=day, timeslot_id=timeslot_id
    ).first()
    if entry:
        teacher = f" — {entry.teacher_name}" if entry.teacher_name else ""
        group = f" ({entry.class_group})" if entry.class_group else ""
        return f"Timetable: {entry.subject}{group}{teacher}"
    booking = Booking.query.filter_by(
        classroom_id=classroom_id,
        day_of_week=day,
        timeslot_id=timeslot_id,
        status="confirmed",
    ).first()
    if booking:
        by = booking.booked_by.full_name if booking.booked_by else "staff"
        return f"Extra booking: {booking.purpose} by {by}"
    return "Occupied"


def _validate_allocation(data, require_subject=True):
    day = data.get("day_of_week") or data.get("day")
    if day not in DAYS:
        return "Please select a valid day."
    data["day_of_week"] = day
    try:
        classroom_id = int(data.get("classroom_id"))
        timeslot_id = int(data.get("timeslot_id"))
    except (TypeError, ValueError):
        return "Classroom and time slot are required."
    if not db.session.get(Classroom, classroom_id):
        return "Classroom not found."
    slot = db.session.get(TimeSlot, timeslot_id)
    if not slot:
        return "Time slot not found."
    if slot.is_break:
        return "Cannot allocate a classroom during a break."
    if require_subject and not (data.get("subject") or "").strip():
        return "Subject is required."
    return None


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
