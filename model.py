# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Database Models
SQLAlchemy ORM 모델 정의
"""
from datetime import datetime
from framework import db

# 플러그인 설정
class ModelSetting(db.Model):
    __tablename__ = '7split_setting'
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = '7split_checklist_21'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(500))
    
    def __init__(self, key, value):
        self.key = key
        self.value = value
    
    def __repr__(self):
        return f'<Setting {self.key}={self.value}>'


# 스크리닝 결과
class StockScreeningResult(db.Model):
    __tablename__ = '7split_screening_result'
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = '7split_checklist_21'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 기본 정보
    code = db.Column(db.String(10), nullable=False, index=True)
    name = db.Column(db.String(100))
    market = db.Column(db.String(10))  # KOSPI/KOSDAQ
    sector = db.Column(db.String(100))
    
    # 스크리닝 정보
    screening_date = db.Column(db.Date, nullable=False, index=True)
    passed = db.Column(db.Boolean, default=False)
    
    # 전략 정보
    strategy_name = db.Column(db.String(50), index=True)  # 전략 ID
    strategy_version = db.Column(db.String(20))  # 전략 버전
    
    # 시장 데이터
    market_cap = db.Column(db.BigInteger)  # 시가총액 (원)
    trading_value = db.Column(db.BigInteger)  # 거래대금 (원)
    
    # 가치 지표
    per = db.Column(db.Float)
    pbr = db.Column(db.Float)
    pcr = db.Column(db.Float)
    psr = db.Column(db.Float)
    div_yield = db.Column(db.Float)  # 배당수익률
    
    # 재무 지표
    debt_ratio = db.Column(db.Float)  # 부채비율
    retention_ratio = db.Column(db.Float)  # 유보율
    roe_avg_3y = db.Column(db.Float)  # ROE 3년 평균
    net_income_3y = db.Column(db.Text)  # 3년 순이익 (JSON 문자열)
    
    # 품질 지표
    fscore = db.Column(db.Integer)  # 피오트로스키 F-Score
    
    # 지배구조
    major_shareholder_ratio = db.Column(db.Float)  # 최대주주 지분율
    
    # 공시 정보
    has_cb_bw = db.Column(db.Boolean, default=False)  # CB/BW 발행 여부
    has_paid_increase = db.Column(db.Boolean, default=False)  # 유상증자 여부
    
    # 상태 정보
    is_managed = db.Column(db.Boolean, default=False)  # 관리종목
    is_suspended = db.Column(db.Boolean, default=False)  # 거래정지
    is_caution = db.Column(db.Boolean, default=False)  # 환기종목
    
    # 21개 조건별 통과 여부 (JSON)
    condition_details = db.Column(db.Text)  # JSON 형태로 저장
    
    # 메타 정보
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<StockResult {self.code} {self.name} passed={self.passed}>'


# 스크리닝 실행 이력
class ScreeningHistory(db.Model):
    __tablename__ = '7split_screening_history'
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = '7split_checklist_21'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 실행 정보
    execution_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    execution_type = db.Column(db.String(20))  # auto, manual
    
    # 통계
    total_stocks = db.Column(db.Integer, default=0)
    passed_stocks = db.Column(db.Integer, default=0)
    
    # 단계별 필터링 통계 (JSON)
    filter_statistics = db.Column(db.Text)  # 각 조건별 탈락 수
    
    # 실행 시간
    execution_time = db.Column(db.Float)  # 초 단위
    
    # 상태
    status = db.Column(db.String(20))  # running, completed, failed
    error_message = db.Column(db.Text)
    
    # 알림 전송 여부
    notification_sent = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<History {self.execution_date} passed={self.passed_stocks}/{self.total_stocks}>'


# 조건별 필터링 상세
class FilterDetail(db.Model):
    __tablename__ = '7split_filter_detail'
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = '7split_checklist_21'
    
    id = db.Column(db.Integer, primary_key=True)
    
    screening_date = db.Column(db.Date, nullable=False, index=True)
    condition_number = db.Column(db.Integer, nullable=False)  # 1-21
    condition_name = db.Column(db.String(100))
    
    total_before = db.Column(db.Integer)  # 필터 적용 전 종목 수
    passed = db.Column(db.Integer)  # 통과 종목 수
    failed = db.Column(db.Integer)  # 탈락 종목 수
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<Filter {self.condition_name} passed={self.passed}/{self.total_before}>'


# 개별 조건 스케줄
class ConditionSchedule(db.Model):
    __tablename__ = '7split_condition_schedule'
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = '7split_checklist_21'

    id = db.Column(db.Integer, primary_key=True)
    strategy_id = db.Column(db.String(50), nullable=False)
    condition_number = db.Column(db.Integer, nullable=False)
    cron_expression = db.Column(db.String(100), nullable=False)
    is_enabled = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<ConditionSchedule {self.strategy_id} - {self.condition_number}>'