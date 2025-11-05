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

    def plugin_load(self):
        try:
            Logic.db_init()
        except Exception as e:
            P.logger.error(f"db_init in plugin_load failed: {e}")

    def process_menu(self, sub, req):
        P.logger.info(f"ModuleBase.process_menu called: sub={sub}")
        try:
            arg = P.ModelSetting.to_dict()
            
            if sub is None or sub == 'base':
                sub = 'setting'

            if sub == 'setting':
                template_name = f'{P.package_name}_{self.name}_{sub}.html'
                arg['settings'] = P.ModelSetting.to_dict()
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

    def process_command(self, command, arg1, arg2, arg3, req):
        try:
            if command == 'reset_db':
                if self.reset_db():
                    return jsonify({'ret': 'success', 'msg': 'DB가 초기화되었습니다.'})
                else:
                    return jsonify({'ret': 'error', 'msg': 'DB 초기화에 실패했습니다.'})
            
            elif command == 'setting_save':
                form_data = req.form.to_dict()
                for key, value in form_data.items():
                    Logic.set_setting(key, value)
                Logic.task_scheduler_restart.apply_async()
                return jsonify({'ret': 'success', 'msg': '설정을 저장했습니다.'})

            return jsonify({'ret': 'not_implemented', 'msg': f'Unknown command: {command}'})

        except Exception as e:
            P.logger.error(f"Exception in process_command: {str(e)}")
            P.logger.error(traceback.format_exc())
            return jsonify({'ret': 'error', 'msg': str(e)})


    def reset_db(self):
        try:
            Logic.db_init()
            return True
        except Exception as e:
            P.logger.error(f"DB reset failed: {str(e)}")
            P.logger.error(traceback.format_exc())
            return False

    def scheduler_function(self):
        Logic.scheduler_start()
