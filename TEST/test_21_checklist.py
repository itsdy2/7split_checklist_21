#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
21가지 체크리스트 기능 테스트 스크립트
FlaskFarm 플러그인 '7split_checklist_21'의 핵심 기능 검증
"""

import os
import sys
import json
import time
import logging
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_test_environment():
    """테스트 환경 설정"""
    logger.info("테스트 환경을 설정합니다...")
    
    # 현재 경로 설정
    current_dir = Path(__file__).parent
    plugin_dir = current_dir.parent
    
    # Python 경로에 플러그인 디렉토리 추가
    sys.path.insert(0, str(plugin_dir))
    
    # 필요한 디펜던시 설치 확인
    try:
        import pandas as pd
        import numpy as np
        import requests
        logger.info("필수 디펜던시 확인 완료")
    except ImportError as e:
        logger.error(f"필수 디펜던시 누락: {e}")
        sys.exit(1)
    
    logger.info("테스트 환경 설정 완료")
    return current_dir, plugin_dir

def import_plugins():
    """플러그인 모듈 가져오기"""
    logger.info("플러그인 모듈을 가져옵니다...")
    
    try:
        # 전략 모듈 가져오기
        from strategies.seven_split_21 import SevenSplit21Strategy
        logger.info("SevenSplit21Strategy 모듈 가져오기 성공")
        
        # 계산기 모듈 가져오기
        from logic_calculator import Calculator
        logger.info("Calculator 모듈 가져오기 성공")
        
        # 수집기 모듈 가져오기
        from logic_collector import DataCollector
        logger.info("DataCollector 모듈 가져오기 성공")
        
        # 모델 가져오기
        from model import StockScreeningResult, ScreeningHistory
        logger.info("모델 가져오기 성공")
        
        return {
            'strategy': SevenSplit21Strategy,
            'calculator': Calculator,
            'collector': DataCollector,
            'models': {
                'StockScreeningResult': StockScreeningResult,
                'ScreeningHistory': ScreeningHistory
            }
        }
    except Exception as e:
        logger.error(f"모듈 가져오기 실패: {e}")
        logger.error(f"에러 상세: {sys.exc_info()[2]}")
        return None

def create_mock_stock_data():
    """테스트용 가상 주식 데이터 생성"""
    logger.info("테스트용 가상 주식 데이터를 생성합니다...")
    
    mock_data = {
        'code': '005930',  # 삼성전자
        'name': '삼성전자',
        'market': 'KOSPI',
        'status': '',  # 정상 상태
        'market_cap': 400000000000000,  # 400조원
        'trading_value': 1000000000000,  # 1000억원
        'per': 12.5,
        'pbr': 1.8,
        'div_yield': 1.5,
        'pcr': 2.0,
        'psr': 1.2,
        'debt_ratio': 30.5,
        'current_ratio': 1.8,
        'retention_ratio': 45.2,
        'roe_avg_3y': 18.3,
        'net_income_3y': [50000000000000, 48000000000000, 45000000000000],  # 최근 3년 순이익
        'fscore': 7,  # 피오트로스키 F-Score
        'has_cb_bw': False,  # CB/BW 발행 여부
        'has_paid_increase': False,  # 유상증자 여부
        'major_shareholder_ratio': 58.2,
        'dividend_history': [1000, 1200, 1300],  # 배당 내역
        'dividend_payout': 25.5  # 배당성향
    }
    
    logger.info("가상 주식 데이터 생성 완료")
    return mock_data

def test_conditions_individually(modules):
    """21가지 조건 각각 테스트"""
    logger.info("21가지 조건 각각 테스트를 시작합니다...")
    
    results = []
    strategy = modules['strategy']()
    
    # 가상 주식 데이터 생성
    mock_stock_data = create_mock_stock_data()
    
    # 각 조건별 테스트
    for condition_num in range(1, 22):  # 1~21번 조건
        logger.info(f"조건 {condition_num} 테스트 시작")
        
        try:
            # 전체 전략 적용 (성능 테스트 목적)
            start_time = time.time()
            passed, condition_details = strategy.apply_filters(mock_stock_data)
            execution_time = time.time() - start_time
            
            # 개별 조건 결과 확인
            condition_passed = condition_details.get(condition_num, False)
            
            result = {
                'condition_number': condition_num,
                'condition_name': strategy.conditions.get(condition_num, f'조건 {condition_num}'),
                'data_type': 'mock',
                'stock_code': mock_stock_data['code'],
                'stock_name': mock_stock_data['name'],
                'result': condition_passed,
                'execution_time_ms': round(execution_time * 1000, 2),
                'test_timestamp': datetime.now(),
                'all_conditions_passed': passed
            }
            
            logger.info(f"조건 {condition_num} 테스트 완료 - 통과: {condition_passed}, 소요시간: {execution_time*1000:.2f}ms")
            results.append(result)
            
        except Exception as e:
            logger.error(f"조건 {condition_num} 테스트 중 오류 발생: {e}")
            result = {
                'condition_number': condition_num,
                'condition_name': strategy.conditions.get(condition_num, f'조건 {condition_num}'),
                'data_type': 'mock',
                'stock_code': mock_stock_data.get('code', 'N/A'),
                'stock_name': mock_stock_data.get('name', 'N/A'),
                'result': False,
                'execution_time_ms': 0,
                'test_timestamp': datetime.now(),
                'error_message': str(e),
                'all_conditions_passed': False
            }
            results.append(result)
    
    return results

def test_with_real_data(modules, dart_api_key=None):
    """DART API를 사용한 실제 데이터 테스트"""
    logger.info("DART API를 사용한 실제 데이터 테스트를 시작합니다...")
    
    results = []
    
    try:
        # 데이터 수집기 초기화 (DART API 키 없이 테스트)
        collector = modules['collector'](dart_api_key=dart_api_key) if dart_api_key else modules['collector']()
        logger.info("데이터 수집기 초기화 완료")
        
        # 전략 가져오기
        strategy = modules['strategy']()
        
        # 실제 데이터 수집 테스트 (KOSPI 상위 5개 종목)
        logger.info("실제 종목 데이터를 수집합니다...")
        
        # 최근 거래일 기준으로 데이터 가져오기
        today = datetime.now().strftime('%Y%m%d')
        try:
            from pykrx import stock as pykrx_stock
            krx_tickers = pykrx_stock.get_market_ticker_list(today, market='KOSPI')
            
            # 상위 5개 종목만 테스트 (성능 고려)
            test_tickers = krx_tickers[:5]
            logger.info(f"테스트 종목: {test_tickers}")
            
            for i, code in enumerate(test_tickers):
                try:
                    logger.info(f"[{i+1}/{len(test_tickers)}] 종목 코드 {code} 테스트")
                    
                    # 종목명 가져오기
                    name = pykrx_stock.get_market_ticker_name(code)
                    
                    # 시장 데이터 수집
                    market_data = collector.get_market_data(code, strategy.required_data)
                    financial_data = collector.get_financial_data(code, strategy.required_data)
                    disclosure_info = collector.get_disclosure_info(code, strategy.required_data)
                    major_shareholder = collector.get_major_shareholder(code, strategy.required_data)
                    
                    # 계산 처리
                    calc = modules['calculator']()
                    retention_ratio = calc.calculate_retention_ratio({
                        'capital': financial_data.get('capital', 0),
                        'capital_surplus': financial_data.get('capital_surplus', 0),
                        'retained_earnings': financial_data.get('retained_earnings', 0)
                    })
                    
                    roe_avg_3y = calc.calculate_roe_average_3y(financial_data.get('roe', []))
                    fscore = calc.calculate_fscore(financial_data)
                    
                    # 종목 데이터 구성
                    stock_data = {
                        'code': code,
                        'name': name,
                        'market': 'KOSPI',
                        'status': '',
                        'market_cap': market_data.get('market_cap', 0),
                        'trading_value': market_data.get('trading_value', 0),
                        'per': market_data.get('per', None),
                        'pbr': market_data.get('pbr', None),
                        'div_yield': market_data.get('div_yield', None),
                        # 계산된 값들
                        'retention_ratio': retention_ratio,
                        'roe_avg_3y': roe_avg_3y,
                        'fscore': fscore,
                        'debt_ratio': financial_data.get('debt_ratio'),
                        'current_ratio': financial_data.get('current_ratio'),
                        'net_income_3y': financial_data.get('net_income', []),
                        'has_cb_bw': disclosure_info.get('has_cb_bw', False),
                        'has_paid_increase': disclosure_info.get('has_paid_increase', False),
                        'major_shareholder_ratio': major_shareholder,
                        'dividend_history': financial_data.get('dividend_history', []),
                        'dividend_payout': financial_data.get('dividend_payout')
                    }
                    
                    # 전략 적용
                    start_time = time.time()
                    passed, condition_details = strategy.apply_filters(stock_data)
                    execution_time = time.time() - start_time
                    
                    # 결과 저장
                    for condition_num, result in condition_details.items():
                        result_entry = {
                            'condition_number': condition_num,
                            'condition_name': strategy.conditions.get(condition_num, f'조건 {condition_num}'),
                            'data_type': 'real',
                            'stock_code': code,
                            'stock_name': name,
                            'result': result,
                            'execution_time_ms': round(execution_time * 1000, 2),
                            'test_timestamp': datetime.now(),
                            'all_conditions_passed': passed
                        }
                        results.append(result_entry)
                    
                    logger.info(f"종목 {code}({name}) 테스트 완료 - 총 {len(condition_details)}개 조건 평가")
                    
                    # API 요청 제한을 고려하여 약간의 대기
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"종목 {code} 테스트 중 오류: {e}")
                    # 오류 상황도 결과에 포함
                    for condition_num in range(1, 22):
                        result_entry = {
                            'condition_number': condition_num,
                            'condition_name': strategy.conditions.get(condition_num, f'조건 {condition_num}'),
                            'data_type': 'real_error',
                            'stock_code': code,
                            'stock_name': 'Error',
                            'result': False,
                            'execution_time_ms': 0,
                            'test_timestamp': datetime.now(),
                            'error_message': str(e),
                            'all_conditions_passed': False
                        }
                        results.append(result_entry)
                    
    except Exception as e:
        logger.error(f"실제 데이터 테스트 중 오류 발생: {e}")
        logger.error(f"에러 상세: {sys.exc_info()[2]}")
    
    return results

def run_comprehensive_tests(modules):
    """포괄적인 기능 테스트 실행"""
    logger.info("포괄적인 기능 테스트를 실행합니다...")
    
    all_results = []
    
    # 1. 가상 데이터 테스트
    logger.info("1. 가상 데이터 테스트 실행")
    mock_results = test_conditions_individually(modules)
    all_results.extend(mock_results)
    
    # 2. 실제 데이터 테스트 (DART API 키 없이 실행)
    logger.info("2. 실제 데이터 테스트 실행")
    real_results = test_with_real_data(modules)
    all_results.extend(real_results)
    
    # 3. 전략 정보 테스트
    logger.info("3. 전략 정보 테스트 실행")
    strategy = modules['strategy']()
    strategy_info = strategy.get_info()
    
    strategy_test_result = {
        'test_type': 'strategy_info',
        'condition_number': 'N/A',
        'condition_name': '전략 정보',
        'data_type': 'info',
        'stock_code': 'N/A',
        'stock_name': '전략 정보',
        'result': True,
        'execution_time_ms': 0,
        'test_timestamp': datetime.now(),
        'all_conditions_passed': True,
        'strategy_info': strategy_info
    }
    all_results.append(strategy_test_result)
    
    logger.info(f"총 {len(all_results)}개의 테스트 결과가 생성되었습니다.")
    
    return all_results

def save_results_as_csv(results, output_path):
    """CSV 파일로 테스트 결과 저장"""
    logger.info(f"테스트 결과를 CSV 파일로 저장합니다: {output_path}")
    
    try:
        # DataFrame 생성
        df = pd.DataFrame(results)
        
        # 날짜 형식 조정
        if 'test_timestamp' in df.columns:
            df['test_timestamp'] = pd.to_datetime(df['test_timestamp'])
        
        # CSV 저장 (UTF-8 인코딩)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"CSV 파일 저장 완료: {output_path}")
        logger.info(f"총 {len(results)}개의 테스트 결과 저장")
        
        # 요약 정보 출력
        total_tests = len(results)
        passed_tests = len([r for r in results if r.get('result') == True])
        failed_tests = total_tests - passed_tests
        
        logger.info(f"=== 테스트 요약 ===")
        logger.info(f"총 테스트 수: {total_tests}")
        logger.info(f"성공: {passed_tests}")
        logger.info(f"실패: {failed_tests}")
        logger.info(f"성공률: {passed_tests/total_tests*100:.2f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"CSV 파일 저장 실패: {e}")
        return False

def main():
    """메인 테스트 실행 함수"""
    logger.info("="*60)
    logger.info("21가지 체크리스트 기능 테스트를 시작합니다.")
    logger.info("="*60)
    
    # 1. 테스트 환경 설정
    current_dir, plugin_dir = setup_test_environment()
    
    # 2. 플러그인 모듈 가져오기
    modules = import_plugins()
    if not modules:
        logger.error("필수 모듈을 가져올 수 없습니다. 테스트를 종료합니다.")
        return
    
    # 3. 포괄적 테스트 실행
    test_results = run_comprehensive_tests(modules)
    
    # 4. 결과 CSV 저장
    output_file = current_dir / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    success = save_results_as_csv(test_results, output_file)
    
    if success:
        logger.info("="*60)
        logger.info("테스트 완료!")
        logger.info(f"결과 파일: {output_file}")
        logger.info("="*60)
        
        # 간단한 요약 테이블 출력
        df = pd.read_csv(output_file, encoding='utf-8-sig')
        if 'result' in df.columns:
            summary = df['result'].value_counts()
            print("\n결과 요약:")
            print(summary)
        
        return True
    else:
        logger.error("테스트 결과 저장에 실패했습니다.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)