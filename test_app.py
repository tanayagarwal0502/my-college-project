"""
End-to-End Verification Test Script for Cleaned User-Facing Interface
Verifies that:
1. Normal user can still enter a mood.
2. Recommendations still work.
3. Recommended songs still appear.
4. Songs can still be played.
5. Like works.
6. Dislike works.
7. Skip works.
8. Rating works.
9. MySQL continues storing the data.
10. Admin/database functionality remains available through its separate route (/admin).
11. The normal homepage no longer displays "How It Works".
12. The normal homepage no longer displays "Admin & MySQL Dashboard" or admin link.
13. The normal homepage no longer displays MySQL tables or system statistics.
"""

import os
import sys
import pymysql
from app import app, get_db_connection

def run_tests():
    print("=" * 65)
    print("STARTING VERIFICATION TESTS FOR CLEAN USER-FACING INTERFACE")
    print("=" * 65)

    client = app.test_client()

    # Part A: Verify Homepage (/): User-Facing Cleanliness (Items 11, 12, 13)
    print("\n[Part A] Verifying Homepage (/) User-Facing Cleanliness...")
    home_res = client.get("/")
    assert home_res.status_code == 200, f"Failed to load homepage: {home_res.status_code}"
    home_html = home_res.get_data(as_text=True)

    # Item 11: The normal homepage no longer displays "How It Works"
    assert "How It Works" not in home_html, "Found 'How It Works' on homepage"
    assert "Song Matching" not in home_html, "Found technical 'Song Matching' on homepage"
    assert "Profile Update" not in home_html, "Found technical 'Profile Update' on homepage"
    print("  [OK] Item 11: 'How It Works' section is completely removed from homepage.")

    # Item 12: The normal homepage no longer displays "Admin & MySQL Dashboard" or admin nav link
    assert "Admin & MySQL Dashboard" not in home_html, "Found 'Admin & MySQL Dashboard' on homepage"
    assert "Admin Dashboard" not in home_html, "Found 'Admin Dashboard' link in navbar"
    assert "/admin" not in home_html, "Found '/admin' link on homepage"
    print("  [OK] Item 12: Admin dashboard text and links removed from homepage.")

    # Item 13: The normal homepage no longer displays MySQL tables or system statistics
    prohibited_terms = [
        "Database & System Monitor",
        "Total Songs",
        "Total Users",
        "Total Requests",
        "Total Feedback",
        "user_profile",
        "user_requests",
        "Live Sync",
        "Refresh Data",
        "MySQL",
        "Database"
    ]
    for term in prohibited_terms:
        assert term not in home_html, f"Found prohibited technical term '{term}' on homepage"
    print("  [OK] Item 13: No MySQL tables, system statistics, or technical terms on homepage.")

    # Part B: Verify Core User Flow (Items 1, 2, 3, 4)
    print("\n[Part B] Verifying User Recommendation Flow (Items 1, 2, 3, 4)...")

    # Item 1: Normal user can still enter a mood & get recommendations
    user_mood = "I'm feeling romantic today"
    res_rec = client.post("/api/recommend", json={
        "request_text": user_mood,
        "user_id": 1
    })
    assert res_rec.status_code == 200, "Failed to get recommendations"
    rec_data = res_rec.get_json()
    assert rec_data["success"] is True

    # Item 2 & 3: Recommendations still work and recommended songs appear
    recommendations = rec_data["recommendations"]
    assert len(recommendations) == 5, f"Expected 5 songs, got {len(recommendations)}"
    titles = [s["title"] for s in recommendations]
    print(f"  [OK] Item 1, 2, 3: User entered mood '{user_mood}', received 5 songs: {', '.join(titles)}")

    # Item 4: Songs can still be played via /dataset/songs/<filename>
    for song in recommendations:
        audio_url = song.get("audio_url")
        assert audio_url and audio_url.startswith("dataset/songs/"), f"Missing audio URL for {song['title']}"
        # Test HTTP streaming of song
        stream_res = client.get(f"/{audio_url}")
        assert stream_res.status_code == 200, f"Cannot stream audio for {song['title']}: {stream_res.status_code}"
        assert len(stream_res.data) > 100_000, f"Audio data too small for {song['title']}"
    print("  [OK] Item 4: All recommended songs have valid local MP3 audio that streams with HTTP 200.")

    # Part C: Verify Feedback & Rating (Items 5, 6, 7, 8, 9)
    print("\n[Part C] Verifying Feedback & Profile Updates (Items 5, 6, 7, 8, 9)...")

    # Item 5 & 8: Like & Rating (5-star)
    res_like = client.post("/api/feedback", json={
        "user_id": 1,
        "song_id": 1,  # Kesariya
        "feedback_type": "like",
        "rating": 5
    })
    assert res_like.status_code == 200 and res_like.get_json()["success"] is True
    print("  [OK] Item 5 & 8: 'Like' and 5-star rating submitted successfully.")

    # Item 6: Dislike
    res_dislike = client.post("/api/feedback", json={
        "user_id": 1,
        "song_id": 9,  # Aaj Ki Raat
        "feedback_type": "dislike",
        "rating": 1
    })
    assert res_dislike.status_code == 200 and res_dislike.get_json()["success"] is True
    print("  [OK] Item 6: 'Dislike' submitted successfully.")

    # Item 7: Skip
    res_skip = client.post("/api/feedback", json={
        "user_id": 1,
        "song_id": 6,  # Safarnama
        "feedback_type": "skip",
        "rating": 3
    })
    assert res_skip.status_code == 200 and res_skip.get_json()["success"] is True
    print("  [OK] Item 7: 'Skip' submitted successfully.")

    # Item 9: MySQL continues storing data
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total_fb FROM feedback WHERE user_id = 1")
        total_fb = cur.fetchone()["total_fb"]
        assert total_fb > 0, "No feedback stored in MySQL"

        cur.execute("SELECT * FROM user_profile WHERE user_id = 1")
        profile = cur.fetchone()
        assert profile is not None
        assert "Kesariya" in profile["liked_songs"]
        print(f"  [OK] Item 9: MySQL stored feedback ({total_fb} records) and updated profile: liked_songs='{profile['liked_songs']}'")
    conn.close()

    # Part D: Verify Admin Route Stays Available Internally (Item 10)
    print("\n[Part D] Verifying Admin Dashboard Remains Available Separately (Item 10)...")
    admin_res = client.get("/admin")
    assert admin_res.status_code == 200, f"Admin route failed: {admin_res.status_code}"
    admin_html = admin_res.get_data(as_text=True)
    assert "Total Songs" in admin_html
    assert "Total Users" in admin_html
    assert "Total Requests" in admin_html
    assert "Total Feedback" in admin_html
    assert "database/songs" in admin_html or "dataset/songs" in admin_html
    print("  [OK] Item 10: /admin remains fully functional internally with all metrics and MySQL tables.")

    print("\n" + "=" * 65)
    print("ALL 13 VERIFICATION CRITERIA PASSED! HOMEPAGE CLEANED 100%.")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
