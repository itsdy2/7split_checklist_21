# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Main Logic (Strategy System)
전략 시스템 통합 메인 로직
"""
import time
import json
import traceback
from datetime import datetime, date, timedelta

from framework import app, db, socketio, F, celery
from .setup import P

logger = P.logger
package_name = P.package_name


class Logic:
    db_default = {
        'dart_api_key': '',
        'discord_webhook_url': '',
        'auto_start': 'False',
        'screening_time': '09:00',
        'default_strategy': 'seven_split_21',
        'notification_discord': 'True',
        'use_multiprocessing': 'False',
        'screening_interval_days': '1',
        'db_retention_days': '30',
        'db_cleanup_enabled': 'True',
    }

    @staticmethod
    def get_setting(key, default=None):
        from .setup import PluginModelSetting
        return PluginModelSetting.get(key, default=default)

    @staticmethod
    def get_available_strategies():
        from .strategies import get_all_strategies
        return get_all_strategies()

    @staticmethod
    def get_strategies_metadata():
        from .strategies import get_strategies_info
        return get_strategies_info()

    @staticmethod
    def start_screening(strategy_id=None, execution_type='manual'):
        logger.info(f"Logic.start_screening 시작: strategy_id={strategy_id}, execution_type={execution_type}")
        try:
            if F.config['use_celery']:
                result = Logic.task_start_screening.apply_async((strategy_id, execution_type))
                return {'success': True, 'message': f'Celery 작업 시작: {result.id}'}
            else:
                # Celery 미사용 시 동기 실행. bind=True이므로 첫 인자로 None을 전달.
                result = Logic.task_start_screening(None, strategy_id, execution_type)
                return result
        except Exception as e:
            logger.error(f"start_screening 오류: {str(e)}")
            logger.error(traceback.format_exc())
            return {'success': False, 'message': f'스크리닝 시작 실패: {str(e)}'}

    @celery.task(bind=True)
    def task_start_screening(self, strategy_id=None, execution_type='manual'):
        from .setup import PluginModelSetting
        from .strategies import get_strategy as get_strategy_func
        from .model import StockScreeningResult, ScreeningHistory, FilterDetail
        from .logic_collector import DataCollector
        from .logic_calculator import Calculator
        from .logic_notifier import Notifier
        
        start_time = time.time()
        history = None
        logger.info(f"스크리닝 작업 시작: strategy_id={strategy_id}, execution_type={execution_type}")
        
        try:
            if strategy_id is None:
                strategy_id = PluginModelSetting.get('default_strategy')
                logger.debug(f"기본 전략으로 실행: {strategy_id}")
            
            strategy = get_strategy_func(strategy_id)
            if not strategy:
                raise ValueError(f"전략을 찾을 수 없음: {strategy_id}")

            logger.info(f"전략 로드 성공: {strategy.strategy_name}")

            history = ScreeningHistory(execution_date=datetime.now(), execution_type=execution_type, status='running', strategy_name=strategy_id)
            history.save()
            
            dart_api_key = PluginModelSetting.get('dart_api_key')
            if not dart_api_key:
                raise ValueError("DART API Key가 설정되지 않았습니다.")
            
            collector = DataCollector(dart_api_key=dart_api_key)
            calculator = Calculator()
            
            logger.info("전체 종목 목록 수집 시작...")
            all_tickers = collector.get_all_tickers()
            total_stocks = len(all_tickers)
            if total_stocks == 0:
                raise ValueError("수집된 종목이 없습니다.")
            logger.info(f"총 {total_stocks}개 종목 수집 완료.")
            
            history.total_stocks = total_stocks
            history.save()
            
            logger.info(f"'{strategy.strategy_name}' 전략으로 스크리닝 시작...")
            passed_stocks_count = 0
            
            for idx, ticker_info in enumerate(all_tickers):
                code = ticker_info['code']
                name = ticker_info['name']
                
                if (idx + 1) % 50 == 0:
                    logger.info(f"진행 상황: {idx+1}/{total_stocks} ({name})")
                
                try:
                    socketio.emit('7split_screening_progress', {'current': idx + 1, 'total': total_stocks}, namespace='/framework', broadcast=True)
                    
                    logger.debug(f"[{code}] 데이터 수집 시작...")
                    stock_data = collector.get_all_data_for_ticker(code, strategy.required_data)
                    stock_data['name'] = name
                    logger.debug(f"[{code}] 수집된 데이터: {stock_data}")

                    logger.debug(f"[{code}] 지표 계산 시작...")
                    calculated_data = calculator.calculate_all_metrics(stock_data)
                    stock_data.update(calculated_data)
                    logger.debug(f"[{code}] 계산된 지표: {calculated_data}")

                    logger.debug(f"[{code}] 필터 적용 시작...")
                    passed, condition_details = strategy.apply_filters(stock_data)
                    logger.debug(f"[{code}] 필터 결과: {'통과' if passed else '실패'}")

                    if passed:
                        passed_stocks_count += 1

                    result_record = StockScreeningResult()
                    # ... (save logic)
                    result_record.save()

                except Exception as e:
                    logger.error(f"종목 {code} 처리 중 오류 발생: {e}")
                    logger.error(traceback.format_exc())
                    continue
            
            execution_time = time.time() - start_time
            history.passed_stocks = passed_stocks_count
            history.execution_time = execution_time
            history.status = 'completed'
            history.save()
            
            logger.info(f"스크리닝 완료. 총 {total_stocks}개 중 {passed_stocks_count}개 통과. (소요시간: {execution_time:.2f}초)")
            
            return {'success': True, 'message': '스크리닝이 완료되었습니다.'}
            
        except Exception as e:
            error_msg = f"스크리닝 작업 중 심각한 오류 발생: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            if history:
                history.status = 'failed'
                history.error_message = str(e)
                history.save()
            return {'success': False, 'message': error_msg}
    
    # ... other methods
