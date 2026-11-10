"""
Music Suggestion System - Flask Backend Application
Connects to MySQL database and serves recommendations via sentence-transformers
using primary proposed model: sentence-transformers/paraphrase-multilingual-mpnet-base-v2,
with complete user activity tracking, history-aware personalization, and local MP3 playback.
"""

import os
import re
import json
import hashlib
from functools import wraps
import pymysql
import pymysql.cursors
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_from_directory,
    redirect,
    url_for,
    flash,
    session,
    Response,
    make_response,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from model.recommender import (
    recommend_songs,
    recommend_by_vibes,
    recommend_personalized,
    get_model_info,
    preload_model,
)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "music_recommender_secret_key_demo_2026")

# MySQL Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_DB = os.getenv("MYSQL_DB", "music_recommendation_db")

# Upload Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads", "avatars")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB max


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db_connection():
    """Returns a new connection to the MySQL database."""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


def initialize_database():
    """Ensures database tables, Demo User, columns and initial songs exist."""
    try:
        # Step 1: Connect to server without database to ensure database exists
        server_conn = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            autocommit=True
        )
        with server_conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}`")
        server_conn.close()

        # Step 2: Run schema if tables are missing
        conn = get_db_connection()
        with conn.cursor() as cur:
            schema_path = os.path.join(os.path.dirname(__file__), "database", "schema.sql")
            if os.path.exists(schema_path):
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema_sql = f.read()
                for stmt in schema_sql.split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        cur.execute(stmt)

            # Ensure columns in users table
            cur.execute("SHOW COLUMNS FROM users LIKE 'username'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE users ADD COLUMN username VARCHAR(100) UNIQUE")
            cur.execute("SHOW COLUMNS FROM users LIKE 'email'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE users ADD COLUMN email VARCHAR(150) UNIQUE")
            cur.execute("SHOW COLUMNS FROM users LIKE 'password_hash'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)")
            cur.execute("SHOW COLUMNS FROM users LIKE 'profile_image'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE users ADD COLUMN profile_image VARCHAR(255) DEFAULT '/static/images/default_avatar.svg'")
            cur.execute("SHOW COLUMNS FROM users LIKE 'profile_completed'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE users ADD COLUMN profile_completed BOOLEAN DEFAULT FALSE")

            # Ensure recommendations_json column in user_requests table
            cur.execute("SHOW COLUMNS FROM user_requests LIKE 'recommendations_json'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE user_requests ADD COLUMN recommendations_json TEXT NULL")

            # Ensure feedback_type enum supports 'rating'
            try:
                cur.execute("ALTER TABLE feedback MODIFY COLUMN feedback_type ENUM('like', 'dislike', 'skip', 'rating') NOT NULL DEFAULT 'like'")
            except Exception as fe:
                pass

            # Ensure Demo User exists with valid password hash
            cur.execute("SELECT * FROM users WHERE user_id = 1")
            demo_user = cur.fetchone()
            if not demo_user:
                demo_hash = generate_password_hash("password123")
                cur.execute(
                    "INSERT INTO users (user_id, name, username, email, password_hash, profile_image, profile_completed) "
                    "VALUES (1, 'Demo User', 'demouser', 'demo@example.com', %s, '/static/images/default_avatar.svg', TRUE)",
                    (demo_hash,)
                )
                cur.execute(
                    "INSERT INTO user_profile (user_id, preferred_moods, preferred_genres, preferred_languages, liked_songs) "
                    "VALUES (1, 'Romantic, Happy, Calm / Peaceful', 'Bollywood, Sufi', 'Hindi', 'Kesariya, Kun Faya Kun')"
                )
            else:
                if not demo_user.get("username") or not demo_user.get("password_hash"):
                    demo_hash = generate_password_hash("password123")
                    cur.execute(
                        "UPDATE users SET username = 'demouser', email = 'demo@example.com', "
                        "password_hash = %s, profile_completed = TRUE WHERE user_id = 1",
                        (demo_hash,)
                    )

            # Check if audio_url column exists in songs table
            cur.execute("SHOW COLUMNS FROM songs LIKE 'audio_url'")
            has_audio_col = cur.fetchone()
            if not has_audio_col:
                cur.execute("ALTER TABLE songs ADD COLUMN audio_url VARCHAR(500)")

            # Check if duration column exists in songs table
            cur.execute("SHOW COLUMNS FROM songs LIKE 'duration'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE songs ADD COLUMN duration VARCHAR(20) NULL")

            # Check if songs table has rows, if not or if audio_url missing, seed it
            cur.execute("SELECT COUNT(*) AS total FROM songs")
            song_count = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS total_with_audio FROM songs WHERE audio_url IS NOT NULL AND audio_url != ''")
            audio_count = cur.fetchone()["total_with_audio"]

            if song_count == 0 or audio_count == 0:
                seed_path = os.path.join(os.path.dirname(__file__), "database", "seed.sql")
                if os.path.exists(seed_path):
                    with open(seed_path, "r", encoding="utf-8") as f:
                        seed_sql = f.read()
                    for stmt in seed_sql.split(";"):
                        stmt = stmt.strip()
                        if stmt:
                            cur.execute(stmt)
            # Check if cover_image and cover_mime_type exist in songs table
            cur.execute("SHOW COLUMNS FROM songs LIKE 'cover_image'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE songs ADD COLUMN cover_image MEDIUMBLOB NULL")

            cur.execute("SHOW COLUMNS FROM songs LIKE 'cover_mime_type'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE songs ADD COLUMN cover_mime_type VARCHAR(50) DEFAULT 'image/jpeg'")

            # Check if any initial song has missing cover image and seed from migration script
            cur.execute("SELECT COUNT(*) AS missing_covers FROM songs WHERE cover_image IS NULL AND song_id <= 10")
            missing_covers = cur.fetchone()["missing_covers"]
            if missing_covers > 0:
                try:
                    from migrate_song_covers import migrate_and_seed_covers
                    migrate_and_seed_covers()
                except Exception as cover_err:
                    print(f"[COVER MIGRATION NOTICE] {cover_err}")

        conn.close()
        print("[SUCCESS] MySQL database initialized and verified.")
    except Exception as e:
        print(f"[WARNING] Database initialization error: {e}")


# Initialize database schema and data on startup
initialize_database()


SONG_METADATA_FIELDS = """
    song_id, title, movie, artist, genre, mood, language, activity, 
    description, audio_url, duration, cover_mime_type, (cover_image IS NOT NULL) AS has_cover
"""

def fetch_songs_catalog(cur, song_id=None):
    """
    Fetches songs from MySQL with metadata and cover_url, omitting raw MEDIUMBLOB
    bytes to keep API responses and template renders fast, lean, and JSON-serializable.
    """
    if song_id is not None:
        cur.execute(f"SELECT {SONG_METADATA_FIELDS} FROM songs WHERE song_id = %s", (song_id,))
        row = cur.fetchone()
        if row:
            row["cover_url"] = f"/api/songs/{row['song_id']}/cover"
        return row
    else:
        cur.execute(f"SELECT {SONG_METADATA_FIELDS} FROM songs ORDER BY song_id ASC")
        rows = cur.fetchall()
        for r in rows:
            r["cover_url"] = f"/api/songs/{r['song_id']}/cover"
        return rows


def login_required(f):
    """Decorator to enforce authenticated session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Authentication required. Please log in."}), 401
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_user():
    """Inject current_user object into all rendered templates."""
    user_id = session.get("user_id")
    if user_id:
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                user = cur.fetchone()
            conn.close()
            if user:
                return {"current_user": user}
        except Exception as e:
            print(f"[ERROR] inject_user error: {e}")
    return {"current_user": None}


def get_user_history_data(user_id):
    """Retrieves full interaction history for user to feed into personalization model."""
    conn = get_db_connection()
    history = {
        "vibe_preferences": [],
        "liked_song_ids": [],
        "disliked_song_ids": [],
        "skipped_song_ids": [],
        "ratings": {},
        "favourite_song_ids": [],
        "past_prompts": [],
        "played_song_ids": []
    }
    try:
        with conn.cursor() as cur:
            # 1. Vibes
            cur.execute("SELECT mood_or_vibe FROM user_preferences WHERE user_id = %s", (user_id,))
            history["vibe_preferences"] = [r["mood_or_vibe"] for r in cur.fetchall()]

            # 2. Favourites
            cur.execute("SELECT song_id FROM user_favourites WHERE user_id = %s", (user_id,))
            history["favourite_song_ids"] = [r["song_id"] for r in cur.fetchall()]

            # 3. Feedback
            cur.execute("SELECT song_id, feedback_type, rating FROM feedback WHERE user_id = %s", (user_id,))
            for f in cur.fetchall():
                sid = f["song_id"]
                ftype = f["feedback_type"]
                rating = f["rating"]
                if ftype == "like":
                    history["liked_song_ids"].append(sid)
                elif ftype == "dislike":
                    history["disliked_song_ids"].append(sid)
                elif ftype == "skip":
                    history["skipped_song_ids"].append(sid)
                if rating is not None:
                    history["ratings"][sid] = rating

            # 4. Searches
            cur.execute("SELECT request_text FROM user_requests WHERE user_id = %s ORDER BY created_at DESC LIMIT 10", (user_id,))
            history["past_prompts"] = [r["request_text"] for r in cur.fetchall()]

            # 5. Playback
            cur.execute("""
                SELECT song_id, MAX(played_at) AS latest_played
                FROM user_playback_history
                WHERE user_id = %s
                GROUP BY song_id
                ORDER BY latest_played DESC
                LIMIT 10
            """, (user_id,))
            history["played_song_ids"] = [r["song_id"] for r in cur.fetchall()]
    except Exception as e:
        print(f"[ERROR] get_user_history_data: {e}")
    finally:
        conn.close()
    return history


# ==============================================================================
# AUTHENTICATION ROUTES
# ==============================================================================

@app.route("/signup", methods=["GET", "POST"])
@app.route("/register", methods=["GET", "POST"])
def signup():
    """Register a new user account with validation and password hashing."""
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validation
        if not username or not email or not password or not confirm_password:
            flash("All fields are required.", "error")
            return render_template("signup.html", username=username, email=email)

        if len(username) < 3 or len(username) > 30 or not re.match(r"^[a-zA-Z0-9_.-]+$", username):
            flash("Username must be 3-30 characters (letters, numbers, underscores, dots, dashes).", "error")
            return render_template("signup.html", username=username, email=email)

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            flash("Please enter a valid email address.", "error")
            return render_template("signup.html", username=username, email=email)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template("signup.html", username=username, email=email)

        if password != confirm_password:
            flash("Password and confirm password do not match.", "error")
            return render_template("signup.html", username=username, email=email)

        # Duplicate check in MySQL
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id, username, email FROM users WHERE username = %s OR email = %s",
                    (username, email)
                )
                existing = cur.fetchone()
                if existing:
                    if existing.get("username", "").lower() == username.lower():
                        flash("This username is already taken. Please choose another.", "error")
                    else:
                        flash("An account with this email already exists. Please log in.", "error")
                    conn.close()
                    return render_template("signup.html", username=username, email=email)

                # Secure password hashing and user insert
                pwd_hash = generate_password_hash(password)
                cur.execute(
                    "INSERT INTO users (name, username, email, password_hash, profile_image, profile_completed) "
                    "VALUES (%s, %s, %s, %s, '/static/images/default_avatar.svg', FALSE)",
                    (username, username, email, pwd_hash)
                )
                new_user_id = cur.lastrowid

                # Initialize empty user profile record
                cur.execute(
                    "INSERT INTO user_profile (user_id, preferred_moods, preferred_genres, preferred_languages, liked_songs) "
                    "VALUES (%s, '', '', 'Hindi', '')",
                    (new_user_id,)
                )

                # Record login session in user_sessions
                cur.execute(
                    "INSERT INTO user_sessions (user_id, login_time, ip_address, session_token) VALUES (%s, NOW(), %s, %s)",
                    (new_user_id, request.remote_addr or '127.0.0.1', request.headers.get("User-Agent", "")[:255])
                )
                session_db_id = cur.lastrowid

            conn.close()

            # Set session and redirect to profile onboarding
            session["user_id"] = new_user_id
            session["db_session_id"] = session_db_id
            flash("Account created successfully! Let's personalize your music tastes.", "success")
            return redirect(url_for("profile_setup"))

        except Exception as e:
            flash(f"Registration error: {str(e)}", "error")
            return render_template("signup.html", username=username, email=email)

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate user with username or email and password."""
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        login_id = request.form.get("login_id", "").strip()
        password = request.form.get("password", "")

        if not login_id or not password:
            flash("Please enter both username/email and password.", "error")
            return render_template("login.html", login_id=login_id)

        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM users WHERE username = %s OR email = %s",
                    (login_id, login_id.lower())
                )
                user = cur.fetchone()

                if not user or not user.get("password_hash") or not check_password_hash(user["password_hash"], password):
                    conn.close()
                    flash("Invalid username/email or password.", "error")
                    return render_template("login.html", login_id=login_id)

                # Record login session in user_sessions table
                cur.execute(
                    "INSERT INTO user_sessions (user_id, login_time, ip_address, session_token) VALUES (%s, NOW(), %s, %s)",
                    (user["user_id"], request.remote_addr or '127.0.0.1', request.headers.get("User-Agent", "")[:255])
                )
                session_db_id = cur.lastrowid

            conn.close()

            session["user_id"] = user["user_id"]
            session["db_session_id"] = session_db_id

            # Redirect new users with incomplete profile to setup
            if not user.get("profile_completed"):
                flash("Welcome! Please complete your quick profile setup.", "info")
                return redirect(url_for("profile_setup"))

            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("index"))

        except Exception as e:
            flash(f"Login error: {str(e)}", "error")
            return render_template("login.html", login_id=login_id)

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Clear session and log out the user, recording logout timestamp in MySQL."""
    db_session_id = session.get("db_session_id")
    if db_session_id:
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("UPDATE user_sessions SET logout_time = NOW() WHERE session_id = %s", (db_session_id,))
            conn.close()
        except Exception as e:
            print(f"[ERROR] logging logout timestamp: {e}")

    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("login"))


# ==============================================================================
# PROFILE & ONBOARDING ROUTES
# ==============================================================================

@app.route("/profile-setup", methods=["GET", "POST"])
@login_required
def profile_setup():
    """Onboarding profile setup page: mood/vibe preferences and optional avatar upload."""
    user_id = session["user_id"]

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()

            cur.execute("SELECT mood_or_vibe FROM user_preferences WHERE user_id = %s", (user_id,))
            prefs = cur.fetchall()
            user_selected_moods = [p["mood_or_vibe"] for p in prefs]
        conn.close()

        if request.method == "POST":
            action = request.form.get("action", "save")

            # Handle Skip option
            if action == "skip":
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("UPDATE users SET profile_completed = TRUE WHERE user_id = %s", (user_id,))
                conn.close()
                flash("Setup skipped. You can personalize your tastes anytime from your profile!", "info")
                return redirect(url_for("index"))

            # Save preferences flow
            new_username = request.form.get("username", "").strip()
            selected_moods = request.form.getlist("moods")

            avatar_file = request.files.get("profile_image")
            avatar_url = None

            if avatar_file and avatar_file.filename and allowed_file(avatar_file.filename):
                safe_name = f"avatar_{user_id}_{secure_filename(avatar_file.filename)}"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
                avatar_file.save(save_path)
                avatar_url = f"/static/uploads/avatars/{safe_name}"

            conn = get_db_connection()
            with conn.cursor() as cur:
                # Update username if changed and valid
                if new_username and new_username != user.get("username"):
                    cur.execute("SELECT user_id FROM users WHERE username = %s AND user_id != %s", (new_username, user_id))
                    dup = cur.fetchone()
                    if not dup and re.match(r"^[a-zA-Z0-9_.-]{3,30}$", new_username):
                        cur.execute("UPDATE users SET username = %s, name = %s WHERE user_id = %s", (new_username, new_username, user_id))

                if avatar_url:
                    cur.execute("UPDATE users SET profile_image = %s WHERE user_id = %s", (avatar_url, user_id))

                # Update preferences in user_preferences table
                cur.execute("DELETE FROM user_preferences WHERE user_id = %s", (user_id,))
                for vibe in selected_moods:
                    vibe = vibe.strip()
                    if vibe:
                        cur.execute(
                            "INSERT INTO user_preferences (user_id, mood_or_vibe) VALUES (%s, %s)",
                            (user_id, vibe)
                        )

                # Mark profile completed
                cur.execute("UPDATE users SET profile_completed = TRUE WHERE user_id = %s", (user_id,))

                # Sync to user_profile table preferred_moods
                if selected_moods:
                    moods_str = ", ".join(selected_moods)
                    cur.execute("""
                        INSERT INTO user_profile (user_id, preferred_moods)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE preferred_moods = VALUES(preferred_moods)
                    """, (user_id, moods_str))
            conn.close()

            flash("Your profile preferences have been saved!", "success")
            return redirect(url_for("index"))

        return render_template(
            "profile_setup.html",
            user_selected_moods=user_selected_moods,
            current_user=user
        )

    except Exception as e:
        flash(f"Error loading setup: {str(e)}", "error")
        return redirect(url_for("index"))


@app.route("/profile")
@login_required
def profile():
    """Dedicated User Profile page displaying personal info, preferences, favourites, and full listening history."""
    user_id = session["user_id"]
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. User info
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()

            # 2. Preferences
            cur.execute("SELECT * FROM user_preferences WHERE user_id = %s ORDER BY preference_id ASC", (user_id,))
            user_preferences = cur.fetchall()

            # 3. Favourite songs
            cur.execute("""
                SELECT s.song_id, s.title, s.movie, s.artist, s.genre, s.mood, s.language, s.activity,
                       s.description, s.audio_url, s.cover_mime_type, f.created_at AS favourited_at
                FROM user_favourites f
                JOIN songs s ON f.song_id = s.song_id
                WHERE f.user_id = %s
                ORDER BY f.created_at DESC
            """, (user_id,))
            favourites = cur.fetchall()
            for fav in favourites:
                fav["cover_url"] = f"/api/songs/{fav['song_id']}/cover"

            # 4. Listening & Playback History
            cur.execute("""
                SELECT p.*, s.title, s.artist, s.movie, s.audio_url, s.genre, s.mood
                FROM user_playback_history p
                JOIN songs s ON p.song_id = s.song_id
                WHERE p.user_id = %s
                ORDER BY p.played_at DESC
                LIMIT 25
            """, (user_id,))
            playbacks = cur.fetchall()
            for p in playbacks:
                p["cover_url"] = f"/api/songs/{p['song_id']}/cover"

            # 5. Search History
            cur.execute("""
                SELECT request_id, request_text, created_at
                FROM user_requests
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 20
            """, (user_id,))
            searches = cur.fetchall()

            # 6. Ratings & Feedback History
            cur.execute("""
                SELECT f.*, s.title, s.artist, s.movie
                FROM feedback f
                JOIN songs s ON f.song_id = s.song_id
                WHERE f.user_id = %s
                ORDER BY f.created_at DESC
                LIMIT 25
            """, (user_id,))
            feedback_records = cur.fetchall()
            for f in feedback_records:
                f["cover_url"] = f"/api/songs/{f['song_id']}/cover"

            # 7. Favourite Actions History
            cur.execute("""
                SELECT a.*, s.title, s.artist, s.movie
                FROM user_favourite_activity a
                JOIN songs s ON a.song_id = s.song_id
                WHERE a.user_id = %s
                ORDER BY a.created_at DESC
                LIMIT 20
            """, (user_id,))
            fav_activities = cur.fetchall()
            for a in fav_activities:
                a["cover_url"] = f"/api/songs/{a['song_id']}/cover"

        conn.close()

        vibe_options = [
            "Romantic",
            "Happy",
            "Sad / Emotional",
            "Calm / Peaceful",
            "Energetic",
            "Motivational",
            "Spiritual",
            "Travel / Adventure",
            "Party / Celebration",
            "Relaxing"
        ]

        return render_template(
            "profile.html",
            current_user=user,
            user_preferences=user_preferences,
            favourites=favourites,
            vibe_options=vibe_options,
            playbacks=playbacks,
            searches=searches,
            feedback_records=feedback_records,
            fav_activities=fav_activities
        )

    except Exception as e:
        flash(f"Error loading profile: {str(e)}", "error")
        return redirect(url_for("index"))


@app.route("/profile/edit", methods=["POST"])
@login_required
def profile_edit():
    """Edit user profile details and vibes."""
    user_id = session["user_id"]
    action = request.form.get("action", "save")

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if action == "remove_avatar":
                cur.execute("UPDATE users SET profile_image = '/static/images/default_avatar.svg' WHERE user_id = %s", (user_id,))
                conn.close()
                flash("Profile picture reset to default avatar.", "info")
                return redirect(url_for("profile"))

            new_username = request.form.get("username", "").strip()
            selected_moods = request.form.getlist("moods")

            avatar_file = request.files.get("profile_image")
            avatar_url = None

            if avatar_file and avatar_file.filename and allowed_file(avatar_file.filename):
                safe_name = f"avatar_{user_id}_{secure_filename(avatar_file.filename)}"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
                avatar_file.save(save_path)
                avatar_url = f"/static/uploads/avatars/{safe_name}"

            # Check duplicate username if changed
            if new_username:
                if not re.match(r"^[a-zA-Z0-9_.-]{3,30}$", new_username):
                    flash("Username must be 3-30 valid characters.", "error")
                    conn.close()
                    return redirect(url_for("profile"))

                cur.execute("SELECT user_id FROM users WHERE username = %s AND user_id != %s", (new_username, user_id))
                if cur.fetchone():
                    flash("That username is already taken.", "error")
                    conn.close()
                    return redirect(url_for("profile"))

                cur.execute("UPDATE users SET username = %s, name = %s WHERE user_id = %s", (new_username, new_username, user_id))

            if avatar_url:
                cur.execute("UPDATE users SET profile_image = %s WHERE user_id = %s", (avatar_url, user_id))

            # Update vibes
            cur.execute("DELETE FROM user_preferences WHERE user_id = %s", (user_id,))
            for vibe in selected_moods:
                vibe = vibe.strip()
                if vibe:
                    cur.execute("INSERT INTO user_preferences (user_id, mood_or_vibe) VALUES (%s, %s)", (user_id, vibe))

            # Update aggregate user_profile table preferred_moods
            if selected_moods:
                moods_str = ", ".join(selected_moods)
                cur.execute("""
                    INSERT INTO user_profile (user_id, preferred_moods)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE preferred_moods = VALUES(preferred_moods)
                """, (user_id, moods_str))

        conn.close()
        flash("Profile updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating profile: {str(e)}", "error")

    return redirect(url_for("profile"))


# ==============================================================================
# FAVOURITES API
# ==============================================================================

@app.route("/api/favourites", methods=["GET"])
@login_required
def api_get_favourites():
    """Retrieve list of favourite song IDs for current user."""
    user_id = session["user_id"]
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT song_id FROM user_favourites WHERE user_id = %s", (user_id,))
            favs = [row["song_id"] for row in cur.fetchall()]
        conn.close()
        return jsonify({"success": True, "favourites": favs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/favourites/toggle", methods=["POST"])
@login_required
def api_toggle_favourite():
    """Toggle a song in user_favourites and record favourite activity in MySQL."""
    user_id = session["user_id"]
    data = request.get_json() or {}
    song_id = data.get("song_id")

    if not song_id:
        return jsonify({"success": False, "error": "Song ID is required."}), 400

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT favourite_id FROM user_favourites WHERE user_id = %s AND song_id = %s", (user_id, song_id))
            existing = cur.fetchone()

            if existing:
                cur.execute("DELETE FROM user_favourites WHERE user_id = %s AND song_id = %s", (user_id, song_id))
                cur.execute("INSERT INTO user_favourite_activity (user_id, song_id, action) VALUES (%s, %s, 'removed')", (user_id, song_id))
                is_favourite = False
                message = "Removed from favorites"
            else:
                cur.execute("INSERT INTO user_favourites (user_id, song_id) VALUES (%s, %s)", (user_id, song_id))
                cur.execute("INSERT INTO user_favourite_activity (user_id, song_id, action) VALUES (%s, %s, 'added')", (user_id, song_id))
                is_favourite = True
                message = "Added to favorites"
        conn.close()

        return jsonify({
            "success": True,
            "song_id": song_id,
            "is_favourite": is_favourite,
            "message": message
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==============================================================================
# PLAYBACK ACTIVITY API
# ==============================================================================

@app.route("/api/activity/playback", methods=["POST"])
@login_required
def api_record_playback():
    """Record song playback events (started, completed, stopped, skipped) in MySQL."""
    user_id = session["user_id"]
    data = request.get_json() or {}
    song_id = data.get("song_id")
    status = data.get("status", "started")
    duration_played = int(data.get("duration_played", 0))

    if not song_id:
        return jsonify({"success": False, "error": "Song ID is required."}), 400

    if status not in ["started", "completed", "stopped", "skipped"]:
        status = "started"

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_playback_history (user_id, song_id, status, duration_played, played_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (user_id, song_id, status, duration_played))
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==============================================================================
# MAIN APPLICATION & RECOMMENDATION ROUTES
# ==============================================================================

@app.route("/")
@login_required
def index():
    """
    Render personalized home page with:
    - Section A: Welcome!! and Chat Area
    - Section B: Recommended for Your Vibe (automatic)
    - Section C: Personalized Recommendations (history-aware)
    """
    user_id = session["user_id"]
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT profile_completed FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        if user and not user.get("profile_completed"):
            conn.close()
            return redirect(url_for("profile_setup"))

        # Fetch songs for Sections B & C (with cover_url, without heavy binary)
        songs = fetch_songs_catalog(cur)

        # Fetch user favourites for marking is_favourite flag
        cur.execute("SELECT song_id FROM user_favourites WHERE user_id = %s", (user_id,))
        fav_ids = {row["song_id"] for row in cur.fetchall()}
    conn.close()

    # Get user history
    user_history = get_user_history_data(user_id)
    user_vibes = user_history.get("vibe_preferences", [])

    # Section B: Recommended for Your Vibe
    vibe_recommendations = recommend_by_vibes(user_vibes, songs, top_k=6)
    for s in vibe_recommendations:
        s["is_favourite"] = s["song_id"] in fav_ids

    # Section C: Personalized Recommendations
    personalized_recommendations = recommend_personalized(songs, user_history, top_k=6)
    for s in personalized_recommendations:
        s["is_favourite"] = s["song_id"] in fav_ids

    # Additional Curated Categorical Rows (Requirement 5)
    romantic_songs = [s for s in songs if any(k in (s.get("mood", "") + " " + s.get("genre", "")).lower() for k in ["romantic", "love"])]
    for s in romantic_songs:
        s["is_favourite"] = s["song_id"] in fav_ids

    calm_songs = [s for s in songs if any(k in (s.get("mood", "") + " " + s.get("genre", "")).lower() for k in ["calm", "peaceful", "spiritual", "sufi", "relaxing"])]
    for s in calm_songs:
        s["is_favourite"] = s["song_id"] in fav_ids

    energetic_songs = [s for s in songs if any(k in (s.get("mood", "") + " " + s.get("genre", "")).lower() for k in ["energetic", "motivational", "party", "dance"])]
    for s in energetic_songs:
        s["is_favourite"] = s["song_id"] in fav_ids

    return render_template(
        "index.html",
        user_vibes=user_vibes,
        vibe_recommendations=vibe_recommendations,
        personalized_recommendations=personalized_recommendations,
        romantic_songs=romantic_songs,
        calm_songs=calm_songs,
        energetic_songs=energetic_songs
    )


@app.route("/api/recommendations/vibe")
@login_required
def api_vibe_recommendations():
    """Endpoint to refresh Section B vibe recommendations."""
    user_id = session["user_id"]
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            songs = fetch_songs_catalog(cur)
            cur.execute("SELECT song_id FROM user_favourites WHERE user_id = %s", (user_id,))
            fav_ids = {row["song_id"] for row in cur.fetchall()}
        conn.close()

        user_history = get_user_history_data(user_id)
        vibe_recommendations = recommend_by_vibes(user_history.get("vibe_preferences", []), songs, top_k=6)
        for s in vibe_recommendations:
            s["is_favourite"] = s["song_id"] in fav_ids

        return jsonify({"success": True, "recommendations": vibe_recommendations})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/recommendations/personalized")
@login_required
def api_personalized_recommendations():
    """Endpoint to refresh Section C personalized recommendations."""
    user_id = session["user_id"]
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            songs = fetch_songs_catalog(cur)
            cur.execute("SELECT song_id FROM user_favourites WHERE user_id = %s", (user_id,))
            fav_ids = {row["song_id"] for row in cur.fetchall()}
        conn.close()

        user_history = get_user_history_data(user_id)
        personalized = recommend_personalized(songs, user_history, top_k=6)
        for s in personalized:
            s["is_favourite"] = s["song_id"] in fav_ids

        return jsonify({"success": True, "recommendations": personalized})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/songs/<int:song_id>/cover")
@app.route("/api/song/<int:song_id>/cover")
def get_song_cover(song_id):
    """
    Serves the official cover image for a song directly from MySQL MEDIUMBLOB.
    Includes HTTP caching (ETag, Cache-Control, If-None-Match) so images
    load instantaneously and are not repeatedly transferred unnecessarily.
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT cover_image, cover_mime_type, title FROM songs WHERE song_id = %s", (song_id,))
            row = cur.fetchone()
        conn.close()

        if row and row.get("cover_image"):
            image_data = row["cover_image"]
            mime_type = row.get("cover_mime_type") or "image/jpeg"
            etag = hashlib.md5(image_data).hexdigest()

            # HTTP 304 Not Modified cache response
            if request.headers.get("If-None-Match") == etag:
                return Response(status=304)

            response = make_response(image_data)
            response.headers["Content-Type"] = mime_type
            response.headers["ETag"] = etag
            response.headers["Cache-Control"] = "public, max-age=604800, immutable"
            return response

        # Fallback to local static poster file if present
        local_poster_dir = os.path.join(os.path.dirname(__file__), "static", "images", "posters")
        if os.path.exists(local_poster_dir) and row and row.get("title"):
            from migrate_song_covers import IMAGE_MAPPING
            img_name = IMAGE_MAPPING.get(row["title"])
            if img_name and os.path.exists(os.path.join(local_poster_dir, img_name)):
                return send_from_directory(local_poster_dir, img_name)

        fallback_file = "default_song_cover.svg" if os.path.exists(os.path.join(os.path.dirname(__file__), "static", "images", "default_song_cover.svg")) else "default_avatar.svg"
        return send_from_directory(
            os.path.join(os.path.dirname(__file__), "static", "images"),
            fallback_file,
            mimetype="image/svg+xml"
        )
    except Exception as e:
        print(f"[COVER SERVE ERROR] Song {song_id}: {e}")
        fallback_file = "default_song_cover.svg" if os.path.exists(os.path.join(os.path.dirname(__file__), "static", "images", "default_song_cover.svg")) else "default_avatar.svg"
        return send_from_directory(
            os.path.join(os.path.dirname(__file__), "static", "images"),
            fallback_file,
            mimetype="image/svg+xml"
        )


@app.route("/dataset/songs/<path:filename>")
def serve_dataset_song(filename):
    """Serve local MP3 audio files from the dataset/songs directory."""
    songs_dir = os.path.join(os.path.dirname(__file__), "dataset", "songs")
    return send_from_directory(songs_dir, filename)


@app.route("/admin")
def admin():
    """Render the admin demonstration dashboard showing all MySQL data."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Aggregate counts
            cur.execute("SELECT COUNT(*) AS count FROM songs")
            total_songs = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) AS count FROM users")
            total_users = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) AS count FROM user_requests")
            total_requests = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) AS count FROM feedback")
            total_feedback = cur.fetchone()["count"]

            # Table rows
            songs = fetch_songs_catalog(cur)

            cur.execute("""
                SELECT r.*, u.name AS user_name
                FROM user_requests r
                LEFT JOIN users u ON r.user_id = u.user_id
                ORDER BY r.created_at DESC
                LIMIT 50
            """)
            requests_list = cur.fetchall()

            cur.execute("""
                SELECT f.*, u.name AS user_name, s.title AS song_title
                FROM feedback f
                LEFT JOIN users u ON f.user_id = u.user_id
                LEFT JOIN songs s ON f.song_id = s.song_id
                ORDER BY f.created_at DESC
                LIMIT 50
            """)
            feedback_list = cur.fetchall()

            cur.execute("""
                SELECT p.*, u.name AS user_name
                FROM user_profile p
                LEFT JOIN users u ON p.user_id = u.user_id
            """)
            profiles = cur.fetchall()

        conn.close()
        return render_template(
            "admin.html",
            total_songs=total_songs,
            total_users=total_users,
            total_requests=total_requests,
            total_feedback=total_feedback,
            songs=songs,
            requests=requests_list,
            feedback=feedback_list,
            profiles=profiles
        )
    except Exception as e:
        return f"Error loading admin dashboard: {str(e)}", 500


@app.route("/api/recommend", methods=["POST"])
@login_required
def api_recommend():
    """
    Recommendation endpoint:
    1. Receives natural language user text
    2. Fetches user history (vibes, past searches, likes, ratings, dislikes, skips)
    3. Retrieves all songs from MySQL
    4. Computes semantic embeddings and cosine similarities, weighted with user history
    5. Saves search to user_requests with recommendations JSON
    6. Records recommendations in recommendation_history
    7. Returns ranked top 5 songs with is_favourite flag
    """
    data = request.get_json() or {}
    user_text = (data.get("request_text") or data.get("user_text") or data.get("prompt") or "").strip()
    user_id = session["user_id"]

    if not user_text:
        return jsonify({"success": False, "error": "Please provide a valid music request."}), 400

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. Retrieve all songs with cover metadata from MySQL
            songs = fetch_songs_catalog(cur)

            # 2. Retrieve user favourites for marking is_favourite
            cur.execute("SELECT song_id FROM user_favourites WHERE user_id = %s", (user_id,))
            fav_ids = {row["song_id"] for row in cur.fetchall()}

        conn.close()

        # 3. Retrieve user history for personalization
        user_history = get_user_history_data(user_id)

        # 4. Generate recommendations combining current mood + previous history
        recommendations = recommend_songs(user_text, songs, top_k=5, user_history=user_history)

        # Attach is_favourite status to each recommendation
        for song in recommendations:
            song["is_favourite"] = song.get("song_id") in fav_ids

        # 5. Store request and recommendations in MySQL
        conn = get_db_connection()
        with conn.cursor() as cur:
            recs_json = json.dumps([{"song_id": r["song_id"], "title": r["title"]} for r in recommendations])
            cur.execute(
                "INSERT INTO user_requests (user_id, request_text, recommendations_json) VALUES (%s, %s, %s)",
                (user_id, user_text, recs_json)
            )

            # Record each item into recommendation_history
            for rank, rec in enumerate(recommendations, start=1):
                cur.execute("""
                    INSERT INTO recommendation_history (user_id, song_id, recommendation_type, source_prompt, rank_order, match_percentage, similarity_score)
                    VALUES (%s, %s, 'prompt_search', %s, %s, %s, %s)
                """, (user_id, rec["song_id"], user_text, rank, rec["match_percentage"], rec.get("similarity_score", 0.0)))
        conn.close()

        return jsonify({
            "success": True,
            "query": user_text,
            "recommendations": recommendations
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/feedback", methods=["POST"])
@login_required
def api_feedback():
    """
    Feedback endpoint:
    1. Stores user feedback (like/dislike/skip/rating) in MySQL feedback table
    2. If skip, also logs to user_playback_history
    3. Dynamically updates user preference profile in user_profile table
    """
    data = request.get_json() or {}
    user_id = session["user_id"]
    song_id = data.get("song_id")
    feedback_type = data.get("feedback_type")  # 'like', 'dislike', 'skip', or 'rating'
    rating = data.get("rating")  # optional int 1-5

    if not feedback_type and rating is not None:
        feedback_type = "rating"

    if not song_id or feedback_type not in ["like", "dislike", "skip", "rating"]:
        return jsonify({"success": False, "error": "Invalid feedback parameters."}), 400

    if rating is not None:
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                rating = None
        except (ValueError, TypeError):
            rating = None

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. Store feedback record
            cur.execute(
                "INSERT INTO feedback (user_id, song_id, feedback_type, rating) VALUES (%s, %s, %s, %s)",
                (user_id, song_id, feedback_type, rating)
            )

            # 2. If skipped, also record to user_playback_history with status 'skipped'
            if feedback_type == "skip":
                cur.execute("""
                    INSERT INTO user_playback_history (user_id, song_id, status, duration_played, played_at)
                    VALUES (%s, %s, 'skipped', 0, NOW())
                """, (user_id, song_id))

            # 3. Retrieve song details for updating profile
            song = fetch_songs_catalog(cur, song_id=song_id)

            if song:
                # 4. Retrieve or create user profile
                cur.execute("SELECT * FROM user_profile WHERE user_id = %s", (user_id,))
                profile = cur.fetchone()

                def parse_csv(val):
                    return [item.strip() for item in (val or "").split(",") if item.strip()]

                def merge_csv(existing_list, new_items):
                    seen = set(existing_list)
                    for item in new_items:
                        if item and item not in seen:
                            existing_list.append(item)
                            seen.add(item)
                    return existing_list

                if not profile:
                    moods = []
                    genres = []
                    languages = []
                    liked = []
                else:
                    moods = parse_csv(profile.get("preferred_moods"))
                    genres = parse_csv(profile.get("preferred_genres"))
                    languages = parse_csv(profile.get("preferred_languages"))
                    liked = parse_csv(profile.get("liked_songs"))

                # Update preferences if liked or high rating
                if feedback_type == "like" or (rating and rating >= 4):
                    if song["title"] not in liked:
                        liked.append(song["title"])

                    song_moods = [m.strip() for m in song.get("mood", "").split(",") if m.strip()]
                    moods = merge_csv(moods, song_moods)

                    song_genres = [g.strip() for g in song.get("genre", "").replace("/", ",").split(",") if g.strip()]
                    genres = merge_csv(genres, song_genres)

                    if song.get("language") and song["language"] not in languages:
                        languages.append(song["language"])

                elif feedback_type == "dislike":
                    if song["title"] in liked:
                        liked.remove(song["title"])

                preferred_moods_str = ", ".join(moods)
                preferred_genres_str = ", ".join(genres)
                preferred_languages_str = ", ".join(languages)
                liked_songs_str = ", ".join(liked)

                cur.execute("""
                    INSERT INTO user_profile (user_id, preferred_moods, preferred_genres, preferred_languages, liked_songs)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        preferred_moods = VALUES(preferred_moods),
                        preferred_genres = VALUES(preferred_genres),
                        preferred_languages = VALUES(preferred_languages),
                        liked_songs = VALUES(liked_songs)
                """, (user_id, preferred_moods_str, preferred_genres_str, preferred_languages_str, liked_songs_str))

        conn.close()

        return jsonify({
            "success": True,
            "message": "Your feedback has been saved."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/user-profile/<int:user_id>")
def get_user_profile(user_id):
    """Fetch current user profile data."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.*, u.name AS user_name
                FROM user_profile p
                LEFT JOIN users u ON p.user_id = u.user_id
                WHERE p.user_id = %s
            """, (user_id,))
            profile = cur.fetchone()
        conn.close()
        return jsonify({"success": True, "profile": profile or {}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/model/info")
def api_model_info():
    """Returns technical details of the active primary recommendation model."""
    try:
        info = get_model_info()
        return jsonify({"success": True, **info})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 70, flush=True)
    print("Starting Music Suggestion System server...", flush=True)
    print("Pre-loading primary recommendation model: paraphrase-multilingual-mpnet-base-v2 (768 dims)...", flush=True)
    try:
        preload_model()
        print("[SUCCESS] Model initialized and cached.", flush=True)
    except Exception as err:
        print(f"[WARNING] Model preload deferred: {err}", flush=True)
    print("Application ready on http://127.0.0.1:5000 (use_reloader=False)", flush=True)
    print("=" * 70, flush=True)
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
