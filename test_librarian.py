import unittest
from unittest import mock

import librarian


def _item(quality, quality_score=0.9):
    return {
        "quality": quality,
        "quality_score": quality_score,
        "size": 1_000_000,
        "duration": 60,
        "title": "",
    }


def _group(quality, items, score=1.0):
    return {
        "quality": quality,
        "items": items,
        "score": score,
        "item_count": len(items),
    }


class _State:
    def __init__(self):
        self.status = None

    def set_status(self, key, status, fmt=None, kbps=None):
        self.status = status


class _Soulbeet:
    def __init__(self, groups):
        self.groups = groups
        self.searched_tracks = []
        self.queued_items = []

    def search_album(self, artist, query):
        return [{"id": "release-id"}]

    def album(self, album_id):
        return {"tracks": [{"title": f"Track {i}"} for i in range(3)]}

    def start_search(self, album, tracks):
        self.searched_tracks = tracks
        return "search-id"

    def poll(self, search_id):
        return {"groups": self.groups}

    def queue(self, items):
        self.queued_items = items


class AlbumCompletenessTests(unittest.TestCase):
    def test_incomplete_flac_is_skipped_for_a_complete_lossy_source(self):
        groups = [
            _group("flac", [_item("flac") for _ in range(2)]),
            _group("mp3", [_item("mp3") for _ in range(3)], score=0.5),
        ]

        status, items, _ = librarian.pick_by_quality_ladder(
            groups, expected_track_count=3)

        self.assertEqual(status, "queued_lossy")
        self.assertEqual(len(items), 3)

    def test_only_incomplete_sources_are_not_queued(self):
        groups = [_group("flac", [_item("flac") for _ in range(2)])]

        status, items, info = librarian.pick_by_quality_ladder(
            groups, expected_track_count=3)

        self.assertEqual((status, items, info), ("incomplete", [], None))

    def test_track_candidates_keep_existing_unbounded_selection(self):
        groups = [_group("flac", [_item("flac")])]

        status, items, _ = librarian.pick_by_quality_ladder(groups)

        self.assertEqual(status, "queued_flac")
        self.assertEqual(len(items), 1)

    def test_candidate_uses_metadata_tracklist_and_does_not_queue_partial_album(self):
        state = _State()
        sb = _Soulbeet([_group("flac", [_item("flac") for _ in range(2)])])
        row = ("candidate-key", "Artist", "Album", "album")

        with mock.patch.object(librarian, "navidrome_album_exists", return_value=False):
            status = librarian.process_candidate(
                state, sb, {"SOULBEET_USER": "user", "SOULBEET_PASS": "pass"}, row)

        self.assertEqual(status, "incomplete")
        self.assertEqual(state.status, "incomplete")
        self.assertEqual(len(sb.searched_tracks), 3)
        self.assertEqual(sb.queued_items, [])


if __name__ == "__main__":
    unittest.main()
