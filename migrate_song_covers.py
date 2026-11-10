"""
Migration Script: Store uploaded song poster images in MySQL as MEDIUMBLOB.
Idempotent, non-destructive, preserves all existing records, IDs, audio paths, and metadata.
Supports all 48 songs (original 10 + 38 newly added).
"""

import os
import sys
import pymysql

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "root")
MYSQL_DB = os.environ.get("MYSQL_DB", "music_recommendation_db")

# Exact mapping for all 48 songs
IMAGE_MAPPING = {
    # Original 10 songs
    "Aaj Ki Raat": "Aaj Ki Raat.jpg",
    "Apna Bana Le": "Aapna Bana Le.jpg",
    "Gallan Goodiyaan": "Gallan Goodiyan.jpg",
    "Iktara": "Iktara.jpg",
    "Ilahi": "Ilahi.jpg",
    "Kar Har Maidaan Fateh": "Kar Har Maidan Fateh.jpg",
    "Kesariya": "Kesariya.jpg",
    "Kun Faya Kun": "Kun Faya Kun.jpg",
    "Safarnama": "Safarnama.jpg",
    "Zinda": "Zinda.jpg",
    # 38 Newly Added Songs
    "Aashayein": "Aashayein.jpg",
    "Achutam Keshavam": "Achutam Keshavam.jpg",
    "Baby Ko Bass Pasand Hai": "Baby Ko Bass Pasand Hai.jpg",
    "Bhagwan Hai Kahan Re Tu": "Bhagwan Hai Kahan Re Tu.jpg",
    "Brothers Anthem": "Brothers Anthem.jpg",
    "Bulleya": "Bulleya.jpg",
    "Chaar Kadam": "Chaar Kadam.jpg",
    "Channa Mereya": "Channa Mereya.jpg",
    "Dance Ka Bhoot": "Dance Ka Bhoot.jpg",
    "Deva Deva": "Deva Deva.jpg",
    "Dhokha Dhadi": "Dhokha Dhadi.jpg",
    "Dhun": "Dhun.jpg",
    "Finding Her": "Finding Her.jpg",
    "Ghungroo": "Ghungroo.jpg",
    "Gulaabo": "Gulaabo.jpg",
    "Hawayein": "Hawayein.jpg",
    "Hookah Bar": "Hooka Bar.jpg",
    "Ishq Hai": "Ishq Hai.jpg",
    "Jai Jai Shivshankar": "Jai Jai Shiv Shankar.jpg",
    "Jo Tum Mere Ho": "Jo Tum Mere Ho.jpg",
    "Kabhii Tumhhe": "Kabhii Tumhhe.jpg",
    "Kar Gayi Chull": "Kar Gayi Chull.jpg",
    "Love Is A Waste Of Time": "Love Is A Waste Of Time.jpg",
    "Love You Zindagi": "Love You Zindagi.jpg",
    "Malhari": "Malhari.jpg",
    "Mat Aazma Re": "Mat Aazma Re.jpg",
    "Nashe Si Chadh Gayi": "Nashe Si Chadh Gayi.jpg",
    "Pehli Nazar Mein": "Pehli Nazar Mein.jpg",
    "Raataan Lambiyan": "Raatan Lambiyan.jpg",
    "Ranjha": "Ranjha.jpg",
    "Sachi Muchi": "Sachi Muchi.jpg",
    "Shaam Shaandaar": "Shaam Shaandaar.jpg",
    "Sultan (Title Track)": "Sultan.jpg",
    "Tera Hone Laga Hoon": "Tera Hone Laga Hoon.jpg",
    "Kho Gaye Hum Kahan": "Kho Gaye Hum Kahan.jpg",
    "Tu Hai Kahan": "Tu Hai Kahan.jpg",
    "Tum Se Hi": "Tum Se Hi.jpg",
    "Shri Hanuman Chalisa": "Shri Hanuman Chalisa.jpg"
}

def get_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

