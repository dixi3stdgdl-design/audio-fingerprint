from __future__ import annotations

import json
import os
import shutil
import sqlite3
import threading
from collections import defaultdict
from typing import Any, Optional


class DatabaseCorruptedError(Exception):
    """Raised when the SQLite database is corrupted and cannot be recovered."""


class DatabaseLockedError(Exception):
    """Raised when the database is locked and cannot be accessed after retries."""


class InMemoryFingerprintDatabase:
    """Original in-memory database using defaultdict. Kept as fallback."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        self.hash_table: dict[int, list[dict[str, Any]]] = defaultdict(list)
        self.songs: dict[int, dict[str, Any]] = {}
        self.song_counter: int = 0

    def add_song(self, song_name: str, fingerprints: dict[str, list[dict[str, Any]]]) -> int:
        self.song_counter += 1
        song_id = self.song_counter
        self.songs[song_id] = {
            'name': song_name,
            'hash_count': len(fingerprints['hashes']),
        }

        for fp in fingerprints['hashes']:
            self.hash_table[fp['hash']].append({
                'song_id': song_id,
                'time': fp['time1'],
            })

        return song_id

    def lookup_hash(self, hash_val: int) -> list[dict[str, Any]]:
        return self.hash_table.get(hash_val, [])

    def get_song_info(self, song_id: int) -> Optional[dict[str, Any]]:
        return self.songs.get(song_id, None)

    def get_all_songs(self) -> dict[int, dict[str, Any]]:
        return self.songs.copy()

    def get_stats(self) -> dict[str, int]:
        return {
            'total_songs': len(self.songs),
            'total_hashes': len(self.hash_table),
            'total_entries': sum(len(v) for v in self.hash_table.values()),
        }

    def save(self, path: Optional[str] = None) -> None:
        save_path = path or self.db_path
        if not save_path:
            raise ValueError("No save path specified")

        data = {
            'songs': self.songs,
            'song_counter': self.song_counter,
            'hash_table': {str(k): v for k, v in self.hash_table.items()},
        }

        with open(save_path, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self, path: Optional[str] = None) -> None:
        load_path = path or self.db_path
        if not load_path or not os.path.exists(load_path):
            raise FileNotFoundError(f"Database file not found: {load_path}")

        with open(load_path, 'r') as f:
            data = json.load(f)

        self.songs = data['songs']
        self.song_counter = data['song_counter']
        self.hash_table = defaultdict(list)
        for k, v in data['hash_table'].items():
            self.hash_table[int(k)] = v


class FingerprintDatabase:
    """SQLite-backed fingerprint database with the same interface.

    Supports connection pooling for concurrent access and automatic
    recovery from corrupted databases.
    """

    _pool: dict[str, sqlite3.Connection] = {}
    _pool_lock: threading.Lock = threading.Lock()

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn

        key = self.db_path or ":memory:"

        with FingerprintDatabase._pool_lock:
            if key in FingerprintDatabase._pool:
                self._conn = FingerprintDatabase._pool[key]
            else:
                try:
                    self._conn = self._open_connection(key)
                except sqlite3.DatabaseError as exc:
                    if self.db_path and self.db_path != ":memory:":
                        self._conn = self._try_recover(key, exc)
                    else:
                        raise DatabaseCorruptedError(
                            f"Failed to open database: {exc}"
                        ) from exc
                FingerprintDatabase._pool[key] = self._conn

        return self._conn

    def _open_connection(self, key: str) -> sqlite3.Connection:
        if key == ":memory:":
            conn = sqlite3.connect(":memory:")
        else:
            conn = sqlite3.connect(key, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    def _try_recover(self, key: str, original_error: Exception) -> sqlite3.Connection:
        backup_path = key + ".backup"
        try:
            shutil.copy2(key, backup_path)
        except OSError:
            pass

        corrupted_path = key + ".corrupted"
        try:
            os.rename(key, corrupted_path)
        except OSError:
            try:
                os.remove(key)
            except OSError:
                pass

        try:
            conn = self._open_connection(key)
            self._ensure_db_on(conn)
            return conn
        except Exception:
            if os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, key)
                    conn = self._open_connection(key)
                    self._ensure_db_on(conn)
                    return conn
                except Exception:
                    pass
            raise DatabaseCorruptedError(
                f"Database is corrupted and recovery failed: {original_error}"
            ) from original_error

    def _ensure_db_on(self, conn: sqlite3.Connection) -> None:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS songs (
                song_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                hash_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS hash_entries (
                hash_val INTEGER NOT NULL,
                song_id INTEGER NOT NULL,
                time_val REAL NOT NULL,
                FOREIGN KEY (song_id) REFERENCES songs(song_id)
            );
            CREATE INDEX IF NOT EXISTS idx_hash ON hash_entries(hash_val);
            CREATE INDEX IF NOT EXISTS idx_hash_song ON hash_entries(hash_val, song_id);
        """)
        conn.commit()

    def _ensure_db(self) -> None:
        conn = self._get_conn()
        self._ensure_db_on(conn)

    def add_song(self, song_name: str, fingerprints: dict[str, list[dict[str, Any]]]) -> int:
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO songs (name, hash_count) VALUES (?, ?)",
                (song_name, len(fingerprints['hashes'])),
            )
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower():
                raise DatabaseLockedError(
                    "Database is locked. Please try again."
                ) from exc
            raise

        song_id = cursor.lastrowid

        entries = []
        for fp in fingerprints['hashes']:
            entries.append((fp['hash'], song_id, fp['time1']))

        try:
            conn.executemany(
                "INSERT INTO hash_entries (hash_val, song_id, time_val) VALUES (?, ?, ?)",
                entries,
            )
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower():
                raise DatabaseLockedError(
                    "Database is locked. Please try again."
                ) from exc
            raise

        conn.commit()
        return song_id

    def lookup_hash(self, hash_val: int) -> list[dict[str, Any]]:
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT song_id, time_val FROM hash_entries WHERE hash_val = ?",
                (hash_val,),
            )
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower():
                raise DatabaseLockedError(
                    "Database is locked. Please try again."
                ) from exc
            raise
        return [{'song_id': row['song_id'], 'time': row['time_val']} for row in cursor]

    def get_song_info(self, song_id: int) -> Optional[dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT name, hash_count FROM songs WHERE song_id = ?",
            (song_id,),
        )
        row = cursor.fetchone()
        if row:
            return {'name': row['name'], 'hash_count': row['hash_count']}
        return None

    def get_all_songs(self) -> dict[int, dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.execute("SELECT song_id, name, hash_count FROM songs")
        return {
            row['song_id']: {'name': row['name'], 'hash_count': row['hash_count']}
            for row in cursor
        }

    def get_stats(self) -> dict[str, int]:
        conn = self._get_conn()
        songs = conn.execute("SELECT COUNT(*) as cnt FROM songs").fetchone()['cnt']
        hashes = conn.execute(
            "SELECT COUNT(DISTINCT hash_val) as cnt FROM hash_entries"
        ).fetchone()['cnt']
        entries = conn.execute("SELECT COUNT(*) as cnt FROM hash_entries").fetchone()['cnt']
        return {
            'total_songs': songs,
            'total_hashes': hashes,
            'total_entries': entries,
        }

    def save(self, path: Optional[str] = None) -> None:
        save_path = path or self.db_path
        if not save_path:
            raise ValueError("No save path specified")
        if self._conn:
            self._conn.commit()
        if save_path != self.db_path and save_path != ":memory:":
            if self.db_path and self.db_path != ":memory:":
                shutil.copy2(self.db_path, save_path)
            else:
                new_conn = sqlite3.connect(save_path)
                self._conn.backup(new_conn)
                new_conn.close()

    def load(self, path: Optional[str] = None) -> None:
        load_path = path or self.db_path
        if not load_path or not os.path.exists(load_path):
            raise FileNotFoundError(f"Database file not found: {load_path}")
        if self._conn:
            self._conn.close()
            self._conn = None
        self.db_path = load_path
        self._get_conn()
        self._ensure_db()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            key = self.db_path or ":memory:"
            with FingerprintDatabase._pool_lock:
                FingerprintDatabase._pool.pop(key, None)
            self._conn = None

    def __del__(self) -> None:
        self.close()
