"""
import_new_song_images.py - Cover Image Migration for 38 Newly Imported Songs
Stores actual binary image data (MEDIUMBLOB) in MySQL songs table.
Preserves existing 10 songs and their records completely untouched.
Idempotent and safe to run multiple times.
"""

import os
import sys
import shutil
import pymysql
import pymysql.cursors

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Database Configuration
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "root")
MYSQL_DB = os.environ.get("MYSQL_DB", "music_recommendation_db")

# Directories
SOURCE_IMAGE_DIR = r"D:\Special_Project_Tanay_2026\New_Added_song_images"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_POSTER_DIR = os.path.join(BASE_DIR, "static", "images", "posters")
ALT_POSTER_DIR = r"C:\Users\acer\OneDrive\Desktop\Sp_demo_tanay\Sp_Demo\static\images\posters"

# Canonical 1-to-1 Mapping Dictionary between Song Title and Image Filename
# Generated based on Priority 1 (Exact), Priority 2 (Normalized), and Priority 3 (Spelling)
IMAGE_MAPPING_38 = {
    11: {"title": "Aashayein", "image": "Aashayein.jpg", "confidence": "Exact (100%)"},
    12: {"title": "Achutam Keshavam", "image": "Achutam Keshavam.jpg", "confidence": "Exact (100%)"},
    13: {"title": "Baby Ko Bass Pasand Hai", "image": "Baby Ko Bass Pasand Hai.jpg", "confidence": "Exact (100%)"},
    14: {"title": "Bhagwan Hai Kahan Re Tu", "image": "Bhagwan Hai Kahan Re Tu.jpg", "confidence": "Exact (100%)"},
    15: {"title": "Brothers Anthem", "image": "Brothers Anthem.jpg", "confidence": "Exact (100%)"},
    16: {"title": "Bulleya", "image": "Bulleya.jpg", "confidence": "Exact (100%)"},
    17: {"title": "Chaar Kadam", "image": "Chaar Kadam.jpg", "confidence": "Exact (100%)"},
    18: {"title": "Channa Mereya", "image": "Channa Mereya.jpg", "confidence": "Exact (100%)"},
    19: {"title": "Dance Ka Bhoot", "image": "Dance Ka Bhoot.jpg", "confidence": "Exact (100%)"},
    20: {"title": "Deva Deva", "image": "Deva Deva.jpg", "confidence": "Exact (100%)"},
    21: {"title": "Dhokha Dhadi", "image": "Dhokha Dhadi.jpg", "confidence": "Exact (100%)"},
    22: {"title": "Dhun", "image": "Dhun.jpg", "confidence": "Exact (100%)"},
    23: {"title": "Finding Her", "image": "Finding Her.jpg", "confidence": "Exact (100%)"},
    24: {"title": "Ghungroo", "image": "Ghungroo.jpg", "confidence": "Exact (100%)"},
    25: {"title": "Gulaabo", "image": "Gulaabo.jpg", "confidence": "Exact (100%)"},
    26: {"title": "Hawayein", "image": "Hawayein.jpg", "confidence": "Exact (100%)"},
    27: {"title": "Hookah Bar", "image": "Hooka Bar.jpg", "confidence": "Spelling Match (98%)"},
    28: {"title": "Ishq Hai", "image": "Ishq Hai.jpg", "confidence": "Exact (100%)"},
    29: {"title": "Jai Jai Shivshankar", "image": "Jai Jai Shiv Shankar.jpg", "confidence": "Normalized (98%)"},
    30: {"title": "Jo Tum Mere Ho", "image": "Jo Tum Mere Ho.jpg", "confidence": "Exact (100%)"},
    31: {"title": "Kabhii Tumhhe", "image": "Kabhii Tumhhe.jpg", "confidence": "Exact (100%)"},
    32: {"title": "Kar Gayi Chull", "image": "Kar Gayi Chull.jpg", "confidence": "Exact (100%)"},
    33: {"title": "Love Is A Waste Of Time", "image": "Love Is A Waste Of Time.jpg", "confidence": "Exact (100%)"},
    34: {"title": "Love You Zindagi", "image": "Love You Zindagi.jpg", "confidence": "Exact (100%)"},
    35: {"title": "Malhari", "image": "Malhari.jpg", "confidence": "Exact (100%)"},
    36: {"title": "Mat Aazma Re", "image": "Mat Aazma Re.jpg", "confidence": "Exact (100%)"},
    37: {"title": "Nashe Si Chadh Gayi", "image": "Nashe Si Chadh Gayi.jpg", "confidence": "Exact (100%)"},
    38: {"title": "Pehli Nazar Mein", "image": "Pehli Nazar Mein.jpg", "confidence": "Exact (100%)"},
    39: {"title": "Raataan Lambiyan", "image": "Raatan Lambiyan.jpg", "confidence": "Spelling Match (98%)"},
    40: {"title": "Ranjha", "image": "Ranjha.jpg", "confidence": "Exact (100%)"},
    41: {"title": "Sachi Muchi", "image": "Sachi Muchi.jpg", "confidence": "Exact (100%)"},
    42: {"title": "Shaam Shaandaar", "image": "Shaam Shaandaar.jpg", "confidence": "Exact (100%)"},
    43: {"title": "Sultan (Title Track)", "image": "Sultan.jpg", "confidence": "Normalized (98%)"},
    44: {"title": "Tera Hone Laga Hoon", "image": "Tera Hone Laga Hoon.jpg", "confidence": "Exact (100%)"},
    45: {"title": "Kho Gaye Hum Kahan", "image": "Kho Gaye Hum Kahan.jpg", "confidence": "Exact (100%)"},
    46: {"title": "Tu Hai Kahan", "image": "Tu Hai Kahan.jpg", "confidence": "Exact (100%)"},
    47: {"title": "Tum Se Hi", "image": "Tum Se Hi.jpg", "confidence": "Exact (100%)"},
    48: {"title": "Shri Hanuman Chalisa", "image": "Shri Hanuman Chalisa.jpg", "confidence": "Exact (100%)"}
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

def run_image_import():
    print("=" * 85)
    print("MUSIC SUGGESTION SYSTEM: 38 COVER IMAGES IMPORT PIPELINE")
    print("=" * 85)

    # 1. Scan source folder
    if not os.path.exists(SOURCE_IMAGE_DIR):
        print(f"[FATAL ERROR] Image folder not found at: {SOURCE_IMAGE_DIR}")
        sys.exit(1)

    source_images = sorted([
        f for f in os.listdir(SOURCE_IMAGE_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ])
    print(f"[SCAN] Source folder: {SOURCE_IMAGE_DIR}")
    print(f"[SCAN] Found {len(source_images)} image files.")
    if len(source_images) != 38:
        print(f"[WARNING] Expected 38 images, found {len(source_images)}")
    else:
        print("[VERIFIED] Exactly 38 valid cover images available.")

    # Ensure local poster directory exists
    os.makedirs(LOCAL_POSTER_DIR, exist_ok=True)
    if os.path.exists(os.path.dirname(ALT_POSTER_DIR)):
        os.makedirs(ALT_POSTER_DIR, exist_ok=True)

    # 2. Check Database connection & existing songs
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT song_id, title, movie, (cover_image IS NOT NULL) AS has_cover FROM songs ORDER BY song_id ASC")
        db_songs = cur.fetchall()

    db_map = {s["song_id"]: s for s in db_songs}
    print(f"[DATABASE] Connected to MySQL. Total songs in table: {len(db_songs)}")

    # 3. Matching Report and Verification
    print("\n" + "=" * 85)
    print("MATCHING REPORT: 38 IMAGES TO SONGS")
    print("=" * 85)
    print(f"{'ID':<4} | {'Song Title':<25} | {'Matched Image File':<28} | {'Confidence':<20} | {'Status'}")
    print("-" * 85)

    matched_images_set = set()
    unmatched_images = []
    unmatched_songs = []
    ambiguous_matches = []

    for s_id, mapping in IMAGE_MAPPING_38.items():
        song_title = mapping["title"]
        img_filename = mapping["image"]
        conf = mapping["confidence"]

        src_path = os.path.join(SOURCE_IMAGE_DIR, img_filename)
        if not os.path.exists(src_path):
            unmatched_songs.append((s_id, song_title, f"Image file {img_filename} not found on disk"))
            status = "FILE MISSING"
        else:
            matched_images_set.add(img_filename)
            status = "READY TO IMPORT"

        print(f"{s_id:<4} | {song_title:<25} | {img_filename:<28} | {conf:<20} | {status}")

    # Check for any source images that were not matched
    for f in source_images:
        if f not in matched_images_set:
            unmatched_images.append(f)

    print("-" * 85)
    print(f"Total songs to update: {len(IMAGE_MAPPING_38)}")
    print(f"Total matched source images: {len(matched_images_set)}")
    print(f"Unmatched source images: {len(unmatched_images)} -> {unmatched_images}")
    print(f"Unmatched songs: {len(unmatched_songs)} -> {unmatched_songs}")
    print(f"Ambiguous matches: {len(ambiguous_matches)} -> {ambiguous_matches}")

    if unmatched_images or unmatched_songs or ambiguous_matches:
        print("[ABORT] Cannot proceed automatically with mismatches or ambiguities.")
        sys.exit(1)

    # 4. Perform Binary Insertion into MySQL
    print("\n" + "=" * 85)
    print("INSERTING COVER IMAGE BINARIES (MEDIUMBLOB) INTO MYSQL...")
    print("=" * 85)

    updated_count = 0
    with conn.cursor() as cur:
        for s_id, mapping in IMAGE_MAPPING_38.items():
            song_title = mapping["title"]
            img_filename = mapping["image"]
            src_path = os.path.join(SOURCE_IMAGE_DIR, img_filename)

            with open(src_path, "rb") as f:
                img_binary = f.read()

            file_size = len(img_binary)
            mime_type = "image/jpeg"
            if img_filename.lower().endswith(".png"):
                mime_type = "image/png"
            elif img_filename.lower().endswith(".webp"):
                mime_type = "image/webp"

            # Copy to local posters directory for caching / backup
            local_dest = os.path.join(LOCAL_POSTER_DIR, img_filename)
            if not os.path.exists(local_dest) or os.path.getsize(local_dest) != file_size:
                shutil.copy2(src_path, local_dest)

            if os.path.exists(ALT_POSTER_DIR):
                alt_dest = os.path.join(ALT_POSTER_DIR, img_filename)
                if not os.path.exists(alt_dest) or os.path.getsize(alt_dest) != file_size:
                    shutil.copy2(src_path, alt_dest)

            # Update database record
            cur.execute("""
                UPDATE songs 
                SET cover_image = %s, cover_mime_type = %s 
                WHERE song_id = %s
            """, (img_binary, mime_type, s_id))

            print(f"[STORED] Song #{s_id:2d}: '{song_title}' <- {img_filename} ({file_size:,} bytes, {mime_type})")
            updated_count += 1

    # 5. Final Verification of All 48 Songs in MySQL
    print("\n" + "=" * 85)
    print("DATABASE COVER IMAGE VERIFICATION (ALL 48 SONGS)")
    print("=" * 85)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT song_id, title, LENGTH(cover_image) as img_bytes, cover_mime_type 
            FROM songs 
            ORDER BY song_id ASC
        """)
        all_songs = cur.fetchall()

    missing_covers = 0
    for s in all_songs:
        b = s["img_bytes"] or 0
        if b > 0:
            status = "OK"
        else:
            status = "MISSING"
            missing_covers += 1
        print(f"[{status}] ID #{s['song_id']:2d}: {s['title']:<25} | {b:7,d} bytes | {s['cover_mime_type']}")

    conn.close()

    print("\n" + "=" * 85)
    print("IMPORT SUMMARY")
    print("=" * 85)
    print(f"Total songs updated with new covers: {updated_count}")
    print(f"Total songs with valid cover image in MySQL: {len(all_songs) - missing_covers} / {len(all_songs)}")
    if missing_covers == 0:
        print("[SUCCESS] All 48 songs in your Music Suggestion System now have active cover images in MySQL!")
    else:
        print(f"[WARNING] {missing_covers} songs still missing cover images.")

if __name__ == "__main__":
    run_image_import()
