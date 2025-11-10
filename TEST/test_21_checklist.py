#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
21가지 체크리스트 기능 테스트 스크립트
FlaskFarm 플러그인 '7split_checklist_21'의 핵심 기능 검증
"""
import sys
import types
import logging
import os
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import traceback # Missing import added

# --- FRAMEWORK MOCKING ---
# 테스트 환경에서 프레임워크 의존성을 제거하기 위한 모의(Mock) 객체 설정
# 이 코드는 다른 플러그인 모듈이 import 되기 전에 실행되어야 합니다.

# 1. 로거 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 2. 'flask' 모듈 모의
mock_flask = types.ModuleType('flask')
sys.modules['flask'] = mock_flask

# 3. 'framework' 모듈 모의
mock_framework = types.ModuleType('framework')

# 3.1. celery 모의: 데코레이터가 작동하도록 더미 데코레이터 생성
def dummy_decorator(*args, **kwargs):
    def wrapper(func):
        return func
    return wrapper
mock_framework.celery = type('celery', (), {'task': dummy_decorator})

# 3.2. db 모의: SQLAlchemy 객체와 세션을 흉내
mock_framework.db = types.SimpleNamespace(
    Column=lambda *args, **kwargs: None,
    Integer=None, String=None, Boolean=None, Float=None, Text=None, DateTime=None, BigInteger=None, Date=None,
    session=types.SimpleNamespace(
        query=lambda *args: types.SimpleNamespace(
            filter=lambda *args: types.SimpleNamespace(delete=lambda: None, all=lambda: [], first=lambda: None, count=lambda: 0),
            filter_by=lambda **kwargs: types.SimpleNamespace(delete=lambda: None, all=lambda: [], first=lambda: None, count=lambda: 0),
            delete=lambda: None,
        ),
        commit=lambda: None,
        rollback=lambda: None,
        add=lambda: None,
        merge=lambda: None,
    )
)

# 3.3. 기타 framework 객체 모의
mock_framework.F = types.SimpleNamespace(config={'use_celery': False})
mock_framework.app = types.SimpleNamespace(app_context=lambda: type('dummy_context', (), {'__enter__': lambda: None, '__exit__': lambda a,b,c: None}))
mock_framework.socketio = types.SimpleNamespace(emit=lambda *args, **kwargs: None)
sys.modules['framework'] = mock_framework

# 4. 'plugin' 모듈 모의
mock_plugin = types.ModuleType('plugin')
class MockModelBase:
    def save(self): pass
    def to_dict(self): return {}
mock_plugin.ModelBase = MockModelBase
mock_plugin.PluginModuleBase = object
def dummy_create_plugin_instance(*args, **kwargs):
    return types.SimpleNamespace(logger=logger, ModelSetting=types.SimpleNamespace())
mock_plugin.create_plugin_instance = dummy_create_plugin_instance
sys.modules['plugin'] = mock_plugin

# 5. '7split_checklist_21.setup' 모듈 모의
mock_setup_module = types.ModuleType('7split_checklist_21.setup')
mock_P = types.SimpleNamespace()
mock_P.logger = logger
mock_P.package_name = '7split_checklist_21'

class MockModelSetting:
    @staticmethod
    def get(key, default=None):
        # 전략 테스트에 필요한 기본 설정값 반환
        defaults = {
            'min_market_cap': '1000', 'max_debt_ratio': '300', 'min_retention_ratio': '100',
            'min_trading_value': '10', 'min_roe_avg': '15', 'min_pbr': '1.0', 'min_per': '10.0',
            'min_div_yield': '3.0', 'min_pcr': '10.0', 'min_psr': '1.0', 'min_fscore': '5',
            'min_major_shareholder_ratio': '30',
        }
        return defaults.get(key, default)
mock_P.ModelSetting = MockModelSetting
mock_setup_module.P = mock_P
mock_setup_module.PluginModelSetting = MockModelSetting
sys.modules['7split_checklist_21.setup'] = mock_setup_module

# --- END OF MOCKING ---


def setup_test_environment():
    """테스트 환경 설정"""
    logger.info("테스트 환경을 설정합니다...")
    current_dir = Path(__file__).parent
    plugin_dir = current_dir.parent
    try:
        import pandas as pd
        import numpy as np
        import requests
        import pykrx
        logger.info("필수 디펜던시 확인 완료")
    except ImportError as e:
        logger.error(f"필수 디펜던시 누락: {e}. 'pip install pandas numpy requests pykrx'를 실행해주세요.")
        sys.exit(1)
    logger.info("테스트 환경 설정 완료")
    return current_dir, plugin_dir

def import_plugins():
    """플러그인 모듈 가져오기"""
    logger.info("플러그인 모듈을 가져옵니다...")
    try:
        from ..strategies.seven_split_21 import SevenSplit21Strategy
        from ..logic_calculator import Calculator
        from ..logic_collector import DataCollector
        from ..logic import Logic
        
        # Logic.get_setting이 MockModelSetting.get을 사용하도록 연결
        Logic.get_setting = MockModelSetting.get

        return {
            'strategy': SevenSplit21Strategy,
            'calculator': Calculator,
            'collector': DataCollector,
            'logic': Logic,
        }
    except Exception as e:
        logger.error(f"모듈 가져오기 실패: {e}")
        logger.error(traceback.format_exc())
        return None

def create_mock_stock_data():
    """테스트용 가상 주식 데이터 생성"""
    return {
        'code': '005930', 'name': '삼성전자', 'market': 'KOSPI', 'status': '',
        'market_cap': 400000000000000, 'trading_value': 1000000000000, 'per': 12.5,
        'pbr': 1.8, 'div_yield': 3.1, 'pcr': 10.5, 'psr': 1.2, 'debt_ratio': 30.5,
        'current_ratio': 1.8, 'retention_ratio': 101.0, 'roe_avg_3y': 18.3,
        'net_income_3y': [50, 48, 45], 'fscore': 7, 'has_cb_bw': False,
        'has_paid_increase': False, 'major_shareholder_ratio': 58.2,
        'dividend_history': [1000, 1200, 1300], 'dividend_payout': 25.5
    }

def test_conditions_individually(modules):
    """21가지 조건 각각 테스트"""
    logger.info("21가지 조건 각각 테스트를 시작합니다...")
    results = []
    strategy = modules['strategy']()
    mock_stock_data = create_mock_stock_data()
    
    for condition_num in range(1, 22):
        try:
            start_time = time.time()
            passed, condition_details = strategy.apply_filters(mock_stock_data)
            execution_time = time.time() - start_time
            
            results.append({
                'condition_number': condition_num,
                'condition_name': strategy.conditions.get(condition_num, f'조건 {condition_num}'),
                'result': condition_details.get(condition_num, False),
                'execution_time_ms': round(execution_time * 1000, 2),
            })
        except Exception as e:
            logger.error(f"조건 {condition_num} 테스트 중 오류: {e}")
            results.append({'condition_number': condition_num, 'result': False, 'error': str(e)})
    return results

def main():
    """메인 테스트 실행 함수"""
    logger.info("="*60)
    logger.info("21가지 체크리스트 기능 테스트를 시작합니다.")
    logger.info("="*60)
    
    current_dir, plugin_dir = setup_test_environment()
    
    modules = import_plugins()
    if not modules:
        logger.error("필수 모듈을 가져올 수 없습니다. 테스트를 종료합니다.")
        sys.exit(1)
    
    test_results = test_conditions_individually(modules)
    
    output_file = current_dir / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    try:
        df = pd.DataFrame(test_results)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"테스트 결과 저장 완료: {output_file}")
        
        print("\n" + "="*30 + " 테스트 결과 요약 " + "="*30)
        print(df.to_string(index=False))
        print("="*80)
        
        if all(df['result']):
            logger.info("✅ 모든 테스트 통과!")
            return True
        else:
            logger.warning("❌ 일부 테스트 실패.")
            return False

    except Exception as e:
        logger.error(f"CSV 파일 저장 실패: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