def migrate_and_seed_covers():
    print("=" * 60)
    print("MIGRATING MYSQL DATABASE: ADDING SONG COVER MEDIUMBLOB")
    print("=" * 60)

    conn = get_connection()
    with conn.cursor() as cur:
        # Step 1: Ensure columns exist in songs table
        cur.execute("SHOW COLUMNS FROM songs LIKE 'cover_image'")
        if not cur.fetchone():
            print("[SCHEMA] Adding column 'cover_image' (MEDIUMBLOB) to songs table...")
            cur.execute("ALTER TABLE songs ADD COLUMN cover_image MEDIUMBLOB NULL")
        else:
            print("[SCHEMA] Column 'cover_image' already exists.")

        cur.execute("SHOW COLUMNS FROM songs LIKE 'cover_mime_type'")
        if not cur.fetchone():
            print("[SCHEMA] Adding column 'cover_mime_type' (VARCHAR(50)) to songs table...")
            cur.execute("ALTER TABLE songs ADD COLUMN cover_mime_type VARCHAR(50) DEFAULT 'image/jpeg'")
        else:
            print("[SCHEMA] Column 'cover_mime_type' already exists.")

        # Step 2: Locate image directories
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_poster_dir = os.path.join(script_dir, "static", "images", "posters")
        source_poster_dirs = [
            local_poster_dir,
            r"D:\Special_Project_Tanay_2026\New_Added_song_images",
            r"D:\Special_Project_Tanay_2026\Songs_images"
        ]

        # Step 3: Fetch all songs from database
        cur.execute("SELECT song_id, title, movie, artist FROM songs ORDER BY song_id ASC")
        songs = cur.fetchall()
        print(f"[DATABASE] Found {len(songs)} songs in database.")

        # Step 4: Map and update each song with binary image data
        updated_count = 0
        for song in songs:
            title = song["title"]
            song_id = song["song_id"]

            image_filename = IMAGE_MAPPING.get(title)
            if not image_filename:
                for map_title, map_file in IMAGE_MAPPING.items():
                    if map_title.lower() in title.lower() or title.lower() in map_title.lower():
                        image_filename = map_file
                        break

            if not image_filename:
                print(f"[WARN] No image mapping found for song {song_id}: '{title}'")
                continue

            # Look for image file across directories
            img_path = None
            for p_dir in source_poster_dirs:
                candidate = os.path.join(p_dir, image_filename)
                if os.path.exists(candidate):
                    img_path = candidate
                    break

            if not img_path:
                print(f"[ERROR] Image file '{image_filename}' not found on disk for '{title}'!")
                continue

            with open(img_path, "rb") as f:
                img_binary = f.read()

            file_size = len(img_binary)
            mime_type = "image/jpeg"
            if image_filename.lower().endswith(".png"):
                mime_type = "image/png"
            elif image_filename.lower().endswith(".webp"):
                mime_type = "image/webp"

            cur.execute(
                "UPDATE songs SET cover_image = %s, cover_mime_type = %s WHERE song_id = %s",
                (img_binary, mime_type, song_id)
            )
            print(f"[UPDATED] Song ID {song_id:2d} ('{title}') -> {image_filename} ({file_size:,} bytes, {mime_type})")
            updated_count += 1

        # Step 5: Verification
        print("\n" + "=" * 60)
        print("VERIFICATION OF COVERS IN MYSQL")
        print("=" * 60)
        cur.execute("SELECT song_id, title, LENGTH(cover_image) as img_bytes, cover_mime_type FROM songs ORDER BY song_id ASC")
        verified_songs = cur.fetchall()
        for s in verified_songs:
            b = s["img_bytes"] or 0
            status = "OK" if b > 0 else "MISSING"
            print(f"[{status}] ID {s['song_id']:2d}: {s['title']:<25} | {b:7,d} bytes | {s['cover_mime_type']}")

    conn.close()
    print("\n[SUCCESS] Migration and cover insertion completed successfully!")

if __name__ == "__main__":
    migrate_and_seed_covers()
