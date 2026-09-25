import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _mysql_uri():
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE", "cias")
    auth = f"{user}:{password}" if password else user
    return f"mysql+pymysql://{auth}@{host}:{port}/{database}?charset=utf8mb4"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "cias-college-secret-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    USE_MYSQL = os.getenv("USE_MYSQL", "1") == "1"
    MYSQL_URI = _mysql_uri()
    SQLITE_URI = f"sqlite:///{BASE_DIR / 'cias.db'}"

    SQLALCHEMY_DATABASE_URI = MYSQL_URI if USE_MYSQL else SQLITE_URI

    # Email Verification
    USE_EMAIL_VERIFICATION = os.getenv("USE_EMAIL_VERIFICATION", "True") == "True"

    # Email Configuration
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM = os.getenv("MAIL_FROM", "noreply@cias.college")

    # Roles
    ROLE_SUPER_ADMIN = "super_admin"
    ROLE_ADMIN = "admin"
    ROLE_STAFF = "staff"

    ADMIN_ROLES = (ROLE_SUPER_ADMIN, ROLE_ADMIN)
    ALL_ROLES = (ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_STAFF)

    ROLE_LABELS = {
        ROLE_SUPER_ADMIN: "Super Admin",
        ROLE_ADMIN: "Admin",
        ROLE_STAFF: "Staff",
    }

    # Permissions by module
    PERMISSIONS = {
        "dashboard": ALL_ROLES,
        "search": ALL_ROLES,
        "buildings": ADMIN_ROLES,
        "classrooms": ADMIN_ROLES,
        "timeslots": ADMIN_ROLES,
        "timetable": ADMIN_ROLES,
        "bookings": ALL_ROLES,
        "occupancy": ALL_ROLES,
        "users": (ROLE_SUPER_ADMIN,),
        "reports": ADMIN_ROLES,
        "profile": ALL_ROLES,
        "setup": ADMIN_ROLES,
    }
