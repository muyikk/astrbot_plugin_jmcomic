import unittest
from pathlib import Path

from astrbot_plugin_jmcomic.helpers import (
    clean_album_id,
    human_size,
    natural_path_key,
    sanitize_filename,
)


class HelpersTest(unittest.TestCase):
    def test_clean_album_id(self) -> None:
        self.assertEqual(clean_album_id("12345"), "12345")
        self.assertEqual(clean_album_id("JM12345"), "12345")
        self.assertEqual(clean_album_id("jm12345"), "12345")

    def test_clean_album_id_rejects_unsafe_values(self) -> None:
        for raw in ("", "JM", "12/34", "abc"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                clean_album_id(raw)

    def test_sanitize_filename(self) -> None:
        self.assertEqual(sanitize_filename('a/b:c*?"<>|'), "abc")

    def test_natural_path_sort(self) -> None:
        paths = [Path("10.jpg"), Path("2.jpg"), Path("1.jpg")]
        self.assertEqual(
            sorted(paths, key=natural_path_key),
            [Path("1.jpg"), Path("2.jpg"), Path("10.jpg")],
        )

    def test_human_size(self) -> None:
        self.assertEqual(human_size(1024), "1.0 KiB")


if __name__ == "__main__":
    unittest.main()
