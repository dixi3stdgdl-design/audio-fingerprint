from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional, Protocol


class DatabaseProtocol(Protocol):
    def lookup_hash(self, hash_val: int) -> list[dict[str, Any]]: ...
    def get_song_info(self, song_id: int) -> Optional[dict[str, Any]]: ...


class FingerprintMatcher:
    def __init__(self, max_offset_tolerance: float = 5.0, min_matches: int = 5) -> None:
        self.max_offset_tolerance = max_offset_tolerance
        self.min_matches = min_matches

    def match(
        self,
        query_fingerprints: dict[str, Any],
        database: DatabaseProtocol,
    ) -> list[dict[str, Any]]:
        query_hashes = query_fingerprints['hashes']
        candidates: dict[int, list[dict[str, Any]]] = defaultdict(list)

        for fp in query_hashes:
            matches = database.lookup_hash(fp['hash'])
            for match in matches:
                offset = match['time'] - fp['time1']
                candidates[match['song_id']].append({
                    'query_time': fp['time1'],
                    'db_time': match['time'],
                    'offset': offset,
                })

        results: list[dict[str, Any]] = []
        for song_id, matches in candidates.items():
            result = self._evaluate_matches(song_id, matches, database)
            if result:
                results.append(result)

        results.sort(key=lambda x: x['score'], reverse=True)
        return results

    def _evaluate_matches(
        self,
        song_id: int,
        matches: list[dict[str, Any]],
        database: DatabaseProtocol,
    ) -> Optional[dict[str, Any]]:
        if len(matches) < self.min_matches:
            return None

        offset_groups: dict[float, list[dict[str, Any]]] = defaultdict(list)
        for match in matches:
            offset_key = round(match['offset'], 1)
            offset_groups[offset_key].append(match)

        best_offset: Optional[float] = None
        best_count = 0

        for offset, group in offset_groups.items():
            if len(group) > best_count:
                best_count = len(group)
                best_offset = offset

        if best_offset is None:
            return None

        consistent_matches = [
            m for m in matches
            if abs(m['offset'] - best_offset) <= self.max_offset_tolerance
        ]

        song_info = database.get_song_info(song_id)
        total_hashes = song_info['hash_count'] if song_info else 100000
        expected_random = len(matches) / max(total_hashes, 1)

        confidence = len(consistent_matches) / max(expected_random, 0.001)
        confidence = min(confidence / 100, 1.0)

        return {
            'song_id': song_id,
            'song_name': song_info['name'] if song_info else f"Song {song_id}",
            'score': len(consistent_matches),
            'confidence': confidence,
            'offset': best_offset,
            'total_matches': len(matches),
            'consistent_matches': len(consistent_matches),
        }

    def get_best_match(
        self,
        query_fingerprints: dict[str, Any],
        database: DatabaseProtocol,
    ) -> Optional[dict[str, Any]]:
        results = self.match(query_fingerprints, database)
        if results:
            return results[0]
        return None
