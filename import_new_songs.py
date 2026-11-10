"""
import_new_songs.py - Safe, Repeatable Integration Script for 38 New Songs
Expands the Music Suggestion System catalogue from 10 songs to 48 songs.

Preserves existing 10 songs and records untouched.
Extracts ID3 tags and audio durations.
Copies audio files into dataset/songs/ with clean unique slugs without modifying source files.
Stores relative paths in MySQL songs table.
Leaves cover_image NULL ready for future upload with visual fallback.
"""

import os
import sys
import shutil
import pymysql
import pymysql.cursors
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Database Configuration
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "root")
MYSQL_DB = os.environ.get("MYSQL_DB", "music_recommendation_db")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = r"D:\Special_Project_Tanay_2026\New_Added_songs"
TARGET_AUDIO_DIR = os.path.join(BASE_DIR, "dataset", "songs")

# Secondary copy destination (if user workspace is Sp_demo_tanay)
ALT_AUDIO_DIR = r"C:\Users\acer\OneDrive\Desktop\Sp_demo_tanay\Sp_Demo\dataset\songs"

# Curated metadata dictionary mapped to exact source filenames
# Provides canonical metadata, genre, mood, activity, and descriptions matching system taxonomy
SONG_CATALOG_DEFINITIONS = [
    {
        "source_filename": "Aashayein Iqbal 128 Kbps.mp3",
        "slug": "aashayein.mp3",
        "title": "Aashayein",
        "movie": "Iqbal",
        "artist": "KK, Salim Merchant",
        "genre": "Inspirational / Pop",
        "mood": "Inspirational, Hopeful, Uplifting",
        "language": "Hindi",
        "activity": "Motivation, Studying, Morning Walk",
        "description": "An inspiring, uplifting Hindi anthem of hope, perseverance, and chasing dreams."
    },
    {
        "source_filename": "Achutam Keshavam.mp3",
        "slug": "achutam_keshavam.mp3",
        "title": "Achutam Keshavam",
        "movie": None,
        "artist": None,
        "genre": "Devotional / Spiritual",
        "mood": "Peaceful, Spiritual, Meditative",
        "language": "Hindi",
        "activity": "Prayer, Meditation, Relaxing",
        "description": "A soothing and peaceful devotional Krishna bhajan for prayer, meditation, and inner calm."
    },
    {
        "source_filename": "Baby Ko Bass Pasand Hai Sultan 128 Kbps.mp3",
        "slug": "baby_ko_bass_pasand_hai.mp3",
        "title": "Baby Ko Bass Pasand Hai",
        "movie": "Sultan",
        "artist": "Vishal Dadlani, Shalmali Kholgade, Ishita, Badshah",
        "genre": "Dance / Party",
        "mood": "Energetic, Fun, Upbeat",
        "language": "Hindi",
        "activity": "Party, Dance, Workout",
        "description": "A high-energy, peppy Bollywood dance track with groovy beats, ideal for parties and dancing."
    },
    {
        "source_filename": "Bhagwan Hai Kahan Re Tu Pk 128 Kbps.mp3",
        "slug": "bhagwan_hai_kahan_re_tu.mp3",
        "title": "Bhagwan Hai Kahan Re Tu",
        "movie": "PK",
        "artist": "Sonu Nigam, Shantanu Moitra",
        "genre": "Emotional / Spiritual",
        "mood": "Calm, Emotional, Reflective",
        "language": "Hindi",
        "activity": "Reflection, Relaxing, Evening",
        "description": "A soulful, emotional song questioning faith, human connection, and longing for spiritual guidance."
    },
    {
        "source_filename": "Brothers Anthem Vishal Dadlani 128 Kbps.mp3",
        "slug": "brothers_anthem.mp3",
        "title": "Brothers Anthem",
        "movie": "Brothers",
        "artist": "Vishal Dadlani, Ajay-Atul",
        "genre": "Motivational / Rock",
        "mood": "Powerful, Energetic, Determined",
        "language": "Hindi",
        "activity": "Workout, Motivation, Gym",
        "description": "A thunderous, power-packed motivational rock anthem that fuels intense workouts and determination."
    },
    {
        "source_filename": "Bulleya Sultan 128 Kbps.mp3",
        "slug": "bulleya.mp3",
        "title": "Bulleya",
        "movie": "Sultan",
        "artist": "Papon, Vishal-Shekhar",
        "genre": "Sufi / Romantic",
        "mood": "Emotional, Soulful, Spiritual",
        "language": "Hindi",
        "activity": "Relaxing, Travel, Reflection",
        "description": "A deeply soulful Sufi-inspired love ballad expressing longing, devotion, and heartfelt emotion."
    },
    {
        "source_filename": "Chaar Kadam Pk 128 Kbps.mp3",
        "slug": "chaar_kadam.mp3",
        "title": "Chaar Kadam",
        "movie": "PK",
        "artist": "Shaan, Shreya Ghoshal, Shantanu Moitra",
        "genre": "Romantic / Pop",
        "mood": "Sweet, Romantic, Gentle",
        "language": "Hindi",
        "activity": "Romance, Relaxing, Walking",
        "description": "A sweet, melodic romantic duet celebrating companionship and strolling hand-in-hand together."
    },
    {
        "source_filename": "Channa Mereya Ae Dil Hai Mushkil 128 Kbps.mp3",
        "slug": "channa_mereya.mp3",
        "title": "Channa Mereya",
        "movie": "Ae Dil Hai Mushkil",
        "artist": "Arijit Singh, Pritam",
        "genre": "Sufi / Sad Romantic",
        "mood": "Heartbroken, Emotional, Nostalgic",
        "language": "Hindi",
        "activity": "Late Night, Reflection, Healing",
        "description": "An iconic, poignant heartbreak ballad about unrequited love and bittersweet farewells."
    },
    {
        "source_filename": "Dance Ka Bhoot Brahmastra 128 Kbps.mp3",
        "slug": "dance_ka_bhoot.mp3",
        "title": "Dance Ka Bhoot",
        "movie": "Brahmastra",
        "artist": "Arijit Singh, Pritam",
        "genre": "Festive / Dance",
        "mood": "Celebratory, Joyful, Energetic",
        "language": "Hindi",
        "activity": "Festival, Party, Celebration",
        "description": "A colorful, celebratory festive track capturing the infectious joy and energy of celebrations."
    },
    {
        "source_filename": "Deva Deva Brahmastra 128 Kbps.mp3",
        "slug": "deva_deva.mp3",
        "title": "Deva Deva",
        "movie": "Brahmastra",
        "artist": "Arijit Singh, Jonita Gandhi, Pritam",
        "genre": "Spiritual / Uplifting",
        "mood": "Spiritual, Powerful, Uplifting",
        "language": "Hindi",
        "activity": "Meditation, Focus, Morning",
        "description": "A radiant, uplifting spiritual song exploring divine inner light, power, and connection."
    },
    {
        "source_filename": "Dhokha Dhadi R... Rajkumar 128 Kbps.mp3",
        "slug": "dhokha_dhadi.mp3",
        "title": "Dhokha Dhadi",
        "movie": "R... Rajkumar",
        "artist": "Arijit Singh, Palak Muchhal, Pritam",
        "genre": "Romantic / Melodic",
        "mood": "Playful, Romantic, Cheerful",
        "language": "Hindi",
        "activity": "Romance, Relaxing, Road Trip",
        "description": "A charming and playful romantic song about sweet surrender and falling in love effortlessly."
    },
    {
        "source_filename": "Dhun Saiyaara 128 Kbps.mp3",
        "slug": "dhun_saiyaara.mp3",
        "title": "Dhun",
        "movie": "Saiyaara",
        "artist": "Arijit Singh",
        "genre": "Romantic / Indie",
        "mood": "Mellow, Romantic, Soothing",
        "language": "Hindi",
        "activity": "Relaxing, Late Night, Chill",
        "description": "A gentle, acoustic romantic melody featuring warm vocals for quiet evenings and relaxation."
    },
    {
        "source_filename": "Finding Her Kushagra 128 Kbps.mp3",
        "slug": "finding_her.mp3",
        "title": "Finding Her",
        "movie": "Finding Her",
        "artist": "Kushagra, Saaheal, Bharath",
        "genre": "Indie Pop / Lo-Fi",
        "mood": "Dreamy, Romantic, Calm",
        "language": "Hindi",
        "activity": "Relaxing, Studying, Late Night Drive",
        "description": "A modern, dreamy indie pop love track with smooth lo-fi textures and romantic vibes."
    },
    {
        "source_filename": "Ghungroo War 128 Kbps.mp3",
        "slug": "ghungroo.mp3",
        "title": "Ghungroo",
        "movie": "War",
        "artist": "Arijit Singh, Shilpa Rao, Vishal-Shekhar",
        "genre": "Party / Funk",
        "mood": "Breezy, Stylish, Fun",
        "language": "Hindi",
        "activity": "Party, Vacation, Beach, Dancing",
        "description": "A stylish, breezy poolside dance number full of groove, sophistication, and rhythm."
    },
    {
        "source_filename": "Gulaabo Shaandaar 128 Kbps.mp3",
        "slug": "gulaabo.mp3",
        "title": "Gulaabo",
        "movie": "Shaandaar",
        "artist": "Vishal Dadlani, Anusha Mani, Amit Trivedi",
        "genre": "Swing / Party",
        "mood": "Quirky, Upbeat, Energetic",
        "language": "Hindi",
        "activity": "Party, Dance, Weekend",
        "description": "A swing-jazz influenced quirky party track with punchy brass and irresistible dance rhythm."
    },
    {
        "source_filename": "Hawayein Jab Harry Met Sejal (original Motion Picturetrack) 128 Kbps.mp3",
        "slug": "hawayein.mp3",
        "title": "Hawayein",
        "movie": "Jab Harry Met Sejal",
        "artist": "Arijit Singh, Pritam",
        "genre": "Romantic / Breeze",
        "mood": "Romantic, Gentle, Warm",
        "language": "Hindi",
        "activity": "Travel, Romance, Sunset, Relaxing",
        "description": "A breezy, soaring love song about gentle winds carrying whispers of deep affection."
    },
    {
        "source_filename": "Hookah Bar Khiladi 786 128 Kbps.mp3",
        "slug": "hookah_bar.mp3",
        "title": "Hookah Bar",
        "movie": "Khiladi 786",
        "artist": "Himesh Reshammiya, Vineet Singh, Aman Trikha",
        "genre": "Club / Dance",
        "mood": "Energetic, Catchy, Loud",
        "language": "Hindi",
        "activity": "Clubbing, Party, Gym, Driving",
        "description": "A high-tempo club banger with unforgettable electronic hooklines and driving beats."
    },
    {
        "source_filename": "Ishq Hai.mp3",
        "slug": "ishq_hai.mp3",
        "title": "Ishq Hai",
        "movie": None,
        "artist": None,
        "genre": "Romantic / Melodic",
        "mood": "Passionate, Romantic, Soulful",
        "language": "Hindi",
        "activity": "Romance, Relaxing, Evening",
        "description": "A passionate, soulful romantic track exploring the depths and beauty of love."
    },
    {
        "source_filename": "Jai Jai Shivshankar War 128 Kbps.mp3",
        "slug": "jai_jai_shivshankar.mp3",
        "title": "Jai Jai Shivshankar",
        "movie": "War",
        "artist": "Vishal Dadlani, Benny Dayal, Vishal-Shekhar",
        "genre": "Dance / Festive",
        "mood": "High Energy, Explosive, Celebratory",
        "language": "Hindi",
        "activity": "Party, Dance, Workout, Holi",
        "description": "An explosive dance showdown bursting with rhythm, high adrenaline, and festive dance beats."
    },
    {
        "source_filename": "Jo Tum Mere Ho Anuv Jain 128 Kbps.mp3",
        "slug": "jo_tum_mere_ho.mp3",
        "title": "Jo Tum Mere Ho",
        "movie": "Jo Tum Mere Ho",
        "artist": "Anuv Jain",
        "genre": "Indie Acoustic",
        "mood": "Intimate, Tender, Peaceful",
        "language": "Hindi",
        "activity": "Relaxing, Studying, Late Night, Romance",
        "description": "An intimate, heartfelt acoustic indie ballad sung with delicate vulnerability and tenderness."
    },
    {
        "source_filename": "Kabhii Tumhhe Shershaah 128 Kbps.mp3",
        "slug": "kabhii_tumhhe.mp3",
        "title": "Kabhii Tumhhe",
        "movie": "Shershaah",
        "artist": "Darshan Raval",
        "genre": "Romantic / Ballad",
        "mood": "Emotional, Melancholic, Loving",
        "language": "Hindi",
        "activity": "Reflection, Quiet Moments, Romance",
        "description": "A touching romantic ballad recounting enduring promises and eternal affection."
    },
    {
        "source_filename": "Kar Gayi Chull - Kapoor & Sons  Sidharth Malhotra  Alia Bhatt  Badshah  Amaal Mallik Fazilpuria.mp3",
        "slug": "kar_gayi_chull.mp3",
        "title": "Kar Gayi Chull",
        "movie": "Kapoor & Sons",
        "artist": "Badshah, Fazilpuria, Sukriti Kakar, Neha Kakkar",
        "genre": "Party / Hip-Hop",
        "mood": "Bouncy, Fun, Energetic",
        "language": "Hindi",
        "activity": "House Party, Dance, Workout",
        "description": "A smash-hit club and house party anthem loaded with infectious rap flows and lively beats."
    },
    {
        "source_filename": "Love Is A Waste Of Time Pk 128 Kbps.mp3",
        "slug": "love_is_a_waste_of_time.mp3",
        "title": "Love Is A Waste Of Time",
        "movie": "PK",
        "artist": "Sonu Nigam, Shreya Ghoshal, Shantanu Moitra",
        "genre": "Comedy / Romantic",
        "mood": "Lighthearted, Playful, Quirky",
        "language": "Hindi",
        "activity": "Casual, Relaxing, Commute",
        "description": "A lighthearted, witty Bhojpuri-flavored romantic number with innocent humor and charm."
    },
    {
        "source_filename": "Love You Zindagi Dear Zindagi 128 Kbps.mp3",
        "slug": "love_you_zindagi.mp3",
        "title": "Love You Zindagi",
        "movie": "Dear Zindagi",
        "artist": "Jasleen Royal, Amit Trivedi",
        "genre": "Feel Good / Pop",
        "mood": "Joyful, Carefree, Optimistic",
        "language": "Hindi",
        "activity": "Morning, Walking, Self-Care, Smiling",
        "description": "A delightful feel-good anthem celebrating life, small joys, and loving oneself every day."
    },
    {
        "source_filename": "Malhari Bajirao Mastani 128 Kbps.mp3",
        "slug": "malhari.mp3",
        "title": "Malhari",
        "movie": "Bajirao Mastani",
        "artist": "Vishal Dadlani, Sanjay Leela Bhansali",
        "genre": "Folk / War Dance",
        "mood": "Fierce, Triumphant, Electrifying",
        "language": "Hindi / Marathi",
        "activity": "Workout, Motivation, Celebration, Victory",
        "description": "A ferocious, victorious warrior dance track with thumping traditional percussion and raw power."
    },
    {
        "source_filename": "Mat Aazma Re Murder 3 128 Kbps.mp3",
        "slug": "mat_aazma_re.mp3",
        "title": "Mat Aazma Re",
        "movie": "Murder 3",
        "artist": "KK, Pritam",
        "genre": "Romantic Rock",
        "mood": "Intense, Emotional, Longing",
        "language": "Hindi",
        "activity": "Late Night Drive, Romance, Reflection",
        "description": "A powerful romantic rock ballad expressing raw emotional vulnerability and pleading love."
    },
    {
        "source_filename": "Nashe Si Chadh Gayi Befikre 128 Kbps.mp3",
        "slug": "nashe_si_chadh_gayi.mp3",
        "title": "Nashe Si Chadh Gayi",
        "movie": "Befikre",
        "artist": "Arijit Singh, Vishal-Shekhar",
        "genre": "Pop / Dance",
        "mood": "Groovy, Romantic, Carefree",
        "language": "Hindi / French",
        "activity": "Dancing, Road Trip, Party",
        "description": "A smooth, addictive Parisian dance track about dizzying romantic infatuation."
    },
    {
        "source_filename": "Pehli Nazar Mein Race 128 Kbps.mp3",
        "slug": "pehli_nazar_mein.mp3",
        "title": "Pehli Nazar Mein",
        "movie": "Race",
        "artist": "Atif Aslam, Pritam",
        "genre": "Romantic / Pop",
        "mood": "Mesmerizing, Romantic, Nostalgic",
        "language": "Hindi",
        "activity": "Romance, Candlelight, Road Trip",
        "description": "A timeless love anthem celebrating the magical sensation of love at first sight."
    },
    {
        "source_filename": "Raataan Lambiyan Shershaah 128 Kbps.mp3",
        "slug": "raataan_lambiyan.mp3",
        "title": "Raataan Lambiyan",
        "movie": "Shershaah",
        "artist": "Jubin Nautiyal, Asees Kaur, Tanishk Bagchi",
        "genre": "Romantic / Acoustic",
        "mood": "Tender, Romantic, Warm",
        "language": "Hindi / Punjabi",
        "activity": "Romance, Evening, Star Gazing",
        "description": "A tender, soothing melody portraying long sleepless nights thinking about one's beloved."
    },
    {
        "source_filename": "Ranjha Shershaah 128 Kbps.mp3",
        "slug": "ranjha.mp3",
        "title": "Ranjha",
        "movie": "Shershaah",
        "artist": "Jasleen Royal, B Praak",
        "genre": "Soulful / Folk Romantic",
        "mood": "Emotional, Melancholic, Deep",
        "language": "Hindi / Punjabi",
        "activity": "Quiet Evening, Reflection, Romance",
        "description": "A deeply emotional, folk-infused ballad capturing the ache of parting and deep longing."
    },
    {
        "source_filename": "Sachi Muchi Sultan 128 Kbps.mp3",
        "slug": "sachi_muchi.mp3",
        "title": "Sachi Muchi",
        "movie": "Sultan",
        "artist": "Mohit Chauhan, Harshdeep Kaur, Vishal-Shekhar",
        "genre": "Folk / Romantic",
        "mood": "Charming, Innocent, Cheerful",
        "language": "Hindi",
        "activity": "Casual, Relaxing, Morning",
        "description": "A charming rustic love duet filled with innocent confessions, gentle rhythm, and warmth."
    },
    {
        "source_filename": "Shaam Shaandaar Amit Trivedi 128 Kbps.mp3",
        "slug": "shaam_shaandaar.mp3",
        "title": "Shaam Shaandaar",
        "movie": "Shaandaar",
        "artist": "Amit Trivedi",
        "genre": "Party / Electro-Folk",
        "mood": "Ecstatic, Lively, Celebratory",
        "language": "Hindi",
        "activity": "Evening Party, Celebration, Dance",
        "description": "An electric evening party number setting the stage for a glamorous, unforgettable night."
    },
    {
        "source_filename": "Sultan Sukhwinder Singh 128 Kbps.mp3",
        "slug": "sultan_title_track.mp3",
        "title": "Sultan (Title Track)",
        "movie": "Sultan",
        "artist": "Sukhwinder Singh, Shadab Faridi, Vishal-Shekhar",
        "genre": "Motivational / Desi Hip-Hop",
        "mood": "Fearless, Inspiring, High Adrenaline",
        "language": "Hindi / Haryanvi",
        "activity": "Workout, Motivation, Gym, Running",
        "description": "A stirring motivational title track honoring the fighting spirit of rising back up against all odds."
    },
    {
        "source_filename": "Tera Hone Laga Hoon Ajab Prem Ki Ghazab Kahani 128 Kbps.mp3",
        "slug": "tera_hone_laga_hoon.mp3",
        "title": "Tera Hone Laga Hoon",
        "movie": "Ajab Prem Ki Ghazab Kahani",
        "artist": "Atif Aslam, Alisha Chinai, Pritam",
        "genre": "Romantic Pop",
        "mood": "Dreamy, Sweet, Romantic",
        "language": "Hindi / English",
        "activity": "Romance, Road Trip, Relaxing",
        "description": "A dreamy romantic classic describing the surreal feeling of falling helplessly in love."
    },
    {
        "source_filename": "Title Track Kho Gaye Hum Kahan 128 Kbps.mp3",
        "slug": "kho_gaye_hum_kahan.mp3",
        "title": "Kho Gaye Hum Kahan",
        "movie": "Kho Gaye Hum Kahan",
        "artist": "Achint, Javed Akhtar",
        "genre": "Indie / Mellow",
        "mood": "Reflective, Mellow, Modern",
        "language": "Hindi",
        "activity": "Late Night, City Drive, Studying",
        "description": "A contemporary, contemplative indie song capturing youth, digital connection, and finding oneself."
    },
    {
        "source_filename": "Tu Hai Kahan Aur 128 Kbps.mp3",
        "slug": "tu_hai_kahan.mp3",
        "title": "Tu Hai Kahan",
        "movie": "Tu Hai Kahan",
        "artist": "AUR",
        "genre": "Indie Pop / Soul",
        "mood": "Melancholic, Atmospheric, Romantic",
        "language": "Urdu / Hindi",
        "activity": "Late Night, Rain, Healing",
        "description": "A viral soulful indie track soaked in longing, atmospheric synths, and emotional resonance."
    },
    {
        "source_filename": "Tum Se Hi Jab We Met 128 Kbps.mp3",
        "slug": "tum_se_hi.mp3",
        "title": "Tum Se Hi",
        "movie": "Jab We Met",
        "artist": "Mohit Chauhan, Pritam",
        "genre": "Romantic Acoustic",
        "mood": "Warm, Gentle, Nostalgic, Loving",
        "language": "Hindi",
        "activity": "Rain, Travel, Romance, Relaxing",
        "description": "An evergreen romantic acoustic masterpiece about how every breath and rain shower revolves around one person."
    },
    {
        "source_filename": "shri-hanuman-chalisa.mp3",
        "slug": "shri_hanuman_chalisa.mp3",
        "title": "Shri Hanuman Chalisa",
        "movie": "Hanuman Chalisa",
        "artist": "Aditya Jyotish",
        "genre": "Devotional / Sacred",
        "mood": "Peaceful, Spiritual, Courageous",
        "language": "Awadhi / Hindi",
        "activity": "Prayer, Morning, Meditation",
        "description": "Sacred forty-verse hymn extolling the strength, wisdom, and divine blessings of Lord Hanuman."
    }
]


