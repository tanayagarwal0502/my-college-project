USE music_recommendation_db;

-- Insert Demo User with login credentials (password: password123)
INSERT INTO users (user_id, name, username, email, password_hash, profile_image, profile_completed)
VALUES (
    1,
    'Demo User',
    'demouser',
    'demo@example.com',
    'scrypt:32768:8:1$9qn5LaWM0ulUORBz$6dad3438ad59b3f5a622cfcc5d486f84e88a478095b3290c27413004a2ad129396d9e8c86a560b573299d0ba05c711837c672482607d7e5f815a741718aa5a88',
    '/static/images/default_avatar.svg',
    TRUE
)
ON DUPLICATE KEY UPDATE 
    name = VALUES(name),
    username = VALUES(username),
    email = VALUES(email),
    password_hash = VALUES(password_hash),
    profile_image = VALUES(profile_image),
    profile_completed = VALUES(profile_completed);

-- Initialize default preferences for Demo User
INSERT INTO user_preferences (user_id, mood_or_vibe)
SELECT 1, 'Romantic' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM user_preferences WHERE user_id = 1 AND mood_or_vibe = 'Romantic');
INSERT INTO user_preferences (user_id, mood_or_vibe)
SELECT 1, 'Relaxing' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM user_preferences WHERE user_id = 1 AND mood_or_vibe = 'Relaxing');

-- Initialize default profile for Demo User
INSERT INTO user_profile (user_id, preferred_moods, preferred_genres, preferred_languages, liked_songs)
VALUES (1, 'Romantic, Relaxing', 'Romantic', 'Hindi', '')
ON DUPLICATE KEY UPDATE user_id = 1;

