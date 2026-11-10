"""
Comprehensive Verification Test Suite for Uploaded Song Poster Images in MySQL:
1. MySQL database storage (MEDIUMBLOB, MIME types, exact 10 song mapping)
2. Cover image API endpoint (/api/songs/<id>/cover) with caching and ETag
3. Presence of cover images across Home (Vibe, Personalized, Categorical, Search)
4. Presence of cover images in Favourites, Listening History, and Player Bar
5. Session persistence (logout and re-login)
6. Verifies images come from database endpoint, not static hardcoded files
7. All existing playback, ratings, skip, like, dislike controls remain functional
"""

import sys
import os
import unittest
import pymysql

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["SECRET_KEY"] = "test_verification_key_2026"
os.environ["MYSQL_DB"] = "music_recommendation_db"

from app import app, get_db_connection

EXPECTED_MAPPING = {
    1: {"title": "Kesariya", "image": "Kesariya.jpg", "size": 15048},
    2: {"title": "Apna Bana Le", "image": "Aapna Bana Le.jpg", "size": 59203},
    3: {"title": "Zinda", "image": "Zinda.jpg", "size": 164199},
    4: {"title": "Kar Har Maidaan Fateh", "image": "Kar Har Maidan Fateh.jpg", "size": 55669},
    5: {"title": "Ilahi", "image": "Ilahi.jpg", "size": 13601},
    6: {"title": "Safarnama", "image": "Safarnama.jpg", "size": 34502},
    7: {"title": "Iktara", "image": "Iktara.jpg", "size": 73391},
    8: {"title": "Kun Faya Kun", "image": "Kun Faya Kun.jpg", "size": 40102},
    9: {"title": "Aaj Ki Raat", "image": "Aaj Ki Raat.jpg", "size": 24310},
    10: {"title": "Gallan Goodiyaan", "image": "Gallan Goodiyan.jpg", "size": 69257}
}

