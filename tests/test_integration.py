import os
import sys
import tempfile
import numpy as np
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio_processor import AudioProcessor
from fingerprint_generator import FingerprintGenerator
from database import FingerprintDatabase, InMemoryFingerprintDatabase
from matcher import FingerprintMatcher

SR = 22050
DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'demo')
MUSIC_DIR = os.path.join(DEMO_DIR, 'music')
CLIPS_DIR = os.path.join(DEMO_DIR, 'clips')


def _make_wav(path, audio, sr=SR):
    audio_int16 = np.int16(np.clip(audio, -1, 1) * 32767)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_int16.tobytes())


def _create_synthetic_files(directory):
    """Create small synthetic audio files for fast testing."""
    os.makedirs(directory, exist_ok=True)
    sr = SR
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), False)

    # Song A: sine at 440 Hz with 880 Hz harmonics
    song_a = np.sin(2 * np.pi * 440 * t) * 0.3
    song_a += np.sin(2 * np.pi * 880 * t) * 0.2
    song_a += np.sin(2 * np.pi * 1320 * t) * 0.1
    path_a = os.path.join(directory, 'synth_a.wav')
    _make_wav(path_a, song_a)

    # Song B: different frequencies
    song_b = np.sin(2 * np.pi * 523 * t) * 0.3
    song_b += np.sin(2 * np.pi * 659 * t) * 0.2
    song_b += np.sin(2 * np.pi * 784 * t) * 0.1
    path_b = os.path.join(directory, 'synth_b.wav')
    _make_wav(path_b, song_b)

    # Clip from song A: take 1s from the middle
    clip_a = song_a[sr:sr*2]
    path_clip_a = os.path.join(directory, 'clip_from_a.wav')
    _make_wav(path_clip_a, clip_a)

    return path_a, path_b, path_clip_a


def test_full_pipeline():
    """Index songs, query with a clip, verify match is found."""
    print("Testing full pipeline (index → query → match)...")

    processor = AudioProcessor()
    generator = FingerprintGenerator()
    matcher = FingerprintMatcher()
    db = FingerprintDatabase()

    tmpdir = tempfile.mkdtemp()
    try:
        path_a, path_b, clip_path = _create_synthetic_files(tmpdir)

        # Index both songs
        for name, path in [('synth_a', path_a), ('synth_b', path_b)]:
            audio_data = processor.process_file(path)
            fps = generator.process_audio_data(audio_data)
            db.add_song(name, fps)
            print(f"    Indexed: {name} ({len(fps['hashes'])} hashes)")

        stats = db.get_stats()
        assert stats['total_songs'] == 2, f"Expected 2 songs, got {stats['total_songs']}"
        print(f"  DB stats: {stats['total_songs']} songs, {stats['total_hashes']} unique hashes")

        # Query with clip from song A
        audio_data = processor.process_file(clip_path)
        fps = generator.process_audio_data(audio_data)
        print(f"  Query hashes: {len(fps['hashes'])}")

        results = matcher.match(fps, db)
        assert len(results) > 0, "No matches found!"
        best = results[0]
        print(f"  Best match: {best['song_name']} (score={best['score']})")
        assert 'synth_a' in best['song_name'], f"Expected synth_a, got {best['song_name']}"

        print("  Full pipeline: PASSED\n")
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_sqlite_persistence():
    """Test save → reload → query survives round-trip."""
    print("Testing SQLite persistence (save → reload → query)...")

    processor = AudioProcessor()
    generator = FingerprintGenerator()

    tmpdir = tempfile.mkdtemp()
    try:
        db_path = os.path.join(tmpdir, 'test.sqlite')
        audio_path = os.path.join(tmpdir, 'test.wav')

        # Create a small test audio
        t = np.linspace(0, 1, SR, False)
        audio = np.sin(2 * np.pi * 440 * t) * 0.5
        _make_wav(audio_path, audio)

        # Index and save
        db = FingerprintDatabase(db_path)
        audio_data = processor.process_file(audio_path)
        fps = generator.process_audio_data(audio_data)
        song_id = db.add_song("persist_test", fps)
        db.close()
        print(f"  Indexed and saved ({len(fps['hashes'])} hashes)")

        # Reload
        db2 = FingerprintDatabase(db_path)
        info = db2.get_song_info(song_id)
        assert info is not None, "Song not found after reload"
        assert info['name'] == "persist_test"
        print(f"  Reloaded: {info['name']} (hash_count={info['hash_count']})")

        # Hash lookup
        sample_hash = fps['hashes'][0]['hash']
        matches = db2.lookup_hash(sample_hash)
        assert len(matches) > 0, "Hash lookup failed after reload"
        print(f"  Hash lookup: {len(matches)} match(es)")

        # Query with clip
        matcher = FingerprintMatcher()
        results = matcher.match(fps, db2)
        assert len(results) > 0, "No match after reload"
        print(f"  Post-reload match: {results[0]['song_name']} (score={results[0]['score']})")

        db2.close()
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("  SQLite persistence: PASSED\n")


def test_in_memory_fallback():
    """Verify InMemoryFingerprintDatabase still works."""
    print("Testing InMemoryFingerprintDatabase fallback...")

    db = InMemoryFingerprintDatabase()
    fingerprints = {
        'hashes': [
            {'hash': 99999, 'time1': 0.0, 'time2': 0.5},
            {'hash': 88888, 'time1': 1.0, 'time2': 1.5},
        ]
    }

    song_id = db.add_song("Fallback Song", fingerprints)
    assert song_id == 1
    info = db.get_song_info(song_id)
    assert info['name'] == "Fallback Song"

    matches = db.lookup_hash(99999)
    assert len(matches) == 1

    stats = db.get_stats()
    assert stats['total_songs'] == 1
    print(f"  Stats: {stats}")

    print("  InMemoryFingerprintDatabase fallback: PASSED\n")


def run_all_integration_tests():
    print("=" * 60)
    print("AUDIO FINGERPRINT SYSTEM - INTEGRATION TEST SUITE")
    print("=" * 60 + "\n")

    test_full_pipeline()
    test_sqlite_persistence()
    test_in_memory_fallback()

    print("=" * 60)
    print("ALL INTEGRATION TESTS PASSED")
    print("=" * 60)


if __name__ == '__main__':
    run_all_integration_tests()
