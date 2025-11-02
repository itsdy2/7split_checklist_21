# -*- coding: utf-8 -*-
# from .setup import * <-- 이 줄을 삭제하고
from .setup import * 
from .logic import Logic
from flask import render_template, request, jsonify
import traceback # (Traceback 임포트 추가)

class ModuleBase(PluginModuleBase):
    def __init__(self, P):
        super(ModuleBase, self).__init__(P, name='base', first_menu='setting')
        # 'Logic' 클래스에서 db_default를 가져옵니다.
        self.db_default = Logic.db_default
        # Logic 클래스의 db_init을 호출합니다. (플러그인 로드 시 1회 실행)
        Logic.db_init()

    def process_menu(self, sub, req):
        arg = P.ModelSetting.to_dict()
        if sub == 'setting':
            # GET 요청 시 설정 페이지를 렌더링합니다.
            settings = {}
            for key in self.db_default.keys():
                settings[key] = Logic.get_setting(key)
            strategies = Logic.get_strategies_metadata()
            
            arg['settings'] = settings
            arg['strategies'] = strategies
            
            # 템플릿 파일명은 '7split_checklist_21_base_setting.html'이어야 합니다.
            return render_template(f'{P.package_name}_{self.name}_{sub}.html', arg=arg, settings=settings, strategies=strategies)
        
        P.logger.error(f"Unknown menu: {sub}") # P.logger 사용
        return "Not Implemented"

    def process_api(self, sub, req):
        # 템플릿의 저장 버튼 AJAX 호출이 이 'setting_save'를 호출해야 합니다.
        if sub == 'setting_save':
            try:
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
                Logic.save_condition_schedules(schedules)
                
                # 스케줄러 재시작
                Logic.scheduler_stop()
                Logic.scheduler_start()
                
                return jsonify({'success': True, 'message': '설정이 저장되었습니다.'})
                
            except Exception as e:
                P.logger.error(f"Setting save error: {str(e)}")
                P.logger.error(traceback.format_exc()) # P.logger 사용
                return jsonify({'success': False, 'message': str(e)})
        return jsonify({'success': False, 'message': 'Unknown API call'})

    def scheduler_function(self):
        # 플러그인 로드 시 Logic의 스케줄러를 시작합니다.
        Logic.scheduler_start()