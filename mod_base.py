# -*- coding: utf-8 -*-
import traceback
from plugin import *
from .setup import P
from framework import F, db

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
        'db_retention_days': '30',
        'db_cleanup_enabled': 'True',
        'db_max_size_gb': '5',
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
                arg['strategy_options'] = [(s['id'], s['name']) for s in strategies]
                
                return render_template(template_name, arg=arg, P=P)

            elif page == 'help':
                template_name = f"{P.package_name}_help.html"
                return render_template(template_name, arg=arg, P=P)

            elif page == 'developer':
                template_name = f"{P.package_name}_base_developer.html"
                return render_template(template_name, arg=arg, P=P)

            elif page == 'scheduler':
                from .logic import Logic
                from .model import ConditionSchedule
                template_name = f"{P.package_name}_{self.name}_{page}.html"
                
                strategies = Logic.get_strategies_metadata()
                # 현재 설정 읽기
                current = {s['id']: {'enabled': False, 'cron': ''} for s in strategies}
                rows = db.session.query(ConditionSchedule).filter(ConditionSchedule.condition_number == 0).all()
                for r in rows:
                    if r.strategy_id in current:
                        current[r.strategy_id] = {'enabled': r.is_enabled, 'cron': r.cron_expression}
                arg['strategies'] = strategies
                arg['current_schedule'] = current
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
                P.logger.info("DB 초기화 요청 시작")
                try:
                    P.ModelSetting.reset_db()
                    P.logger.info("DB 초기화 성공")
                    return jsonify({'ret': 'success', 'msg': 'DB가 초기화되었습니다.'})
                except Exception as e:
                    P.logger.error(f"DB 초기화 중 오류 발생: {str(e)}")
                    P.logger.error(traceback.format_exc())
                    return jsonify({'ret': 'error', 'msg': f'DB 초기화 실패: {str(e)}'})
            
            elif sub == 'manual_cleanup':
                P.logger.info("수동 DB 정리 요청 시작")
                from .logic import Logic
                try:
                    if F.config['use_celery']:
                        P.logger.debug("Celery 사용하여 DB 정리 시작")
                        result = Logic.task_cleanup_old_data.apply_async()
                        P.logger.info(f"DB 정리 Celery 작업 시작됨 (ID: {result.id})")
                        return jsonify({'ret': 'success', 'msg': f'DB 정리 작업이 시작되었습니다. (작업 ID: {result.id})'})
                    else:
                        P.logger.debug("Celery 미사용 - 동기식 DB 정리 시작")
                        result = Logic.cleanup_old_data()
                        P.logger.info("DB 정리 완료")
                        return jsonify(result)
                except Exception as e:
                    P.logger.error(f"수동 DB 정리 중 오류 발생: {str(e)}")
                    P.logger.error(traceback.format_exc())
                    return jsonify({'ret': 'error', 'msg': f'수동 DB 정리 실패: {str(e)}'})
            
            elif sub == 'save_schedules':
                from .logic import Logic
                schedules = []
                form_data = req.form.to_dict()
                from .strategies import get_strategies_info
                
                strategies = get_strategies_info()
                
                for s in strategies:
                    strategy_id = s['id']
                    cron_key = f'cron_{strategy_id}'
                    enabled_key = f'enabled_{strategy_id}'
                    
                    cron_expression = form_data.get(cron_key, '').strip()
                    is_enabled = enabled_key in form_data

                    if cron_expression:
                        schedules.append({
                            'strategy_id': strategy_id,
                            'condition_number': 0, # 전략 전체 스케줄링
                            'cron_expression': cron_expression,
                            'is_enabled': is_enabled
                        })

                if F.config['use_celery']:
                    result = Logic.task_save_condition_schedules.apply_async((schedules,))
                    return jsonify({'ret': 'success', 'msg': '스케줄이 저장되었습니다.'})
                else:
                    success = Logic.task_save_condition_schedules(schedules)
                    if success:
                        return jsonify({'ret': 'success', 'msg': '스케줄이 저장되었습니다.'})
                    else:
                        return jsonify({'ret': 'error', 'msg': '스케줄 저장에 실패했습니다.'})

        except Exception as e:
            P.logger.error(f"Exception in process_ajax: {str(e)}")
            P.logger.error(traceback.format_exc())
            return jsonify({'ret': 'error', 'msg': str(e)})

    def setting_save_after(self, change_list):
        from .logic import Logic
        if 'auto_start' in change_list or 'screening_time' in change_list:
            P.logger.info("스케줄러 관련 설정이 변경되어 스케줄러를 재시작합니다.")
            Logic.task_scheduler_restart.apply_async()

    def get_scheduler_interval(self):
        """스케줄러 간격을 분 단위로 반환"""
        try:
            # 모듈명_interval 키로 설정된 간격 가져오기 (예: base_interval)
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
        from .logic import Logic
        Logic.scheduler_start()