-- Insert 10 Initial Bollywood/Hindi Songs with exact local MP3 dataset paths
INSERT INTO songs (song_id, title, movie, artist, genre, mood, language, activity, description, audio_url, duration)
VALUES
(1, 'Kesariya', 'Brahmāstra', 'Arijit Singh', 'Romantic', 'Romantic, Warm, Happy', 'Hindi', 'Romance, Relaxing', 'A romantic Hindi song with a warm and affectionate feeling.', 'dataset/songs/kesariya.mp3', '4:28'),
(2, 'Apna Bana Le', 'Bhediya', 'Arijit Singh', 'Romantic', 'Romantic, Emotional, Comforting', 'Hindi', 'Romance, Relaxing', 'A soulful romantic song suitable for love, comfort and emotional connection.', 'dataset/songs/apna_bana_le.mp3', '4:21'),
(3, 'Zinda', 'Naam Shabana', 'Various', 'Motivational', 'Energetic, Determined, Motivational', 'Hindi', 'Workout, Motivation', 'An energetic motivational song suitable for confidence, determination and overcoming challenges.', 'dataset/songs/zinda.mp3', '3:16'),
(4, 'Kar Har Maidaan Fateh', 'Sanju', 'Sukhwinder Singh, Shreya Ghoshal', 'Motivational', 'Powerful, Determined, Inspirational', 'Hindi', 'Workout, Motivation, Studying', 'A powerful inspirational song about determination and overcoming obstacles.', 'dataset/songs/kar_har_maidaan_fateh.mp3', '5:11'),
(5, 'Ilahi', 'Yeh Jawaani Hai Deewani', 'Arijit Singh', 'Travel', 'Happy, Free, Adventurous', 'Hindi', 'Travel, Road Trip', 'A cheerful and adventurous song associated with travel, freedom and exploration.', 'dataset/songs/ilahi.mp3', '3:49'),
(6, 'Safarnama', 'Tamasha', 'Lucky Ali', 'Travel', 'Calm, Reflective, Peaceful', 'Hindi', 'Travel, Relaxing', 'A reflective travel song suitable for peaceful journeys and self-reflection.', 'dataset/songs/safarnama.mp3', '4:11'),
(7, 'Iktara', 'Wake Up Sid', 'Kavita Seth', 'Indie / Romantic', 'Calm, Peaceful, Emotional', 'Hindi', 'Relaxing, Studying', 'A soft and peaceful song suitable for quiet moments and relaxation.', 'dataset/songs/iktara.mp3', '4:13'),
(8, 'Kun Faya Kun', 'Rockstar', 'A.R. Rahman, Javed Ali, Mohit Chauhan', 'Sufi / Spiritual', 'Peaceful, Spiritual, Emotional', 'Hindi', 'Relaxing, Reflection', 'A spiritual and emotional song suitable for peaceful moments and reflection.', 'dataset/songs/kun_faya_kun.mp3', '7:53'),
(9, 'Aaj Ki Raat', 'Don', 'Alisha Chinai, Mahalakshmi Iyer, Sonu Nigam', 'Dance / Party', 'Energetic, Excited, Fun', 'Hindi', 'Party, Dance', 'An energetic Bollywood dance song suitable for parties and celebrations.', 'dataset/songs/aaj_ki_raat.mp3', '4:48'),
(10, 'Gallan Goodiyaan', 'Dil Dhadakne Do', 'Various', 'Party / Family', 'Happy, Energetic, Celebratory', 'Hindi', 'Party, Celebration', 'A joyful Bollywood song suitable for celebrations, family gatherings and parties.', 'dataset/songs/gallan_goodiyaan.mp3', '4:19'),
(11, 'Aashayein', 'Iqbal', 'KK, Salim Merchant', 'Inspirational / Pop', 'Inspirational, Hopeful, Uplifting', 'Hindi', 'Motivation, Studying, Morning Walk', 'An inspiring, uplifting Hindi anthem of hope, perseverance, and chasing dreams.', 'dataset/songs/aashayein.mp3', '4:20'),
(12, 'Achutam Keshavam', NULL, NULL, 'Devotional / Spiritual', 'Peaceful, Spiritual, Meditative', 'Hindi', 'Prayer, Meditation, Relaxing', 'A soothing and peaceful devotional Krishna bhajan for prayer, meditation, and inner calm.', 'dataset/songs/achutam_keshavam.mp3', '6:22'),
(13, 'Baby Ko Bass Pasand Hai', 'Sultan', 'Vishal Dadlani, Shalmali Kholgade, Ishita, Badshah', 'Dance / Party', 'Energetic, Fun, Upbeat', 'Hindi', 'Party, Dance, Workout', 'A high-energy, peppy Bollywood dance track with groovy beats, ideal for parties and dancing.', 'dataset/songs/baby_ko_bass_pasand_hai.mp3', '4:13'),
(14, 'Bhagwan Hai Kahan Re Tu', 'PK', 'Sonu Nigam, Shantanu Moitra', 'Emotional / Spiritual', 'Calm, Emotional, Reflective', 'Hindi', 'Reflection, Relaxing, Evening', 'A soulful, emotional song questioning faith, human connection, and longing for spiritual guidance.', 'dataset/songs/bhagwan_hai_kahan_re_tu.mp3', '5:11'),
(15, 'Brothers Anthem', 'Brothers', 'Vishal Dadlani, Ajay-Atul', 'Motivational / Rock', 'Powerful, Energetic, Determined', 'Hindi', 'Workout, Motivation, Gym', 'A thunderous, power-packed motivational rock anthem that fuels intense workouts and determination.', 'dataset/songs/brothers_anthem.mp3', '5:54'),
(16, 'Bulleya', 'Sultan', 'Papon, Vishal-Shekhar', 'Sufi / Romantic', 'Emotional, Soulful, Spiritual', 'Hindi', 'Relaxing, Travel, Reflection', 'A deeply soulful Sufi-inspired love ballad expressing longing, devotion, and heartfelt emotion.', 'dataset/songs/bulleya.mp3', '5:57'),
(17, 'Chaar Kadam', 'PK', 'Shaan, Shreya Ghoshal, Shantanu Moitra', 'Romantic / Pop', 'Sweet, Romantic, Gentle', 'Hindi', 'Romance, Relaxing, Walking', 'A sweet, melodic romantic duet celebrating companionship and strolling hand-in-hand together.', 'dataset/songs/chaar_kadam.mp3', '4:03'),
(18, 'Channa Mereya', 'Ae Dil Hai Mushkil', 'Arijit Singh, Pritam', 'Sufi / Sad Romantic', 'Heartbroken, Emotional, Nostalgic', 'Hindi', 'Late Night, Reflection, Healing', 'An iconic, poignant heartbreak ballad about unrequited love and bittersweet farewells.', 'dataset/songs/channa_mereya.mp3', '4:49'),
(19, 'Dance Ka Bhoot', 'Brahmastra', 'Arijit Singh, Pritam', 'Festive / Dance', 'Celebratory, Joyful, Energetic', 'Hindi', 'Festival, Party, Celebration', 'A colorful, celebratory festive track capturing the infectious joy and energy of celebrations.', 'dataset/songs/dance_ka_bhoot.mp3', '4:06'),
(20, 'Deva Deva', 'Brahmastra', 'Arijit Singh, Jonita Gandhi, Pritam', 'Spiritual / Uplifting', 'Spiritual, Powerful, Uplifting', 'Hindi', 'Meditation, Focus, Morning', 'A radiant, uplifting spiritual song exploring divine inner light, power, and connection.', 'dataset/songs/deva_deva.mp3', '4:39'),
(21, 'Dhokha Dhadi', 'R... Rajkumar', 'Arijit Singh, Palak Muchhal, Pritam', 'Romantic / Melodic', 'Playful, Romantic, Cheerful', 'Hindi', 'Romance, Relaxing, Road Trip', 'A charming and playful romantic song about sweet surrender and falling in love effortlessly.', 'dataset/songs/dhokha_dhadi.mp3', '4:09'),
(22, 'Dhun', 'Saiyaara', 'Arijit Singh', 'Romantic / Indie', 'Mellow, Romantic, Soothing', 'Hindi', 'Relaxing, Late Night, Chill', 'A gentle, acoustic romantic melody featuring warm vocals for quiet evenings and relaxation.', 'dataset/songs/dhun_saiyaara.mp3', '4:37'),
(23, 'Finding Her', 'Finding Her', 'Kushagra, Saaheal, Bharath', 'Indie Pop / Lo-Fi', 'Dreamy, Romantic, Calm', 'Hindi', 'Relaxing, Studying, Late Night Drive', 'A modern, dreamy indie pop love track with smooth lo-fi textures and romantic vibes.', 'dataset/songs/finding_her.mp3', '3:27'),
(24, 'Ghungroo', 'War', 'Arijit Singh, Shilpa Rao, Vishal-Shekhar', 'Party / Funk', 'Breezy, Stylish, Fun', 'Hindi', 'Party, Vacation, Beach, Dancing', 'A stylish, breezy poolside dance number full of groove, sophistication, and rhythm.', 'dataset/songs/ghungroo.mp3', '5:03'),
(25, 'Gulaabo', 'Shaandaar', 'Vishal Dadlani, Anusha Mani, Amit Trivedi', 'Swing / Party', 'Quirky, Upbeat, Energetic', 'Hindi', 'Party, Dance, Weekend', 'A swing-jazz influenced quirky party track with punchy brass and irresistible dance rhythm.', 'dataset/songs/gulaabo.mp3', '4:24'),
(26, 'Hawayein', 'Jab Harry Met Sejal', 'Arijit Singh, Pritam', 'Romantic / Breeze', 'Romantic, Gentle, Warm', 'Hindi', 'Travel, Romance, Sunset, Relaxing', 'A breezy, soaring love song about gentle winds carrying whispers of deep affection.', 'dataset/songs/hawayein.mp3', '4:50'),
(27, 'Hookah Bar', 'Khiladi 786', 'Himesh Reshammiya, Vineet Singh, Aman Trikha', 'Club / Dance', 'Energetic, Catchy, Loud', 'Hindi', 'Clubbing, Party, Gym, Driving', 'A high-tempo club banger with unforgettable electronic hooklines and driving beats.', 'dataset/songs/hookah_bar.mp3', '4:14'),
(28, 'Ishq Hai', NULL, NULL, 'Romantic / Melodic', 'Passionate, Romantic, Soulful', 'Hindi', 'Romance, Relaxing, Evening', 'A passionate, soulful romantic track exploring the depths and beauty of love.', 'dataset/songs/ishq_hai.mp3', '5:13'),
(29, 'Jai Jai Shivshankar', 'War', 'Vishal Dadlani, Benny Dayal, Vishal-Shekhar', 'Dance / Festive', 'High Energy, Explosive, Celebratory', 'Hindi', 'Party, Dance, Workout, Holi', 'An explosive dance showdown bursting with rhythm, high adrenaline, and festive dance beats.', 'dataset/songs/jai_jai_shivshankar.mp3', '3:51'),
(30, 'Jo Tum Mere Ho', 'Jo Tum Mere Ho', 'Anuv Jain', 'Indie Acoustic', 'Intimate, Tender, Peaceful', 'Hindi', 'Relaxing, Studying, Late Night, Romance', 'An intimate, heartfelt acoustic indie ballad sung with delicate vulnerability and tenderness.', 'dataset/songs/jo_tum_mere_ho.mp3', '4:12'),
(31, 'Kabhii Tumhhe', 'Shershaah', 'Darshan Raval', 'Romantic / Ballad', 'Emotional, Melancholic, Loving', 'Hindi', 'Reflection, Quiet Moments, Romance', 'A touching romantic ballad recounting enduring promises and eternal affection.', 'dataset/songs/kabhii_tumhhe.mp3', '3:50'),
(32, 'Kar Gayi Chull', 'Kapoor & Sons', 'Badshah, Fazilpuria, Sukriti Kakar, Neha Kakkar', 'Party / Hip-Hop', 'Bouncy, Fun, Energetic', 'Hindi', 'House Party, Dance, Workout', 'A smash-hit club and house party anthem loaded with infectious rap flows and lively beats.', 'dataset/songs/kar_gayi_chull.mp3', '2:22'),
(33, 'Love Is A Waste Of Time', 'PK', 'Sonu Nigam, Shreya Ghoshal, Shantanu Moitra', 'Comedy / Romantic', 'Lighthearted, Playful, Quirky', 'Hindi', 'Casual, Relaxing, Commute', 'A lighthearted, witty Bhojpuri-flavored romantic number with innocent humor and charm.', 'dataset/songs/love_is_a_waste_of_time.mp3', '4:30'),
(34, 'Love You Zindagi', 'Dear Zindagi', 'Jasleen Royal, Amit Trivedi', 'Feel Good / Pop', 'Joyful, Carefree, Optimistic', 'Hindi', 'Morning, Walking, Self-Care, Smiling', 'A delightful feel-good anthem celebrating life, small joys, and loving oneself every day.', 'dataset/songs/love_you_zindagi.mp3', '3:53'),
(35, 'Malhari', 'Bajirao Mastani', 'Vishal Dadlani, Sanjay Leela Bhansali', 'Folk / War Dance', 'Fierce, Triumphant, Electrifying', 'Hindi / Marathi', 'Workout, Motivation, Celebration, Victory', 'A ferocious, victorious warrior dance track with thumping traditional percussion and raw power.', 'dataset/songs/malhari.mp3', '4:04'),
(36, 'Mat Aazma Re', 'Murder 3', 'KK, Pritam', 'Romantic Rock', 'Intense, Emotional, Longing', 'Hindi', 'Late Night Drive, Romance, Reflection', 'A powerful romantic rock ballad expressing raw emotional vulnerability and pleading love.', 'dataset/songs/mat_aazma_re.mp3', '4:08'),
(37, 'Nashe Si Chadh Gayi', 'Befikre', 'Arijit Singh, Vishal-Shekhar', 'Pop / Dance', 'Groovy, Romantic, Carefree', 'Hindi / French', 'Dancing, Road Trip, Party', 'A smooth, addictive Parisian dance track about dizzying romantic infatuation.', 'dataset/songs/nashe_si_chadh_gayi.mp3', '3:58'),
(38, 'Pehli Nazar Mein', 'Race', 'Atif Aslam, Pritam', 'Romantic / Pop', 'Mesmerizing, Romantic, Nostalgic', 'Hindi', 'Romance, Candlelight, Road Trip', 'A timeless love anthem celebrating the magical sensation of love at first sight.', 'dataset/songs/pehli_nazar_mein.mp3', '5:13'),
(39, 'Raataan Lambiyan', 'Shershaah', 'Jubin Nautiyal, Asees Kaur, Tanishk Bagchi', 'Romantic / Acoustic', 'Tender, Romantic, Warm', 'Hindi / Punjabi', 'Romance, Evening, Star Gazing', 'A tender, soothing melody portraying long sleepless nights thinking about one''s beloved.', 'dataset/songs/raataan_lambiyan.mp3', '3:50'),
(40, 'Ranjha', 'Shershaah', 'Jasleen Royal, B Praak', 'Soulful / Folk Romantic', 'Emotional, Melancholic, Deep', 'Hindi / Punjabi', 'Quiet Evening, Reflection, Romance', 'A deeply emotional, folk-infused ballad capturing the ache of parting and deep longing.', 'dataset/songs/ranjha.mp3', '3:49'),
(41, 'Sachi Muchi', 'Sultan', 'Mohit Chauhan, Harshdeep Kaur, Vishal-Shekhar', 'Folk / Romantic', 'Charming, Innocent, Cheerful', 'Hindi', 'Casual, Relaxing, Morning', 'A charming rustic love duet filled with innocent confessions, gentle rhythm, and warmth.', 'dataset/songs/sachi_muchi.mp3', '4:00'),
(42, 'Shaam Shaandaar', 'Shaandaar', 'Amit Trivedi', 'Party / Electro-Folk', 'Ecstatic, Lively, Celebratory', 'Hindi', 'Evening Party, Celebration, Dance', 'An electric evening party number setting the stage for a glamorous, unforgettable night.', 'dataset/songs/shaam_shaandaar.mp3', '3:58'),
(43, 'Sultan (Title Track)', 'Sultan', 'Sukhwinder Singh, Shadab Faridi, Vishal-Shekhar', 'Motivational / Desi Hip-Hop', 'Fearless, Inspiring, High Adrenaline', 'Hindi / Haryanvi', 'Workout, Motivation, Gym, Running', 'A stirring motivational title track honoring the fighting spirit of rising back up against all odds.', 'dataset/songs/sultan_title_track.mp3', '4:40'),
(44, 'Tera Hone Laga Hoon', 'Ajab Prem Ki Ghazab Kahani', 'Atif Aslam, Alisha Chinai, Pritam', 'Romantic Pop', 'Dreamy, Sweet, Romantic', 'Hindi / English', 'Romance, Road Trip, Relaxing', 'A dreamy romantic classic describing the surreal feeling of falling helplessly in love.', 'dataset/songs/tera_hone_laga_hoon.mp3', '5:00'),
(45, 'Kho Gaye Hum Kahan', 'Kho Gaye Hum Kahan', 'Achint, Javed Akhtar', 'Indie / Mellow', 'Reflective, Mellow, Modern', 'Hindi', 'Late Night, City Drive, Studying', 'A contemporary, contemplative indie song capturing youth, digital connection, and finding oneself.', 'dataset/songs/kho_gaye_hum_kahan.mp3', '3:38'),
(46, 'Tu Hai Kahan', 'Tu Hai Kahan', 'AUR', 'Indie Pop / Soul', 'Melancholic, Atmospheric, Romantic', 'Urdu / Hindi', 'Late Night, Rain, Healing', 'A viral soulful indie track soaked in longing, atmospheric synths, and emotional resonance.', 'dataset/songs/tu_hai_kahan.mp3', '4:23'),
(47, 'Tum Se Hi', 'Jab We Met', 'Mohit Chauhan, Pritam', 'Romantic Acoustic', 'Warm, Gentle, Nostalgic, Loving', 'Hindi', 'Rain, Travel, Romance, Relaxing', 'An evergreen romantic acoustic masterpiece about how every breath and rain shower revolves around one person.', 'dataset/songs/tum_se_hi.mp3', '5:24'),
(48, 'Shri Hanuman Chalisa', 'Hanuman Chalisa', 'Aditya Jyotish', 'Devotional / Sacred', 'Peaceful, Spiritual, Courageous', 'Awadhi / Hindi', 'Prayer, Morning, Meditation', 'Sacred forty-verse hymn extolling the strength, wisdom, and divine blessings of Lord Hanuman.', 'dataset/songs/shri_hanuman_chalisa.mp3', '9:42')
ON DUPLICATE KEY UPDATE 
    title = VALUES(title),
    movie = VALUES(movie),
    artist = VALUES(artist),
    genre = VALUES(genre),
    mood = VALUES(mood),
    language = VALUES(language),
    activity = VALUES(activity),
    description = VALUES(description),
    audio_url = VALUES(audio_url),
    duration = VALUES(duration);
