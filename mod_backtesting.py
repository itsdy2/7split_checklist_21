# -*- coding: utf-8 -*-
import traceback
import json
from datetime import datetime
from plugin import *
from .setup import P
from framework import db
from .backtesting import BacktestingEngine, BacktestingHistory
from .strategies import get_strategies_info


class ModuleBacktesting(PluginModuleBase):
    # Define the db_default directly to avoid import during initialization
    _db_default = {
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
        'db_max_size_gb': '5',
        'trend_market': 'ALL',
        'trend_top_n': '30',
        'trend_show_market_column': 'True',
        'trend_send_discord': 'True',
        'trend_send_insight': 'True',
        'trend_send_1day': 'True',
        'trend_send_1week': 'True',
        'trend_send_1month': 'True',
        'backtest_start_date': '2014-01-01',
        'backtest_end_date': datetime.now().strftime('%Y-%m-%d'),
        'backtest_initial_capital': '100000000',  # 1억
        'backtest_rebalance_interval': 'monthly',
    }

    def __init__(self, P):
        super(ModuleBacktesting, self).__init__(P, name='backtesting', first_menu='backtest')
        self.db_default = ModuleBacktesting._db_default
        P.logger.info("ModuleBacktesting initialized")

    def process_menu(self, page, req):
        P.logger.info(f"ModuleBacktesting.process_menu called: page={page}")
        try:
            arg = P.ModelSetting.to_dict()
            
            if page is None:
                page = 'backtest'

            if page == 'backtest':
                template_name = f'{P.package_name}_{self.name}_{page}.html'
                
                # 전략 정보 로드
                strategies = get_strategies_info()
                arg['strategies'] = strategies
                arg['default_strategy'] = P.ModelSetting.get('default_strategy')
                
                return render_template(template_name, arg=arg, P=P)
                
            elif page == 'history':
                template_name = f'{P.package_name}_{self.name}_{page}.html'
                
                # 백테스팅 이력 조회
                page_num = req.args.get('page', 1, type=int)
                per_page = req.args.get('per_page', 20, type=int)
                
                pagination = db.session.query(BacktestingHistory).order_by(
                    BacktestingHistory.created_at.desc()
                ).paginate(page=page_num, per_page=per_page, error_out=False)
                
                arg['histories'] = pagination.items
                arg['pagination'] = pagination
                
                return render_template(template_name, arg=arg, P=P)

            else:
                return f"<div class='container'><h3>알 수 없는 메뉴: {page}</h3></div>"

        except Exception as e:
            P.logger.error(f"Error in menu '{page}': {str(e)}")
            P.logger.error(traceback.format_exc())
            return f"""
            <div class='container'>
                <div class='alert alert-danger'>
                    <h3>오류 발생</h3>
                    <p><strong>에러:</strong> {str(e)}</p>
                    <pre>{traceback.format_exc()}</pre>
                </div>
            </div>
            """

    def process_ajax(self, sub, req):
        try:
            if sub == 'run_backtest':
                # 백테스팅 실행
                strategy_id = req.form.get('strategy_id')
                start_date = req.form.get('start_date', P.ModelSetting.get('backtest_start_date'))
                end_date = req.form.get('end_date', P.ModelSetting.get('backtest_end_date'))
                initial_capital = int(req.form.get('initial_capital', P.ModelSetting.get('backtest_initial_capital')))
                rebalance_interval = req.form.get('rebalance_interval', P.ModelSetting.get('backtest_rebalance_interval'))
                
                # 백테스팅 엔진 생성
                dart_api_key = P.ModelSetting.get('dart_api_key')
                engine = BacktestingEngine(dart_api_key=dart_api_key)
                
                # 백테스팅 실행
                result = engine.run_backtest(
                    strategy_id=strategy_id,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                    rebalance_interval=rebalance_interval
                )
                
                if result['success']:
                    # 이력 저장
                    backtest_result = result['results']
                    history = BacktestingHistory()
                    history.strategy_id = strategy_id
                    history.strategy_name = backtest_result['strategy_name']
                    history.start_date = datetime.strptime(start_date, '%Y-%m-%d')
                    history.end_date = datetime.strptime(end_date, '%Y-%m-%d')
                    history.initial_capital = initial_capital
                    history.final_value = backtest_result['performance_metrics'].get('final_value', 0)
                    history.total_return = backtest_result['performance_metrics'].get('total_return', 0)
                    history.cagr = backtest_result['performance_metrics'].get('cagr', 0)
                    history.sharpe_ratio = backtest_result['performance_metrics'].get('sharpe_ratio', 0)
                    history.backtest_data = json.dumps(backtest_result, default=str)
                    
                    db.session.add(history)
                    db.session.commit()
                    
                    return jsonify({
                        'ret': 'success', 
                        'msg': '백테스팅이 완료되었습니다.', 
                        'data': backtest_result
                    })
                else:
                    return jsonify({'ret': 'error', 'msg': result['error']})
            
            elif sub == 'get_backtest_history':
                # 백테스팅 이력 조회
                histories = db.session.query(BacktestingHistory).order_by(
                    BacktestingHistory.created_at.desc()
                ).limit(10).all()
                
                history_list = []
                for h in histories:
                    history_list.append({
                        'id': h.id,
                        'strategy_name': h.strategy_name,
                        'period': f"{h.start_date.strftime('%Y-%m-%d')} ~ {h.end_date.strftime('%Y-%m-%d')}",
                        'initial_capital': h.initial_capital,
                        'final_value': h.final_value,
                        'total_return': h.total_return,
                        'cagr': h.cagr,
                        'sharpe_ratio': h.sharpe_ratio,
                        'created_at': h.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                return jsonify({'ret': 'success', 'data': history_list})

        except Exception as e:
            P.logger.error(f"Exception in process_ajax: {str(e)}")
            P.logger.error(traceback.format_exc())
            return jsonify({'ret': 'error', 'msg': str(e)})

    def get_scheduler_interval(self):
        """스케줄러 간격을 분 단위로 반환"""
        try:
            # 모듈명_interval 키로 설정된 간격 가져오기 (예: backtesting_interval)
            interval = P.ModelSetting.get(f'{self.name}_interval')
            if interval and interval != 'None' and interval.strip() != '':
                return int(interval)
            else:
                # 기본값: 60분
                return 60
        except (ValueError, TypeError):
            # 변환 실패 시 기본값 반환
            return 60

    def get_scheduler_desc(self):
        """스케줄러 설명 반환"""
        return f"{self.name} 모듈 스케줄러"
    
    def scheduler_function(self):
        """주기적으로 실행될 작업 정의"""
        P.logger.info("Backtesting module scheduler executed")
        
    def setting_save_after(self, change_list):
        """
        설정 저장 후 호출됩니다.
        
        Args:
            change_list: 변경된 설정 키 목록
        """
        from .logic import Logic
        P.logger.debug(f"Backtesting module setting saved. Changed keys: {change_list}")
        
        # 스케줄링 간격이 변경되었다면 스케줄러 재시작
        if f'{self.name}_interval' in change_list:
            Logic.task_scheduler_restart.apply_async()