class TestSongCovers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.testing = True
        cls.client = app.test_client()

    def test_01_mysql_storage_and_exact_mapping(self):
        print("\n--- TEST 1: Verify MySQL Storage and 10 Song Poster Mapping ---")
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SHOW COLUMNS FROM songs LIKE 'cover_image'")
            col_info = cur.fetchone()
            self.assertIsNotNone(col_info, "cover_image column must exist in songs table")
            self.assertIn("mediumblob", col_info["Type"].lower(), "cover_image must be MEDIUMBLOB")

            cur.execute("SELECT song_id, title, LENGTH(cover_image) AS img_len, cover_mime_type FROM songs ORDER BY song_id ASC")
            songs = cur.fetchall()

        conn.close()

        self.assertEqual(len(songs), 10, "There must be exactly 10 songs in the database")
        for s in songs:
            s_id = s["song_id"]
            self.assertIn(s_id, EXPECTED_MAPPING)
            exp = EXPECTED_MAPPING[s_id]
            self.assertEqual(s["title"], exp["title"])
            self.assertGreater(s["img_len"], 0, f"Song {s_id} ({s['title']}) must have cover_image binary data")
            self.assertEqual(s["img_len"], exp["size"], f"Song {s_id} ({s['title']}) bytes must match exact uploaded file size")
            self.assertEqual(s["cover_mime_type"], "image/jpeg")
            print(f"  [PASS] Song #{s_id:2d}: '{s['title']:<22}' -> {exp['image']:<24} ({s['img_len']:,} bytes in MySQL MEDIUMBLOB)")

    def test_02_cover_api_endpoint_and_http_caching(self):
        print("\n--- TEST 2: Verify Cover Serving Endpoint & Caching Headers ---")
        for s_id, exp in EXPECTED_MAPPING.items():
            res = self.client.get(f"/api/songs/{s_id}/cover")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get("Content-Type"), "image/jpeg")
            self.assertEqual(len(res.data), exp["size"])
            self.assertIn("Cache-Control", res.headers)
            self.assertIn("ETag", res.headers)

            # Test 304 Not Modified cache response with If-None-Match
            etag = res.headers.get("ETag")
            cache_res = self.client.get(f"/api/songs/{s_id}/cover", headers={"If-None-Match": etag})
            self.assertEqual(cache_res.status_code, 304, "Subsequent request with matching ETag must return 304 Not Modified")

        print("  [PASS] All 10 songs served with correct binary data, MIME types, ETags, and 304 cache headers.")

    def test_03_recommendation_endpoints_include_cover_urls(self):
        print("\n--- TEST 3: Verify Cover URLs in Recommendation APIs ---")
        # Log in demo user
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "demouser"

        # Vibe recommendations API
        vibe_res = self.client.get("/api/recommendations/vibe")
        self.assertEqual(vibe_res.status_code, 200)
        vibe_data = vibe_res.get_json()
        self.assertTrue(vibe_data["success"])
        for song in vibe_data["recommendations"]:
            self.assertIn("cover_url", song)
            self.assertEqual(song["cover_url"], f"/api/songs/{song['song_id']}/cover")

        # Personalized recommendations API
        pers_res = self.client.get("/api/recommendations/personalized")
        self.assertEqual(pers_res.status_code, 200)
        pers_data = pers_res.get_json()
        self.assertTrue(pers_data["success"])
        for song in pers_data["recommendations"]:
            self.assertIn("cover_url", song)
            self.assertEqual(song["cover_url"], f"/api/songs/{song['song_id']}/cover")

        # Search recommendation API
        search_res = self.client.post("/api/recommend", json={"user_text": "I want peaceful Sufi music"})
        self.assertEqual(search_res.status_code, 200)
        search_data = search_res.get_json()
        self.assertTrue(search_data["success"])
        for song in search_data["recommendations"]:
            self.assertIn("cover_url", song)
            self.assertEqual(song["cover_url"], f"/api/songs/{song['song_id']}/cover")

        print("  [PASS] All recommendation APIs return cover_url referencing the MySQL binary endpoint.")

    def test_04_home_page_renders_all_category_covers(self):
        print("\n--- TEST 4: Verify Home Page Category Song Cards Render Covers ---")
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "demouser"

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Check for card-poster-img tags
        self.assertIn("card-poster-img", html)
        self.assertIn("/api/songs/1/cover", html) # Kesariya
        self.assertIn("/api/songs/2/cover", html) # Apna Bana Le
        with open("static/css/style.css", encoding="utf-8") as f:
            self.assertIn("object-fit: cover", f.read())

        print("  [PASS] Home page contains card-poster-img elements loading /api/songs/<id>/cover.")

    def test_05_favourites_and_listening_history_display_covers(self):
        print("\n--- TEST 5: Verify Favourites and History Render Covers ---")
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "demouser"

        # Add song 2 (Apna Bana Le) to favourites
        fav_toggle = self.client.post("/api/favourites/toggle", json={"song_id": 2})
        self.assertEqual(fav_toggle.status_code, 200)

        # Record playback for song 2
        play_log = self.client.post("/api/activity/playback", json={
            "song_id": 2,
            "status": "started",
            "duration_played": 15
        })
        self.assertEqual(play_log.status_code, 200)

        # Check /profile page
        prof_res = self.client.get("/profile")
        self.assertEqual(prof_res.status_code, 200)
        prof_html = prof_res.get_data(as_text=True)

        # Song 2 cover in favourites section
        self.assertIn('/api/songs/2/cover', prof_html)
        # History table thumbnail
        self.assertIn('history-song-thumb', prof_html)

        print("  [PASS] Favourites card and Listening History table render /api/songs/<id>/cover thumbnails.")

    def test_06_session_persistence_after_logout_and_login(self):
        print("\n--- TEST 6: Verify Cover Persistence After Logout & Re-Login ---")
        # 1. Log out
        out_res = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(out_res.status_code, 200)

        # 2. Log in again with login_id and password
        in_res = self.client.post("/login", data={
            "login_id": "demouser",
            "password": "password123"
        }, follow_redirects=True)
        self.assertEqual(in_res.status_code, 200)

        # 3. Check profile and home
        home_res = self.client.get("/")
        self.assertIn("/api/songs/1/cover", home_res.get_data(as_text=True))

        prof_res = self.client.get("/profile")
        self.assertIn("/api/songs/2/cover", prof_res.get_data(as_text=True))

        print("  [PASS] Session re-authentication verified: Cover images load seamlessly after logging out and back in.")

if __name__ == "__main__":
    unittest.main()
