# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Value Investing Strategy
벤저민 그레이엄 스타일 가치투자 전략
"""
from strategies.base_strategy import BaseStrategy
from logic import Logic
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
    def required_data(self) -> set:
        return {'market', 'financial'}
    
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

        # 설정 값 가져오기
        min_market_cap_value = int(Logic.get_setting('min_market_cap_value') or 300) * 100_000_000
        max_per_value = float(Logic.get_setting('max_per_value') or 15.0)
        min_pbr_value = float(Logic.get_setting('min_pbr_value') or 0.3)
        max_pbr_value = float(Logic.get_setting('max_pbr_value') or 1.5)
        max_debt_ratio_value = int(Logic.get_setting('max_debt_ratio_value') or 200)
        min_current_ratio_value = int(Logic.get_setting('min_current_ratio_value') or 150)
        min_roe_value = int(Logic.get_setting('min_roe_value') or 8)
        min_trading_value_value = int(Logic.get_setting('min_trading_value_value') or 3) * 100_000_000
        
        condition_results = {}
        
        # 1. 관리종목 제외
        status = stock_data.get('status', '').upper()
        condition_results[1] = (
            '관리' not in status and
            '거래정지' not in status and
            '폐지' not in status
        )

        # 2. 시가총액
        market_cap = stock_data.get('market_cap', 0)
        condition_results[2] = market_cap >= min_market_cap_value
        
        # 3. PER
        per = stock_data.get('per')
        condition_results[3] = per is not None and 0 < per <= max_per_value
        
        # 4. PBR
        pbr = stock_data.get('pbr')
        condition_results[4] = pbr is not None and min_pbr_value <= pbr <= max_pbr_value
        
        # 5. 부채비율
        debt_ratio = stock_data.get('debt_ratio')
        condition_results[5] = debt_ratio is not None and debt_ratio < max_debt_ratio_value
        
        # 6. 유동비율
        current_ratio = stock_data.get('current_ratio')
        if current_ratio is not None:
            condition_results[6] = current_ratio >= min_current_ratio_value
        else:
            # 데이터 없으면 일단 통과 (나중에 개선)
            condition_results[6] = True
        
        # 7. ROE
        roe_avg_3y = stock_data.get('roe_avg_3y')
        condition_results[7] = roe_avg_3y is not None and roe_avg_3y >= min_roe_value
        
        # 8. 3년 중 2년 이상 흑자
        net_income_3y = stock_data.get('net_income_3y', [])
        if len(net_income_3y) >= 3:
            profit_years = sum(1 for income in net_income_3y[:3] if income > 0)
            condition_results[8] = profit_years >= 2
        else:
            condition_results[8] = False
        
        # 9. 거래대금
        trading_value = stock_data.get('trading_value', 0)
        condition_results[9] = trading_value >= min_trading_value_value
        
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