# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Main Logic (Strategy System)
전략 시스템 통합 메인 로직
"""
import time
import json
from datetime import datetime, date
from framework import db, socketio
# from framework.logger import get_logger
from .setup import *



# logger = get_logger(__name__)  <-- 이 줄을 삭제하고
logger = P.logger                # <-- 이 줄을 추가합니다.
# package_name = '7split_checklist_21' <-- 이 줄을 삭제하고
package_name = P.package_name    # <-- 이 줄을 추가합니다. (표준 방식)


class Logic:
    """메인 로직 클래스 (전략 시스템)"""
    
    db_default = {
        'dart_api_key': '',
        'discord_webhook_url': '',
        'auto_start': 'False',
        'screening_time': '09:00',
        'default_strategy': 'seven_split_21',  # 기본 전략
        'notification_discord': 'True',
        'use_multiprocessing': 'False',
        'screening_interval_days': '1',

        # seven_split_21 & seven_split_mini
        'min_market_cap': '1000',
        'max_debt_ratio': '300',
        'min_retention_ratio': '100',
        'min_trading_value': '10',
        'min_roe_avg': '15',
        'min_pbr': '1.0',
        'min_per': '10.0',
        'min_div_yield': '3.0',
        'min_pcr': '10.0',
        'min_psr': '1.0',
        'min_fscore': '5',
        'min_major_shareholder_ratio': '30',

        # dividend_strategy
        'min_market_cap_dividend': '500',
        'min_div_yield_dividend': '5.0',
        'min_dividend_payout': '20',
        'max_dividend_payout': '80',
        'max_debt_ratio_dividend': '200',
        'min_trading_value_dividend': '5',

        # value_investing
        'min_market_cap_value': '300',
        'max_per_value': '15.0',
        'min_pbr_value': '0.3',
        'max_pbr_value': '1.5',
        'max_debt_ratio_value': '200',
        'min_current_ratio_value': '150',
        'min_roe_value': '8',
        'min_trading_value_value': '3',

    }
    
    
    @staticmethod
    def db_init():
        """DB 초기화"""
        from model import ModelSetting
        try:
            for key, value in Logic.db_default.items():
                if db.session.query(ModelSetting).filter_by(key=key).count() == 0:
                    db.session.add(ModelSetting(key, value))
            db.session.commit()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"DB init error: {str(e)}")
            db.session.rollback()
    
    
    @staticmethod
    def get_setting(key):
        """설정 값 가져오기"""
        from model import ModelSetting
        try:
            setting = db.session.query(ModelSetting).filter_by(key=key).first()
            if setting:
                return setting.value
            return Logic.db_default.get(key, '')
        except Exception as e:
            logger.error(f"Get setting error: {str(e)}")
            return Logic.db_default.get(key, '')
    
    
    @staticmethod
    def set_setting(key, value):
        """설정 값 저장"""
        from model import ModelSetting
        try:
            setting = db.session.query(ModelSetting).filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                db.session.add(ModelSetting(key, value))
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Set setting error: {str(e)}")
            db.session.rollback()
            return False
    
    
    @staticmethod
    def get_available_strategies():
        """사용 가능한 전략 목록"""
        from strategies import get_all_strategies
        return get_all_strategies()
    
    
    @staticmethod
    def get_strategies_metadata():
        """전략 메타데이터 목록"""
        from strategies import get_strategies_info
        return get_strategies_info()
    
    
    @staticmethod
    def start_screening(strategy_id=None, execution_type='manual'):
        """
        스크리닝 시작 (전략 선택 가능)
        
        Args:
            strategy_id (str): 사용할 전략 ID (None이면 기본 전략)
            execution_type (str): 'auto' or 'manual'
        
        Returns:
            dict: 실행 결과
        """
        from strategies import get_strategy
        from model import StockScreeningResult, ScreeningHistory, FilterDetail, ModelSetting
        from logic_collector import DataCollector
        from logic_calculator import Calculator
        from logic_notifier import Notifier
        start_time = time.time()
        from strategies import get_strategy
        
        # 기본 전략 설정
        if strategy_id is None:
            strategy_id = Logic.get_setting('default_strategy')
        
        # 전략 로드
        strategy = get_strategy(strategy_id)
        
        if not strategy:
            error_msg = f"존재하지 않는 전략: {strategy_id}"
            logger.error(error_msg)
            return {'success': False, 'message': error_msg}

        required_data = strategy.required_data
        
        logger.info(f"Starting screening with strategy: {strategy.strategy_name}")
        
        try:
            # 스크리닝 히스토리 생성
            history = ScreeningHistory()
            history.execution_date = datetime.now()
            history.execution_type = execution_type
            history.status = 'running'
            db.session.add(history)
            db.session.commit()
            
            # 설정 로드
            dart_api_key = Logic.get_setting('dart_api_key')
            webhook_url = Logic.get_setting('discord_webhook_url')
            
            if not dart_api_key:
                error_msg = "DART API Key가 설정되지 않았습니다."
                logger.error(error_msg)
                history.status = 'failed'
                history.error_message = error_msg
                db.session.commit()
                return {'success': False, 'message': error_msg}
            
            # 데이터 수집기 초기화
            collector = DataCollector(dart_api_key=dart_api_key)
            calculator = Calculator()
            notifier = Notifier(webhook_url=webhook_url)
            
            # 전체 종목 수집
            logger.info("Collecting all tickers...")
            all_tickers = collector.get_all_tickers()
            total_stocks = len(all_tickers)
            
            if total_stocks == 0:
                error_msg = "종목 수집 실패"
                logger.error(error_msg)
                history.status = 'failed'
                history.error_message = error_msg
                db.session.commit()
                return {'success': False, 'message': error_msg}
            
            history.total_stocks = total_stocks
            db.session.commit()
            
            # Discord 시작 알림
            if Logic.get_setting('notification_discord') == 'True':
                notifier.send_start_notification(total_stocks, strategy.strategy_name)
            
            # 스크리닝 실행
            logger.info(f"Screening {total_stocks} stocks with {strategy.strategy_name}...")
            passed_stocks = []
            filter_stats = {i: {'passed': 0, 'failed': 0} for i in strategy.conditions.keys()}
            
            today = date.today()

            # 이전 필터링 상세 데이터 삭제
            try:
                db.session.query(FilterDetail).filter_by(screening_date=today).delete()
                db.session.commit()
            except Exception as e:
                logger.error(f"Failed to delete previous filter details: {str(e)}")
                db.session.rollback()
            
            for idx, ticker_info in enumerate(all_tickers):
                try:
                    # 진행 상황 전송 (10개마다)
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
                    
                    # 데이터 수집
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
                    
                    # F-Score (데이터 충분하면 계산)
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
                    
                    # 종목 데이터 구성
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
                    
                    # 선택한 전략 적용
                    passed, condition_details = strategy.apply_filters(stock_data)
                    
                    # 조건별 통계 업데이트
                    for condition_num, result in condition_details.items():
                        if result:
                            filter_stats[condition_num]['passed'] += 1
                        else:
                            filter_stats[condition_num]['failed'] += 1

                    # 필터 상세 정보 저장
                    for condition_num, passed_status in condition_details.items():
                        filter_detail = FilterDetail(
                            screening_date=today,
                            condition_number=condition_num,
                            condition_name=strategy.conditions.get(condition_num, 'N/A'),
                            total_before=idx + 1,
                            passed=filter_stats[condition_num]['passed'],
                            failed=filter_stats[condition_num]['failed']
                        )
                        db.session.merge(filter_detail)

                    
                    # DB 저장
                    result_record = StockScreeningResult()
                    result_record.code = code
                    result_record.name = name
                    result_record.market = market
                    result_record.screening_date = today
                    result_record.strategy_name = strategy_id  # 전략 이름 저장
                    result_record.strategy_version = strategy.version
                    result_record.passed = passed
                    result_record.is_managed = '관리' in stock_data.get('status', '').upper()
                    result_record.is_suspended = '거래정지' in stock_data.get('status', '').upper() or 'HALT' in stock_data.get('status', '').upper()
                    result_record.is_caution = '환기' in stock_data.get('status', '').upper() or 'CAUTION' in stock_data.get('status', '').upper()
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
                    
                    db.session.add(result_record)
                    
                    if passed:
                        passed_stocks.append(stock_data)
                    
                    # 100개마다 커밋
                    if idx % 100 == 0:
                        db.session.commit()
                    
                    # API 제한 회피
                    time.sleep(0.05)
                    
                except Exception as e:
                    logger.error(f"Error processing {code}: {str(e)}")
                    continue
            
            # 최종 커밋
            db.session.commit()
            
            # 실행 시간 계산
            execution_time = time.time() - start_time
            
            # 히스토리 업데이트
            history.passed_stocks = len(passed_stocks)
            history.execution_time = execution_time
            history.filter_statistics = json.dumps(filter_stats)
            history.status = 'completed'
            db.session.commit()
            
            # Discord 알림
            if Logic.get_setting('notification_discord') == 'True':
                notifier.send_screening_result(
                    passed_stocks, 
                    total_stocks, 
                    execution_time,
                    strategy.strategy_name
                )
            
            # 완료 알림 (SocketIO)
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
            
            # 히스토리 업데이트
            try:
                history.status = 'failed'
                history.error_message = error_msg
                db.session.commit()
            except:
                pass
            
            # 에러 알림
            if Logic.get_setting('notification_discord') == 'True':
                notifier = Notifier(webhook_url=Logic.get_setting('discord_webhook_url'))
                notifier.send_error_notification(error_msg)
            
            return {'success': False, 'message': error_msg}
    
    
    @staticmethod
    def save_condition_schedules(schedules):
        """개별 조건 스케줄 저장"""
        from model import ConditionSchedule
        try:
            # 기존 스케줄 모두 삭제
            db.session.query(ConditionSchedule).delete()

            for schedule_data in schedules:
                schedule = ConditionSchedule(
                    strategy_id=schedule_data['strategy_id'],
                    condition_number=schedule_data['condition_number'],
                    cron_expression=schedule_data['cron_expression'],
                    is_enabled=schedule_data['is_enabled']
                )
                db.session.add(schedule)
            
            db.session.commit()
            Logic.scheduler_stop()
            Logic.scheduler_start()
            return True

        except Exception as e:
            logger.error(f'Failed to save condition schedules: {e}')
            db.session.rollback()
            return False

    @staticmethod
    def run_single_condition(strategy_id, condition_number):
        """단일 조건 실행"""
        from strategies import get_strategy
        from logic_collector import DataCollector
        from logic_notifier import Notifier
        try:
            logger.info(f'Running single condition: {strategy_id} - {condition_number}')
            
            strategy = get_strategy(strategy_id)
            if not strategy:
                logger.error(f'Strategy not found: {strategy_id}')
                return

            condition_name = strategy.conditions.get(condition_number, 'N/A')
            logger.info(f'Condition name: {condition_name}')

            collector = DataCollector(dart_api_key=Logic.get_setting('dart_api_key'))
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

            notifier = Notifier(webhook_url=Logic.get_setting('discord_webhook_url'))
            notifier.send_condition_result_notification(strategy_id, condition_number, result)

        except Exception as e:
            logger.error(f'Error running single condition: {e}')

    @staticmethod
    def scheduler_start():
        """스케줄러 시작"""
        from framework.job import Job
        from model import ConditionSchedule
        try:
            from framework.job import Job
            
            # 전체 스크리닝 스케줄
            if Logic.get_setting('auto_start') == 'True':
                screening_time = Logic.get_setting('screening_time')
                hour, minute = map(int, screening_time.split(':'))
                default_strategy = Logic.get_setting('default_strategy')
                
                Job.scheduler.add_job(
                    id=f'{package_name}_auto',
                    func=Logic.start_screening,
                    kwargs={'strategy_id': default_strategy, 'execution_type': 'auto'},
                    trigger='cron',
                    hour=hour,
                    minute=minute,
                    day_of_week='mon-fri',
                    replace_existing=True
                )
                logger.info(f"Scheduler started: {screening_time} with strategy {default_strategy}")

            # 개별 조건 스케줄
            schedules = db.session.query(ConditionSchedule).filter_by(is_enabled=True).all()
            for schedule in schedules:
                job_id = f'{package_name}_condition_{schedule.strategy_id}_{schedule.condition_number}'
                Job.scheduler.add_job(
                    id=job_id,
                    func=Logic.run_single_condition,
                    kwargs={'strategy_id': schedule.strategy_id, 'condition_number': schedule.condition_number},
                    trigger='cron',
                    **cron_to_dict(schedule.cron_expression)
                )
                logger.info(f'Scheduled condition {job_id} with cron: {schedule.cron_expression}')

        except Exception as e:
            logger.error(f"Scheduler start error: {str(e)}")
    
    
    @staticmethod
    def scheduler_stop():
        """스케줄러 중지"""
        from framework.job import Job
        from model import ConditionSchedule
        try:
            from framework.job import Job
            Job.scheduler.remove_job(f'{package_name}_auto')
            schedules = db.session.query(ConditionSchedule).all()
            for schedule in schedules:
                job_id = f'{package_name}_condition_{schedule.strategy_id}_{schedule.condition_number}'
                try:
                    Job.scheduler.remove_job(job_id)
                except Exception as e:
                    logger.debug(f'Failed to remove job {job_id}: {e}')
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.debug(f"Scheduler stop error: {str(e)}")

def cron_to_dict(cron_expression):
    """Cron 표현식을 APScheduler trigger 인자로 변환"""
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