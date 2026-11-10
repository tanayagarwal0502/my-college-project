"""
Generate 10 distinct, pleasant, non-copyrighted instrumental preview tracks
for the 10 Bollywood songs in the demo, matching their respective moods and genres.
"""

import os
import wave
import struct
import math

SAMPLE_RATE = 22050  # 22.05 kHz for compact file size and clear sound

def note_freq(note_name):
    """Convert note name like 'C4', 'A#4', 'Bb3' to frequency in Hz."""
    note_name = note_name.replace('Bb', 'A#').replace('Db', 'C#').replace('Eb', 'D#').replace('Gb', 'F#').replace('Ab', 'G#')
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    name = note_name[:-1].upper()
    octave = int(note_name[-1])
    idx = notes.index(name)
    semitones = (octave - 4) * 12 + (idx - 9)
    return 440.0 * (2.0 ** (semitones / 12.0))

def generate_track(filename, duration, pattern_func):
    """Generate a 16-bit mono WAV file with given pattern function."""
    out_dir = os.path.join(os.path.dirname(__file__), "static", "audio")
    os.makedirs(out_dir, exist_ok=True)
    filepath = os.path.join(out_dir, filename)

    total_samples = int(SAMPLE_RATE * duration)
    wav_file = wave.open(filepath, 'w')
    wav_file.setnchannels(1)  # mono
    wav_file.setsampwidth(2)  # 16-bit
    wav_file.setframerate(SAMPLE_RATE)

    buffer = bytearray()
    for i in range(total_samples):
        t = i / SAMPLE_RATE
        val = pattern_func(t, duration)
        # Clip to -1.0 to 1.0
        val = max(-1.0, min(1.0, val))
        sample = int(val * 32767.0 * 0.8)  # Headroom to avoid clipping
        buffer.extend(struct.pack('<h', sample))

    wav_file.writeframes(buffer)
    wav_file.close()
    print(f"Generated preview audio: {filename} ({duration:.1f}s)")

# 1. Kesariya (Romantic, Warm, Happy) - Warm acoustic chord arpeggios
def synth_kesariya(t, dur):
    # Progression: C - G - Am - F
    prog = [
        ['C4', 'E4', 'G4', 'C5'],
        ['G3', 'B3', 'D4', 'G4'],
        ['A3', 'C4', 'E4', 'A4'],
        ['F3', 'A3', 'C4', 'F4']
    ]
    chord_idx = int(t / 2.0) % len(prog)
    chord = prog[chord_idx]
    sub_t = t % 0.5
    note_idx = int((t % 2.0) / 0.5)
    f = note_freq(chord[note_idx])
    
    # Soft pluck envelope
    env = math.exp(-sub_t * 5.0)
    # Warm harmonic overtone
    sig = (math.sin(2 * math.pi * f * t) + 
           0.4 * math.sin(2 * math.pi * f * 2 * t) + 
           0.15 * math.sin(2 * math.pi * f * 3 * t)) * env
    return sig * 0.7

# 2. Apna Bana Le (Soulful, Romantic, Comforting) - Soulful slow minor-major melody
def synth_apna_bana_le(t, dur):
    # Progression: Dm - Bb - F - C
    prog = [
        ['D4', 'F4', 'A4'],
        ['Bb3', 'D4', 'F4'],
        ['F3', 'A3', 'C4'],
        ['C4', 'E4', 'G4']
    ]
    chord_idx = int(t / 2.5) % len(prog)
    chord = prog[chord_idx]
    sub_t = t % 2.5
    # Smooth pad + soft melody
    pad = sum(math.sin(2 * math.pi * note_freq(n) * t) for n in chord) / len(chord)
    melody_notes = ['A4', 'F4', 'G4', 'E4']
    m_f = note_freq(melody_notes[chord_idx])
    m_env = math.sin(math.pi * (sub_t / 2.5))
    melody = math.sin(2 * math.pi * m_f * t) * m_env
    return (pad * 0.4 + melody * 0.5)

