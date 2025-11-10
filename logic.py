# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Main Logic (Strategy System)
전략 시스템 통합 메인 로직
"""
import time
import json
import traceback
from datetime import datetime, date, timedelta

# framework 의존성을 가진 모듈은 각 함수 내부에서 import 합니다.
from .setup import P
# Celery task decorator를 위해 모듈 레벨에서 import 시도.
# 테스트 환경 등 framework 모듈이 없을 경우를 대비해 dummy decorator 생성.
try:
    from framework import celery
except ImportError:
    def dummy_decorator(*args, **kwargs):
        def wrapper(func):
            return func
        return wrapper
    celery = type('celery', (), {'task': dummy_decorator})

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
        """플러그인 설정을 가져옵니다."""
        from .setup import PluginModelSetting
        return PluginModelSetting.get(key, default=default)

    @staticmethod
    def get_available_strategies():
        """사용 가능한 전략 목록"""
        from .strategies import get_all_strategies
        return get_all_strategies()

    @staticmethod
    def get_strategies_metadata():
        """전략 메타데이터 목록"""
        from .strategies import get_strategies_info
        return get_strategies_info()

    @staticmethod
    def start_screening(strategy_id=None, execution_type='manual'):
        """스크리닝 시작"""
        logger.info(f"Logic.start_screening 시작: strategy_id={strategy_id}, execution_type={execution_type}")
        try:
            if F.config['use_celery']:
                logger.info(f"Celery를 통해 스크리닝 시작: strategy_id={strategy_id}, type={execution_type}")
                result = Logic.task_start_screening.apply_async((strategy_id, execution_type))
                logger.info(f"Celery 작업 시작: {result.id}")
                return {'success': True, 'message': f'Celery 작업 시작: {result.id}'}
            else:
                logger.info(f"동기적으로 스크리닝 시작: strategy_id={strategy_id}, type={execution_type}")
                result = Logic.task_start_screening(strategy_id, execution_type)
                logger.info("스크리닝 동기 실행 완료")
                return result
        except Exception as e:
            logger.error(f"start_screening 오류: {str(e)}")
            logger.error(traceback.format_exc())
            return {'success': False, 'message': f'스크리닝 시작 실패: {str(e)}'}

    @staticmethod
    def cleanup_old_data():
        """오래된 데이터 정리"""
        from .setup import PluginModelSetting
        from .model import StockScreeningResult, ScreeningHistory, FilterDetail
        
        try:
            retention_days_str = PluginModelSetting.get('db_retention_days') or '30'
            retention_days = int(retention_days_str)
            cleanup_enabled_str = PluginModelSetting.get('db_cleanup_enabled') or 'True'
            cleanup_enabled = cleanup_enabled_str == 'True'

            if not cleanup_enabled:
                logger.info("DB 정리가 비활성화되어 있습니다.")
                return {'success': True, 'message': 'DB 정리가 비활성화되어 있습니다.'}

            cutoff_date = datetime.now().date() - timedelta(days=retention_days)

            # 오래된 데이터 삭제
            old_results_deleted = db.session.query(StockScreeningResult).filter(StockScreeningResult.screening_date < cutoff_date).delete()
            old_histories_deleted = db.session.query(ScreeningHistory).filter(ScreeningHistory.execution_date < cutoff_date).delete()
            old_details_deleted = db.session.query(FilterDetail).filter(FilterDetail.created_at < cutoff_date).delete()
            
            db.session.commit()

            message = f'{retention_days}일 이상 된 {old_results_deleted}건의 결과, {old_histories_deleted}건의 이력, {old_details_deleted}건의 상세 데이터를 삭제했습니다.'
            logger.info(f"DB 정리 완료: {message}")

            return {
                'success': True,
                'message': message,
                'deleted': {
                    'results': old_results_deleted,
                    'histories': old_histories_deleted,
                    'details': old_details_deleted
                }
            }

        except Exception as e:
            logger.error(f"DB 정리 오류: {str(e)}")
            db.session.rollback()
            return {'success': False, 'message': f'DB 정리 오류: {str(e)}'}

    @staticmethod
    @celery.task(bind=True)
    def task_cleanup_old_data(self):
        """Celery 작업으로 오래된 데이터 정리"""
        return Logic.cleanup_old_data()

    @staticmethod
    @celery.task(bind=True)
    def task_start_screening(self, strategy_id=None, execution_type='manual'):
        """
        스크리닝 작업 (전략 선택 가능)
        
        Args:
            strategy_id (str): 사용할 전략 ID (None이면 기본 전략)
            execution_type (str): 'auto' or 'manual'
        
        Returns:
            dict: 실행 결과
        """
        from .setup import PluginModelSetting
        from .strategies import get_strategy as get_strategy_func
        from .model import StockScreeningResult, ScreeningHistory, FilterDetail
        from .logic_collector import DataCollector
        from .logic_calculator import Calculator
        from .logic_notifier import Notifier
        
        start_time = time.time()
        history = None
        
        logger.info(f"스크리닝 작업 호출: strategy_id={strategy_id}, execution_type={execution_type}")
        
        try:
            # 기본 전략 설정
            if strategy_id is None:
                strategy_id = PluginModelSetting.get('default_strategy')
                logger.debug(f"기본 전략 사용: {strategy_id}")
            
            # 전략 로드
            strategy = get_strategy_func(strategy_id)
            if not strategy:
                raise ValueError(f"존재하지 않는 전략: {strategy_id}")

            logger.info(f"전략 로드 성공: {strategy.strategy_name} (ID: {strategy_id})")
            
            # 스크리닝 히스토리 생성
            history = ScreeningHistory(
                execution_date=datetime.now(),
                execution_type=execution_type,
                status='running',
                strategy_name=strategy_id
            )
            history.save()
            
            # 설정 로드
            dart_api_key = PluginModelSetting.get('dart_api_key')
            if not dart_api_key:
                raise ValueError("DART API Key가 설정되지 않았습니다.")
            
            webhook_url = PluginModelSetting.get('discord_webhook_url')
            
            # 모듈 초기화
            collector = DataCollector(dart_api_key=dart_api_key)
            calculator = Calculator()
            notifier = Notifier(webhook_url=webhook_url)
            
            # 전체 종목 수집
            all_tickers = collector.get_all_tickers()
            total_stocks = len(all_tickers)
            if total_stocks == 0:
                raise ValueError("수집된 종목이 없습니다.")
            
            history.total_stocks = total_stocks
            history.save()
            
            # 시작 알림
            if PluginModelSetting.get('notification_discord') == 'True':
                notifier.send_start_notification(total_stocks, strategy.strategy_name)
            
            # 스크리닝 실행
            logger.info(f"{total_stocks}개 종목을 '{strategy.strategy_name}' 전략으로 스크리닝합니다...")
            passed_stocks = []
            filter_stats = {i: {'passed': 0, 'failed': 0} for i in strategy.conditions.keys()}
            today = date.today()

            # 이전 필터 상세 데이터 삭제
            db.session.query(FilterDetail).filter_by(screening_date=today).delete()
            db.session.commit()
                
            for idx, ticker_info in enumerate(all_tickers):
                code = ticker_info['code']
                try:
                    # 진행 상황 전송 (10개마다)
                    if idx % 10 == 0:
                        progress = {
                            'current': idx, 'total': total_stocks,
                            'percent': round((idx / total_stocks) * 100, 1),
                            'strategy': strategy.strategy_name
                        }
                        socketio.emit('7split_screening_progress', progress, namespace='/framework', broadcast=True)
                    
                    # 데이터 수집 및 계산
                    stock_data = collector.get_all_data_for_ticker(code, strategy.required_data)
                    calculated_data = calculator.calculate_all_metrics(stock_data)
                    stock_data.update(calculated_data)
                    
                    # 전략 적용
                    passed, condition_details = strategy.apply_filters(stock_data)
                    
                    # 통계 업데이트
                    for num, res in condition_details.items():
                        filter_stats[num]['passed' if res else 'failed'] += 1

                    # 필터 상세 정보 저장
                    for num, passed_status in condition_details.items():
                        filter_detail = FilterDetail(
                            screening_date=today, condition_number=num,
                            condition_name=strategy.conditions.get(num, 'N/A'),
                            total_before=idx + 1, passed=filter_stats[num]['passed'],
                            failed=filter_stats[num]['failed']
                        )
                        db.session.merge(filter_detail)
                    
                    # 결과 저장
                    result_record = StockScreeningResult.from_dict(stock_data, strategy_id, strategy.version, passed, condition_details)
                    db.session.merge(result_record)
                    
                    if passed:
                        passed_stocks.append(stock_data)
                    
                    # 100개마다 커밋
                    if (idx + 1) % 100 == 0:
                        db.session.commit()
                        logger.debug(f"중간 커밋: {idx+1}/{total_stocks}")
                    
                    time.sleep(0.05)
                    
                except Exception as e:
                    logger.error(f"{code} 처리 중 오류: {str(e)}")
                    logger.debug(traceback.format_exc())
                    continue
            
            db.session.commit()
            
            # 실행 시간 및 히스토리 업데이트
            execution_time = time.time() - start_time
            history.passed_stocks = len(passed_stocks)
            history.execution_time = execution_time
            history.filter_statistics = json.dumps(filter_stats)
            history.status = 'completed'
            history.save()
            
            # 완료 알림
            if PluginModelSetting.get('notification_discord') == 'True':
                notifier.send_screening_result(passed_stocks, total_stocks, execution_time, strategy.strategy_name)
            
            socketio.emit('7split_screening_complete', {
                'total': total_stocks, 'passed': len(passed_stocks),
                'time': execution_time, 'strategy': strategy.strategy_name
            }, namespace='/framework', broadcast=True)
            
            logger.info(f"스크리닝 완료: {len(passed_stocks)}/{total_stocks} 통과 ({execution_time:.1f}초 소요, 전략: {strategy.strategy_name})")
            
            return {
                'success': True, 'strategy': strategy_id, 'strategy_name': strategy.strategy_name,
                'total_stocks': total_stocks, 'passed_stocks': len(passed_stocks),
                'execution_time': execution_time
            }
            
        except Exception as e:
            error_msg = f"스크리닝 오류: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            if history:
                history.status = 'failed'
                history.error_message = str(e)
                history.save()
            
            from .setup import PluginModelSetting
            if PluginModelSetting.get('notification_discord') == 'True':
                webhook_url = PluginModelSetting.get('discord_webhook_url')
                if webhook_url:
                    Notifier(webhook_url=webhook_url).send_error_notification(error_msg)
            
            return {'success': False, 'message': error_msg}

    @staticmethod
    def save_condition_schedules(schedules):
        """개별 조건 스케줄 저장"""
        logger.info(f"{len(schedules)}개 스케줄 저장 중")
        try:
            if F.config['use_celery']:
                Logic.task_save_condition_schedules.apply_async((schedules,))
                return True
            else:
                return Logic.task_save_condition_schedules(schedules)
        except Exception as e:
            logger.error(f"스케줄 저장 오류: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    @celery.task(bind=True)
    def task_save_condition_schedules(self, schedules):
        """Celery 작업으로 스케줄 저장"""
        from .model import ConditionSchedule
        try:
            with app.app_context():
                db.session.query(ConditionSchedule).delete()
                for data in schedules:
                    schedule = ConditionSchedule(
                        strategy_id=data['strategy_id'],
                        condition_number=data['condition_number'],
                        cron_expression=data['cron_expression'],
                        is_enabled=data['is_enabled']
                    )
                    db.session.add(schedule)
                db.session.commit()
                
                logger.info("스케줄 저장 완료, 스케줄러 재시작")
                Logic.scheduler_stop()
                Logic.scheduler_start()
                return True
        except Exception as e:
            logger.error(f'스케줄 저장 실패: {e}')
            logger.error(traceback.format_exc())
            db.session.rollback()
            return False

    @staticmethod
    def run_single_condition(strategy_id, condition_number):
        """단일 조건 실행"""
        from .setup import PluginModelSetting
        from .strategies import get_strategy as get_strategy_func
        from .logic_collector import DataCollector
        from .logic_notifier import Notifier
        try:
            logger.info(f'단일 조건 실행: {strategy_id} - {condition_number}')
            strategy = get_strategy_func(strategy_id)
            if not strategy:
                raise ValueError(f"전략을 찾을 수 없음: {strategy_id}")

            collector = DataCollector(dart_api_key=PluginModelSetting.get('dart_api_key'))
            all_tickers = collector.get_all_tickers()

            passed_count = 0
            for ticker_info in all_tickers:
                try:
                    stock_data = collector.get_all_data_for_ticker(ticker_info['code'], strategy.required_data)
                    _, condition_details = strategy.apply_filters(stock_data)
                    if condition_details.get(condition_number, False):
                        passed_count += 1
                except Exception as e:
                    logger.error(f'{ticker_info["code"]} 처리 중 오류: {e}')

            result = {'passed': passed_count, 'total': len(all_tickers)}
            Notifier(webhook_url=PluginModelSetting.get('discord_webhook_url')).send_condition_result_notification(strategy_id, condition_number, result)

        except Exception as e:
            logger.error(f'단일 조건 실행 오류: {e}')

    @staticmethod
    def scheduler_start():
        """스케줄러 시작"""
        from .setup import PluginModelSetting
        from framework.job import Job
        from .model import ConditionSchedule
        try:
            # 전체 스크리닝 스케줄
            if PluginModelSetting.get('auto_start') == 'True':
                screening_time = PluginModelSetting.get('screening_time')
                hour, minute = map(int, screening_time.split(':'))
                Job.scheduler.add_job(
                    id=f'{package_name}_auto', name='자동 스크리닝',
                    func=Logic.start_screening,
                    kwargs={'strategy_id': PluginModelSetting.get('default_strategy'), 'execution_type': 'auto'},
                    trigger='cron', hour=hour, minute=minute, day_of_week='mon-fri',
                    replace_existing=True
                )
                logger.info(f"자동 스크리닝 스케줄 시작: 매일 {screening_time}")

            # 개별 조건/전략 스케줄
            schedules = db.session.query(ConditionSchedule).filter_by(is_enabled=True).all()
            for schedule in schedules:
                func = Logic.start_screening if schedule.condition_number == 0 else Logic.run_single_condition
                kwargs = {'strategy_id': schedule.strategy_id}
                if schedule.condition_number != 0:
                    kwargs['condition_number'] = schedule.condition_number
                
                job_id = f'{package_name}_{schedule.strategy_id}_{schedule.condition_number}'
                Job.scheduler.add_job(
                    id=job_id, name=f'스케줄: {job_id}', func=func, kwargs=kwargs,
                    trigger='cron', **cron_to_dict(schedule.cron_expression)
                )
                logger.info(f'스케줄 등록: {job_id} ({schedule.cron_expression})')

            # 매매 동향 분석 스케줄
            from .trading_trend_analyzer import analyze_trading_trends
            Job.scheduler.add_job(
                id=f'{package_name}_trend', name='매매 동향 분석', func=analyze_trading_trends,
                trigger='cron', hour=9, minute=0, day_of_week='mon-fri', replace_existing=True
            )
            logger.info("매매 동향 분석 스케줄 추가: 매일 오전 9시")

            # DB 정리 스케줄
            Job.scheduler.add_job(
                id=f'{package_name}_cleanup', name='DB 정리',
                func=Logic.task_cleanup_old_data if F.config['use_celery'] else Logic.cleanup_old_data,
                trigger='cron', hour=2, minute=0, replace_existing=True
            )
            logger.info("DB 정리 스케줄 추가: 매일 오전 2시")

        except Exception as e:
            logger.error(f"스케줄러 시작 오류: {str(e)}")

    @staticmethod
    def scheduler_stop():
        """스케줄러 중지"""
        from framework.job import Job
        try:
            for job in Job.scheduler.get_jobs():
                if job.id.startswith(package_name):
                    Job.scheduler.remove_job(job.id)
                    logger.info(f"삭제된 스케줄: {job.id}")
        except Exception as e:
            logger.error(f"스케줄러 중지 오류: {str(e)}")

    @staticmethod
    @celery.task(bind=True)
    def task_scheduler_restart(self):
        """Celery 작업으로 스케줄러 재시작"""
        logger.info("Celery를 통해 스케줄러 재시작 중...")
        Logic.scheduler_stop()
        Logic.scheduler_start()
        logger.info("스케줄러 재시작 완료.")

def cron_to_dict(cron_expression):
    """Cron 표현식을 APScheduler trigger 인자로 변환"""
    parts = cron_expression.split()
    if len(parts) != 5:
        raise ValueError("잘못된 Cron 표현식")
    return {'minute': parts[0], 'hour': parts[1], 'day': parts[2], 'month': parts[3], 'day_of_week': parts[4]}