# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Seven Split 21 Strategy
세븐스플릿 21가지 체크리스트 전략
"""
from .base_strategy import BaseStrategy
from ..logic_calculator import Calculator
from framework.logger import get_logger

logger = get_logger(__name__)


class SevenSplit21Strategy(BaseStrategy):
    """세븐스플릿 21가지 체크리스트 전략"""
    
    def _initialize(self):
        """전략 초기화"""
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
    def difficulty(self):
        return "hard"
    
    @property
    def expected_stocks(self):
        return "5-20개"
    
    @property
    def execution_time(self):
        return "40-60분"
    
    @property
    def conditions(self):
        return {
            1: "관리종목 제외",
            2: "거래정지 제외",
            3: "환기종목 제외",
            4: "정리매매 제외",
            5: "불성실공시 제외",
            6: "상장폐지 제외",
            7: "시가총액 1000억 이상",
            8: "부채비율 300% 미만",
            9: "유보율 100% 이상",
            10: "3년 연속 적자 제외",
            11: "거래대금 10억 이상",
            12: "ROE 3년 평균 15% 이상",
            13: "PBR 1 이상",
            14: "PER 10 이상",
            15: "배당수익률 3% 이상",
            16: "PCR 10 이상",
            17: "PSR 1 이상",
            18: "F-SCORE 5점 이상",
            19: "최근 1년 CB/BW 미발행",
            20: "최근 1년 유상증자 미실시",
            21: "최대주주 지분율 30% 이상"
        }
    
    def apply_filters(self, stock_data):
        """
        21가지 조건 필터 적용
        
        Args:
            stock_data (dict): 종목 데이터
        
        Returns:
            tuple: (passed: bool, condition_details: dict)
        """
        if not self.validate_stock_data(stock_data):
            return False, {}
        
        condition_results = {}
        passed = True
        
        # 1-6. 상태 제외 조건
        status_filters = self._check_status_filters(stock_data)
        condition_results.update(status_filters)
        
        if not all(status_filters.values()):
            passed = False
            return passed, condition_results
        
        # 7. 시가총액
        market_cap_check = self._check_market_cap(stock_data.get('market_cap', 0))
        condition_results[7] = market_cap_check
        if not market_cap_check:
            passed = False
            return passed, condition_results
        
        # 8. 부채비율
        debt_check = self._check_debt_ratio(stock_data.get('debt_ratio'))
        condition_results[8] = debt_check
        if not debt_check:
            passed = False
            return passed, condition_results
        
        # 9. 유보율
        retention_check = self._check_retention_ratio(stock_data.get('retention_ratio'))
        condition_results[9] = retention_check
        if not retention_check:
            passed = False
            return passed, condition_results
        
        # 10. 3년 연속 적자
        loss_check = self._check_consecutive_losses(stock_data.get('net_income_3y', []))
        condition_results[10] = loss_check
        if not loss_check:
            passed = False
            return passed, condition_results
        
        # 11. 거래대금
        trading_check = self._check_trading_value(stock_data.get('trading_value', 0))
        condition_results[11] = trading_check
        if not trading_check:
            passed = False
            return passed, condition_results
        
        # 12-21. 선별 조건 (모두 평가)
        condition_results[12] = self._check_roe(stock_data.get('roe_avg_3y'))
        condition_results[13] = self._check_pbr(stock_data.get('pbr'))
        condition_results[14] = self._check_per(stock_data.get('per'))
        condition_results[15] = self._check_dividend_yield(stock_data.get('div_yield'))
        condition_results[16] = self._check_pcr(stock_data.get('pcr'))
        condition_results[17] = self._check_psr(stock_data.get('psr'))
        condition_results[18] = self._check_fscore(stock_data.get('fscore'))
        condition_results[19] = self._check_cb_bw(stock_data.get('has_cb_bw', False))
        condition_results[20] = self._check_paid_increase(stock_data.get('has_paid_increase', False))
        condition_results[21] = self._check_major_shareholder(stock_data.get('major_shareholder_ratio'))
        
        # 전체 통과 여부
        passed = all(condition_results.values())
        
        # 로깅
        self.log_filter_result(
            stock_data.get('code'),
            stock_data.get('name'),
            passed,
            condition_results
        )
        
        return passed, condition_results
    
    # 개별 조건 체크 메서드들
    def _check_status_filters(self, stock_data):
        """조건 1-6: 상태 필터"""
        status = stock_data.get('status', '').upper()
        
        return {
            1: '관리' not in status,
            2: '거래정지' not in status and 'HALT' not in status,
            3: '환기' not in status and 'CAUTION' not in status,
            4: '정리매매' not in status,
            5: '불성실' not in status,
            6: '폐지' not in status and 'DELIST' not in status
        }
    
    def _check_market_cap(self, market_cap):
        """조건 7: 시가총액 1000억 이상"""
        try:
            return market_cap >= 100_000_000_000
        except:
            return False
    
    def _check_debt_ratio(self, debt_ratio):
        """조건 8: 부채비율 300% 미만"""
        try:
            if debt_ratio is None:
                return False
            return debt_ratio < 300
        except:
            return False
    
    def _check_retention_ratio(self, retention_ratio):
        """조건 9: 유보율 100% 이상"""
        try:
            if retention_ratio is None:
                return False
            return retention_ratio >= 100
        except:
            return False
    
    def _check_consecutive_losses(self, net_income_3y):
        """조건 10: 3년 연속 적자 제외"""
        try:
            if not net_income_3y or len(net_income_3y) < 3:
                return False
            consecutive_loss = self.calculator.check_consecutive_losses(net_income_3y)
            return not consecutive_loss
        except:
            return False
    
    def _check_trading_value(self, trading_value):
        """조건 11: 거래대금 10억 이상"""
        try:
            return trading_value >= 1_000_000_000
        except:
            return False
    
    def _check_roe(self, roe_avg_3y):
        """조건 12: ROE 3년 평균 15% 이상"""
        try:
            if roe_avg_3y is None:
                return False
            return roe_avg_3y >= 15
        except:
            return False
    
    def _check_pbr(self, pbr):
        """조건 13: PBR 1 이상"""
        try:
            if pbr is None or pbr <= 0:
                return False
            return pbr >= 1.0
        except:
            return False
    
    def _check_per(self, per):
        """조건 14: PER 10 이상"""
        try:
            if per is None or per <= 0:
                return False
            return per >= 10
        except:
            return False
    
    def _check_dividend_yield(self, div_yield):
        """조건 15: 배당수익률 3% 이상"""
        try:
            if div_yield is None:
                return False
            return div_yield >= 3.0
        except:
            return False
    
    def _check_pcr(self, pcr):
        """조건 16: PCR 10 이상"""
        try:
            if pcr is None or pcr <= 0:
                return False
            return pcr >= 10
        except:
            return False
    
    def _check_psr(self, psr):
        """조건 17: PSR 1 이상"""
        try:
            if psr is None or psr <= 0:
                return False
            return psr >= 1.0
        except:
            return False
    
    def _check_fscore(self, fscore):
        """조건 18: F-SCORE 5점 이상"""
        try:
            if fscore is None:
                return False
            return fscore >= 5
        except:
            return False
    
    def _check_cb_bw(self, has_cb_bw):
        """조건 19: CB/BW 미발행"""
        return not has_cb_bw
    
    def _check_paid_increase(self, has_paid_increase):
        """조건 20: 유상증자 미실시"""
        return not has_paid_increase
    
    def _check_major_shareholder(self, major_shareholder_ratio):
        """조건 21: 최대주주 지분율 30% 이상"""
        try:
            if major_shareholder_ratio is None:
                return False
            return major_shareholder_ratio >= 30
        except:
            return False