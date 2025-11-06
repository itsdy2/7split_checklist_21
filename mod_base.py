# -*- coding: utf-8 -*-
import traceback
from plugin import *
from .setup import *
from .logic import Logic

class ModuleBase(PluginModuleBase):
    def __init__(self, P):
        super(ModuleBase, self).__init__(P, name='base', first_menu='setting')
        self.db_default = Logic.db_default
        P.logger.info("ModuleBase initialized")

    def process_menu(self, sub, req):
        P.logger.info(f"ModuleBase.process_menu called: sub={sub}")
        try:
            arg = P.ModelSetting.to_dict()
            
            if sub is None or sub == 'base':
                sub = 'setting'

            if sub == 'setting':
                template_name = f'{P.package_name}_{self.name}_{sub}.html'
                arg['is_include'] = F.scheduler.is_include(f'{P.package_name}_auto')
                arg['is_running'] = F.scheduler.is_running(f'{P.package_name}_auto')
                arg['strategies'] = Logic.get_strategies_metadata()
                return render_template(template_name, arg=arg, P=P)

            elif sub == 'help':
                template_name = f"{P.package_name}_help.html"
                return render_template(template_name, arg=arg, P=P)

            elif sub == 'developer':
                template_name = f"{P.package_name}_base_developer.html"
                return render_template(template_name, arg=arg, P=P)

            else:
                return f"<div class='container'><h3>알 수 없는 메뉴: {sub}</h3></div>"

        except Exception as e:
            P.logger.error(f"Error in menu '{sub}': {str(e)}")
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
        if 'auto_start' in change_list or 'screening_time' in change_list:
            P.logger.info("스케줄러 관련 설정이 변경되어 스케줄러를 재시작합니다.")
            Logic.task_scheduler_restart.apply_async()

    def scheduler_function(self):
        Logic.scheduler_start()
