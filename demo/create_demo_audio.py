import numpy as np
import struct
import wave
import os


def create_demo_audio():
    demo_dir = os.path.dirname(os.path.abspath(__file__))
    music_dir = os.path.join(demo_dir, 'music')
    clips_dir = os.path.join(demo_dir, 'clips')

    os.makedirs(music_dir, exist_ok=True)
    os.makedirs(clips_dir, exist_ok=True)

    print("Creating demo audio files...")

    song1 = create_song_1()
    save_wav(song1, os.path.join(music_dir, 'song1_tech_beat.wav'))
    print("  Created song1_tech_beat.wav")

    song2 = create_song_2()
    save_wav(song2, os.path.join(music_dir, 'song2_jazz_melody.wav'))
    print("  Created song2_jazz_melody.wav")

    song3 = create_song_3()
    save_wav(song3, os.path.join(music_dir, 'song3_ambient_pad.wav'))
    print("  Created song3_ambient_pad.wav")

    sr = 22050
    clip1 = song1[5 * sr:10 * sr]
    save_wav(clip1, os.path.join(clips_dir, 'clip_from_song1.wav'))
    print("  Created clip_from_song1.wav (5s from song1)")

    clip2 = song2[3 * sr:8 * sr]
    save_wav(clip2, os.path.join(clips_dir, 'clip_from_song2.wav'))
    print("  Created clip_from_song2.wav (5s from song2)")

    print(f"\nDemo files created in {demo_dir}")


def save_wav(audio, path, sample_rate=22050):
    audio = audio / np.max(np.abs(audio))
    audio_int16 = np.int16(audio * 32767)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())


def tone(freq, duration, sample_rate=22050):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    return np.sin(2 * np.pi * freq * t)


def create_song_1():
    sr = 22050
    duration = 30
    audio = np.zeros(sr * duration)

    for i in range(20):
        freq = 220 * (2 ** (i % 12 / 12))
        t_pos = int(i * 1.5 * sr)
        t_len = int(0.5 * sr)
        if t_pos + t_len < len(audio):
            audio[t_pos:t_pos + t_len] += tone(freq, 0.5, sr) * 0.3

    bass_freqs = [55, 55, 82.5, 55]
    for i, freq in enumerate(bass_freqs):
        t_pos = int(i * 0.75 * sr)
        t_len = int(0.75 * sr)
        if t_pos + t_len < len(audio):
            audio[t_pos:t_pos + t_len] += tone(freq, 0.75, sr) * 0.5

    return audio


def create_song_2():
    sr = 22050
    duration = 30
    audio = np.zeros(sr * duration)

    melody_notes = [440, 494, 523, 587, 659, 587, 523, 494]
    for i, freq in enumerate(melody_notes):
        t_pos = int(i * sr)
        t_len = int(sr)
        if t_pos + t_len < len(audio):
            audio[t_pos:t_pos + t_len] += tone(freq, 1.0, sr) * 0.25

    chords = [
        [262, 330, 392],
        [294, 370, 440],
        [330, 415, 494],
        [349, 440, 523]
    ]
    for i, freqs in enumerate(chords):
        for freq in freqs:
            t_pos = int(i * 2 * sr)
            t_len = int(2 * sr)
            if t_pos + t_len < len(audio):
                audio[t_pos:t_pos + t_len] += tone(freq, 2.0, sr) * 0.15

    return audio


def create_song_3():
    sr = 22050
    duration = 30
    audio = np.zeros(sr * duration)

    pad_freqs = [130.81, 164.81, 196.00, 220.00]
    for i, freq in enumerate(pad_freqs):
        t_pos = int(i * 6 * sr)
        t_len = int(8 * sr)
        if t_pos + t_len < len(audio):
            audio[t_pos:t_pos + t_len] += tone(freq, 8.0, sr) * 0.2

    np.random.seed(42)
    for i in range(30):
        freq = 200 + np.random.randint(0, 400)
        t_pos = int(i * sr)
        t_len = int(0.2 * sr)
        if t_pos + t_len < len(audio):
            audio[t_pos:t_pos + t_len] += tone(freq, 0.2, sr) * 0.1

    return audio


if __name__ == '__main__':
    create_demo_audio()
