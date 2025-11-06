# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Main Logic (Strategy System)
?�략 ?�스???�합 메인 로직
"""
import time
import json
from datetime import datetime, date
from flask import has_app_context
from framework import app, db, socketio, F, celery
from .setup import P # P?� ?�께 PluginModelSetting ?�포??-> PluginModelSetting ?�거



# logger = get_logger(__name__)  <-- ??줄을 ??��?�고
logger = P.logger                # <-- ??줄을 추�??�니??
# package_name = '7split_checklist_21' <-- ??줄을 ??��?�고
package_name = P.package_name    # <-- ??줄을 추�??�니?? (?��? 방식)


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
        # ... (기존 db_default ?�용�??�일)
    }

    @staticmethod
    def get_available_strategies():
        """?�용 가?�한 ?�략 목록"""
        from .strategies import get_all_strategies
        return get_all_strategies()
    
    
    @staticmethod
    def get_strategies_metadata():
        """?�략 메�??�이??목록"""
        from .strategies import get_strategies_info
        return get_strategies_info()
    
    
    @staticmethod
    def start_screening(strategy_id=None, execution_type='manual'):
        logger.info(f"Logic.start_screening ?�작: strategy_id={strategy_id}, execution_type={execution_type}")
        logger.debug(f"Logic.start_screening called with strategy_id: {strategy_id}, execution_type: {execution_type}")
        
        try:
            if F.config['use_celery']:
                logger.info(f"Starting screening via Celery: strategy_id={strategy_id}, type={execution_type}")
                logger.debug("Celery config ?�인 �?..")
                result = Logic.task_start_screening.apply_async((strategy_id, execution_type))
                logger.info(f"Celery task started: {result.id}")
                logger.debug(f"Task result object: {result}")
                return {'success': True, 'message': f'Celery task started: {result.id}'}
            else:
                logger.info(f"Starting screening synchronously: strategy_id={strategy_id}, type={execution_type}")
                logger.debug("?�기???�행 - task_start_screening ?�출 �?..")
                result = Logic.task_start_screening(None, strategy_id, execution_type)
                logger.info(f"Screening completed synchronously")
                logger.debug(f"Synchronous result: {result}")
                return result
        except Exception as e:
            logger.error(f"Error in start_screening: {str(e)}")
            logger.error(traceback.format_exc())
            return {'success': False, 'message': f'?�크리닝 ?�작 ?�패: {str(e)}'}

    @staticmethod
    def cleanup_old_data():
        """?�래???�이???�리"""
        from .setup import PluginModelSetting
        from .model import StockScreeningResult, ScreeningHistory, FilterDetail
        from datetime import datetime, timedelta
        import os

        try:
            # ?�정 가?�오�?            retention_days_str = PluginModelSetting.get('db_retention_days') or '30'
            retention_days = int(retention_days_str)
            cleanup_enabled_str = PluginModelSetting.get('db_cleanup_enabled') or 'True'
            cleanup_enabled = cleanup_enabled_str == 'True'
            
            if not cleanup_enabled:
                logger.info("DB ?�리가 비활?�화?�어 ?�습?�다.")
                return {'success': True, 'message': 'DB ?�리가 비활?�화?�어 ?�습?�다.'}
                
            cutoff_date = datetime.now().date() - timedelta(days=retention_days)
            
            # StockScreeningResult ?�리
            old_results_count = db.session.query(StockScreeningResult).filter(
                StockScreeningResult.screening_date < cutoff_date
            ).count()
            old_results_deleted = db.session.query(StockScreeningResult).filter(
                StockScreeningResult.screening_date < cutoff_date
            ).delete()
            
            # ScreeningHistory ?�리
            old_histories_count = db.session.query(ScreeningHistory).filter(
                ScreeningHistory.execution_date < cutoff_date
            ).count()
            old_histories_deleted = db.session.query(ScreeningHistory).filter(
                ScreeningHistory.execution_date < cutoff_date
            ).delete()
            
            # FilterDetail ?�리
            old_details_count = db.session.query(FilterDetail).filter(
                FilterDetail.created_at < cutoff_date
            ).count()
            old_details_deleted = db.session.query(FilterDetail).filter(
                FilterDetail.created_at < cutoff_date
            ).delete()
            
            db.session.commit()
            
            logger.info(f"DB ?�리 ?�료: {old_results_deleted}�?결과, {old_histories_deleted}�??�력, {old_details_deleted}�??�터 ?�세 ??��??)
            
            return {
                'success': True, 
                'message': f'{retention_days}???�상??{old_results_deleted}�?결과, {old_histories_deleted}�??�력, {old_details_deleted}�??�터 ?�세 ??��??,
                'deleted': {
                    'results': old_results_deleted,
                    'histories': old_histories_deleted,
                    'details': old_details_deleted
                }
            }
                
        except Exception as e:
            logger.error(f"DB ?�리 ?�류: {str(e)}")
            db.session.rollback()
            return {'success': False, 'message': f'DB ?�리 ?�류: {str(e)}'}

    @staticmethod
    @celery.task(bind=True)
    def task_cleanup_old_data(self):
        """Celery ?�업?�로 ?�래???�이???�리"""
        return Logic.cleanup_old_data()

    @staticmethod
    @celery.task(bind=True)
    def task_start_screening(self, strategy_id=None, execution_type='manual'):
        """
        ?�크리닝 ?�작 (?�략 ?�택 가??
        
        Args:
            strategy_id (str): ?�용???�략 ID (None?�면 기본 ?�략)
            execution_type (str): 'auto' or 'manual'
        
        Returns:
            dict: ?�행 결과
        """
        from .setup import PluginModelSetting
        from .strategies import get_strategy as get_strategy_func
        from .model import StockScreeningResult, ScreeningHistory, FilterDetail
        from .logic_collector import DataCollector
        from .logic_calculator import Calculator
        from .logic_notifier import Notifier
        import os
        
        start_time = time.time()
        
        logger.info(f"Task start screening task ?�출: strategy_id={strategy_id}, execution_type={execution_type}")
        logger.debug(f"Started at: {datetime.now()}")
        
        try:
            # 기본 ?�략 ?�정
            if strategy_id is None:
                strategy_id = PluginModelSetting.get('default_strategy')
                logger.debug(f"Using default strategy: {strategy_id}")
            
            # ?�략 로드
            logger.debug(f"Attempting to load strategy: {strategy_id}")
            strategy = get_strategy_func(strategy_id)
            
            if not strategy:
                error_msg = f"존재?��? ?�는 ?�략: {strategy_id}"
                logger.error(error_msg)
                return {'success': False, 'message': error_msg}

            logger.info(f"Successfully loaded strategy: {strategy.strategy_name} (ID: {strategy_id})")
            required_data = strategy.required_data
            
            # 로그 ?�세 ?�용???�한 추�? ?�보
            logger.debug(f"Required data: {required_data}")
            logger.debug(f"Strategy conditions: {strategy.conditions}")
            
            # ?�크리닝 ?�스?�리 ?�성
            history = ScreeningHistory()
            history.execution_date = datetime.now()
            history.execution_type = execution_type
            history.status = 'running'
            history.save()
            
            # ?�정 로드
            dart_api_key = PluginModelSetting.get('dart_api_key')
            webhook_url = PluginModelSetting.get('discord_webhook_url')
            
            logger.debug(f"DART API Key available: {'Yes' if dart_api_key else 'No'}")
            logger.debug(f"Webhook URL available: {'Yes' if webhook_url else 'No'}")
            
            if not dart_api_key:
                error_msg = "DART API Key가 ?�정?��? ?�았?�니??"
                logger.error(error_msg)
                history.status = 'failed'
                history.error_message = error_msg
                history.save()
                return {'success': False, 'message': error_msg}
            
            # ?�이???�집�?초기??            logger.debug("Initializing DataCollector...")
            collector = DataCollector(dart_api_key=dart_api_key)
            logger.info(f"DataCollector initialized. DART API key available: {bool(dart_api_key)}")
            
            calculator = Calculator()
            logger.debug("Calculator initialized")
            
            notifier = Notifier(webhook_url=webhook_url)
            logger.debug("Notifier initialized")
            
            # ?�체 종목 ?�집
            logger.info("Collecting all tickers...")
            all_tickers = collector.get_all_tickers()
            total_stocks = len(all_tickers)
            
            logger.info(f"Total tickers collected: {total_stocks}")
            
            if total_stocks == 0:
                error_msg = "종목 ?�집 ?�패"
                logger.error(error_msg)
                history.status = 'failed'
                history.error_message = error_msg
                history.save()
                return {'success': False, 'message': error_msg}
            
            history.total_stocks = total_stocks
            history.save()
            
            # Discord ?�작 ?�림
            if PluginModelSetting.get('notification_discord') == 'True':
                logger.info("Sending start notification to Discord")
                notifier.send_start_notification(total_stocks, strategy.strategy_name)
            
            # ?�크리닝 ?�행
            logger.info(f"Screening {total_stocks} stocks with {strategy.strategy_name}...")
            passed_stocks = []
            filter_stats = {i: {'passed': 0, 'failed': 0} for i in strategy.conditions.keys()}
            
            today = date.today()

            # ?�전 ?�터�??�세 ?�이????��
            try:
                deleted_count = db.session.query(FilterDetail).filter_by(screening_date=today).delete()
                db.session.commit()
                logger.debug(f"Deleted {deleted_count} previous filter details for date {today}")
            except Exception as e:
                logger.error(f"Failed to delete previous filter details: {str(e)}")
                db.session.rollback()
                
            for idx, ticker_info in enumerate(all_tickers):
                try:
                    # 진행 ?�황 ?�송 (10개마??
                    if idx % 10 == 0:
                        progress = {
                            'current': idx,
                            'total': total_stocks,
                            'percent': round((idx / total_stocks) * 100, 1),
                            'strategy': strategy.strategy_name
                        }
                        socketio.emit(
                            '7split_screening_progress',
                            progress,
                            namespace='/framework',
                            broadcast=True
                        )
                        logger.debug(f"Progress: {idx}/{total_stocks} ({progress['percent']}%)")
                    
                    code = ticker_info['code']
                    name = ticker_info['name']
                    market = ticker_info['market']
                    
                    # ?�이???�집
                    market_data = collector.get_market_data(code, required_data)
                    financial_data = collector.get_financial_data(code, required_data)
                    disclosure_info = collector.get_disclosure_info(code, required_data)
                    major_shareholder = collector.get_major_shareholder(code, required_data)
                    
                    # 계산
                    retention_ratio = calculator.calculate_retention_ratio({
                        'capital': financial_data.get('capital', 0),
                        'capital_surplus': financial_data.get('capital_surplus', 0),
                        'retained_earnings': financial_data.get('retained_earnings', 0)
                    })
                    
                    roe_avg_3y = calculator.calculate_roe_average_3y(financial_data.get('roe', []))
                    
                    # F-Score (?�이??충분?�면 계산)
                    fscore = calculator.calculate_fscore(financial_data)
                    
                    # PCR, PSR 계산
                    pcr = calculator.calculate_pcr(
                        market_data.get('market_cap', 0),
                        financial_data.get('operating_cashflow', 1)
                    )
                    
                    psr = calculator.calculate_psr(
                        market_data.get('market_cap', 0),
                        financial_data.get('revenue', [1])[0] if financial_data.get('revenue') else 1
                    )
                    
                    # 종목 ?�이??구성
                    stock_data = {
                        'code': code,
                        'name': name,
                        'market': market,
                        'status': ticker_info.get('status', ''),
                        'market_cap': market_data.get('market_cap', 0),
                        'trading_value': market_data.get('trading_value', 0),
                        'per': market_data.get('per'),
                        'pbr': market_data.get('pbr'),
                        'div_yield': market_data.get('div_yield'),
                        'pcr': pcr,
                        'psr': psr,
                        'debt_ratio': financial_data.get('debt_ratio'),
                        'current_ratio': financial_data.get('current_ratio'),
                        'retention_ratio': retention_ratio,
                        'roe_avg_3y': roe_avg_3y,
                        'net_income_3y': financial_data.get('net_income', []),
                        'fscore': fscore,
                        'has_cb_bw': disclosure_info.get('has_cb_bw', False),
                        'has_paid_increase': disclosure_info.get('has_paid_increase', False),
                        'major_shareholder_ratio': major_shareholder,
                        'dividend_history': financial_data.get('dividend_history', []),
                        'dividend_payout': financial_data.get('dividend_payout')
                    }
                    
                    # ?�략 ?�용
                    passed, condition_details = strategy.apply_filters(stock_data)
                    
                    # 조건�??�계 ?�데?�트
                    for condition_num, result in condition_details.items():
                        if result:
                            filter_stats[condition_num]['passed'] += 1
                        else:
                            filter_stats[condition_num]['failed'] += 1

                    # ?�터 ?�세 ?�보 ?�??                    for condition_num, passed_status in condition_details.items():
                        filter_detail = FilterDetail(
                            screening_date=today,
                            condition_number=condition_num,
                            condition_name=strategy.conditions.get(condition_num, 'N/A'),
                            total_before=idx + 1,
                            passed=filter_stats[condition_num]['passed'],
                            failed=filter_stats[condition_num]['failed']
                        )
                        db.session.merge(filter_detail)

                    
                    # DB ?�??                    result_record = StockScreeningResult()
                    result_record.code = code
                    result_record.name = name
                    result_record.market = market
                    result_record.screening_date = today
                    result_record.strategy_name = strategy_id  # ?�략 ?�름 ?�??                    result_record.strategy_version = strategy.version
                    result_record.passed = passed
                    result_record.is_managed = '관�? in stock_data.get('status', '').upper()
                    result_record.is_suspended = '거래?��?' in stock_data.get('status', '').upper() or 'HALT' in stock_data.get('status', '').upper()
                    result_record.is_caution = '?�기' in stock_data.get('status', '').upper() or 'CAUTION' in stock_data.get('status', '').upper()
                    result_record.market_cap = stock_data['market_cap']
                    result_record.trading_value = stock_data['trading_value']
                    result_record.per = stock_data['per']
                    result_record.pbr = stock_data['pbr']
                    result_record.pcr = stock_data['pcr']
                    result_record.psr = stock_data['psr']
                    result_record.div_yield = stock_data['div_yield']
                    result_record.debt_ratio = stock_data['debt_ratio']
                    result_record.retention_ratio = stock_data['retention_ratio']
                    result_record.roe_avg_3y = stock_data['roe_avg_3y']
                    result_record.net_income_3y = json.dumps(stock_data['net_income_3y'])
                    result_record.fscore = stock_data['fscore']
                    result_record.major_shareholder_ratio = stock_data['major_shareholder_ratio']
                    result_record.has_cb_bw = stock_data['has_cb_bw']
                    result_record.has_paid_increase = stock_data['has_paid_increase']
                    result_record.condition_details = json.dumps(condition_details)
                    
                    result_record.save()
                    
                    if passed:
                        passed_stocks.append(stock_data)
                    
                    # 100개마??커밋
                    if idx % 100 == 0:
                        db.session.commit()
                        logger.debug(f"Committed at index {idx}")
                    
                    # API ?�한 ?�피
                    time.sleep(0.05)
                    
                except Exception as e:
                    logger.error(f"Error processing {code}: {str(e)}")
                    logger.debug(traceback.format_exc())
                    continue
            
            # 최종 커밋
            db.session.commit()
            
            # ?�행 ?�간 계산
            execution_time = time.time() - start_time
            
            # ?�스?�리 ?�데?�트
            history.passed_stocks = len(passed_stocks)
            history.execution_time = execution_time
            history.filter_statistics = json.dumps(filter_stats)
            history.status = 'completed'
            history.save()
            
            # Discord ?�림
            if PluginModelSetting.get('notification_discord') == 'True':
                logger.info("Sending screening result notification to Discord")
                notifier.send_screening_result(
                    passed_stocks, 
                    total_stocks, 
                    execution_time,
                    strategy.strategy_name
                )
            
            # ?�료 ?�림 (SocketIO)
            socketio.emit(
                '7split_screening_complete',
                {
                    'total': total_stocks,
                    'passed': len(passed_stocks),
                    'time': execution_time,
                    'strategy': strategy.strategy_name
                },
                namespace='/framework',
                broadcast=True
            )
            
            logger.info(
                f"Screening completed: {len(passed_stocks)}/{total_stocks} passed "
                f"in {execution_time:.1f}s with {strategy.strategy_name}"
            )
            
            return {
                'success': True,
                'strategy': strategy_id,
                'strategy_name': strategy.strategy_name,
                'total_stocks': total_stocks,
                'passed_stocks': len(passed_stocks),
                'execution_time': execution_time
            }
            
        except Exception as e:
            error_msg = f"Screening error: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            # ?�스?�리 ?�데?�트
            try:
                history.status = 'failed'
                history.error_message = str(e)
                history.save()
            except:
                pass
            
            # ?�러 ?�림
            from .setup import PluginModelSetting
            if PluginModelSetting.get('notification_discord') == 'True':
                webhook_url = PluginModelSetting.get('discord_webhook_url')
                if webhook_url:
                    notifier = Notifier(webhook_url=webhook_url)
                    notifier.send_error_notification(error_msg)
            
            return {'success': False, 'message': error_msg}
        
        logger.info(f"Starting screening with strategy: {strategy.strategy_name}")
        
        try:
            # ?�크리닝 ?�스?�리 ?�성
            history = ScreeningHistory()
            history.execution_date = datetime.now()
            history.execution_type = execution_type
            history.status = 'running'
            history.save()
            
            # ?�정 로드
            dart_api_key = PluginModelSetting.get('dart_api_key')
            webhook_url = PluginModelSetting.get('discord_webhook_url')
            
            if not dart_api_key:
                error_msg = "DART API Key가 ?�정?��? ?�았?�니??"
                logger.error(error_msg)
                history.status = 'failed'
                history.error_message = error_msg
                history.save()
                return {'success': False, 'message': error_msg}
            
            # ?�이???�집�?초기??            logger.info("Initializing DataCollector...")
            collector = DataCollector(dart_api_key=dart_api_key)
            logger.info(f"DataCollector initialized. DART API key available: {bool(dart_api_key)}")
            
            calculator = Calculator()
            logger.debug("Calculator initialized")
            
            notifier = Notifier(webhook_url=webhook_url)
            logger.debug("Notifier initialized")
            
            # ?�체 종목 ?�집
            logger.info("Collecting all tickers...")
            all_tickers = collector.get_all_tickers()
            total_stocks = len(all_tickers)
            
            if total_stocks == 0:
                error_msg = "종목 ?�집 ?�패"
                logger.error(error_msg)
                history.status = 'failed'
                history.error_message = error_msg
                history.save()
                return {'success': False, 'message': error_msg}
            
            history.total_stocks = total_stocks
            history.save()
            
            # Discord ?�작 ?�림
            if PluginModelSetting.get('notification_discord') == 'True':
                notifier.send_start_notification(total_stocks, strategy.strategy_name)
            
            # ?�크리닝 ?�행
            logger.info(f"Screening {total_stocks} stocks with {strategy.strategy_name}...")
            passed_stocks = []
            filter_stats = {i: {'passed': 0, 'failed': 0} for i in strategy.conditions.keys()}
            
            today = date.today()

            # ?�전 ?�터�??�세 ?�이????��
            try:
                db.session.query(FilterDetail).filter_by(screening_date=today).delete()
                db.session.commit()
            except Exception as e:
                logger.error(f"Failed to delete previous filter details: {str(e)}")
                db.session.rollback()
            
            for idx, ticker_info in enumerate(all_tickers):
                try:
                    # 진행 ?�황 ?�송 (10개마??
                    if idx % 10 == 0:
                        progress = {
                            'current': idx,
                            'total': total_stocks,
                            'percent': round((idx / total_stocks) * 100, 1),
                            'strategy': strategy.strategy_name
                        }
                        socketio.emit(
                            '7split_screening_progress',
                            progress,
                            namespace='/framework',
                            broadcast=True
                        )
                        logger.debug(f"Progress: {idx}/{total_stocks} ({progress['percent']}%)")
                    
                    code = ticker_info['code']
                    name = ticker_info['name']
                    market = ticker_info['market']
                    
                    # ?�이???�집
                    market_data = collector.get_market_data(code, required_data)
                    financial_data = collector.get_financial_data(code, required_data)
                    disclosure_info = collector.get_disclosure_info(code, required_data)
                    major_shareholder = collector.get_major_shareholder(code, required_data)
                    
                    # 계산
                    retention_ratio = calculator.calculate_retention_ratio({
                        'capital': financial_data.get('capital', 0),
                        'capital_surplus': financial_data.get('capital_surplus', 0),
                        'retained_earnings': financial_data.get('retained_earnings', 0)
                    })
                    
                    roe_avg_3y = calculator.calculate_roe_average_3y(financial_data.get('roe', []))
                    
                    # F-Score (?�이??충분?�면 계산)
                    fscore = calculator.calculate_fscore(financial_data)
                    
                    # PCR, PSR 계산
                    pcr = calculator.calculate_pcr(
                        market_data.get('market_cap', 0),
                        financial_data.get('operating_cashflow', 1)
                    )
                    
                    psr = calculator.calculate_psr(
                        market_data.get('market_cap', 0),
                        financial_data.get('revenue', [1])[0] if financial_data.get('revenue') else 1
                    )
                    
                    # 종목 ?�이??구성
                    stock_data = {
                        'code': code,
                        'name': name,
                        'market': market,
                        'status': ticker_info.get('status', ''),
                        'market_cap': market_data.get('market_cap', 0),
                        'trading_value': market_data.get('trading_value', 0),
                        'per': market_data.get('per'),
                        'pbr': market_data.get('pbr'),
                        'div_yield': market_data.get('div_yield'),
                        'pcr': pcr,
                        'psr': psr,
                        'debt_ratio': financial_data.get('debt_ratio'),
                        'current_ratio': financial_data.get('current_ratio'),
                        'retention_ratio': retention_ratio,
                        'roe_avg_3y': roe_avg_3y,
                        'net_income_3y': financial_data.get('net_income', []),
                        'fscore': fscore,
                        'has_cb_bw': disclosure_info.get('has_cb_bw', False),
                        'has_paid_increase': disclosure_info.get('has_paid_increase', False),
                        'major_shareholder_ratio': major_shareholder,
                        'dividend_history': financial_data.get('dividend_history', []),
                        'dividend_payout': financial_data.get('dividend_payout')
                    }
                    
                    # ?�택???�략 ?�용
                    passed, condition_details = strategy.apply_filters(stock_data)
                    
                    # 조건�??�계 ?�데?�트
                    for condition_num, result in condition_details.items():
                        if result:
                            filter_stats[condition_num]['passed'] += 1
                        else:
                            filter_stats[condition_num]['failed'] += 1

                    # ?�터 ?�세 ?�보 ?�??                    for condition_num, passed_status in condition_details.items():
                        filter_detail = FilterDetail(
                            screening_date=today,
                            condition_number=condition_num,
                            condition_name=strategy.conditions.get(condition_num, 'N/A'),
                            total_before=idx + 1,
                            passed=filter_stats[condition_num]['passed'],
                            failed=filter_stats[condition_num]['failed']
                        )
                        db.session.merge(filter_detail)

                    
                    # DB ?�??                    result_record = StockScreeningResult()
                    result_record.code = code
                    result_record.name = name
                    result_record.market = market
                    result_record.screening_date = today
                    result_record.strategy_name = strategy_id  # ?�략 ?�름 ?�??                    result_record.strategy_version = strategy.version
                    result_record.passed = passed
                    result_record.is_managed = '관�? in stock_data.get('status', '').upper()
                    result_record.is_suspended = '거래?��?' in stock_data.get('status', '').upper() or 'HALT' in stock_data.get('status', '').upper()
                    result_record.is_caution = '?�기' in stock_data.get('status', '').upper() or 'CAUTION' in stock_data.get('status', '').upper()
                    result_record.market_cap = stock_data['market_cap']
                    result_record.trading_value = stock_data['trading_value']
                    result_record.per = stock_data['per']
                    result_record.pbr = stock_data['pbr']
                    result_record.pcr = stock_data['pcr']
                    result_record.psr = stock_data['psr']
                    result_record.div_yield = stock_data['div_yield']
                    result_record.debt_ratio = stock_data['debt_ratio']
                    result_record.retention_ratio = stock_data['retention_ratio']
                    result_record.roe_avg_3y = stock_data['roe_avg_3y']
                    result_record.net_income_3y = json.dumps(stock_data['net_income_3y'])
                    result_record.fscore = stock_data['fscore']
                    result_record.major_shareholder_ratio = stock_data['major_shareholder_ratio']
                    result_record.has_cb_bw = stock_data['has_cb_bw']
                    result_record.has_paid_increase = stock_data['has_paid_increase']
                    result_record.condition_details = json.dumps(condition_details)
                    
                    result_record.save()
                    
                    if passed:
                        passed_stocks.append(stock_data)
                    
                    # 100개마??커밋
                    if idx % 100 == 0:
                        db.session.commit()
                    
                    # API ?�한 ?�피
                    time.sleep(0.05)
                    
                except Exception as e:
                    logger.error(f"Error processing {code}: {str(e)}")
                    continue
            
            # 최종 커밋
            db.session.commit()
            
            # ?�행 ?�간 계산
            execution_time = time.time() - start_time
            
            # ?�스?�리 ?�데?�트
            history.passed_stocks = len(passed_stocks)
            history.execution_time = execution_time
            history.filter_statistics = json.dumps(filter_stats)
            history.status = 'completed'
            history.save()
            
            # Discord ?�림
            if PluginModelSetting.get('notification_discord') == 'True':
                notifier.send_screening_result(
                    passed_stocks, 
                    total_stocks, 
                    execution_time,
                    strategy.strategy_name
                )
            
            # ?�료 ?�림 (SocketIO)
            socketio.emit(
                '7split_screening_complete',
                {
                    'total': total_stocks,
                    'passed': len(passed_stocks),
                    'time': execution_time,
                    'strategy': strategy.strategy_name
                },
                namespace='/framework',
                broadcast=True
            )
            
            logger.info(
                f"Screening completed: {len(passed_stocks)}/{total_stocks} passed "
                f"in {execution_time:.1f}s with {strategy.strategy_name}"
            )
            
            return {
                'success': True,
                'strategy': strategy_id,
                'strategy_name': strategy.strategy_name,
                'total_stocks': total_stocks,
                'passed_stocks': len(passed_stocks),
                'execution_time': execution_time
            }
            
        except Exception as e:
            error_msg = f"Screening error: {str(e)}"
            logger.error(error_msg)
            
            # ?�스?�리 ?�데?�트
            try:
                history.status = 'failed'
                history.error_message = error_msg
                history.save()
            except:
                pass
            
            # ?�러 ?�림
            from .setup import PluginModelSetting
            if PluginModelSetting.get('notification_discord') == 'True':
                notifier = Notifier(webhook_url=PluginModelSetting.get('discord_webhook_url'))
                notifier.send_error_notification(error_msg)
            
            return {'success': False, 'message': error_msg}
    
    
    @staticmethod
    def save_condition_schedules(schedules):
        """개별 조건 ?��?�??�??""
        logger.info(f"Saving condition schedules: {len(schedules)} schedules to save")
        try:
            if F.config['use_celery']:
                logger.debug("Using Celery for saving schedules")
                result = Logic.task_save_condition_schedules.apply_async((schedules,))
                logger.info(f"Scheduled save_condition_schedules Celery task: {result.id}")
                return True
            else:
                logger.debug("Executing schedule save synchronously")
                result = Logic.task_save_condition_schedules(schedules)
                logger.info(f"Schedule save completed: {result}")
                return result
        except Exception as e:
            logger.error(f"Error in save_condition_schedules: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    @celery.task(bind=True)
    def task_save_condition_schedules(self, schedules):
        logger.info(f"Celery task to save condition schedules started: {len(schedules)} schedules")
        from .model import ConditionSchedule
        try:
            with app.app_context():
                logger.debug("App context acquired")
                # 기존 ?��?�?모두 ??��
                logger.debug("Deleting all existing condition schedules...")
                deleted_count = db.session.query(ConditionSchedule).delete()
                logger.debug(f"Deleted {deleted_count} existing condition schedules")
                
                logger.debug(f"Saving {len(schedules)} new schedules...")
                for i, schedule_data in enumerate(schedules):
                    logger.debug(f"Saving schedule {i+1}/{len(schedules)}: {schedule_data.get('strategy_id', 'N/A')}")
                    schedule = ConditionSchedule(
                        strategy_id=schedule_data['strategy_id'],
                        condition_number=schedule_data['condition_number'],
                        cron_expression=schedule_data['cron_expression'],
                        is_enabled=schedule_data['is_enabled']
                    )
                    db.session.add(schedule)
                
                db.session.commit()
                logger.info("Schedules saved successfully, restarting scheduler")
                Logic.scheduler_stop()
                Logic.scheduler_start()
                logger.info("Scheduler restarted successfully")
                return True

        except Exception as e:
            logger.error(f'Failed to save condition schedules: {e}')
            logger.error(traceback.format_exc())
            db.session.rollback()
            return False

    @staticmethod
    def run_single_condition(strategy_id, condition_number):
        """?�일 조건 ?�행"""
        from .setup import PluginModelSetting
        from .strategies import get_strategy as get_strategy_func
        from .logic_collector import DataCollector
        from .logic_notifier import Notifier
        try:
            logger.info(f'Running single condition: {strategy_id} - {condition_number}')
            
            strategy = get_strategy_func(strategy_id)
            if not strategy:
                logger.error(f'Strategy not found: {strategy_id}')
                return

            condition_name = strategy.conditions.get(condition_number, 'N/A')
            logger.info(f'Condition name: {condition_name}')

            collector = DataCollector(dart_api_key=PluginModelSetting.get('dart_api_key'))
            all_tickers = collector.get_all_tickers()

            passed_count = 0
            failed_count = 0

            for ticker_info in all_tickers:
                try:
                    code = ticker_info['code']
                    stock_data = collector.get_market_data(code, strategy.required_data)
                    stock_data.update(collector.get_financial_data(code, strategy.required_data))
                    stock_data.update(collector.get_disclosure_info(code, strategy.required_data))
                    stock_data['major_shareholder_ratio'] = collector.get_major_shareholder(code, strategy.required_data)

                    # This is not efficient, but it works for now.
                    # A better approach would be to have a method in each strategy to run a single condition.
                    _, condition_details = strategy.apply_filters(stock_data)
                    
                    if condition_details.get(condition_number, False):
                        passed_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    logger.error(f'Error processing {ticker_info.get("code")}: {e}')
                    failed_count += 1

            result = {'passed': passed_count, 'failed': failed_count}

            notifier = Notifier(webhook_url=PluginModelSetting.get('discord_webhook_url'))
            notifier.send_condition_result_notification(strategy_id, condition_number, result)

        except Exception as e:
            logger.error(f'Error running single condition: {e}')

    @staticmethod
    def scheduler_start():
        """?��?줄러 ?�작"""
        from .setup import PluginModelSetting
        from framework.job import Job
        from .model import ConditionSchedule
        try:
            from framework.job import Job
            
            # ?�체 ?�크리닝 ?��?�?            if PluginModelSetting.get('auto_start') == 'True':
                screening_time = PluginModelSetting.get('screening_time')
                hour, minute = map(int, screening_time.split(':'))
                default_strategy = PluginModelSetting.get('default_strategy')
                
                Job.scheduler.add_job(
                    id=f'{package_name}_auto',
                    name='자동 스크리닝',
                    func=Logic.start_screening,
                    kwargs={'strategy_id': default_strategy, 'execution_type': 'auto'},
                    trigger='cron',
                    hour=hour,
                    minute=minute,
                    day_of_week='mon-fri',
                    replace_existing=True
                )
                logger.info(f"Scheduler started: {screening_time} with strategy {default_strategy}")

            # ?�략/개별 조건 ?��?�?            schedules = db.session.query(ConditionSchedule).filter_by(is_enabled=True).all()
            for schedule in schedules:
                if schedule.condition_number == 0:
                    # ?�략 ?�체 ?�크리닝 ?��?�?                    job_id = f'{package_name}_strategy_{schedule.strategy_id}'
                    Job.scheduler.add_job(
                        id=job_id,
                        name=f'전략: {schedule.strategy_id}',
                        func=Logic.start_screening,
                        kwargs={'strategy_id': schedule.strategy_id, 'execution_type': 'auto'},
                        trigger='cron',
                        **cron_to_dict(schedule.cron_expression)
                    )
                    logger.info(f'Scheduled strategy {job_id} with cron: {schedule.cron_expression}')
                else:
                    # 개별 조건 ?��?�?                    job_id = f'{package_name}_condition_{schedule.strategy_id}_{schedule.condition_number}'
                    Job.scheduler.add_job(
                        id=job_id,
                        name=f'개별 조건: {schedule.strategy_id} #{schedule.condition_number}',
                        func=Logic.run_single_condition,
                        kwargs={'strategy_id': schedule.strategy_id, 'condition_number': schedule.condition_number},
                        trigger='cron',
                        **cron_to_dict(schedule.cron_expression)
                    )
                    logger.info(f'Scheduled condition {job_id} with cron: {schedule.cron_expression}')

            # 매매 ?�향 분석 ?��?�?(매일 ?�전 9??- ???�작 ??
            from .trading_trend_analyzer import analyze_trading_trends
            Job.scheduler.add_job(
                id=f'{package_name}_trend',
                name='매매 동향 분석',
                func=analyze_trading_trends,
                trigger='cron',
                hour=9,
                minute=0,
                day_of_week='mon-fri',
                replace_existing=True
            )
            logger.info(f"매매 ?�향 분석 ?��?�?추�?: 매일 ?�전 9??)

            # DB ?�리 ?��?�?(매일 ?�벽 2??
            Job.scheduler.add_job(
                id=f'{package_name}_cleanup',
                name='DB 정리',
                func=Logic.task_cleanup_old_data if F.config['use_celery'] else Logic.cleanup_old_data,
                trigger='cron',
                hour=2,
                minute=0,
                replace_existing=True
            )
            logger.info(f"DB ?�리 ?��?�?추�?: 매일 ?�전 2??)

        except Exception as e:
            logger.error(f"Scheduler start error: {str(e)}")
    
    
    @staticmethod
    def scheduler_stop():
        """?��?줄러 중�?"""
        from framework.job import Job
        from .model import ConditionSchedule
        try:
            # 플러그인 관련 스케줄만 삭제 (전체 제거는 위험할 수 있음)
            package_specific_jobs = [job for job in Job.scheduler.get_jobs() 
                                     if job.id.startswith(package_name)]
            
            for job in package_specific_jobs:
                Job.scheduler.remove_job(job.id)
                logger.info(f"Removed job: {job.id}")
                
            logger.info(f"Package '{package_name}' scheduler jobs stopped")
        except Exception as e:
            logger.error(f"Scheduler stop error: {str(e)}")

    @staticmethod
    @celery.task(bind=True)
    def task_scheduler_restart(self):
        """Celery ?�업?�로 ?��?줄러 ?�시??""
        logger.info("Restarting scheduler via Celery task...")
        Logic.scheduler_stop()
        Logic.scheduler_start()
        logger.info("Scheduler restart task completed.")

def cron_to_dict(cron_expression):
    """Cron ?�현?�을 APScheduler trigger ?�자�?변??""
    parts = cron_expression.split()
    if len(parts) != 5:
        raise ValueError("Invalid cron expression")
    return {
        'minute': parts[0],
        'hour': parts[1],
        'day': parts[2],
        'month': parts[3],
        'day_of_week': parts[4],
    }
