# -*- coding: utf-8 -*-
import traceback
from plugin import *
from .setup import P, F

class ModuleBase(PluginModuleBase):
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
        # ... (기존 db_default 내용과 동일)
    }

    def __init__(self, P):
        super(ModuleBase, self).__init__(P, name='base', first_menu='setting')
        self.db_default = ModuleBase._db_default
        P.logger.info("ModuleBase initialized")

    def process_menu(self, page, req):
        P.logger.info(f"ModuleBase.process_menu called: page={page}")
        try:
            from .logic import Logic
            arg = P.ModelSetting.to_dict()
            
            if page is None or page == 'base':
                page = 'setting'

            if page == 'setting':
                template_name = f'{P.package_name}_{self.name}_{page}.html'
                arg['is_include'] = F.scheduler.is_include(f'{P.package_name}_auto')
                arg['is_running'] = F.scheduler.is_running(f'{P.package_name}_auto')
                
                strategies = Logic.get_strategies_metadata()
                arg['strategies'] = strategies # Keep for other potential uses in template
                arg['strategy_options'] = [(s.strategy_id, s.strategy_name) for s in strategies]
                
                return render_template(template_name, arg=arg, P=P)

            elif page == 'help':
                template_name = f"{P.package_name}_help.html"
                return render_template(template_name, arg=arg, P=P)

            elif page == 'developer':
                template_name = f"{P.package_name}_base_developer.html"
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
            if sub == 'reset_db':
                P.ModelSetting.reset_db()
                return jsonify({'ret': 'success', 'msg': 'DB가 초기화되었습니다.'})

        except Exception as e:
            P.logger.error(f"Exception in process_ajax: {str(e)}")
            P.logger.error(traceback.format_exc())
            return jsonify({'ret': 'error', 'msg': str(e)})

    def setting_save_after(self, change_list):
        from .logic import Logic
        if 'auto_start' in change_list or 'screening_time' in change_list:
            P.logger.info("스케줄러 관련 설정이 변경되어 스케줄러를 재시작합니다.")
            Logic.task_scheduler_restart.apply_async()

    def scheduler_function(self):
        from .logic import Logic
        Logic.scheduler_start()
