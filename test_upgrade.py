"""
Comprehensive End-to-End Verification Test Suite
Tests all phases: Auth, Profile Setup, Avatar Upload, Profile Page,
Favourites, Recommendations, Feedback, Player API, and User Isolation.
"""

import os
import io
import pymysql
from werkzeug.security import check_password_hash
from app import app, get_db_connection

def run_all_tests():
    print("=" * 70)
    print("STARTING MUSIC SUGGESTION SYSTEM E2E UPGRADE VERIFICATION")
    print("=" * 70)

    client = app.test_client()
    passed = 0
    total = 0

    def assert_test(condition, test_name, error_detail=""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"[PASS] {test_name}")
        else:
            print(f"[FAIL] {test_name}: {error_detail}")

    # Clean up any leftover test users from prior runs
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE username IN ('testuser_alpha', 'testuser_beta')")
    conn.close()

    # TEST 1: Unauthenticated access to protected routes
    res = client.get("/", follow_redirects=False)
    assert_test(res.status_code == 302 and "/login" in res.headers.get("Location", ""),
                "Test 1: Unauthenticated GET / redirects to /login")

    res = client.get("/profile", follow_redirects=False)
    assert_test(res.status_code == 302 and "/login" in res.headers.get("Location", ""),
                "Test 2: Unauthenticated GET /profile redirects to /login")

    res = client.post("/api/recommend", json={"request_text": "happy party song"})
    assert_test(res.status_code == 401,
                "Test 3: Unauthenticated POST /api/recommend returns 401")

    # TEST 2: User Registration Validation
    res = client.post("/signup", data={
        "username": "ab", # too short
        "email": "invalid_email",
        "password": "123",
        "confirm_password": "456"
    }, follow_redirects=True)
    assert_test(b"Username must be 3-30 characters" in res.data,
                "Test 4: Registration fails on short username")

    res = client.post("/signup", data={
        "username": "testuser_alpha",
        "email": "notanemail",
        "password": "password123",
        "confirm_password": "password123"
    }, follow_redirects=True)
    assert_test(b"valid email address" in res.data,
                "Test 5: Registration fails on invalid email format")

    res = client.post("/signup", data={
        "username": "testuser_alpha",
        "email": "alpha@example.com",
        "password": "password123",
        "confirm_password": "differentpassword"
    }, follow_redirects=True)
    assert_test(b"do not match" in res.data,
                "Test 6: Registration fails when passwords do not match")

    # TEST 3: Successful Registration
    res = client.post("/signup", data={
        "username": "testuser_alpha",
        "email": "alpha@example.com",
        "password": "password123",
        "confirm_password": "password123"
    }, follow_redirects=False)
    assert_test(res.status_code == 302 and "/profile-setup" in res.headers.get("Location", ""),
                "Test 7: Successful registration redirects to /profile-setup")

    # Verify password hash in MySQL
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE username = 'testuser_alpha'")
        alpha_user = cur.fetchone()
    conn.close()

    assert_test(alpha_user is not None and check_password_hash(alpha_user["password_hash"], "password123"),
                "Test 8: Password is securely hashed in MySQL and not stored in plain-text")

    # TEST 4: Duplicate Registration Prevention (requires logged out state)
    client.get("/logout")
    res = client.post("/signup", data={
        "username": "testuser_alpha",
        "email": "different_email@example.com",
        "password": "password123",
        "confirm_password": "password123"
    }, follow_redirects=True)
    assert_test(b"username is already taken" in res.data,
                "Test 9: Duplicate username registration rejected")

    res = client.post("/signup", data={
        "username": "another_user",
        "email": "alpha@example.com",
        "password": "password123",
        "confirm_password": "password123"
    }, follow_redirects=True)
    assert_test(b"account with this email already exists" in res.data,
                "Test 10: Duplicate email registration rejected")

    # Log back in as testuser_alpha for profile setup testing
    client.post("/login", data={
        "login_id": "testuser_alpha",
        "password": "password123"
    })

    # TEST 5: Profile Setup with Moods and Avatar Upload
    avatar_bytes = io.BytesIO(b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;")
    res = client.post("/profile-setup", data={
        "username": "testuser_alpha",
        "moods": ["Romantic", "Happy", "Energetic"],
        "profile_image": (avatar_bytes, "my_avatar.gif"),
        "action": "save"
    }, content_type="multipart/form-data", follow_redirects=False)
    assert_test(res.status_code == 302 and res.headers.get("Location", "").endswith("/"),
                "Test 11: Profile setup save redirects to home (/)")

    # Verify MySQL profile preferences and uploaded avatar
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT mood_or_vibe FROM user_preferences WHERE user_id = %s", (alpha_user["user_id"],))
        prefs = [row["mood_or_vibe"] for row in cur.fetchall()]
        cur.execute("SELECT profile_image, profile_completed FROM users WHERE user_id = %s", (alpha_user["user_id"],))
        u_row = cur.fetchone()
    conn.close()

    assert_test(set(prefs) == {"Romantic", "Happy", "Energetic"},
                "Test 12: Selected vibes saved correctly to user_preferences table")
    assert_test(u_row["profile_completed"] == 1 and "avatar_" in u_row["profile_image"],
                "Test 13: Profile completed flag set and custom avatar saved")

    # TEST 6: Dedicated Profile Page
    res = client.get("/profile")
    assert_test(res.status_code == 200 and b"testuser_alpha" in res.data and b"Romantic" in res.data,
                "Test 14: Profile page displays user details and saved vibes")

    # TEST 7: Recommendation Endpoint with Semantic Similarity & Favourites Flag
    res = client.post("/api/recommend", json={
        "request_text": "I feel romantic and want a soulful Bollywood song"
    })
    data = res.get_json()
    assert_test(res.status_code == 200 and data.get("success") is True and len(data.get("recommendations", [])) == 5,
                "Test 15: /api/recommend returns top 5 recommendations")
    recs = data.get("recommendations", [])
    top_song = recs[0]
    assert_test("is_favourite" in top_song and top_song["is_favourite"] is False,
                "Test 16: Recommendations include is_favourite boolean flag (initially False)")

    # TEST 8: Toggle Favourite Song (Add)
    res = client.post("/api/favourites/toggle", json={"song_id": top_song["song_id"]})
    fav_data = res.get_json()
    assert_test(fav_data.get("success") is True and fav_data.get("is_favourite") is True,
                f"Test 17: Added song {top_song['title']} to favourites via /api/favourites/toggle")

    # Verify user_favourites table in MySQL
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM user_favourites WHERE user_id = %s AND song_id = %s",
                    (alpha_user["user_id"], top_song["song_id"]))
        fav_row = cur.fetchone()
    conn.close()
    assert_test(fav_row is not None,
                "Test 18: Favourite song record persisted in MySQL user_favourites table")

    # TEST 9: Profile Page Shows Favourite Song
    res = client.get("/profile")
    assert_test(top_song["title"].encode("utf-8") in res.data and b"btn-fav-play" in res.data,
                f"Test 19: My Favourite Songs section displays {top_song['title']} with Play button")

    # TEST 10: Toggle Favourite Song (Remove)
    res = client.post("/api/favourites/toggle", json={"song_id": top_song["song_id"]})
    unfav_data = res.get_json()
    assert_test(unfav_data.get("success") is True and unfav_data.get("is_favourite") is False,
                f"Test 20: Removed song {top_song['title']} from favourites")

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM user_favourites WHERE user_id = %s AND song_id = %s",
                    (alpha_user["user_id"], top_song["song_id"]))
        fav_row = cur.fetchone()
    conn.close()
    assert_test(fav_row is None,
                "Test 21: Favourite song properly removed from MySQL user_favourites table")

    # Add back to test direct playback and separation from Like/Dislike
    client.post("/api/favourites/toggle", json={"song_id": top_song["song_id"]})

    # TEST 11: Like, Dislike, Rating Feedback (Independent from Favourite)
    res = client.post("/api/feedback", json={
        "song_id": top_song["song_id"],
        "feedback_type": "like",
        "rating": 5
    })
    feed_data = res.get_json()
    assert_test(feed_data.get("success") is True,
                "Test 22: Like and 5-star rating submitted successfully to /api/feedback")

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM feedback WHERE user_id = %s AND song_id = %s ORDER BY feedback_id DESC LIMIT 1",
                    (alpha_user["user_id"], top_song["song_id"]))
        f_row = cur.fetchone()
    conn.close()
    assert_test(f_row is not None and f_row["feedback_type"] == "like" and f_row["rating"] == 5,
                "Test 23: Feedback recorded in MySQL feedback table")

    # TEST 12: Audio File Streaming
    audio_path = top_song["audio_url"]
    res = client.get(audio_path)
    assert_test(res.status_code == 200 and (len(res.data) > 1000 or res.headers.get("Content-Type") == "audio/mpeg"),
                f"Test 24: Actual audio stream served at {audio_path}")

    # TEST 13: Edit Profile (Username and Vibes)
    res = client.post("/profile/edit", data={
        "username": "testuser_alpha",
        "moods": ["Spiritual", "Motivational"],
        "action": "save"
    }, follow_redirects=True)
    assert_test(b"Profile updated successfully" in res.data and b"Spiritual" in res.data,
                "Test 25: Profile edited successfully with updated vibes")

    # TEST 14: Edit Profile (Remove Avatar / Reset to default)
    res = client.post("/profile/edit", data={
        "action": "remove_avatar"
    }, follow_redirects=True)
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT profile_image FROM users WHERE user_id = %s", (alpha_user["user_id"],))
        img_row = cur.fetchone()
    conn.close()
    assert_test(img_row["profile_image"] == "/static/images/default_avatar.svg",
                "Test 26: Avatar reset to default SVG via remove_avatar action")

    # TEST 15: Logout
    res = client.get("/logout", follow_redirects=False)
    assert_test(res.status_code == 302 and "/login" in res.headers.get("Location", ""),
                "Test 27: Logout clears session and redirects to /login")

    # Verify session is dead
    res = client.get("/profile", follow_redirects=False)
    assert_test(res.status_code == 302 and "/login" in res.headers.get("Location", ""),
                "Test 28: Session cleared, accessing /profile redirects to /login")

    # TEST 16: Login with Valid Credentials
    res = client.post("/login", data={
        "login_id": "testuser_alpha",
        "password": "password123"
    }, follow_redirects=False)
    assert_test(res.status_code == 302 and res.headers.get("Location", "").endswith("/"),
                "Test 29: Existing completed user logs in and redirects to home screen (/)")

    # TEST 17: User Isolation (User Beta cannot see User Alpha's favourites)
    client.get("/logout")
    client.post("/signup", data={
        "username": "testuser_beta",
        "email": "beta@example.com",
        "password": "password123",
        "confirm_password": "password123"
    })
    client.post("/profile-setup", data={"action": "skip"})

    res = client.get("/profile")
    assert_test(b"0 saved" in res.data and (b"No favourite songs saved yet" in res.data or b"No favourite songs yet" in res.data),
                "Test 30: User Beta starts with 0 favourites (complete user isolation from Alpha)")

    # Clean up test users
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE username IN ('testuser_alpha', 'testuser_beta')")
    conn.close()

    print("=" * 70)
    print(f"VERIFICATION COMPLETE: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("=" * 70)
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
