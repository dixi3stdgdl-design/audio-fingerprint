from __future__ import annotations

import os
import sys
import argparse
from typing import Any, Optional

from tqdm import tqdm

from audio_processor import AudioProcessor
from fingerprint_generator import FingerprintGenerator
from database import FingerprintDatabase
from matcher import FingerprintMatcher
from utils import print_match_results, print_index_stats, plot_spectrogram

__version__ = "1.1.0"


class FingerprintApp:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self.processor = AudioProcessor()
        self.generator = FingerprintGenerator()
        self.database = FingerprintDatabase(db_path)
        self.matcher = FingerprintMatcher()

    def index_directory(self, directory: str, db_path: Optional[str] = None) -> None:
        audio_files: list[str] = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(('.wav', '.mp3', '.flac', '.ogg')):
                    audio_files.append(os.path.join(root, file))

        if not audio_files:
            print(f"No audio files found in {directory}")
            return

        print(f"Found {len(audio_files)} audio files")

        for file_path in tqdm(audio_files, desc="Indexing"):
            try:
                self._index_file(file_path)
            except Exception as e:
                print(f"Error indexing {file_path}: {e}")

        if db_path:
            self.database.save(db_path)
            print(f"\nDatabase saved to {db_path}")

        print_index_stats(self.database.get_stats())

    def _index_file(self, file_path: str) -> None:
        audio_data = self.processor.process_file(file_path)
        fingerprints = self.generator.process_audio_data(audio_data)
        song_name = os.path.splitext(os.path.basename(file_path))[0]
        self.database.add_song(song_name, fingerprints)

    def identify_file(self, file_path: str, db_path: Optional[str] = None) -> Optional[dict[str, Any]]:
        if db_path and os.path.exists(db_path):
            self.database.load(db_path)

        if not self.database.get_all_songs():
            print("Database is empty. Index some songs first.")
            return None

        print(f"Processing {file_path}...")
        audio_data = self.processor.process_file(file_path)
        fingerprints = self.generator.process_audio_data(audio_data)

        print(f"Generated {len(fingerprints['hashes'])} hashes")
        print("Searching for matches...")

        results = self.matcher.match(fingerprints, self.database)
        print_match_results(results)

        return results

    def visualize_file(self, file_path: str) -> None:
        print(f"Processing {file_path}...")
        audio_data = self.processor.process_file(file_path)

        print(f"Detected {len(audio_data['peaks'])} peaks")
        plot_spectrogram(audio_data)


def _print_stats(db_path: str) -> None:
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)

    db = FingerprintDatabase(db_path)
    stats = db.get_stats()
    db_size = os.path.getsize(db_path)

    print(f"Database: {db_path}")
    print(f"  Size:          {db_size:,} bytes ({db_size / 1024:.1f} KB)")
    print(f"  Total songs:   {stats['total_songs']}")
    print(f"  Unique hashes: {stats['total_hashes']}")
    print(f"  Hash entries:  {stats['total_entries']}")
    db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fingerprint",
        description="Audio Fingerprint System — index, identify, and visualize audio files.",
        epilog=(
            "Examples:\n"
            "  python fingerprint_app.py index ./music --db songs.db\n"
            "  python fingerprint_app.py identify clip.wav --db songs.db\n"
            "  python fingerprint_app.py visualize song.wav\n"
            "  python fingerprint_app.py --stats --db songs.db"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--version', action='version', version=f'%(prog)s {__version__}',
        help='show program version and exit',
    )
    parser.add_argument(
        '--db', default='fingerprint_db.sqlite',
        help='SQLite database file path (default: fingerprint_db.sqlite)',
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    index_parser = subparsers.add_parser(
        'index',
        help='Index audio files from a directory into the database',
        description='Walk a directory, extract fingerprints from every audio file, and store them in the database.',
    )
    index_parser.add_argument('directory', help='Directory containing audio files to index (recursively)')
    index_parser.add_argument(
        '--db', default='fingerprint_db.sqlite',
        help='SQLite database file path (default: fingerprint_db.sqlite)',
    )

    identify_parser = subparsers.add_parser(
        'identify',
        help='Identify an audio file against the indexed database',
        description='Compare a query audio file against all previously indexed songs and report matches.',
    )
    identify_parser.add_argument('file', help='Audio file to identify')
    identify_parser.add_argument(
        '--db', default='fingerprint_db.sqlite',
        help='SQLite database file path to query against (default: fingerprint_db.sqlite)',
    )

    viz_parser = subparsers.add_parser(
        'visualize',
        help='Show spectrogram and waveform of an audio file',
        description='Process an audio file and display its spectrogram with detected peaks and waveform.',
    )
    viz_parser.add_argument('file', help='Audio file to visualize')

    parser.add_argument(
        '--stats', action='store_true',
        help='Show database statistics and exit',
    )

    args = parser.parse_args()

    if args.stats:
        _print_stats(args.db)
        return

    if not args.command:
        parser.print_help()
        return

    app = FingerprintApp(args.db if hasattr(args, 'db') else None)

    if args.command == 'index':
        app.index_directory(args.directory, args.db)
    elif args.command == 'identify':
        app.identify_file(args.file, args.db)
    elif args.command == 'visualize':
        app.visualize_file(args.file)


if __name__ == '__main__':
    main()
