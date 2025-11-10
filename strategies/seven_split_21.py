# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Seven Split 21 Strategy
세븐스플릿 21가지 체크리스트 전략
"""
from .base_strategy import BaseStrategy
from ..logic import Logic
from ..logic_calculator import Calculator
from ..setup import P

logger = P.logger       


class SevenSplit21Strategy(BaseStrategy):
    """세븐스플릿 21가지 체크리스트 전략"""
    
    def _initialize(self):
        self.calculator = Calculator()
    
    @property
    def strategy_id(self):
        return "seven_split_21"
    
    @property
    def strategy_name(self):
        return "세븐스플릿 21개 조건"
    
    @property
    def strategy_description(self):
        return "세븐스플릿의 정량적 체크리스트 21가지 조건을 모두 충족하는 우량주를 선별합니다."
    
    @property
    def strategy_category(self):
        return "quality"

    @property
    def required_data(self) -> set:
        return {'market', 'financial', 'disclosure', 'major_shareholder'}
    
    @property
    def conditions(self):
        return {
            1: "관리종목 제외", 2: "거래정지 제외", 3: "환기종목 제외",
            4: "정리매매 제외", 5: "불성실공시 제외", 6: "상장폐지 제외",
            7: "시가총액 1000억 이상", 8: "부채비율 300% 미만", 9: "유보율 100% 이상",
            10: "3년 연속 적자 제외", 11: "거래대금 10억 이상", 12: "ROE 3년 평균 15% 이상",
            13: "PBR 1 이상", 14: "PER 10 이상", 15: "배당수익률 3% 이상",
            16: "PCR 10 이상", 17: "PSR 1 이상", 18: "F-SCORE 5점 이상",
            19: "최근 1년 CB/BW 미발행", 20: "최근 1년 유상증자 미실시",
            21: "최대주주 지분율 30% 이상"
        }
    
    def apply_filters(self, stock_data):
        if not self.validate_stock_data(stock_data):
            return False, {}

        code = stock_data.get('code')
        logger.debug(f"[{code}] SevenSplit21Strategy 필터 적용 시작...")

        min_market_cap = int(Logic.get_setting('min_market_cap') or 1000) * 100_000_000
        # ... (get other settings)

        condition_results = {}
        
        # 1-6. 상태 제외 조건
        status_check = self._check_status(stock_data.get('status', ''))
        condition_results[1] = status_check['is_managed']
        # ... (other status checks)

        # 7. 시가총액
        condition_results[7] = self._check_market_cap(code, stock_data.get('market_cap', 0), min_market_cap)
        
        # ... (other checks)

        passed = all(condition_results.values())
        logger.debug(f"[{code}] SevenSplit21Strategy 필터 적용 완료: {'통과' if passed else '실패'}")
        return passed, condition_results

    def _check_market_cap(self, code, market_cap, min_market_cap):
        passed = market_cap >= min_market_cap
        logger.debug(f"  - [{code}] 조건 7 (시총): {market_cap/10**8:,.0f}억 >= {min_market_cap/10**8:,.0f}억 -> {'PASS' if passed else 'FAIL'}")
        return passed
    
    # ... (other _check methods with logging)
