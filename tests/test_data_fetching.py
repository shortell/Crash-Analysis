from src.data_fetching import is_date_range_valid, get_current_month, get_current_year, fetch_crash_data
import unittest
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../src')))


class TestIsDateRangeValid(unittest.TestCase):
    # def test_start_date_before_earliest(self):
    #     start_month = 7
    #     start_year = 2010
    #     end_month = 7
    #     end_year = 2011
    #     self.assertFalse(is_date_range_valid(
    #         start_month, start_year, end_month, end_year))
    #     self.assertIsNone(fetch_crash_data(
    #         start_month, start_year, end_month, end_year))

    # def test_end_date_before_earliest(self):
    #     start_month = 8
    #     start_year = 2011
    #     end_month = 7
    #     end_year = 2011
    #     self.assertFalse(is_date_range_valid(
    #         start_month, start_year, end_month, end_year))
    #     self.assertIsNone(fetch_crash_data(
    #         start_month, start_year, end_month, end_year))

    # def test_start_date_after_latest(self):
    #     current_month = get_current_month()
    #     current_year = get_current_year()
    #     self.assertFalse(is_date_range_valid(
    #         current_month, current_year, current_month, current_year))
    #     self.assertIsNone(fetch_crash_data(
    #         current_month, current_year, current_month, current_year))

    # def test_end_date_after_latest(self):
    #     current_month = get_current_month()
    #     current_year = get_current_year()
    #     self.assertFalse(is_date_range_valid(
    #         current_month, current_year, current_month + 1, current_year))
    #     self.assertIsNone(fetch_crash_data(
    #         current_month, current_year, current_month + 1, current_year))

    # def test_start_date_equals_end_date(self):
    #     start_month = 8
    #     start_year = 2011
    #     end_month = 8
    #     end_year = 2011
    #     self.assertTrue(is_date_range_valid(
    #         start_month, start_year, end_month, end_year))
    #     self.assertIsNone(fetch_crash_data(
    #         start_month, start_year, end_month, end_year))

    # def test_valid_range(self):
    #     start_month = 8
    #     start_year = 2011
    #     end_month = 9
    #     end_year = 2011
    #     self.assertTrue(is_date_range_valid(
    #         start_month, start_year, end_month, end_year))
    #     self.assertIsNotNone(fetch_crash_data(
    #         start_month, start_year, end_month, end_year))

    # def test_end_date_in_far_future(self):
    #     start_month = 8
    #     start_year = 2011
    #     end_month = 1
    #     end_year = 2100
    #     self.assertFalse(is_date_range_valid(
    #         start_month, start_year, end_month, end_year))
    #     self.assertIsNone(fetch_crash_data(
    #         start_month, start_year, end_month, end_year))

    def test_start_date_in_far_future(self):
        # start_month = 2
        # start_year = 2025
        # end_month = 2
        # end_year = 2025
        # self.assertFalse(is_date_range_valid(
        #     start_month, start_year, end_month, end_year))
        # self.assertIsNone(fetch_crash_data(
        #     start_month, start_year, end_month, end_year))
        pass




if __name__ == "__main__":
    unittest.main()
