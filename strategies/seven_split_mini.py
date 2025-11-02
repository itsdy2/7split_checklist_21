# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Seven Split Mini Strategy
세븐스플릿 핵심 10개 조건 (빠른 스크리닝)
"""
from .base_strategy import BaseStrategy
from ..logic_calculator import Calculator
from framework.logger import get_logger

logger = get_logger(__name__)


class SevenSplitMiniStrategy(BaseStrategy):
    """세븐스플릿 핵심 10개 조건 전략"""
    
    def _initialize(self):
        self.calculator = Calculator()
    
    @property
    def strategy_id(self):
        return "seven_split_mini"
    
    @property
    def strategy_name(self):
        return "세븐스플릿 핵심 10개"
    
    @property
    def strategy_description(self):
        return "세븐스플릿의 가장 중요한 10개 조건만을 선별하여 빠르게 스크리닝합니다. 더 많은 종목을 발굴할 수 있습니다."
    
    @property
    def strategy_category(self):
        return "quality"
    
    @property
    def difficulty(self):
        return "medium"
    
    @property
    def expected_stocks(self):
        return "20-50개"
    
    @property
    def execution_time(self):
        return "20-30분"
    
    @property
    def conditions(self):
        return {
            1: "관리종목/거래정지/환기종목 제외",
            2: "시가총액 1000억 이상",
            3: "부채비율 300% 미만",
            4: "ROE 3년 평균 15% 이상",
            5: "PER 10 이상",
            6: "PBR 1 이상",
            7: "배당수익률 3% 이상",
            8: "3년 연속 흑자",
            9: "최대주주 지분율 30% 이상",
            10: "최근 1년 유상증자 미실시"
        }
    
    def apply_filters(self, stock_data):
        """
        핵심 10개 조건 필터 적용
        
        Args:
            stock_data (dict): 종목 데이터
        
        Returns:
            tuple: (passed: bool, condition_details: dict)
        """
        if not self.validate_stock_data(stock_data):
            return False, {}
        
        condition_results = {}
        
        # 1. 상태 제외 (통합)
        status = stock_data.get('status', '').upper()
        condition_results[1] = (
            '관리' not in status and
            '거래정지' not in status and
            '환기' not in status and
            'HALT' not in status and
            'CAUTION' not in status
        )
        
        if not condition_results[1]:
            return False, condition_results
        
        # 2. 시가총액
        market_cap = stock_data.get('market_cap', 0)
        condition_results[2] = market_cap >= 100_000_000_000
        
        if not condition_results[2]:
            return False, condition_results
        
        # 3. 부채비율
        debt_ratio = stock_data.get('debt_ratio')
        condition_results[3] = debt_ratio is not None and debt_ratio < 300
        
        if not condition_results[3]:
            return False, condition_results
        
        # 4. ROE
        roe_avg_3y = stock_data.get('roe_avg_3y')
        condition_results[4] = roe_avg_3y is not None and roe_avg_3y >= 15
        
        # 5. PER
        per = stock_data.get('per')
        condition_results[5] = per is not None and per > 0 and per >= 10
        
        # 6. PBR
        pbr = stock_data.get('pbr')
        condition_results[6] = pbr is not None and pbr > 0 and pbr >= 1.0
        
        # 7. 배당수익률
        div_yield = stock_data.get('div_yield')
        condition_results[7] = div_yield is not None and div_yield >= 3.0
        
        # 8. 3년 연속 흑자
        net_income_3y = stock_data.get('net_income_3y', [])
        if len(net_income_3y) >= 3:
            consecutive_loss = self.calculator.check_consecutive_losses(net_income_3y)
            condition_results[8] = not consecutive_loss
        else:
            condition_results[8] = False
        
        # 9. 최대주주 지분율
        major_shareholder_ratio = stock_data.get('major_shareholder_ratio')
        condition_results[9] = (
            major_shareholder_ratio is not None and 
            major_shareholder_ratio >= 30
        )
        
        # 10. 유상증자
        has_paid_increase = stock_data.get('has_paid_increase', False)
        condition_results[10] = not has_paid_increase
        
        # 전체 통과 여부
        passed = all(condition_results.values())
        
        self.log_filter_result(
            stock_data.get('code'),
            stock_data.get('name'),
            passed,
            condition_results
        )
        
        return passed, condition_results