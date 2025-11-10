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
                # Celery 미사용 시 동기 실행 (apply 사용)
                result = Logic.task_start_screening.apply(args=[strategy_id, execution_type])
                return result.get() # 결과를 반환
        except Exception as e:
            logger.error(f"start_screening 오류: {str(e)}")
            logger.error(traceback.format_exc())
            return {'success': False, 'message': f'스크리닝 시작 실패: {str(e)}'}

    @celery.task(bind=True)
    def task_start_screening(self, strategy_id=None, execution_type='manual'):
        from .setup import PluginModelSetting
        from .strategies import get_strategy as get_strategy_func
        from .model import StockScreeningResult, ScreeningHistory
        from .logic_collector import DataCollector
        from .logic_calculator import Calculator
        
        start_time = time.time()
        history = None
        logger.info(f"스크리닝 작업 시작: strategy_id={strategy_id}, execution_type={execution_type}")
        
        try:
            if strategy_id is None:
                strategy_id = PluginModelSetting.get('default_strategy')
            
            strategy = get_strategy_func(strategy_id)
            if not strategy:
                raise ValueError(f"전략을 찾을 수 없음: {strategy_id}")

            logger.info(f"전략 로드 성공: {strategy.strategy_name}")

            history = ScreeningHistory(execution_date=datetime.now(), execution_type=execution_type, status='running', strategy_name=strategy_id)
            history.save()
            
            collector = DataCollector(dart_api_key=PluginModelSetting.get('dart_api_key'))
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
                    
                    stock_data = collector.get_all_data_for_ticker(code, strategy.required_data)
                    stock_data['name'] = name
                    
                    calculated_data = calculator.calculate_all_metrics(stock_data)
                    stock_data.update(calculated_data)

                    passed, condition_details = strategy.apply_filters(stock_data)

                    if passed:
                        passed_stocks_count += 1

                    result_record = StockScreeningResult.from_dict(stock_data, strategy_id, strategy.version, passed, condition_details)
                    db.session.merge(result_record)
                    
                    if (idx + 1) % 100 == 0:
                        db.session.commit()

                except Exception as e:
                    logger.error(f"종목 {code} 처리 중 오류 발생: {e}")
                    logger.error(traceback.format_exc())
                    continue
            
            db.session.commit()
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
    
    # ... (other methods like cleanup, scheduler_start, etc.)