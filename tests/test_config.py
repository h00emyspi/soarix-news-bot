import unittest

from app.config import _safe_int, _validate_hhmm


class TestConfig(unittest.TestCase):
    def test_validate_hhmm_filters_invalid_values(self) -> None:
        got = _validate_hhmm(["09:00", "9:aa", "25:00", "18:30", "xx", "00:00"])
        self.assertEqual(got, ["09:00", "18:30", "00:00"])

    def test_safe_int_fallback(self) -> None:
        self.assertEqual(_safe_int("12", 6), 12)
        self.assertEqual(_safe_int("abc", 6), 6)


if __name__ == "__main__":
    unittest.main()
