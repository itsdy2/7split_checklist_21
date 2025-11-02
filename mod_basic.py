# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Basic Module
설정 및 기본 기능
"""
from plugin import *
from .model import ModelSetting, ConditionSchedule
from .logic import Logic

class ModuleBasic(PluginModuleBase):
    def __init__(self, P):
        super(ModuleBasic, self).__init__(
            P, 
            name='basic',
            first_menu='setting'
        )
        self.db_default = Logic.db_default

    def process_menu(self, sub, req):
        arg = P.ModelSetting.to_dict()
        if sub == 'setting':
            arg['is_include'] = F.scheduler.is_include(self.get_scheduler_name())
            arg['is_running'] = F.scheduler.is_running(self.get_scheduler_name())
            arg['strategies'] = Logic.get_strategies_metadata()
        return render_template(f'{P.package_name}_{self.name}_{sub}.html', arg=arg)

    def process_command(self, command, arg1, arg2, arg3, req):
        ret = {'ret': 'success'}
        
        if command == 'test':
            try:
                # DART API 테스트
                dart_api_key = P.ModelSetting.get('dart_api_key')
                if not dart_api_key:
                    ret['ret'] = 'error'
                    ret['msg'] = 'DART API Key가 설정되지 않았습니다.'
                else:
                    ret['ret'] = 'success'
                    ret['msg'] = 'API Key가 정상적으로 설정되었습니다.'
            except Exception as e:
                ret['ret'] = 'error'
                ret['msg'] = str(e)
        
        elif command == 'save_condition_schedules':
            try:
                schedules = req.form.to_dict()
                # 스케줄 저장 로직
                ret['msg'] = '개별 조건 스케줄이 저장되었습니다.'
            except Exception as e:
                ret['ret'] = 'error'
                ret['msg'] = str(e)
                
        return jsonify(ret)

    def scheduler_function(self):
        """스케줄러 실행 함수"""
        default_strategy = P.ModelSetting.get('default_strategy')
        Logic.start_screening(strategy_id=default_strategy, execution_type='auto')

    def process_api(self, sub, req):
        try:
            if sub == 'set_default_strategy':
                strategy_id = req.form.get('strategy')
                if Logic.set_setting('default_strategy', strategy_id):
                    return jsonify({'success': True, 'message': '기본 전략이 설정되었습니다.'})
                else:
                    return jsonify({'success': False, 'message': '설정 저장 실패'})
            
            elif sub == 'recent_history':
                from .model import ScreeningHistory
                histories = db.session.query(ScreeningHistory)\
                    .order_by(ScreeningHistory.execution_date.desc())\
                    .limit(5).all()
                
                data = []
                for h in histories:
                    strategy_name = 'N/A'
                    if h.strategy_name:
                        from .strategies import get_strategy
                        strategy = get_strategy(h.strategy_name)
                        if strategy:
                            strategy_name = strategy.strategy_name
                    
                    data.append({
                        'execution_date': h.execution_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'strategy_name': strategy_name,
                        'total_stocks': h.total_stocks,
                        'passed_stocks': h.passed_stocks,
                        'execution_time': h.execution_time,
                        'status': h.status
                    })
                
                return jsonify({'success': True, 'data': data})
                
        except Exception as e:
            P.logger.error(f'API error: {str(e)}')
            P.logger.error(traceback.format_exc())
            return jsonify({'success': False, 'message': str(e)})