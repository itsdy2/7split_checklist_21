# -*- coding: utf-8 -*-
import traceback
from plugin import *
from .setup import *
from .logic import Logic

class ModuleBase(PluginModuleBase):
    def __init__(self, P):
        # 기본 진입 서브를 명확히 지정하여 라우터가 템플릿으로 진입하도록 함
        super(ModuleBase, self).__init__(P, name='base', first_menu='setting')
        self.db_default = Logic.db_default
        P.logger.info("ModuleBase initialized")

    def process_menu(self, sub, req):
        P.logger.info(f"ModuleBase.process_menu called: sub={sub}")
        # 요청 컨텍스트 내에서 DB 초기화 수행 (app context 보장)
        try:
            Logic.db_init()
        except Exception as e:
            P.logger.error(f"db_init in request context failed: {e}")
        arg = P.ModelSetting.to_dict()
        
        # 기본 페이지 라우팅
        if not sub or sub == 'base' or sub == 'setting':
            sub = 'setting'
        elif sub == 'help':
            # 도움말 템플릿은 모듈명이 포함되지 않은 파일명 규칙을 사용
            try:
                template_name = f"{P.package_name}_help.html"
                P.logger.info(f"Rendering template: {template_name}")
                return render_template(template_name, arg=arg)
            except Exception as e:
                P.logger.error(f"Error in help menu: {str(e)}")
                P.logger.error(traceback.format_exc())
                return f"<div class='container'><h3>도움말 로드 오류</h3><pre>{traceback.format_exc()}</pre></div>"
        else:
            P.logger.warning(f"Unknown sub menu in base module: {sub}")
            return f"<div class='container'><h3>알 수 없는 메뉴: {sub}</h3></div>"

        try:
            # 설정 값 로드
            settings = {}
            for key in self.db_default.keys():
                settings[key] = Logic.get_setting(key)
            
            # 전략 정보 로드
            try:
                # from strategies import get_strategies_info # 원본에는 strategies 임포트가 없음. 해당 파일은 strategies 폴더 하위에 있음.
                # logic.py 에 이미 strategies 임포트하는 함수가 있으므로 Logic 클래스를 통해 호출
                strategies = Logic.get_strategies_metadata()
                P.logger.info(f"Loaded {len(strategies)} strategies")
            except Exception as e:
                P.logger.error(f"Failed to load strategies: {str(e)}")
                P.logger.error(traceback.format_exc())
                strategies = []
            
            arg['settings'] = settings
            arg['strategies'] = strategies
            
            # 템플릿 이름: 7split_checklist_21_base_setting.html
            template_name = f'{P.package_name}_{self.name}_{sub}.html'
            P.logger.info(f"Rendering template: {template_name}")
            
            return render_template(template_name, arg=arg)
            
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

    def process_api(self, sub, req):
        P.logger.info(f"ModuleBase.process_api: sub={sub}")
        try:
            if sub == 'setting_save':
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
            P.logger.error(f"API error: {str(e)}")
            P.logger.error(traceback.format_exc())
            return jsonify({'ret': 'error', 'msg': str(e)})
        
        return jsonify({'ret': 'error', 'msg': 'Unknown sub-command'})

    def scheduler_function(self):
        Logic.scheduler_start()
