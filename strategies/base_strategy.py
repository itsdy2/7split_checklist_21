# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Base Strategy
전략 베이스 클래스 정의
"""
from abc import ABC, abstractmethod
from typing import Dict, Tuple
# from framework.logger import get_logger  <-- 이 줄을 삭제하고
from ..plugin import P                     # <-- '..' 점 두 개로 변경합니다.

# logger = get_logger(__name__)  <-- 이 줄을 삭제하고
logger = P.logger                # <-- 이 줄을 추가합니다.


class BaseStrategy(ABC):
    """투자 전략 베이스 클래스"""
    
    def __init__(self):
        """전략 초기화"""
        self._initialize()
    
    def _initialize(self):
        """전략별 초기화 (오버라이드 가능)"""
        pass
    
    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """
        전략 고유 ID
        예: 'seven_split_21', 'dividend_strategy'
        """
        pass
    
    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """
        전략 표시 이름
        예: '세븐스플릿 21개 조건'
        """
        pass
    
    @property
    @abstractmethod
    def strategy_description(self) -> str:
        """
        전략 상세 설명
        """
        pass
    
    @property
    @abstractmethod
    def strategy_category(self) -> str:
        """
        전략 카테고리
        예: 'value', 'dividend', 'growth', 'quality'
        """
        pass
    
    @property
    @abstractmethod
    def conditions(self) -> Dict[int, str]:
        """
        조건 목록
        Returns:
            {조건번호: 조건명} 딕셔너리
        """
        pass

    @property
    @abstractmethod
    def required_data(self) -> set:
        """
        필요한 데이터 목록
        Returns:
            {'market', 'financial', 'disclosure', 'major_shareholder'} 와 같은 set
        """
        pass
    
    @property
    def version(self) -> str:
        """전략 버전"""
        return "1.0.0"
    
    @property
    def difficulty(self) -> str:
        """
        난이도
        Returns:
            'easy', 'medium', 'hard'
        """
        return "medium"
    
    @property
    def expected_stocks(self) -> str:
        """
        예상 통과 종목 수
        Returns:
            '10-30개', '50-100개' 등
        """
        return "알 수 없음"
    
    @property
    def execution_time(self) -> str:
        """
        예상 실행 시간
        Returns:
            '30분', '1시간' 등
        """
        return "30-60분"
    
    @abstractmethod
    def apply_filters(self, stock_data: dict) -> Tuple[bool, dict]:
        """
        필터 적용
        
        Args:
            stock_data (dict): 종목 데이터
                {
                    'code': str,
                    'name': str,
                    'market': str,
                    'market_cap': int,
                    'per': float,
                    'pbr': float,
                    ...
                }
        
        Returns:
            tuple: (passed: bool, condition_details: dict)
                - passed: 전체 조건 통과 여부
                - condition_details: {조건번호: 통과여부(bool)} 딕셔너리
        """
        pass
    
    def get_info(self) -> dict:
        """
        전략 전체 정보 반환
        
        Returns:
            dict: 전략 메타데이터
        """
        return {
            'id': self.strategy_id,
            'name': self.strategy_name,
            'description': self.strategy_description,
            'category': self.strategy_category,
            'version': self.version,
            'difficulty': self.difficulty,
            'expected_stocks': self.expected_stocks,
            'execution_time': self.execution_time,
            'conditions_count': len(self.conditions),
            'conditions': self.conditions
        }
    
    def validate_stock_data(self, stock_data: dict) -> bool:
        """
        종목 데이터 유효성 검사
        
        Args:
            stock_data (dict): 종목 데이터
        
        Returns:
            bool: 유효한 데이터인지 여부
        """
        required_fields = ['code', 'name', 'market']
        
        for field in required_fields:
            if field not in stock_data or not stock_data[field]:
                logger.warning(f"Missing required field: {field}")
                return False
        
        return True
    
    def log_filter_result(self, code: str, name: str, passed: bool, condition_details: dict):
        """
        필터링 결과 로깅
        
        Args:
            code (str): 종목코드
            name (str): 종목명
            passed (bool): 통과 여부
            condition_details (dict): 조건별 결과
        """
        if passed:
            logger.info(f"[{self.strategy_id}] ✅ {name}({code}) - 모든 조건 통과")
        else:
            failed_conditions = [
                f"{num}번" for num, result in condition_details.items() if not result
            ]
            logger.debug(
                f"[{self.strategy_id}] ❌ {name}({code}) - "
                f"미통과 조건: {', '.join(failed_conditions)}"
            )

    def _check_status(self, status: str) -> dict:
        """
        공통 상태 필터 (관리종목, 거래정지 등)
        
        Args:
            status (str): 종목 상태 문자열
        
        Returns:
            dict: 각 상태 필터 결과
        """
        status = status.upper()
        return {
            'is_managed': '관리' not in status,
            'is_suspended': '거래정지' not in status and 'HALT' not in status,
            'is_caution': '환기' not in status and 'CAUTION' not in status,
            'is_delisting': '정리매매' not in status or '폐지' not in status,
        }
    
    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.strategy_id} name={self.strategy_name}>"