# 3. Zinda (Motivational, Energetic Workout) - Fast driving beat & synth bass
def synth_zinda(t, dur):
    bpm = 135
    beat = (t * (bpm / 60.0)) % 1.0
    beat_idx = int(t * (bpm / 60.0)) % 4
    # Kick on every beat
    kick_env = math.exp(-beat * 15.0)
    kick = math.sin(2 * math.pi * (120.0 * math.exp(-beat * 20.0) + 40.0) * t) * kick_env
    # Bass line
    bass_notes = ['D2', 'D2', 'F2', 'G2']
    b_f = note_freq(bass_notes[beat_idx])
    bass = (math.sin(2 * math.pi * b_f * t) + 0.3 * math.sin(2 * math.pi * b_f * 2 * t)) * (1.0 - beat * 0.6)
    # Hi-hat on 8ths
    hat_sub = (t * (bpm / 30.0)) % 1.0
    hat_noise = math.sin(t * 15000.0) * math.exp(-hat_sub * 25.0) * 0.15
    return (kick * 0.6 + bass * 0.35 + hat_noise)

# 4. Kar Har Maidaan Fateh (Powerful, Determined, Inspirational) - Marching rising chords
def synth_kar_har_maidaan(t, dur):
    step = int(t / 1.5) % 4
    chords = [
        ['D3', 'A3', 'D4'],
        ['G3', 'B3', 'D4'],
        ['A3', 'C#4', 'E4'],
        ['B3', 'D4', 'F#4']
    ]
    cur_chord = chords[step]
    sub_t = t % 1.5
    brass = sum(math.sin(2 * math.pi * note_freq(n) * t) + 0.3 * math.sin(2 * math.pi * note_freq(n) * 2 * t) for n in cur_chord) / 3.0
    # Pulse
    pulse = math.sin(2 * math.pi * 4.0 * t) * 0.2 + 0.8
    drum = math.sin(2 * math.pi * 60 * t) * math.exp(-(t % 0.75) * 10.0)
    return (brass * pulse * 0.5 + drum * 0.4)

# 5. Ilahi (Travel, Happy, Adventurous) - Cheerful acoustic strumming
def synth_ilahi(t, dur):
    # Upbeat G - Em - C - D
    chords = [['G3', 'B3', 'D4', 'G4'], ['E3', 'G3', 'B3', 'E4'], ['C3', 'E3', 'G3', 'C4'], ['D3', 'F#3', 'A3', 'D4']]
    c_idx = int(t / 1.8) % 4
    chord = chords[c_idx]
    strum_t = (t * 4.0) % 1.0
    pluck_idx = int(t * 8.0) % 4
    f = note_freq(chord[pluck_idx])
    env = math.exp(-strum_t * 6.0)
    return (math.sin(2 * math.pi * f * t) + 0.3 * math.sin(2 * math.pi * f * 2 * t)) * env * 0.7

# 6. Safarnama (Calm, Reflective, Peaceful) - Slow reflective piano/guitar
def synth_safarnama(t, dur):
    chords = [['E3', 'G#3', 'B3'], ['B2', 'D#3', 'F#3'], ['C#3', 'E3', 'G#3'], ['A2', 'C#3', 'E3']]
    idx = int(t / 3.0) % 4
    sub = (t % 1.0)
    chord = chords[idx]
    f = note_freq(chord[int(t * 2.0) % 3])
    env = math.exp(-sub * 2.5)
    return (math.sin(2 * math.pi * f * t) + 0.2 * math.sin(2 * math.pi * f * 3 * t)) * env * 0.6

# 7. Iktara (Indie Romantic, Calm, Peaceful) - Soft acoustic picking
def synth_iktara(t, dur):
    notes = ['F#3', 'A#3', 'C#4', 'F#4', 'C#4', 'A#3']
    idx = int(t * 3.0) % len(notes)
    f = note_freq(notes[idx])
    sub = (t * 3.0) % 1.0
    env = math.exp(-sub * 4.0)
    return (math.sin(2 * math.pi * f * t) + 0.25 * math.sin(2 * math.pi * f * 2 * t)) * env * 0.65

