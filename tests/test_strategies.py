import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategies import get_strategy

class TestStrategies(unittest.TestCase):

    def test_get_all_strategies(self):
        """Test that all strategies can be loaded."""
        from strategies import get_all_strategies
        all_strategies = get_all_strategies()
        self.assertIsInstance(all_strategies, dict)
        self.assertGreater(len(all_strategies), 0)

    def test_apply_filters(self):
        """Test that the apply_filters method of each strategy returns the correct format."""
        from strategies import get_all_strategies
        all_strategies = get_all_strategies()

        mock_stock_data = {
            'code': '005930', 'name': 'Samsung Electronics', 'market': 'KOSPI',
            'market_cap': 500000000000, 'per': 15, 'pbr': 1.5, 'div_yield': 2.5,
            'debt_ratio': 50, 'roe_avg_3y': 20, 'has_cb_bw': False, 'has_paid_increase': False,
            'major_shareholder_ratio': 40.0, 'status': '', 'trading_value': 10000000000,
            'retention_ratio': 200.0, 'net_income_3y': [1, 2, 3], 'pcr': 10, 'psr': 1, 'fscore': 5,
            'current_ratio': 200, 'dividend_history': [1, 1, 1], 'dividend_payout': 30
        }

        for strategy_id, strategy in all_strategies.items():
            with self.subTest(strategy=strategy_id):
                passed, condition_details = strategy.apply_filters(mock_stock_data)
                self.assertIsInstance(passed, bool)
                self.assertIsInstance(condition_details, dict)

if __name__ == '__main__':
    unittest.main()