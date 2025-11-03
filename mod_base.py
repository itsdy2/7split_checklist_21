# -*- coding: utf-8 -*-
from .setup import * 
from .logic import Logic

class ModuleBase(PluginModuleBase):
    def __init__(self, P):
        # first_menu 제거 - FlaskFarm이 자동으로 첫 번째 sub 메뉴 사용
        super(ModuleBase, self).__init__(P, name='base', first_menu=None)
        self.db_default = Logic.db_default
        Logic.db_init()
        P.logger.info("ModuleBase initialized")

    def process_menu(self, sub, req):
        P.logger.info(f"ModuleBase.process_menu called: sub={sub}")
        arg = P.ModelSetting.to_dict()
        
        # sub가 None이거나 빈 문자열이면 setting으로 설정
        if not sub or sub == 'base':
            sub = 'setting'
            P.logger.info(f"sub redirected to: {sub}")
        
        if sub == 'setting':
            try:
                # 설정 값 로드
                settings = {}
                for key in self.db_default.keys():
                    settings[key] = Logic.get_setting(key)
                
                # 전략 정보 로드
                try:
                    from strategies import get_strategies_info
                    strategies = get_strategies_info()
                    P.logger.info(f"Loaded {len(strategies)} strategies")
                except Exception as e:
                    P.logger.error(f"Failed to load strategies: {str(e)}")
                    P.logger.error(traceback.format_exc())
                    strategies = []
                
                arg['settings'] = settings
                arg['strategies'] = strategies
                
                template_name = f'{P.package_name}_{self.name}_{sub}.html'
                P.logger.info(f"Rendering template: {template_name}")
                
                return render_template(template_name, arg=arg, settings=settings, strategies=strategies)
                
            except Exception as e:
                P.logger.error(f"Error in setting menu: {str(e)}")
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
        
        P.logger.warning(f"Unknown sub menu: {sub}")
        return f"<div class='container'><h3>알 수 없는 메뉴: {sub}</h3></div>"

    def process_command(self, command, arg1, arg2, arg3, req):
        P.logger.info(f"ModuleBase.process_command: command={command}")
        
        try:
            if command == 'setting_save':
                form_data = req.form.to_dict()
                
                # 설정 저장
                for key in form_data:
                    if not (key.startswith('cron_') or key.startswith('enabled_')):
                        Logic.set_setting(key, form_data[key])
                
                # 개별 조건 스케줄 저장
                schedules = []
                for key, value in form_data.items():
                    if key.startswith('cron_'):
                        parts = key.split('_')
                        if len(parts) >= 3:
                            strategy_id = parts[1]
                            condition_number = int(parts[2])
                            cron_expression = value
                            is_enabled = form_data.get(f'enabled_{strategy_id}_{condition_number}') == 'True'
                            schedules.append({
                                'strategy_id': strategy_id,
                                'condition_number': condition_number,
                                'cron_expression': cron_expression,
                                'is_enabled': is_enabled
                            })
                
                if schedules:
                    Logic.save_condition_schedules(schedules)
                
                # 스케줄러 재시작
                Logic.scheduler_stop()
                Logic.scheduler_start()
                
                return jsonify({'ret': 'success', 'msg': '설정이 저장되었습니다.'})
                
        except Exception as e:
            P.logger.error(f"Command error: {str(e)}")
            P.logger.error(traceback.format_exc())
            return jsonify({'ret': 'error', 'msg': str(e)})
        
        return jsonify({'ret': 'error', 'msg': 'Unknown command'})

    def scheduler_function(self):
        Logic.scheduler_start()
