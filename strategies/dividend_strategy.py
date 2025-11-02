# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Dividend Strategy
안정적인 배당주 투자 전략
"""
from .base_strategy import BaseStrategy  # 'strategies.base_strategy'를 '.base_strategy'로 변경
from ..logic import Logic  # 'logic'을 '..logic'으로 변경
from ..setup import * # 'from ..setup import *' 추가 (P.logger 사용을 위해)

logger = P.logger      


class DividendStrategy(BaseStrategy):
    """배당주 투자 전략"""
    
    @property
    def strategy_id(self):
        return "dividend_strategy"
    
    @property
    def strategy_name(self):
        return "배당주 전략"
    
    @property
    def strategy_description(self):
        return "안정적이고 높은 배당수익을 제공하는 우량 배당주를 선별합니다."
    
    @property
    def strategy_category(self):
        return "dividend"
    
    @property
    def difficulty(self):
        return "easy"
    
    @property
    def expected_stocks(self):
        return "30-80개"
    
    @property
    def execution_time(self):
        return "15-25분"

    @property
    def required_data(self) -> set:
        return {'market', 'financial'}
    
    @property
    def conditions(self):
        return {
            1: "관리종목 제외",
            2: "시가총액 500억 이상",
            3: "배당수익률 5% 이상",
            4: "배당성향 20-80%",
            5: "3년 연속 배당",
            6: "부채비율 200% 미만",
            7: "3년 연속 흑자",
            8: "거래대금 5억 이상"
        }
    
    def apply_filters(self, stock_data):
        """
        배당주 조건 필터 적용
        
        Args:
            stock_data (dict): 종목 데이터
        
        Returns:
            tuple: (passed: bool, condition_details: dict)
        """
        if not self.validate_stock_data(stock_data):
            return False, {}

        # 설정 값 가져오기
        min_market_cap_dividend = int(Logic.get_setting('min_market_cap_dividend') or 500) * 100_000_000
        min_div_yield_dividend = float(Logic.get_setting('min_div_yield_dividend') or 5.0)
        min_dividend_payout = int(Logic.get_setting('min_dividend_payout') or 20)
        max_dividend_payout = int(Logic.get_setting('max_dividend_payout') or 80)
        max_debt_ratio_dividend = int(Logic.get_setting('max_debt_ratio_dividend') or 200)
        min_trading_value_dividend = int(Logic.get_setting('min_trading_value_dividend') or 5) * 100_000_000
        
        condition_results = {}
        
        # 1. 관리종목 제외
        status_check = self._check_status(stock_data.get('status', ''))
        condition_results[1] = status_check['is_managed'] and status_check['is_suspended'] and status_check['is_delisting']

        # 2. 시가총액 (배당주는 중소형주도 포함)
        market_cap = stock_data.get('market_cap', 0)
        condition_results[2] = market_cap >= min_market_cap_dividend
        
        # 3. 배당수익률
        div_yield = stock_data.get('div_yield')
        condition_results[3] = div_yield is not None and div_yield >= min_div_yield_dividend
        
        # 4. 배당성향
        dividend_payout = stock_data.get('dividend_payout')
        if dividend_payout is not None:
            condition_results[4] = min_dividend_payout <= dividend_payout <= max_dividend_payout
        else:
            # 배당성향 데이터 없으면 일단 통과 (나중에 개선)
            condition_results[4] = True
        
        # 5. 3년 연속 배당 (배당 히스토리 확인)
        dividend_history = stock_data.get('dividend_history', [])
        if len(dividend_history) >= 3:
            # 모두 0보다 크면 연속 배당
            condition_results[5] = all(d > 0 for d in dividend_history[:3])
        else:
            # 히스토리 없으면 현재 배당수익률로 판단
            condition_results[5] = div_yield is not None and div_yield > 0
        
        # 6. 부채비율
        debt_ratio = stock_data.get('debt_ratio')
        condition_results[6] = debt_ratio is not None and debt_ratio < max_debt_ratio_dividend
        
        # 7. 3년 연속 흑자
        net_income_3y = stock_data.get('net_income_3y', [])
        if len(net_income_3y) >= 3:
            condition_results[7] = all(income > 0 for income in net_income_3y[:3])
        else:
            condition_results[7] = False
        
        # 8. 거래대금
        trading_value = stock_data.get('trading_value', 0)
        condition_results[8] = trading_value >= min_trading_value_dividend
        
        # 전체 통과 여부
        passed = all(condition_results.values())
        
        self.log_filter_result(
            stock_data.get('code'),
            stock_data.get('name'),
            passed,
            condition_results
        )
        
        return passed, condition_results