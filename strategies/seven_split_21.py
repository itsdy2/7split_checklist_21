# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Seven Split 21 Strategy
세븐스플릿 21가지 체크리스트 전략
"""
from strategies.base_strategy import BaseStrategy
from logic import Logic
from logic_calculator import Calculator
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
    def required_data(self) -> set:
        return {'market', 'financial', 'disclosure', 'major_shareholder'}
    
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

        # 설정 값 가져오기
        min_market_cap = int(Logic.get_setting('min_market_cap') or 1000) * 100_000_000
        max_debt_ratio = int(Logic.get_setting('max_debt_ratio') or 300)
        min_retention_ratio = int(Logic.get_setting('min_retention_ratio') or 100)
        min_trading_value = int(Logic.get_setting('min_trading_value') or 10) * 100_000_000
        min_roe_avg = int(Logic.get_setting('min_roe_avg') or 15)
        min_pbr = float(Logic.get_setting('min_pbr') or 1.0)
        min_per = float(Logic.get_setting('min_per') or 10.0)
        min_div_yield = float(Logic.get_setting('min_div_yield') or 3.0)
        min_pcr = float(Logic.get_setting('min_pcr') or 10.0)
        min_psr = float(Logic.get_setting('min_psr') or 1.0)
        min_fscore = int(Logic.get_setting('min_fscore') or 5)
        min_major_shareholder_ratio = int(Logic.get_setting('min_major_shareholder_ratio') or 30)
        
        condition_results = {}
        passed = True
        
        # 1-6. 상태 제외 조건
        status_check = self._check_status(stock_data.get('status', ''))
        condition_results[1] = status_check['is_managed']
        condition_results[2] = status_check['is_suspended']
        condition_results[3] = status_check['is_caution']
        condition_results[4] = '정리매매' not in stock_data.get('status', '').upper()
        condition_results[5] = '불성실' not in stock_data.get('status', '').upper()
        condition_results[6] = status_check['is_delisting']

        # 7. 시가총액
        condition_results[7] = self._check_market_cap(stock_data.get('market_cap', 0), min_market_cap)
        
        # 8. 부채비율
        condition_results[8] = self._check_debt_ratio(stock_data.get('debt_ratio'), max_debt_ratio)
        
        # 9. 유보율
        condition_results[9] = self._check_retention_ratio(stock_data.get('retention_ratio'), min_retention_ratio)
        
        # 10. 3년 연속 적자
        condition_results[10] = self._check_consecutive_losses(stock_data.get('net_income_3y', []))
        
        # 11. 거래대금
        condition_results[11] = self._check_trading_value(stock_data.get('trading_value', 0), min_trading_value)
        
        # 12-21. 선별 조건 (모두 평가)
        condition_results[12] = self._check_roe(stock_data.get('roe_avg_3y'), min_roe_avg)
        condition_results[13] = self._check_pbr(stock_data.get('pbr'), min_pbr)
        condition_results[14] = self._check_per(stock_data.get('per'), min_per)
        condition_results[15] = self._check_dividend_yield(stock_data.get('div_yield'), min_div_yield)
        condition_results[16] = self._check_pcr(stock_data.get('pcr'), min_pcr)
        condition_results[17] = self._check_psr(stock_data.get('psr'), min_psr)
        condition_results[18] = self._check_fscore(stock_data.get('fscore'), min_fscore)
        condition_results[19] = self._check_cb_bw(stock_data.get('has_cb_bw', False))
        condition_results[20] = self._check_paid_increase(stock_data.get('has_paid_increase', False))
        condition_results[21] = self._check_major_shareholder(stock_data.get('major_shareholder_ratio'), min_major_shareholder_ratio)
        
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

    
    def _check_market_cap(self, market_cap, min_market_cap):
        """조건 7: 시가총액"""
        try:
            return market_cap >= min_market_cap
        except:
            return False
    
    def _check_debt_ratio(self, debt_ratio, max_debt_ratio):
        """조건 8: 부채비율"""
        try:
            if debt_ratio is None:
                return False
            return debt_ratio < max_debt_ratio
        except:
            return False
    
    def _check_retention_ratio(self, retention_ratio, min_retention_ratio):
        """조건 9: 유보율"""
        try:
            if retention_ratio is None:
                return False
            return retention_ratio >= min_retention_ratio
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
    
    def _check_trading_value(self, trading_value, min_trading_value):
        """조건 11: 거래대금"""
        try:
            return trading_value >= min_trading_value
        except:
            return False
    
    def _check_roe(self, roe_avg_3y, min_roe_avg):
        """조건 12: ROE 3년 평균"""
        try:
            if roe_avg_3y is None:
                return False
            return roe_avg_3y >= min_roe_avg
        except:
            return False
    
    def _check_pbr(self, pbr, min_pbr):
        """조건 13: PBR"""
        try:
            if pbr is None or pbr <= 0:
                return False
            return pbr >= min_pbr
        except:
            return False
    
    def _check_per(self, per, min_per):
        """조건 14: PER"""
        try:
            if per is None or per <= 0:
                return False
            return per >= min_per
        except:
            return False
    
    def _check_dividend_yield(self, div_yield, min_div_yield):
        """조건 15: 배당수익률"""
        try:
            if div_yield is None:
                return False
            return div_yield >= min_div_yield
        except:
            return False
    
    def _check_pcr(self, pcr, min_pcr):
        """조건 16: PCR"""
        try:
            if pcr is None or pcr <= 0:
                return False
            return pcr >= min_pcr
        except:
            return False
    
    def _check_psr(self, psr, min_psr):
        """조건 17: PSR"""
        try:
            if psr is None or psr <= 0:
                return False
            return psr >= min_psr
        except:
            return False
    
    def _check_fscore(self, fscore, min_fscore):
        """조건 18: F-SCORE"""
        try:
            if fscore is None:
                return False
            return fscore >= min_fscore
        except:
            return False
    
    def _check_cb_bw(self, has_cb_bw):
        """조건 19: CB/BW 미발행"""
        return not has_cb_bw
    
    def _check_paid_increase(self, has_paid_increase):
        """조건 20: 유상증자 미실시"""
        return not has_paid_increase
    
    def _check_major_shareholder(self, major_shareholder_ratio, min_major_shareholder_ratio):
        """조건 21: 최대주주 지분율"""
        try:
            if major_shareholder_ratio is None:
                return False
            return major_shareholder_ratio >= min_major_shareholder_ratio
        except:
            return False