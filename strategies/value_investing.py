# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Value Investing Strategy
벤저민 그레이엄 스타일 가치투자 전략
"""
from .base_strategy import BaseStrategy
from framework.logger import get_logger

logger = get_logger(__name__)


class ValueInvestingStrategy(BaseStrategy):
    """가치투자 전략 (저평가 우량주)"""
    
    @property
    def strategy_id(self):
        return "value_investing"
    
    @property
    def strategy_name(self):
        return "가치투자 전략"
    
    @property
    def strategy_description(self):
        return "벤저민 그레이엄의 가치투자 철학을 기반으로 저평가된 우량주를 선별합니다."
    
    @property
    def strategy_category(self):
        return "value"
    
    @property
    def difficulty(self):
        return "medium"
    
    @property
    def expected_stocks(self):
        return "40-100개"
    
    @property
    def execution_time(self):
        return "20-30분"
    
    @property
    def conditions(self):
        return {
            1: "관리종목 제외",
            2: "시가총액 300억 이상",
            3: "PER 0-15 (저평가)",
            4: "PBR 0.3-1.5 (저평가)",
            5: "부채비율 200% 미만",
            6: "유동비율 150% 이상",
            7: "ROE 8% 이상",
            8: "3년 중 2년 이상 흑자",
            9: "거래대금 3억 이상",
            10: "배당 지급 실적"
        }
    
    def apply_filters(self, stock_data):
        """
        가치투자 조건 필터 적용
        
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
        
        # 2. 시가총액 300억 이상
        market_cap = stock_data.get('market_cap', 0)
        condition_results[2] = market_cap >= 30_000_000_000
        
        if not condition_results[2]:
            return False, condition_results
        
        # 3. PER 0-15 (저평가)
        per = stock_data.get('per')
        condition_results[3] = per is not None and 0 < per <= 15
        
        # 4. PBR 0.3-1.5 (저평가, 하지만 청산가치 이하는 제외)
        pbr = stock_data.get('pbr')
        condition_results[4] = pbr is not None and 0.3 <= pbr <= 1.5
        
        # 5. 부채비율 200% 미만 (건전성)
        debt_ratio = stock_data.get('debt_ratio')
        condition_results[5] = debt_ratio is not None and debt_ratio < 200
        
        # 6. 유동비율 150% 이상 (유동성)
        current_ratio = stock_data.get('current_ratio')
        if current_ratio is not None:
            condition_results[6] = current_ratio >= 150
        else:
            # 데이터 없으면 일단 통과 (나중에 개선)
            condition_results[6] = True
        
        # 7. ROE 8% 이상 (최소한의 수익성)
        roe_avg_3y = stock_data.get('roe_avg_3y')
        condition_results[7] = roe_avg_3y is not None and roe_avg_3y >= 8
        
        # 8. 3년 중 2년 이상 흑자
        net_income_3y = stock_data.get('net_income_3y', [])
        if len(net_income_3y) >= 3:
            profit_years = sum(1 for income in net_income_3y[:3] if income > 0)
            condition_results[8] = profit_years >= 2
        else:
            condition_results[8] = False
        
        # 9. 거래대금 3억 이상
        trading_value = stock_data.get('trading_value', 0)
        condition_results[9] = trading_value >= 300_000_000
        
        # 10. 배당 지급 실적 (최소 1회)
        div_yield = stock_data.get('div_yield')
        dividend_history = stock_data.get('dividend_history', [])
        
        if len(dividend_history) > 0:
            condition_results[10] = any(d > 0 for d in dividend_history)
        else:
            condition_results[10] = div_yield is not None and div_yield > 0
        
        # 전체 통과 여부
        passed = all(condition_results.values())
        
        self.log_filter_result(
            stock_data.get('code'),
            stock_data.get('name'),
            passed,
            condition_results
        )
        
        return passed, condition_results