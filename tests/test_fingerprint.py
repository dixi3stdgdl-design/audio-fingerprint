import numpy as np
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio_processor import AudioProcessor
from fingerprint_generator import FingerprintGenerator
from database import FingerprintDatabase
from matcher import FingerprintMatcher


def test_audio_processor():
    print("Testing AudioProcessor...")
    processor = AudioProcessor()

    duration = 2.0
    sample_rate = 22050
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio = np.sin(2 * np.pi * 440 * t)

    freqs, times, Sxx = processor.compute_spectrogram(audio)
    assert len(freqs) > 0, "No frequencies detected"
    assert len(times) > 0, "No time steps detected"
    print(f"  Spectrogram shape: {Sxx.shape}")

    peaks = processor.detect_peaks(Sxx)
    assert len(peaks) > 0, "No peaks detected"
    print(f"  Detected {len(peaks)} peaks")

    print("  AudioProcessor: PASSED\n")


def test_fingerprint_generator():
    print("Testing FingerprintGenerator...")
    generator = FingerprintGenerator()

    peaks = [
        {'frequency': 440, 'time': 0.0, 'amplitude': 0.8},
        {'frequency': 880, 'time': 0.5, 'amplitude': 0.9},
        {'frequency': 1320, 'time': 1.0, 'amplitude': 0.7},
    ]

    hashes = generator.generate_hashes(peaks)
    assert len(hashes) > 0, "No hashes generated"
    print(f"  Generated {len(hashes)} hashes from {len(peaks)} peaks")

    for h in hashes[:3]:
        assert 'hash' in h, "Hash missing 'hash' key"
        assert 'freq1' in h, "Hash missing 'freq1' key"
        assert 'freq2' in h, "Hash missing 'freq2' key"
        assert 'time_delta' in h, "Hash missing 'time_delta' key"

    print("  FingerprintGenerator: PASSED\n")


def test_database():
    print("Testing FingerprintDatabase...")
    db = FingerprintDatabase()

    fingerprints = {
        'hashes': [
            {'hash': 12345678, 'time1': 0.0, 'time2': 0.5},
            {'hash': 87654321, 'time1': 1.0, 'time2': 1.5},
        ]
    }

    song_id = db.add_song("Test Song", fingerprints)
    assert song_id == 1, f"Expected song_id 1, got {song_id}"

    info = db.get_song_info(song_id)
    assert info['name'] == "Test Song", "Song name mismatch"
    print(f"  Added song: {info['name']}")

    matches = db.lookup_hash(12345678)
    assert len(matches) == 1, f"Expected 1 match, got {len(matches)}"
    assert matches[0]['song_id'] == song_id
    print(f"  Lookup found {len(matches)} match(es)")

    stats = db.get_stats()
    assert stats['total_songs'] == 1
    print(f"  Stats: {stats}")

    print("  FingerprintDatabase: PASSED\n")


def test_matcher():
    print("Testing FingerprintMatcher...")
    db = FingerprintDatabase()
    matcher = FingerprintMatcher(min_matches=2)

    song_fingerprints = {
        'hashes': [
            {'hash': 111, 'time1': 0.0},
            {'hash': 222, 'time1': 0.5},
            {'hash': 333, 'time1': 1.0},
            {'hash': 444, 'time1': 1.5},
        ]
    }
    db.add_song("Match Song", song_fingerprints)

    query_fingerprints = {
        'hashes': [
            {'hash': 111, 'time1': 0.0},
            {'hash': 222, 'time1': 0.5},
            {'hash': 333, 'time1': 1.0},
            {'hash': 555, 'time1': 2.0},
        ]
    }

    results = matcher.match(query_fingerprints, db)
    assert len(results) > 0, "No matches found"
    assert results[0]['song_name'] == "Match Song"
    print(f"  Best match: {results[0]['song_name']} (score: {results[0]['score']})")

    print("  FingerprintMatcher: PASSED\n")


def run_all_tests():
    print("=" * 50)
    print("AUDIO FINGERPRINT SYSTEM - TEST SUITE")
    print("=" * 50 + "\n")

    test_audio_processor()
    test_fingerprint_generator()
    test_database()
    test_matcher()

    print("=" * 50)
    print("ALL TESTS PASSED")
    print("=" * 50)


if __name__ == '__main__':
    run_all_tests()
