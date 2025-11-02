# -*- coding: utf-8 -*-
from .setup import *
from .logic import Logic
from .model import StockScreeningResult, ScreeningHistory
from flask import render_template, request, jsonify, Response
from datetime import datetime, timedelta
from sqlalchemy import func
import csv
from io import StringIO
import traceback
import os

class ModuleScreening(PluginModuleBase):
    def __init__(self, P):
        super(ModuleScreening, self).__init__(P, name='screening', first_menu='strategies')
        self.db_default = Logic.db_default

    def process_menu(self, sub, req):
        arg = P.ModelSetting.to_dict()
        
        P.logger.info(f"ModuleScreening.process_menu called: sub={sub}")
        
        try:
            # 템플릿 파일 존재 확인
            template_name = f'{P.package_name}_{self.name}_{sub}.html'
            template_path = os.path.join(
                os.path.dirname(__file__), 
                'templates', 
                template_name
            )
            
            P.logger.info(f"Loading template: {template_name}")
            P.logger.info(f"Template exists: {os.path.exists(template_path)}")
            
            if sub == 'strategies':
                strategies_info = Logic.get_strategies_metadata()
                default_strategy = Logic.get_setting('default_strategy')
                
                P.logger.info(f"Strategies loaded: {len(strategies_info)} strategies")
                
                return render_template(
                    template_name,
                    arg=arg, 
                    strategies=strategies_info, 
                    default_strategy=default_strategy
                )

            elif sub == 'list':
                page = request.args.get('page', 1, type=int)
                per_page = request.args.get('per_page', 50, type=int)
                date_filter = request.args.get('date')
                market_filter = request.args.get('market')
                strategy_filter = request.args.get('strategy')
                passed_only = request.args.get('passed_only', 'true') == 'true'
                
                query = db.session.query(StockScreeningResult)
                if date_filter: 
                    query = query.filter(StockScreeningResult.screening_date == date_filter)
                if market_filter: 
                    query = query.filter(StockScreeningResult.market == market_filter)
                if strategy_filter: 
                    query = query.filter(StockScreeningResult.strategy_name == strategy_filter)
                if passed_only: 
                    query = query.filter(StockScreeningResult.passed == True)
                
                query = query.order_by(
                    StockScreeningResult.screening_date.desc(), 
                    StockScreeningResult.market_cap.desc()
                )
                pagination = query.paginate(page=page, per_page=per_page, error_out=False)
                
                available_dates = db.session.query(
                    StockScreeningResult.screening_date
                ).distinct().order_by(
                    StockScreeningResult.screening_date.desc()
                ).limit(30).all()
                dates = [d[0] for d in available_dates]
                available_strategies = Logic.get_strategies_metadata()
                
                return render_template(
                    template_name,
                    arg=arg,
                    results=pagination.items, 
                    pagination=pagination, 
                    dates=dates,
                    available_strategies=available_strategies, 
                    current_date=date_filter,
                    current_market=market_filter, 
                    current_strategy=strategy_filter, 
                    passed_only=passed_only
                )
            
            elif sub == 'detail':
                code = request.args.get('code')
                if not code:
                    path_parts = request.path.split('/')
                    try:
                        detail_index = path_parts.index('detail')
                        if detail_index + 1 < len(path_parts):
                            code = path_parts[detail_index + 1]
                    except (ValueError, IndexError):
                        pass

                if not code:
                    return render_template(
                        template_name,
                        arg=arg, 
                        error='종목 코드가 필요합니다.'
                    )

                result = db.session.query(StockScreeningResult).filter_by(
                    code=code
                ).order_by(StockScreeningResult.screening_date.desc()).first()
                
                if not result:
                    return render_template(
                        template_name,
                        arg=arg, 
                        error='종목을 찾을 수 없습니다.'
                    )
                
                history = db.session.query(StockScreeningResult).filter_by(
                    code=code
                ).order_by(StockScreeningResult.screening_date.desc()).limit(30).all()
                
                return render_template(
                    template_name,
                    arg=arg, 
                    result=result, 
                    history=history
                )

            elif sub == 'manual':
                default_strategy = Logic.get_setting('default_strategy')
                arg['default_strategy'] = default_strategy
                return render_template(template_name, arg=arg)
            
            elif sub == 'history':
                page = request.args.get('page', 1, type=int)
                pagination = db.session.query(ScreeningHistory).order_by(
                    ScreeningHistory.execution_date.desc()
                ).paginate(page=page, per_page=20, error_out=False)
                return render_template(
                    template_name,
                    arg=arg, 
                    histories=pagination.items, 
                    pagination=pagination
                )

            elif sub == 'statistics':
                thirty_days_ago = datetime.now() - timedelta(days=30)
                daily_stats = db.session.query(
                    StockScreeningResult.screening_date,
                    func.count(StockScreeningResult.id).label('total'),
                    func.sum(func.cast(StockScreeningResult.passed, db.Integer)).label('passed')
                ).filter(
                    StockScreeningResult.screening_date >= thirty_days_ago.date()
                ).group_by(
                    StockScreeningResult.screening_date
                ).order_by(StockScreeningResult.screening_date.desc()).all()
                
                market_stats = db.session.query(
                    StockScreeningResult.market,
                    func.count(StockScreeningResult.id).label('total'),
                    func.sum(func.cast(StockScreeningResult.passed, db.Integer)).label('passed')
                ).filter(StockScreeningResult.passed == True).group_by(
                    StockScreeningResult.market
                ).all()
                
                return render_template(
                    template_name,
                    arg=arg, 
                    daily_stats=daily_stats, 
                    market_stats=market_stats
                )
            
            else:
                P.logger.warning(f"Unknown sub menu: {sub}")
                return f"<div class='container'><h3>알 수 없는 메뉴: {sub}</h3></div>"

        except Exception as e:
            error_msg = f"Error in process_menu '{sub}': {str(e)}"
            P.logger.error(error_msg)
            P.logger.error(traceback.format_exc())
            return f"""
            <div class="container">
                <div class="alert alert-danger">
                    <h4>오류 발생</h4>
                    <p><strong>메뉴:</strong> {sub}</p>
                    <p><strong>에러:</strong> {str(e)}</p>
                    <pre>{traceback.format_exc()}</pre>
                </div>
            </div>
            """

    def process_command(self, command, arg1, arg2, arg3, req):
        """FlaskFarm의 command 처리"""
        P.logger.info(f"ModuleScreening.process_command: command={command}, arg1={arg1}")
        
        try:
            if command == 'start':
                strategy_id = arg1 if arg1 else Logic.get_setting('default_strategy')
                def screening_job():
                    Logic.start_screening(strategy_id=strategy_id, execution_type='manual')
                Job.start(f'{P.package_name}_manual', screening_job)
                return jsonify({'ret': 'success', 'msg': '스크리닝이 시작되었습니다.'})
            
            elif command == 'status':
                history = db.session.query(ScreeningHistory).order_by(
                    ScreeningHistory.execution_date.desc()
                ).first()
                if not history:
                    return jsonify({'ret': 'success', 'status': 'none'})
                return jsonify({
                    'ret': 'success',
                    'status': history.status,
                    'execution_date': history.execution_date.isoformat(),
                    'total_stocks': history.total_stocks,
                    'passed_stocks': history.passed_stocks,
                    'execution_time': history.execution_time
                })

            elif command == 'set_default_strategy':
                strategy_id = arg1
                if not strategy_id:
                    return jsonify({'ret': 'error', 'msg': '전략 ID가 필요합니다.'})
                Logic.set_setting('default_strategy', strategy_id)
                return jsonify({'ret': 'success', 'msg': '기본 전략이 설정되었습니다.'})
            
            elif command == 'recent_history':
                histories = db.session.query(ScreeningHistory).order_by(
                    ScreeningHistory.execution_date.desc()
                ).limit(5).all()
                data = []
                for h in histories:
                    strategy_name = 'N/A'
                    if h.strategy_name:
                        from strategies import get_strategy
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
                return jsonify({'ret': 'success', 'data': data})

        except Exception as e:
            P.logger.error(f"Command error: {str(e)}")
            P.logger.error(traceback.format_exc())
            return jsonify({'ret': 'error', 'msg': str(e)})
        
        return jsonify({'ret': 'error', 'msg': 'Unknown command'})

    def process_api(self, sub, req):
        """API 엔드포인트 처리"""
        P.logger.info(f"ModuleScreening.process_api: sub={sub}")
        
        try:
            if sub == 'download_csv':
                date_filter = request.args.get('date')
                query = db.session.query(StockScreeningResult).filter(
                    StockScreeningResult.passed == True
                )
                if date_filter:
                    query = query.filter(StockScreeningResult.screening_date == date_filter)
                results = query.order_by(StockScreeningResult.market_cap.desc()).all()
                
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow([
                    '종목코드', '종목명', '시장', '시가총액(억)', 
                    'PER', 'PBR', 'ROE(%)', 'F-Score', '배당수익률(%)', '스크리닝일자'
                ])
                for r in results:
                    writer.writerow([
                        r.code, r.name, r.market, 
                        r.market_cap // 100000000 if r.market_cap else 0, 
                        r.per, r.pbr, r.roe_avg_3y, r.fscore, r.div_yield, r.screening_date
                    ])
                output.seek(0)
                return Response(
                    output.getvalue(), 
                    mimetype='text/csv', 
                    headers={
                        'Content-Disposition': f'attachment; filename=7split_screening_{date_filter or "all"}.csv'
                    }
                )

        except Exception as e:
            P.logger.error(f"API error: {str(e)}")
            P.logger.error(traceback.format_exc())
            return jsonify({'ret': 'error', 'msg': str(e)})
