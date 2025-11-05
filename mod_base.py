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

    def plugin_load(self):
        """플러그인 로드 시 1회 실행"""
        try:
            Logic.db_init()
        except Exception as e:
            P.logger.error(f"db_init in plugin_load failed: {e}")

    def process_menu(self, sub, req):
        P.logger.info(f"ModuleBase.process_menu called: sub={sub}")
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
        elif sub == 'developer':
            try:
                template_name = f"{P.package_name}_base_developer.html"
                P.logger.info(f"Rendering template: {template_name}")
                return render_template(template_name, arg=arg)
            except Exception as e:
                P.logger.error(f"Error in developer menu: {str(e)}")
                P.logger.error(traceback.format_exc())
                return f"<div class='container'><h3>개발 정의서 로드 오류</h3><pre>{traceback.format_exc()}</pre></div>"
            else:
                P.logger.warning(f"Unknown sub menu in base module: {sub}")
                return f"<div class='container'><h3>알 수 없는 메뉴: {sub}</h3></div>"
        
            template_name = f'{P.package_name}_{self.name}_{sub}.html'
            P.logger.info(f"Rendering template: {template_name}")
        
            try:            # 설정 페이지 렌더링
            arg['settings'] = P.ModelSetting.to_dict()
            arg['strategies'] = Logic.get_strategies_metadata()
            return render_template(template_name, arg=arg, P=P)
            
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

    def process_command(self, command, arg1, arg2, arg3, req):
        if command == 'reset_db':
            self.reset_db()
            return jsonify({'ret': 'success', 'msg': 'DB가 초기화되었습니다.'})
        return jsonify({'ret': 'not_implemented', 'msg': f'Unknown command: {command}'})

    def setting_save_after(self):
        """설정 저장 후 스케줄러 재시작"""
        try:
            Logic.scheduler_stop()
            Logic.scheduler_start()
            P.logger.info("Scheduler restarted after saving settings.")
        except Exception as e:
            P.logger.error(f"Failed to restart scheduler: {str(e)}")
            P.logger.error(traceback.format_exc())

    def reset_db(self):
        """DB 초기화"""
        try:
            # 여기에 DB 초기화 로직 추가 (예: 모든 관련 테이블 drop 및 create)
            # 이 예제에서는 기본 설정 값을 다시 로드하는 것으로 대체합니다.
            Logic.db_init()
            return True
        except Exception as e:
            P.logger.error(f"DB reset failed: {str(e)}")
            P.logger.error(traceback.format_exc())
            return False


    def scheduler_function(self):
        Logic.scheduler_start()
