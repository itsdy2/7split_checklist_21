import unittest
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic import Logic
from model import ModelSetting, StockScreeningResult, ScreeningHistory

class TestLogic(unittest.TestCase):

    def setUp(self):
        """Set up a mock database and other initializations."""
        self.db_session_patch = patch('framework.db.session')
        self.mock_db_session = self.db_session_patch.start()

        # Mock the query method and its chained calls
        self.mock_query = self.mock_db_session.query.return_value
        self.mock_filter_by = self.mock_query.filter_by.return_value
        self.mock_first = self.mock_filter_by.first.return_value
        self.mock_count = self.mock_filter_by.count.return_value = 0

    def tearDown(self):
        """Clean up after tests."""
        self.db_session_patch.stop()

    @patch('logic.DataCollector')
    @patch('logic.Notifier')
    def test_start_screening(self, MockNotifier, MockDataCollector):
        """Test the main screening process."""
        # Arrange
        mock_collector_instance = MockDataCollector.return_value
        mock_collector_instance.get_all_tickers.return_value = [
            {'code': '005930', 'name': 'Samsung Electronics', 'market': 'KOSPI'}
        ]
        mock_collector_instance.get_market_data.return_value = {'market_cap': 500000000000, 'per': 15, 'pbr': 1.5, 'div_yield': 2.5}
        mock_collector_instance.get_financial_data.return_value = {'debt_ratio': 50, 'roe_avg_3y': 20}
        mock_collector_instance.get_disclosure_info.return_value = {'has_cb_bw': False, 'has_paid_increase': False}
        mock_collector_instance.get_major_shareholder.return_value = 40.0

        # Mock settings
        with patch.object(Logic, 'get_setting', side_effect=lambda key: {'dart_api_key': 'test_key'}.get(key, 'False')):
            # Act
            result = Logic.start_screening(strategy_id='seven_split_21')

            # Assert
            self.assertTrue(result['success'])
            self.assertEqual(result['total_stocks'], 1)
            self.assertEqual(result['passed_stocks'], 0) # Based on the mock data, it should not pass
            self.assertIn('execution_time', result)

if __name__ == '__main__':
    unittest.main()