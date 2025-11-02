# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Dividend Strategy
안정적인 배당주 투자 전략
"""
from .base_strategy import BaseStrategy
from framework.logger import get_logger

logger = get_logger(__name__)


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
        
        condition_results = {}
        
        # 1. 관리종목 제외
        status = stock_data.get('status', '').upper()
        condition_results[1] = (
            '관리' not in status and
            '거래정지' not in status and
            '폐지' not in status
        )
        
        if not condition_results[1]:
            return False, condition_results
        
        # 2. 시가총액 (배당주는 중소형주도 포함)
        market_cap = stock_data.get('market_cap', 0)
        condition_results[2] = market_cap >= 50_000_000_000  # 500억
        
        if not condition_results[2]:
            return False, condition_results
        
        # 3. 배당수익률 5% 이상
        div_yield = stock_data.get('div_yield')
        condition_results[3] = div_yield is not None and div_yield >= 5.0
        
        # 4. 배당성향 20-80% (너무 낮거나 높으면 제외)
        dividend_payout = stock_data.get('dividend_payout')
        if dividend_payout is not None:
            condition_results[4] = 20 <= dividend_payout <= 80
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
        
        # 6. 부채비율 200% 미만 (배당주는 더 보수적)
        debt_ratio = stock_data.get('debt_ratio')
        condition_results[6] = debt_ratio is not None and debt_ratio < 200
        
        # 7. 3년 연속 흑자
        net_income_3y = stock_data.get('net_income_3y', [])
        if len(net_income_3y) >= 3:
            condition_results[7] = all(income > 0 for income in net_income_3y[:3])
        else:
            condition_results[7] = False
        
        # 8. 거래대금 5억 이상 (유동성)
        trading_value = stock_data.get('trading_value', 0)
        condition_results[8] = trading_value >= 500_000_000
        
        # 전체 통과 여부
        passed = all(condition_results.values())
        
        self.log_filter_result(
            stock_data.get('code'),
            stock_data.get('name'),
            passed,
            condition_results
        )
        
        return passed, condition_results