# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Seven Split Mini Strategy
세븐스플릿 핵심 10개 조건 (빠른 스크리닝)
"""
from strategies.base_strategy import BaseStrategy
from logic import Logic
from logic_calculator import Calculator
from ..setup import *

logger = P.logger   


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
    def required_data(self) -> set:
        return {'market', 'financial', 'disclosure', 'major_shareholder'}
    
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

        # 설정 값 가져오기
        min_market_cap = int(Logic.get_setting('min_market_cap') or 1000) * 100_000_000
        max_debt_ratio = int(Logic.get_setting('max_debt_ratio') or 300)
        min_roe_avg = int(Logic.get_setting('min_roe_avg') or 15)
        min_pbr = float(Logic.get_setting('min_pbr') or 1.0)
        min_per = float(Logic.get_setting('min_per') or 10.0)
        min_div_yield = float(Logic.get_setting('min_div_yield') or 3.0)
        min_major_shareholder_ratio = int(Logic.get_setting('min_major_shareholder_ratio') or 30)
        
        condition_results = {}
        
        # 1. 상태 제외 (통합)
        status_check = self._check_status(stock_data.get('status', ''))
        condition_results[1] = all(status_check.values())

        # 2. 시가총액
        market_cap = stock_data.get('market_cap', 0)
        condition_results[2] = market_cap >= min_market_cap
        
        # 3. 부채비율
        debt_ratio = stock_data.get('debt_ratio')
        condition_results[3] = debt_ratio is not None and debt_ratio < max_debt_ratio
        
        # 4. ROE
        roe_avg_3y = stock_data.get('roe_avg_3y')
        condition_results[4] = roe_avg_3y is not None and roe_avg_3y >= min_roe_avg
        
        # 5. PER
        per = stock_data.get('per')
        condition_results[5] = per is not None and per > 0 and per >= min_per
        
        # 6. PBR
        pbr = stock_data.get('pbr')
        condition_results[6] = pbr is not None and pbr > 0 and pbr >= min_pbr
        
        # 7. 배당수익률
        div_yield = stock_data.get('div_yield')
        condition_results[7] = div_yield is not None and div_yield >= min_div_yield
        
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
            major_shareholder_ratio >= min_major_shareholder_ratio
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