# 8. Kun Faya Kun (Sufi Spiritual, Meditative) - Sacred spiritual harmonium & drone
def synth_kun_faya_kun(t, dur):
    drone = (math.sin(2 * math.pi * note_freq('C3') * t) + 
             math.sin(2 * math.pi * note_freq('G3') * t) * 0.6 +
             math.sin(2 * math.pi * note_freq('C4') * t) * 0.4)
    # Subtle slow flute/harmonium modulation
    mod = math.sin(2 * math.pi * 0.3 * t) * 0.15 + 0.85
    melody_notes = ['C4', 'D#4', 'F4', 'G4', 'A#4', 'G4']
    m_idx = int(t / 2.0) % len(melody_notes)
    m_f = note_freq(melody_notes[m_idx])
    melody = math.sin(2 * math.pi * m_f * t) * 0.4 * (math.sin(math.pi * ((t % 2.0) / 2.0)))
    return (drone * 0.4 * mod + melody * 0.4)

# 9. Aaj Ki Raat (Dance Party, Energetic, Fun) - Pulsing electronic synth dance groove
def synth_aaj_ki_raat(t, dur):
    bpm = 128
    beat = (t * (bpm / 60.0)) % 1.0
    kick = math.sin(2 * math.pi * (140.0 * math.exp(-beat * 18.0) + 45.0) * t) * math.exp(-beat * 12.0)
    # Dance synth chord on offbeats
    offbeat = ((t * (bpm / 60.0)) + 0.5) % 1.0
    syn_env = math.exp(-offbeat * 10.0)
    syn_f = note_freq(['C4', 'D#4', 'G4'][int(t * 2.0) % 3])
    syn = (math.sin(2 * math.pi * syn_f * t) + 0.5 * math.sin(2 * math.pi * syn_f * 2 * t)) * syn_env
    return (kick * 0.65 + syn * 0.35)

# 10. Gallan Goodiyaan (Party / Family, Celebratory) - Festive celebratory rhythm
def synth_gallan_goodiyaan(t, dur):
    bpm = 132
    beat = (t * (bpm / 60.0)) % 1.0
    dhol_bass = math.sin(2 * math.pi * 90.0 * t) * math.exp(-beat * 8.0)
    dhol_treble = math.sin(2 * math.pi * 350.0 * t) * math.exp(-((t * (bpm / 30.0)) % 1.0) * 15.0)
    melody_notes = ['G4', 'B4', 'D5', 'E5']
    m_f = note_freq(melody_notes[int(t * 2.0) % 4])
    lead = math.sin(2 * math.pi * m_f * t) * 0.35
    return (dhol_bass * 0.5 + dhol_treble * 0.3 + lead)

def main():
    tracks = [
        ("kesariya.wav", 18.0, synth_kesariya),
        ("apna_bana_le.wav", 18.0, synth_apna_bana_le),
        ("zinda.wav", 18.0, synth_zinda),
        ("kar_har_maidaan_fateh.wav", 18.0, synth_kar_har_maidaan),
        ("ilahi.wav", 18.0, synth_ilahi),
        ("safarnama.wav", 18.0, synth_safarnama),
        ("iktara.wav", 18.0, synth_iktara),
        ("kun_faya_kun.wav", 18.0, synth_kun_faya_kun),
        ("aaj_ki_raat.wav", 18.0, synth_aaj_ki_raat),
        ("gallan_goodiyaan.wav", 18.0, synth_gallan_goodiyaan),
    ]

    print("Generating 10 audio preview files...")
    for filename, dur, func in tracks:
        generate_track(filename, dur, func)
    print("All 10 preview audio tracks generated successfully!")

if __name__ == "__main__":
    main()
