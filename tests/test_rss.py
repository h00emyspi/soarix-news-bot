import unittest

from app.rss import NewsItem, canonicalize_link


class TestRSS(unittest.TestCase):
    def test_canonicalize_link_removes_tracking(self) -> None:
        link = "https://Example.com/path/?utm_source=x&id=42&fbclid=abc"
        self.assertEqual(canonicalize_link(link), "https://example.com/path?id=42")

    def test_newsitem_sort_key_shape(self) -> None:
        # sanity check that timestamps can drive sorting semantics in fetch pipeline
        old = NewsItem("a", "https://a", "", "s", "", 1)
        new = NewsItem("b", "https://b", "", "s", "", 2)
        self.assertGreater(new.published_ts, old.published_ts)


if __name__ == "__main__":
    unittest.main()
