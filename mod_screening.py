# -*- coding: utf-8 -*-
from plugin import *
from .setup import P, F
from framework import db
from .model import StockScreeningResult, ScreeningHistory
from datetime import datetime, timedelta
from sqlalchemy import func
import csv
from io import StringIO
import os

class ModuleScreening(PluginModuleBase):
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
        super(ModuleScreening, self).__init__(P, name='screening', first_menu='strategies')
        self.db_default = ModuleScreening._db_default
        self.default_strategy_ids = ['seven_split_21', 'seven_split_mini', 'dividend_strategy', 'value_investing']
        P.logger.info("ModuleScreening initialized")

    def process_menu(self, page, req):
        from .logic import Logic
        P.logger.info(f"ModuleScreening.process_menu called: page={page}")
        arg = P.ModelSetting.to_dict()
        
        # setup.py 수정으로 인해 'screening' 메뉴 클릭 시 page가 None으로 들어옵니다.
        # 이 경우 'strategies' (first_menu)로 리디렉션합니다.
        if not page:
            page = 'strategies'
        try:
            # V V V 수정: 'detail' 페이지 로직 변경 V V V
            # 'detail'은 템플릿 이름에 포함되면 안 되므로 분기 처리
            if page.startswith('detail'):
                template_name = f'{P.package_name}_{self.name}_detail.html'
                P.logger.info(f"Rendering template: {template_name}")
                
                # .../detail?code=005930 방식 (쿼리 파라미터)
                code = req.args.get('code')
                
                # .../detail/005930 방식 (기존 경로 파라미터) - 하위 호환성
                if not code:
                    path_parts = req.path.split('/')
                    try:
                        detail_index = path_parts.index('detail')
                        if detail_index + 1 < len(path_parts):
                            code = path_parts[detail_index + 1]
                    except (ValueError, IndexError):
                        pass

                if not code:
                    return render_template(template_name, arg=arg, P=P, error='종목 코드가 필요합니다.')

                result = db.session.query(StockScreeningResult).filter_by(code=code).order_by(StockScreeningResult.screening_date.desc()).first()
                if not result:
                    return render_template(template_name, arg=arg, P=P, error='종목을 찾을 수 없습니다.')
                
                history = db.session.query(StockScreeningResult).filter_by(code=code).order_by(StockScreeningResult.screening_date.desc()).limit(30).all()
                arg['result'] = result
                arg['history'] = history
                return render_template(template_name, arg=arg, P=P)
            # ^ ^ ^ 수정: 'detail' 페이지 로직 변경 ^ ^ ^

            template_name = f'{P.package_name}_{self.name}_{page}.html'
            P.logger.info(f"Rendering template: {template_name}")
            
            if page == 'strategies':
                strategies = Logic.get_strategies_metadata()
                arg['strategies'] = strategies
                arg['default_strategy'] = P.ModelSetting.get('default_strategy')
                P.logger.info(f"Loaded {len(arg['strategies'])} strategies")
                return render_template(template_name, arg=arg, P=P)

            elif page == 'list':
                page_num = req.args.get('page', 1, type=int)
                per_page = req.args.get('per_page', 50, type=int)
                date_filter = req.args.get('date')
                market_filter = req.args.get('market')
                strategy_filter = req.args.get('strategy')
                passed_only = req.args.get('passed_only', 'true') == 'true'
                
                query = db.session.query(StockScreeningResult)
                if date_filter: 
                    query = query.filter(StockScreeningResult.screening_date == date_filter)
                if market_filter: 
                    query = query.filter(StockScreeningResult.market == market_filter)
                if strategy_filter: 
                    query = query.filter(StockScreeningResult.strategy_name == strategy_filter)
                if passed_only: 
                    query = query.filter(StockScreeningResult.passed == True)
                
                query = query.order_by(StockScreeningResult.screening_date.desc(), StockScreeningResult.market_cap.desc())
                pagination = query.paginate(page=page_num, per_page=per_page, error_out=False)
                
                available_dates = db.session.query(StockScreeningResult.screening_date).distinct().order_by(StockScreeningResult.screening_date.desc()).limit(30).all()
                dates = [d[0] for d in available_dates]
                arg['results'] = pagination.items
                arg['pagination'] = pagination
                arg['dates'] = [d[0] for d in available_dates]
                arg['available_strategies'] = Logic.get_strategies_metadata()
                arg['current_date'] = date_filter
                arg['current_market'] = market_filter
                arg['current_strategy'] = strategy_filter
                arg['passed_only'] = passed_only
                return render_template(template_name, arg=arg, P=P)
            
            elif page == 'manual':
                arg['default_strategy'] = P.ModelSetting.get('default_strategy')
                return render_template(template_name, arg=arg, P=P)
            
            elif page == 'scheduler':
                # NOTE: Scheduler page moved to base module
                # Redirect to new location
                from flask import redirect, url_for
                return redirect(f'/{P.package_name}/base/scheduler')
        
            elif page == 'history':
                page_num = req.args.get('page', 1, type=int)
                pagination = db.session.query(ScreeningHistory).order_by(ScreeningHistory.execution_date.desc()).paginate(page=page_num, per_page=20, error_out=False)
                arg['histories'] = pagination.items
                arg['pagination'] = pagination
                return render_template(template_name, arg=arg, P=P)

            elif page == 'statistics':
                thirty_days_ago = datetime.now() - timedelta(days=30)
                arg['daily_stats'] = db.session.query(StockScreeningResult.screening_date, func.count(StockScreeningResult.id).label('total'), func.sum(func.cast(StockScreeningResult.passed, db.Integer)).label('passed')).filter(StockScreeningResult.screening_date >= thirty_days_ago.date()).group_by(StockScreeningResult.screening_date).order_by(StockScreeningResult.screening_date.desc()).all()
                arg['market_stats'] = db.session.query(StockScreeningResult.market, func.count(StockScreeningResult.id).label('total'), func.sum(func.cast(StockScreeningResult.passed, db.Integer)).label('passed')).filter(StockScreeningResult.passed == True).group_by(StockScreeningResult.market).all()
                return render_template(template_name, arg=arg, P=P)

            elif page == 'compare':
                # 여러 전략/날짜로 결과를 동시에 비교 표시
                # 쿼리: ?strategies=a,b,c&date=YYYY-MM-DD&passed_only=true
                strategies_q = req.args.get('strategies', '')
                selected = [s.strip() for s in strategies_q.split(',') if s.strip()]
                date_filter = req.args.get('date')
                passed_only = req.args.get('passed_only', 'true') == 'true'

                if not selected:
                    # 기본: 등록된 상위 3개 전략
                    meta = Logic.get_strategies_metadata()
                    selected = [m['id'] for m in meta[:3]] if meta else []

                # 전략별 결과 수집
                grouped = {}
                for sid in selected:
                    query = db.session.query(StockScreeningResult).filter(StockScreeningResult.strategy_name == sid)
                    if date_filter:
                        query = query.filter(StockScreeningResult.screening_date == date_filter)
                    if passed_only:
                        query = query.filter(StockScreeningResult.passed == True)
                    grouped[sid] = query.order_by(StockScreeningResult.screening_date.desc(), StockScreeningResult.market_cap.desc()).limit(200).all()

                available_strategies = Logic.get_strategies_metadata()
                arg['selected_strategies'] = selected
                arg['available_strategies'] = available_strategies
                arg['grouped_results'] = grouped
                arg['current_date'] = date_filter
                arg['passed_only'] = passed_only
                return render_template(template_name, arg=arg, P=P)
            
            elif page == 'scaffold':
                return render_template(template_name, arg=arg, P=P)

            elif page == 'import':
                return render_template(f'{P.package_name}_{self.name}_import.html', arg=arg, P=P)

            elif page == 'setting':
                # The screening module doesn't have a setting page, redirect to strategies as default
                # or inform user that this page doesn't exist for this module
                P.logger.warning(f"Setting page not available for screening module: {page}")
                return f"<div class='container'><h3>스크리닝 모듈에는 설정 페이지가 없습니다. <a href='/{P.package_name}/screening/strategies'>전략 선택</a> 페이지로 이동하세요.</h3></div>"

            elif page == 'command':
                # This handles cases where /screening/command is accessed directly
                # which shouldn't happen in normal operation, but might occur due to malformed requests
                P.logger.warning(f"Direct command access attempt: {page}")
                return f"<div class='container'><h3>명령 실행은 올바른 방식으로 접근해야 합니다.</h3></div>"
            
            else:
                P.logger.warning(f"Unknown sub menu: {page}")
                return f"<div class='container'><h3>알 수 없는 메뉴: {page}</h3></div>"

        except Exception as e:
            P.logger.error(f"Error in process_menu '{page}': {str(e)}")
            P.logger.error(traceback.format_exc())
            return f"<div class='container'><div class='alert alert-danger'><h3>오류 발생</h3><p><strong>메뉴:</strong> {page}</p><p><strong>에러:</strong> {str(e)}</p><pre>{traceback.format_exc()}</pre></div></div>"
    
    # (process_command, process_api는 변경 없음)
    def process_command(self, command, arg1, arg2, arg3, req):
        from .logic import Logic
        P.logger.info(f"ModuleScreening.process_command: {command}, arg1={arg1}")
        try:
            if command == 'start':
                P.logger.info(f"Play_arrow 실행 명령 시작: arg1={arg1}")
                try:
                    P.logger.debug(f"Command 'start' received with arg1: {arg1}")
                    strategy_id = arg1 if arg1 else P.ModelSetting.get('default_strategy')
                    P.logger.info(f"Starting screening with strategy_id: {strategy_id}, execution_type: manual")
                    
                    # Log the actual strategy ID being used
                    P.logger.debug(f"Using strategy_id for screening: {strategy_id}")
                    
                    result = Logic.start_screening(strategy_id=strategy_id, execution_type='manual')
                    P.logger.debug(f"Screening result: {result}")
                    
                    if result and result.get('success'):
                        P.logger.info("Play_arrow 실행 명령 성공적으로 시작됨")
                        return jsonify({'ret': 'success', 'msg': result.get('message', '스크리닝이 시작되었습니다.')})
                    else:
                        error_msg = result.get('message', '스크리닝 시작에 실패했습니다.') if result else '스크리닝 시작에 실패했습니다. (결과 없음)'
                        P.logger.error(f"Screening failed: {error_msg}")
                        return jsonify({'ret': 'error', 'msg': error_msg})
                except Exception as e:
                    P.logger.error(f"Exception in start command: {str(e)}")
                    P.logger.error(traceback.format_exc())
                    return jsonify({'ret': 'error', 'msg': f'스크리닝 시작 중 오류 발생: {str(e)}'})
            elif command == 'status':
                history = db.session.query(ScreeningHistory).order_by(ScreeningHistory.execution_date.desc()).first()
                if not history:
                    return jsonify({'ret': 'success', 'status': 'none'})
                return jsonify({'ret': 'success', 'status': history.status, 'execution_date': history.execution_date.isoformat(), 'total_stocks': history.total_stocks, 'passed_stocks': history.passed_stocks, 'execution_time': history.execution_time})
            elif command == 'set_default_strategy':
                strategy_id = arg1
                if not strategy_id:
                    return jsonify({'ret': 'error', 'msg': '전략 ID가 필요합니다.'})
                P.ModelSetting.set('default_strategy', strategy_id)
                return jsonify({'ret': 'success', 'msg': '기본 전략이 설정되었습니다.'})
            elif command == 'recent_history':
                histories = db.session.query(ScreeningHistory).order_by(ScreeningHistory.execution_date.desc()).limit(5).all()
                data = []
                for h in histories:
                    strategy_name = 'N/A'
                    if h.strategy_name:
                        from .strategies import get_strategy
                        strategy = get_strategy(h.strategy_name)
                        if strategy: 
                            strategy_name = strategy.strategy_name
                    data.append({'execution_date': h.execution_date.strftime('%Y-%m-%d %H:%M:%S'), 'strategy_name': strategy_name, 'total_stocks': h.total_stocks, 'passed_stocks': h.passed_stocks, 'execution_time': h.execution_time, 'status': h.status})
                return jsonify({'ret': 'success', 'data': data})
            elif command == 'create_scaffold':
                data = req.form.to_dict()
                strategy_id = (data.get('strategy_id') or '').strip()
                strategy_name = (data.get('strategy_name') or '').strip()
                version = (data.get('version') or '1.0.0').strip()
                required_data = data.get('required_data') or ''
                conditions_text = data.get('conditions') or ''

                if not strategy_id or not strategy_name:
                    return jsonify({'ret': 'error', 'msg': 'strategy_id와 strategy_name은 필수입니다.'})
                if not strategy_id.replace('_', '').isalnum():
                    return jsonify({'ret': 'error', 'msg': 'strategy_id는 영문/숫자/밑줄만 허용됩니다.'})

                base_dir = os.path.dirname(os.path.abspath(__file__))
                strategies_dir = os.path.join(base_dir, 'strategies')
                target_path = os.path.join(strategies_dir, f"{strategy_id}.py")
                if os.path.exists(target_path):
                    return jsonify({'ret': 'error', 'msg': '동일한 파일이 이미 존재합니다.'})

                def to_camel(s):
                    return ''.join([p.capitalize() for p in s.split('_')])
                class_name = f"{to_camel(strategy_id)}Strategy"

                req_set = [x.strip() for x in str(required_data).replace('\n', ',').split(',') if x.strip()]
                req_set = [x for x in req_set if x in ['market', 'financial', 'disclosure', 'major_shareholder']]
                if not req_set:
                    req_set = ['market']

                condition_lines = [line.strip() for line in str(conditions_text).split('\n') if line.strip()]
                cond_pairs = []
                for line in condition_lines:
                    if ':' in line:
                        num, desc = line.split(':', 1)
                        try:
                            num_i = int(num.strip())
                            cond_pairs.append((num_i, desc.strip()))
                        except:
                            pass
                if not cond_pairs:
                    cond_pairs = [(1, '조건 설명을 여기에 작성하세요')]

                conditions_dict_lines = [f"        {k}: '{v}'," for k, v in cond_pairs]
                required_data_items = ', '.join([f"'{x}'" for x in req_set])

                template_code = f"""
from strategies.base_strategy import BaseStrategy


class {class_name}(BaseStrategy):
    strategy_id = '{strategy_id}'
    strategy_name = '{strategy_name}'
    version = '{version}'
    required_data = {{{required_data_items}}}

    conditions = {{
{chr(10).join(conditions_dict_lines)}
    }}

    def get_info(self):
        return {{
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'version': self.version,
            'description': '{strategy_name} 전략',
            'conditions': self.conditions,
        }}

    def apply_filters(self, stock):
        detail = {{}}
        passed = True
        # TODO: 각 조건 로직을 구현하세요
        for num in self.conditions.keys():
            detail[num] = True
        passed = all(detail.values())
        return passed, detail
"""

                try:
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(template_code.lstrip('\n'))
                except Exception as e:
                    return jsonify({'ret': 'error', 'msg': f'파일 생성 실패: {str(e)}'})

                return jsonify({'ret': 'success', 'msg': '전략 파일이 생성되었습니다.', 'file': target_path})

            elif command == 'download_strategy':
                strategy_id = arg1
                if not strategy_id.replace('_', '').isalnum():
                    return jsonify({'ret': 'error', 'msg': '잘못된 전략 ID입니다.'})
                base_dir = os.path.dirname(os.path.abspath(__file__))
                strategy_path = os.path.join(base_dir, 'strategies', f"{strategy_id}.py")
                if os.path.exists(strategy_path):
                    return send_file(strategy_path, as_attachment=True)
                else:
                    return jsonify({'ret': 'error', 'msg': '전략 파일을 찾을 수 없습니다.'})

            elif command == 'delete_strategy':
                strategy_id = arg1
                if strategy_id in self.default_strategy_ids:
                    return jsonify({'ret': 'error', 'msg': '기본 전략은 삭제할 수 없습니다.'})
                if not strategy_id.replace('_', '').isalnum():
                    return jsonify({'ret': 'error', 'msg': '잘못된 전략 ID입니다.'})
                
                base_dir = os.path.dirname(os.path.abspath(__file__))
                strategy_path = os.path.join(base_dir, 'strategies', f"{strategy_id}.py")
                
                if os.path.exists(strategy_path):
                    try:
                        os.remove(strategy_path)
                        return jsonify({'ret': 'success', 'msg': '전략이 삭제되었습니다.'})
                    except Exception as e:
                        return jsonify({'ret': 'error', 'msg': f'파일 삭제 중 오류 발생: {e}'})
                else:
                    return jsonify({'ret': 'error', 'msg': '전략 파일을 찾을 수 없습니다.'})

            elif command == 'save_strategy_from_text':
                code = req.form.get('strategy_code', '')
                if not code.strip():
                    return jsonify({'ret': 'error', 'msg': '코드가 비어있습니다.'})
                
                # 코드에서 strategy_id 추출 (정규식 사용)
                import re
                match = re.search(r"strategy_id\s*=\s*['\"](.+?)['\"]", code)
                if not match:
                    return jsonify({'ret': 'error', 'msg': "코드에서 'strategy_id'를 찾을 수 없습니다."})
                
                strategy_id = match.group(1)
                if not strategy_id.replace('_', '').isalnum():
                    return jsonify({'ret': 'error', 'msg': '추출된 strategy_id가 유효하지 않습니다.'})

                base_dir = os.path.dirname(os.path.abspath(__file__))
                target_path = os.path.join(base_dir, 'strategies', f"{strategy_id}.py")

                if os.path.exists(target_path):
                    return jsonify({'ret': 'error', 'msg': '동일한 ID의 전략이 이미 존재합니다.'})

                try:
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(code)
                    return jsonify({'ret': 'success', 'msg': f"'{strategy_id}' 전략을 성공적으로 가져왔습니다."})
                except Exception as e:
                    return jsonify({'ret': 'error', 'msg': f'파일 저장 중 오류 발생: {e}'})
        except Exception as e:
            P.logger.error(f"Command error: {str(e)}")
            P.logger.error(traceback.format_exc())
            return jsonify({'ret': 'error', 'msg': str(e)})

        return jsonify({'ret': 'error', 'msg': 'Unknown command'})

    def process_api(self, sub, req):
        P.logger.info(f"ModuleScreening.process_api: sub={sub}")
        try:
            if sub == 'download_csv':
                date_filter = req.args.get('date')
                query = db.session.query(StockScreeningResult).filter(StockScreeningResult.passed == True)
                if date_filter:
                    query = query.filter(StockScreeningResult.screening_date == date_filter)
                results = query.order_by(StockScreeningResult.market_cap.desc()).all()
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(['종목코드', '종목명', '시장', '시가총액(억)', 'PER', 'PBR', 'ROE(%)', 'F-Score', '배당수익률(%)', '스크리닝일자'])
                for r in results:
                    writer.writerow([r.code, r.name, r.market, r.market_cap // 100000000 if r.market_cap else 0, r.per, r.pbr, r.roe_avg_3y, r.fscore, r.div_yield, r.screening_date])
                output.seek(0)
                return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename=7split_screening_{date_filter or "all"}.csv'})


        except Exception as e:
            P.logger.error(f"API error: {str(e)}")
            P.logger.error(traceback.format_exc())
            return jsonify({'ret': 'error', 'msg': str(e)})

    def process_ajax(self, sub, req):
        from .logic import Logic
        try:
            if sub == 'save_schedules':
                P.logger.info("스케줄 저장 요청 시작")
                try:
                    schedules = []
                    form_data = req.form.to_dict()
                    P.logger.debug(f"Received form data keys: {list(form_data.keys())}")
                    
                    strategies = Logic.get_strategies_metadata()
                    P.logger.debug(f"Found {len(strategies)} strategies")
                    
                    for s in strategies:
                        strategy_id = s['id']
                        cron_key = f'cron_{strategy_id}'
                        enabled_key = f'enabled_{strategy_id}'
                        
                        cron_expression = form_data.get(cron_key, '').strip()
                        is_enabled = enabled_key in form_data
                        
                        P.logger.debug(f"Strategy {strategy_id}: cron={cron_expression}, enabled={is_enabled}")
                        
                        if cron_expression:
                            schedules.append({
                                'strategy_id': strategy_id,
                                'condition_number': 0, # 전략 전체 스케줄링
                                'cron_expression': cron_expression,
                                'is_enabled': is_enabled
                            })

                    P.logger.debug(f"Saving {len(schedules)} schedules")
                    Logic.save_condition_schedules(schedules)
                    P.logger.info(f"스케줄 저장 완료: {len(schedules)}개 스케줄 저장됨")
                    return jsonify({'ret': 'success', 'msg': '스케줄이 저장되었습니다.'})
                except Exception as e:
                    P.logger.error(f"스케줄 저장 중 오류 발생: {str(e)}")
                    P.logger.error(traceback.format_exc())
                    return jsonify({'ret': 'error', 'msg': f'스케줄 저장 실패: {str(e)}'})

        except Exception as e:
            P.logger.error(f"AJAX error: {str(e)}")
            P.logger.error(traceback.format_exc())
            return jsonify({'ret': 'error', 'msg': str(e)})

    def get_scheduler_interval(self):
        """스케줄러 간격을 분 단위로 반환"""
        try:
            # 모듈명_interval 키로 설정된 간격 가져오기 (예: screening_interval)
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