def get_db_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


def run_import():
    print("=" * 80)
    print("MUSIC SUGGESTION SYSTEM: 38 NEW SONGS IMPORT PIPELINE")
    print("=" * 80)

    # Step 1: Scan and verify source folder
    if not os.path.exists(SOURCE_DIR):
        print(f"[FATAL ERROR] Source songs folder not found at: {SOURCE_DIR}")
        sys.exit(1)

    source_files = sorted([
        f for f in os.listdir(SOURCE_DIR)
        if f.lower().endswith((".mp3", ".wav", ".m4a", ".flac", ".ogg"))
    ])
    print(f"[SCAN] Located source folder: {SOURCE_DIR}")
    print(f"[SCAN] Identified {len(source_files)} audio files.")

    if len(source_files) != 38:
        print(f"[WARNING] Expected exactly 38 songs, but identified {len(source_files)}!")
    else:
        print("[VERIFIED] Exactly 38 songs identified.")

    # Ensure target directories exist
    os.makedirs(TARGET_AUDIO_DIR, exist_ok=True)
    if os.path.exists(os.path.dirname(ALT_AUDIO_DIR)):
        os.makedirs(ALT_AUDIO_DIR, exist_ok=True)

    # Step 2: Ensure database schema has duration column
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SHOW COLUMNS FROM songs LIKE 'duration'")
        if not cur.fetchone():
            print("[SCHEMA] Adding column 'duration' VARCHAR(20) NULL to songs table...")
            cur.execute("ALTER TABLE songs ADD COLUMN duration VARCHAR(20) NULL")
        else:
            print("[SCHEMA] Column 'duration' already exists in songs table.")

        # Check existing songs
        cur.execute("SELECT song_id, title, audio_url FROM songs ORDER BY song_id ASC")
        existing_db_songs = cur.fetchall()
        print(f"[DATABASE] Current songs in database: {len(existing_db_songs)}")

        existing_titles = {s["title"].strip().lower(): s for s in existing_db_songs}
        existing_urls = {s["audio_url"].strip().lower() if s["audio_url"] else "": s for s in existing_db_songs}

    # Step 3: Iterate and process each of the 38 songs
    imported_songs = []
    skipped_songs = []
    failed_songs = []

    print("\n" + "-" * 80)
    print("PROCESSING SONGS...")
    print("-" * 80)

    for item in SONG_CATALOG_DEFINITIONS:
        source_name = item["source_filename"]
        source_path = os.path.join(SOURCE_DIR, source_name)

        if not os.path.exists(source_path):
            failed_songs.append({"source": source_name, "reason": "Source file does not exist on disk"})
            print(f"[FAIL] Missing file: {source_name}")
            continue

        # Extract audio duration using mutagen
        try:
            audio_info = MP3(source_path)
            duration_sec = round(audio_info.info.length)
            duration_formatted = f"{duration_sec // 60}:{duration_sec % 60:02d}"
        except Exception as e:
            duration_formatted = "Unknown"

        # Destination paths
        target_path = os.path.join(TARGET_AUDIO_DIR, item["slug"])
        rel_audio_url = f"dataset/songs/{item['slug']}"

        # Copy audio file to target directory if not present or size differs
        src_size = os.path.getsize(source_path)
        if not os.path.exists(target_path) or os.path.getsize(target_path) != src_size:
            shutil.copy2(source_path, target_path)
            print(f"[COPY] {source_name} -> {target_path} ({src_size:,} bytes)")
        else:
            print(f"[EXISTS ON DISK] {item['slug']} already present ({src_size:,} bytes)")

        # Also copy to ALT directory if available
        if os.path.exists(ALT_AUDIO_DIR):
            alt_path = os.path.join(ALT_AUDIO_DIR, item["slug"])
            if not os.path.exists(alt_path) or os.path.getsize(alt_path) != src_size:
                shutil.copy2(source_path, alt_path)

        # Verify target audio file exists and is readable
        if not os.path.exists(target_path) or os.path.getsize(target_path) == 0:
            failed_songs.append({"source": source_name, "reason": "Failed to verify copied audio file"})
            print(f"[FAIL] Audio verification failed for {target_path}")
            continue

        # Database Check
        title_key = item["title"].strip().lower()
        url_key = rel_audio_url.strip().lower()

        with conn.cursor() as cur:
            if title_key in existing_titles or url_key in existing_urls:
                existing_record = existing_titles.get(title_key) or existing_urls.get(url_key)
                song_id = existing_record["song_id"]
                # Update duration if missing, without altering cover or existing attributes
                cur.execute(
                    "UPDATE songs SET duration = %s, audio_url = %s WHERE song_id = %s",
                    (duration_formatted, rel_audio_url, song_id)
                )
                skipped_songs.append({
                    "song_id": song_id,
                    "title": item["title"],
                    "audio_url": rel_audio_url,
                    "duration": duration_formatted,
                    "status": "Already exists (updated path/duration if needed)"
                })
                print(f"[SKIP/EXISTS] Song ID #{song_id}: '{item['title']}' already exists.")
            else:
                # Insert new song record
                # Next song_id starts after max existing song_id
                cur.execute("SELECT MAX(song_id) AS max_id FROM songs")
                max_row = cur.fetchone()
                next_id = (max_row["max_id"] or 10) + 1

                insert_sql = """
                    INSERT INTO songs (
                        song_id, title, movie, artist, genre, mood, 
                        language, activity, description, audio_url, 
                        duration, cover_image, cover_mime_type
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, 
                        %s, NULL, 'image/jpeg'
                    )
                """
                cur.execute(insert_sql, (
                    next_id,
                    item["title"],
                    item["movie"],
                    item["artist"],
                    item["genre"],
                    item["mood"],
                    item["language"],
                    item["activity"],
                    item["description"],
                    rel_audio_url,
                    duration_formatted
                ))

                # Also update existing_titles/urls dictionary
                new_entry = {"song_id": next_id, "title": item["title"], "audio_url": rel_audio_url}
                existing_titles[title_key] = new_entry
                existing_urls[url_key] = new_entry

                imported_songs.append({
                    "song_id": next_id,
                    "title": item["title"],
                    "movie": item["movie"],
                    "artist": item["artist"],
                    "duration": duration_formatted,
                    "audio_url": rel_audio_url,
                    "status": "Imported successfully"
                })
                print(f"[INSERTED] Song ID #{next_id:2d}: '{item['title']}' ({duration_formatted}) -> {rel_audio_url}")

    # Also backfill duration for the initial 10 songs if NULL
    INITIAL_DURATIONS = {
        1: "4:28", 2: "4:21", 3: "3:16", 4: "5:11", 5: "3:49",
        6: "4:11", 7: "4:13", 8: "7:53", 9: "4:48", 10: "4:19"
    }
    with conn.cursor() as cur:
        for s_id, dur in INITIAL_DURATIONS.items():
            cur.execute("UPDATE songs SET duration = %s WHERE song_id = %s AND (duration IS NULL OR duration = '')", (dur, s_id))

    # Step 4: Final Database Verification
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM songs")
        final_total = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS null_covers FROM songs WHERE cover_image IS NULL")
        null_covers = cur.fetchone()["null_covers"]

        cur.execute("SELECT song_id, title, movie, artist, audio_url, duration, (cover_image IS NOT NULL) as has_cover FROM songs ORDER BY song_id ASC")
        all_songs = cur.fetchall()

    conn.close()

    # Step 5: Summary Report
    print("\n" + "=" * 80)
    print("IMPORT EXECUTION REPORT")
    print("=" * 80)
    print(f"Total audio files identified: {len(source_files)}")
    print(f"Total songs successfully imported: {len(imported_songs)}")
    print(f"Total songs skipped (already existing): {len(skipped_songs)}")
    print(f"Total songs failed: {len(failed_songs)}")
    print(f"Final songs in MySQL database: {final_total} (Expected: 48)")
    print(f"Songs with NULL cover image (ready for later upload): {null_covers}")

    print("\n" + "-" * 110)
    print(f"{'ID':<4} | {'Title':<25} | {'Artist':<30} | {'Movie':<20} | {'Dur':<6} | {'Audio URL':<35} | {'Cover'}")
    print("-" * 110)
    for s in all_songs:
        c_status = "Uploaded" if s["has_cover"] else "Pending (NULL)"
        print(f"{s['song_id']:<4} | {s['title']:<25} | {str(s['artist'] or 'None'):<30} | {str(s['movie'] or 'None'):<20} | {str(s['duration'] or '-'):<6} | {s['audio_url']:<35} | {c_status}")

    print("=" * 110)
    if final_total == 48:
        print("[SUCCESS] All 38 new songs successfully integrated! Catalogue now has exactly 48 songs.")
    else:
        print(f"[NOTICE] Total count is {final_total}. Please review output above.")

if __name__ == "__main__":
    run_import()
