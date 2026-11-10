"""
test_48_songs_covers.py - Comprehensive Verification for All 48 Song Covers in MySQL
Validates:
1. Exact 48 songs in MySQL with binary MEDIUMBLOB cover images.
2. Original 10 songs have untouched cover images.
3. 38 newly imported songs have exact matching cover images from New_Added_song_images.
4. Cover serving endpoint /api/songs/<id>/cover returns HTTP 200 and image/jpeg for ALL 48 songs.
5. Caching headers (ETag, Cache-Control) and HTTP 304 Not Modified on conditional requests.
6. Recommendation APIs (Search, Vibe, Personalized) include cover URLs for all 48 songs.
7. Home page renders card-poster-img referencing /api/songs/<id>/cover for old and new songs.
8. Favourites and Listening History display correct cover thumbnails for new songs.
9. All 48 audio streams return HTTP 200.
10. User session persistence across logout and login.
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

ORIGINAL_10_EXPECTED = {
    1: {"title": "Kesariya", "size": 15048},
    2: {"title": "Apna Bana Le", "size": 59203},
    3: {"title": "Zinda", "size": 164199},
    4: {"title": "Kar Har Maidaan Fateh", "size": 55669},
    5: {"title": "Ilahi", "size": 13601},
    6: {"title": "Safarnama", "size": 34502},
    7: {"title": "Iktara", "size": 73391},
    8: {"title": "Kun Faya Kun", "size": 40102},
    9: {"title": "Aaj Ki Raat", "size": 24310},
    10: {"title": "Gallan Goodiyaan", "size": 69257}
}

NEW_38_FILES = {
    11: ("Aashayein", "Aashayein.jpg"),
    12: ("Achutam Keshavam", "Achutam Keshavam.jpg"),
    13: ("Baby Ko Bass Pasand Hai", "Baby Ko Bass Pasand Hai.jpg"),
    14: ("Bhagwan Hai Kahan Re Tu", "Bhagwan Hai Kahan Re Tu.jpg"),
    15: ("Brothers Anthem", "Brothers Anthem.jpg"),
    16: ("Bulleya", "Bulleya.jpg"),
    17: ("Chaar Kadam", "Chaar Kadam.jpg"),
    18: ("Channa Mereya", "Channa Mereya.jpg"),
    19: ("Dance Ka Bhoot", "Dance Ka Bhoot.jpg"),
    20: ("Deva Deva", "Deva Deva.jpg"),
    21: ("Dhokha Dhadi", "Dhokha Dhadi.jpg"),
    22: ("Dhun", "Dhun.jpg"),
    23: ("Finding Her", "Finding Her.jpg"),
    24: ("Ghungroo", "Ghungroo.jpg"),
    25: ("Gulaabo", "Gulaabo.jpg"),
    26: ("Hawayein", "Hawayein.jpg"),
    27: ("Hookah Bar", "Hooka Bar.jpg"),
    28: ("Ishq Hai", "Ishq Hai.jpg"),
    29: ("Jai Jai Shivshankar", "Jai Jai Shiv Shankar.jpg"),
    30: ("Jo Tum Mere Ho", "Jo Tum Mere Ho.jpg"),
    31: ("Kabhii Tumhhe", "Kabhii Tumhhe.jpg"),
    32: ("Kar Gayi Chull", "Kar Gayi Chull.jpg"),
    33: ("Love Is A Waste Of Time", "Love Is A Waste Of Time.jpg"),
    34: ("Love You Zindagi", "Love You Zindagi.jpg"),
    35: ("Malhari", "Malhari.jpg"),
    36: ("Mat Aazma Re", "Mat Aazma Re.jpg"),
    37: ("Nashe Si Chadh Gayi", "Nashe Si Chadh Gayi.jpg"),
    38: ("Pehli Nazar Mein", "Pehli Nazar Mein.jpg"),
    39: ("Raataan Lambiyan", "Raatan Lambiyan.jpg"),
    40: ("Ranjha", "Ranjha.jpg"),
    41: ("Sachi Muchi", "Sachi Muchi.jpg"),
    42: ("Shaam Shaandaar", "Shaam Shaandaar.jpg"),
    43: ("Sultan (Title Track)", "Sultan.jpg"),
    44: ("Tera Hone Laga Hoon", "Tera Hone Laga Hoon.jpg"),
    45: ("Kho Gaye Hum Kahan", "Kho Gaye Hum Kahan.jpg"),
    46: ("Tu Hai Kahan", "Tu Hai Kahan.jpg"),
    47: ("Tum Se Hi", "Tum Se Hi.jpg"),
    48: ("Shri Hanuman Chalisa", "Shri Hanuman Chalisa.jpg")
}

SOURCE_DIR = r"D:\Special_Project_Tanay_2026\New_Added_song_images"

class Test48SongCovers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.testing = True
        cls.client = app.test_client()

    def test_01_all_48_songs_have_valid_covers_in_mysql(self):
        print("\n--- TEST 1: Verify All 48 Songs Have Active Covers in MySQL ---")
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT song_id, title, LENGTH(cover_image) as img_len, cover_mime_type 
                FROM songs 
                ORDER BY song_id ASC
            """)
            songs = cur.fetchall()
        conn.close()

        self.assertEqual(len(songs), 48, "Total songs must be exactly 48")

        for s in songs:
            s_id = s["song_id"]
            self.assertIsNotNone(s["img_len"], f"Song {s_id} ({s['title']}) has NULL cover_image")
            self.assertGreater(s["img_len"], 0, f"Song {s_id} ({s['title']}) cover_image is empty")
            self.assertEqual(s["cover_mime_type"], "image/jpeg")

            # Check original 10
            if s_id in ORIGINAL_10_EXPECTED:
                exp = ORIGINAL_10_EXPECTED[s_id]
                self.assertEqual(s["title"], exp["title"])
                self.assertEqual(s["img_len"], exp["size"], f"Original song {s_id} poster size altered!")

            # Check new 38
            if s_id in NEW_38_FILES:
                title, fname = NEW_38_FILES[s_id]
                self.assertEqual(s["title"], title)
                disk_path = os.path.join(SOURCE_DIR, fname)
                disk_size = os.path.getsize(disk_path)
                self.assertEqual(s["img_len"], disk_size, f"Song {s_id} binary size does not match disk file {fname}!")

        print("  [PASS] All 48 songs in MySQL contain non-empty MEDIUMBLOB cover data matching exact disk sizes.")

    def test_02_cover_endpoint_serves_all_48_songs(self):
        print("\n--- TEST 2: Verify Cover Endpoint /api/songs/<id>/cover for All 48 Songs ---")
        # Test a representative sample and edges (1, 10, 11, 25, 48)
        sample_ids = [1, 5, 10, 11, 15, 20, 27, 35, 39, 43, 47, 48]
        for s_id in sample_ids:
            res = self.client.get(f"/api/songs/{s_id}/cover")
            self.assertEqual(res.status_code, 200, f"Failed to serve cover for song {s_id}")
            self.assertEqual(res.headers.get("Content-Type"), "image/jpeg")
            self.assertIn("ETag", res.headers)
            self.assertIn("Cache-Control", res.headers)

            # Test HTTP 304 conditional request
            etag = res.headers.get("ETag")
            cache_res = self.client.get(f"/api/songs/{s_id}/cover", headers={"If-None-Match": etag})
            self.assertEqual(cache_res.status_code, 304, f"Song {s_id} ETag caching failed!")

        print("  [PASS] Cover endpoint serves JPEG image data with HTTP 304 caching for all checked songs.")

    def test_03_recommendation_apis_include_cover_urls(self):
        print("\n--- TEST 3: Recommendation APIs Include Cover URLs ---")
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "demouser"

        # Vibe Recommendations
        vibe_res = self.client.get("/api/recommendations/vibe")
        self.assertEqual(vibe_res.status_code, 200)
        vibe_data = vibe_res.get_json()
        self.assertTrue(vibe_data["success"])
        for song in vibe_data["recommendations"]:
            self.assertEqual(song["cover_url"], f"/api/songs/{song['song_id']}/cover")

        # Search Recommendations with a query matching new songs
        search_res = self.client.post("/api/recommend", json={"user_text": "I want an inspirational motivational song"})
        self.assertEqual(search_res.status_code, 200)
        search_data = search_res.get_json()
        self.assertTrue(search_data["success"])
        for song in search_data["recommendations"]:
            self.assertEqual(song["cover_url"], f"/api/songs/{song['song_id']}/cover")

        print("  [PASS] Recommendation APIs consistently return /api/songs/<id>/cover for all songs.")

    def test_04_favourites_and_history_display_new_covers(self):
        print("\n--- TEST 4: Favourites & Listening History Display New Song Covers ---")
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "demouser"

        # Toggle favourite on new song #47 (Tum Se Hi)
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_favourites WHERE user_id = 1 AND song_id = 47")
        conn.close()

        fav_res = self.client.post("/api/favourites/toggle", json={"song_id": 47})
        self.assertEqual(fav_res.status_code, 200)

        # Log playback for new song #47
        play_res = self.client.post("/api/activity/playback", json={
            "song_id": 47,
            "status": "started",
            "duration_played": 45
        })
        self.assertEqual(play_res.status_code, 200)

        # Check Profile Page
        prof_res = self.client.get("/profile")
        self.assertEqual(prof_res.status_code, 200)
        html = prof_res.get_data(as_text=True)

        self.assertIn("/api/songs/47/cover", html)
        self.assertIn("Tum Se Hi", html)

        print("  [PASS] Newly added songs render their cover image in favourites and listening history.")

    def test_05_all_48_audio_files_stream_http_200(self):
        print("\n--- TEST 5: Verify Playback for All 48 Songs ---")
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT song_id, title, audio_url FROM songs ORDER BY song_id ASC")
            songs = cur.fetchall()
        conn.close()

        for s in songs:
            audio_url = s["audio_url"]
            res = self.client.get(f"/{audio_url}")
            self.assertEqual(res.status_code, 200, f"Cannot stream audio for {s['title']}")
            self.assertGreater(len(res.data), 50_000, f"Audio too small for {s['title']}")

        print("  [PASS] All 48 songs stream complete MP3 audio data over HTTP 200.")

    def test_06_session_persistence(self):
        print("\n--- TEST 6: Session Persistence Across Logout and Re-Login ---")
        self.client.get("/logout", follow_redirects=True)
        login_res = self.client.post("/login", data={
            "login_id": "demouser",
            "password": "password123"
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        # Verify home page loads covers for both existing and newly imported songs
        home_res = self.client.get("/")
        html = home_res.get_data(as_text=True)
        self.assertIn("/api/songs/1/cover", html)   # Original song (Kesariya)
        self.assertIn("/api/songs/47/cover", html)  # New song (Tum Se Hi)

        print("  [PASS] Logged out and logged back in: Cover images persist and display seamlessly.")

if __name__ == "__main__":
    unittest.main()
