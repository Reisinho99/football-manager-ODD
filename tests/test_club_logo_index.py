"""Isolated regression tests; no installed graphics or FM process required."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tools.club_logo_index import index_club_logos


class ClubLogoIndexTests(unittest.TestCase):
    def test_recursive_country_configs_and_uid_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            country = root / "Portugal" / "clubs"
            country.mkdir(parents=True)
            (country / "123.png").write_bytes(b"png")
            (country / "config.xml").write_text(
                '<list><record from="123" to="graphics/pictures/club/123/logo"/></list>',
                encoding="utf-8")
            index = index_club_logos(root)
            self.assertEqual(index.resolve(123), country / "123.png")
            self.assertIsNone(index.resolve(124))
            self.assertEqual(index.config_files, 1)

    def test_conflicting_mapping_is_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for country in ("A", "B"):
                folder = root / country
                folder.mkdir()
                (folder / "123.png").write_bytes(b"png")
                (folder / "config.xml").write_text(
                    '<list><record from="123" to="graphics/pictures/club/123/logo"/></list>',
                    encoding="utf-8")
            index = index_club_logos(root)
            self.assertIn("123", index.conflicts)
            self.assertIsNone(index.resolve(123))

    def test_source_mismatch_and_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "456.png").write_bytes(b"png")
            (root / "config.xml").write_text(
                '<list><record from="456" to="graphics/pictures/club/123/logo"/>'
                '<record from="../123" to="graphics/pictures/club/123/logo"/></list>',
                encoding="utf-8")
            index = index_club_logos(root)
            self.assertIsNone(index.resolve(123))
            self.assertEqual(index.rejected_records, 2)

    def test_bad_xml_does_not_abort_other_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config.xml").write_text("<broken", encoding="utf-8")
            index = index_club_logos(root)
            self.assertEqual(index.config_files, 1)
            self.assertEqual(index.rejected_records, 1)


if __name__ == "__main__":
    unittest.main()
