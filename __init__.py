# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Flask Blueprint
웹 인터페이스 라우팅
"""
from flask import Blueprint, request, render_template, jsonify, redirect
from framework import db
from framework.logger import get_logger

from .plugin import package_name
from .model import ModelSetting, StockScreeningResult, ScreeningHistory, FilterDetail
from .logic import Logic

logger = get_logger(__name__)

# Blueprint 생성
blueprint = Blueprint(
    package_name,
    __name__,
    url_prefix=f'/{package_name}',
    template_folder='templates',
    static_folder='static'
)


# 메인 페이지 (리다이렉트)
@blueprint.route('/')
def index():
    """메인 페이지 - 결과 목록으로 리다이렉트"""
    return redirect(f'/{package_name}/list')


# 전략 선택 페이지
@blueprint.route('/strategies')
def strategies():
    """전략 선택 페이지"""
    try:
        strategies_info = Logic.get_strategies_metadata()
        default_strategy = Logic.get_setting('default_strategy')
        
        return render_template(
            f'{package_name}_strategies.html',
            strategies=strategies_info,
            default_strategy=default_strategy
        )
        
    except Exception as e:
        logger.error(f"Strategies page error: {str(e)}")
        return render_template(f'{package_name}_strategies.html', strategies=[], error=str(e))


# 설정 페이지
@blueprint.route('/setting', methods=['GET', 'POST'])
def setting():
    """설정 페이지"""
    if request.method == 'POST':
        try:
            # 설정 저장
            for key in request.form:
                Logic.set_setting(key, request.form[key])
            
            # 스케줄러 재시작
            Logic.scheduler_stop()
            Logic.scheduler_start()
            
            return jsonify({'success': True, 'message': '설정이 저장되었습니다.'})
            
        except Exception as e:
            logger.error(f"Setting save error: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    
    # GET: 설정 로드
    settings = {}
    for key in Logic.db_default.keys():
        settings[key] = Logic.get_setting(key)

    strategies = Logic.get_strategies_metadata()
    
    return render_template(f'{package_name}_setting.html', settings=settings, strategies=strategies)


# 스크리닝 결과 목록
@blueprint.route('/list')
def list_results():
    """스크리닝 결과 목록"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # 필터 옵션
        date_filter = request.args.get('date')
        market_filter = request.args.get('market')
        strategy_filter = request.args.get('strategy')
        passed_only = request.args.get('passed_only', 'true') == 'true'
        
        # 쿼리 빌드
        query = db.session.query(StockScreeningResult)
        
        if date_filter:
            query = query.filter(StockScreeningResult.screening_date == date_filter)
        
        if market_filter:
            query = query.filter(StockScreeningResult.market == market_filter)

        if strategy_filter:
            query = query.filter(StockScreeningResult.strategy_name == strategy_filter)
        
        if passed_only:
            query = query.filter(StockScreeningResult.passed == True)
        
        # 최신순 정렬
        query = query.order_by(
            StockScreeningResult.screening_date.desc(),
            StockScreeningResult.market_cap.desc()
        )
        
        # 페이지네이션
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # 날짜 목록 (필터용)
        available_dates = db.session.query(StockScreeningResult.screening_date)\
            .distinct()\
            .order_by(StockScreeningResult.screening_date.desc())\
            .limit(30)\
            .all()
        dates = [d[0] for d in available_dates]

        # 전략 목록 (필터용)
        available_strategies = Logic.get_strategies_metadata()
        
        return render_template(
            f'{package_name}_list.html',
            results=pagination.items,
            pagination=pagination,
            dates=dates,
            available_strategies=available_strategies,
            current_date=date_filter,
            current_market=market_filter,
            current_strategy=strategy_filter,
            passed_only=passed_only
        )
        
    except Exception as e:
        logger.error(f"List error: {str(e)}")
        return render_template(f'{package_name}_list.html', results=[], error=str(e))


# 종목 상세
@blueprint.route('/detail/<code>')
def detail(code):
    """종목 상세 정보"""
    try:
        # 최신 스크리닝 결과
        result = db.session.query(StockScreeningResult)\
            .filter_by(code=code)\
            .order_by(StockScreeningResult.screening_date.desc())\
            .first()
        
        if not result:
            return render_template(f'{package_name}_detail.html', error='종목을 찾을 수 없습니다.')
        
        # 이력 데이터
        history = db.session.query(StockScreeningResult)\
            .filter_by(code=code)\
            .order_by(StockScreeningResult.screening_date.desc())\
            .limit(30)\
            .all()
        
        return render_template(
            f'{package_name}_detail.html',
            result=result,
            history=history
        )
        
    except Exception as e:
        logger.error(f"Detail error: {str(e)}")
        return render_template(f'{package_name}_detail.html', error=str(e))


# 수동 실행 페이지
@blueprint.route('/manual')
def manual():
    """수동 실행 페이지"""
    return render_template(f'{package_name}_manual.html')


# 실행 이력
@blueprint.route('/history')
def history():
    """실행 이력 페이지"""
    try:
        page = request.args.get('page', 1, type=int)
        
        pagination = db.session.query(ScreeningHistory)\
            .order_by(ScreeningHistory.execution_date.desc())\
            .paginate(page=page, per_page=20, error_out=False)
        
        return render_template(
            f'{package_name}_history.html',
            histories=pagination.items,
            pagination=pagination
        )
        
    except Exception as e:
        logger.error(f"History error: {str(e)}")
        return render_template(f'{package_name}_history.html', histories=[], error=str(e))


# 통계 페이지
@blueprint.route('/statistics')
def statistics():
    """통계 페이지"""
    try:
        # 최근 30일 통계
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # 일자별 통과 종목 수
        daily_stats = db.session.query(
            StockScreeningResult.screening_date,
            func.count(StockScreeningResult.id).label('total'),
            func.sum(func.cast(StockScreeningResult.passed, db.Integer)).label('passed')
        ).filter(
            StockScreeningResult.screening_date >= thirty_days_ago.date()
        ).group_by(
            StockScreeningResult.screening_date
        ).order_by(
            StockScreeningResult.screening_date.desc()
        ).all()
        
        # 시장별 통계
        market_stats = db.session.query(
            StockScreeningResult.market,
            func.count(StockScreeningResult.id).label('total'),
            func.sum(func.cast(StockScreeningResult.passed, db.Integer)).label('passed')
        ).filter(
            StockScreeningResult.passed == True
        ).group_by(
            StockScreeningResult.market
        ).all()
        
        return render_template(
            f'{package_name}_statistics.html',
            daily_stats=daily_stats,
            market_stats=market_stats
        )
        
    except Exception as e:
        logger.error(f"Statistics error: {str(e)}")
        return render_template(f'{package_name}_statistics.html', error=str(e))


# API: 스크리닝 시작
@blueprint.route('/api/start', methods=['POST'])
def api_start():
    """스크리닝 수동 시작"""
    try:
        from framework.job import Job
        strategy_id = request.form.get('strategy')
        
        def screening_job():
            Logic.start_screening(strategy_id=strategy_id, execution_type='manual')
        
        Job.start(f'{package_name}_manual', screening_job)
        
        return jsonify({'success': True, 'message': '스크리닝이 시작되었습니다.'})
        
    except Exception as e:
        logger.error(f"Start screening error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# API: 진행 상황 조회
@blueprint.route('/api/status')
def api_status():
    """현재 실행 상태 조회"""
    try:
        # 가장 최근 히스토리 조회
        history = db.session.query(ScreeningHistory)\
            .order_by(ScreeningHistory.execution_date.desc())\
            .first()
        
        if not history:
            return jsonify({'status': 'none'})
        
        return jsonify({
            'status': history.status,
            'execution_date': history.execution_date.isoformat(),
            'total_stocks': history.total_stocks,
            'passed_stocks': history.passed_stocks,
            'execution_time': history.execution_time
        })
        
    except Exception as e:
        logger.error(f"Status error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})


# API: 결과 데이터 (JSON)
@blueprint.route('/api/results')
def api_results():
    """결과 데이터 API"""
    try:
        date_filter = request.args.get('date')
        limit = request.args.get('limit', 100, type=int)
        
        query = db.session.query(StockScreeningResult)\
            .filter(StockScreeningResult.passed == True)
        
        if date_filter:
            query = query.filter(StockScreeningResult.screening_date == date_filter)
        
        results = query.order_by(
            StockScreeningResult.screening_date.desc(),
            StockScreeningResult.market_cap.desc()
        ).limit(limit).all()
        
        data = []
        for r in results:
            data.append({
                'code': r.code,
                'name': r.name,
                'market': r.market,
                'market_cap': r.market_cap,
                'per': r.per,
                'pbr': r.pbr,
                'roe': r.roe_avg_3y,
                'fscore': r.fscore,
                'div_yield': r.div_yield,
                'screening_date': r.screening_date.isoformat()
            })
        
        return jsonify({'success': True, 'data': data})
        
    except Exception as e:
        logger.error(f"API results error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# API: CSV 다운로드
@blueprint.route('/api/download_csv')
def api_download_csv():
    """결과 CSV 다운로드"""
    try:
        import csv
        from io import StringIO
        from flask import Response
        
        date_filter = request.args.get('date')
        
        query = db.session.query(StockScreeningResult)\
            .filter(StockScreeningResult.passed == True)
        
        if date_filter:
            query = query.filter(StockScreeningResult.screening_date == date_filter)
        
        results = query.order_by(
            StockScreeningResult.market_cap.desc()
        ).all()
        
        # CSV 생성
        output = StringIO()
        writer = csv.writer(output)
        
        # 헤더
        writer.writerow([
            '종목코드', '종목명', '시장', '시가총액(억)', 'PER', 'PBR', 
            'ROE(%)', 'F-Score', '배당수익률(%)', '스크리닝일자'
        ])
        
        # 데이터
        for r in results:
            writer.writerow([
                r.code,
                r.name,
                r.market,
                r.market_cap // 100000000 if r.market_cap else 0,
                r.per,
                r.pbr,
                r.roe_avg_3y,
                r.fscore,
                r.div_yield,
                r.screening_date
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
        return jsonify({'success': False, 'message': str(e)})


# API: 기본 전략 설정
@blueprint.route('/api/set_default_strategy', methods=['POST'])
def api_set_default_strategy():
    """기본 전략 설정"""
    try:
        strategy_id = request.form.get('strategy')
        if not strategy_id:
            return jsonify({'success': False, 'message': '전략 ID가 필요합니다.'})
        
        Logic.set_setting('default_strategy', strategy_id)
        return jsonify({'success': True, 'message': '기본 전략이 설정되었습니다.'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# API: 최근 실행 이력
@blueprint.route('/api/recent_history')
def api_recent_history():
    """최근 실행 이력 5건"""
    try:
        histories = db.session.query(ScreeningHistory)\
            .order_by(ScreeningHistory.execution_date.desc())\
            .limit(5)\
            .all()
        
        data = []
        for h in histories:
            strategy_name = 'N/A'
            if h.strategy_name:
                strategy = Logic.get_strategy(h.strategy_name)
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
        
        return jsonify({'success': True, 'data': data})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@blueprint.route('/api/save_condition_schedules', methods=['POST'])
def api_save_condition_schedules():
    """개별 조건 스케줄 저장"""
    try:
        schedules = []
        for key, value in request.form.items():
            if key.startswith('cron_'):
                parts = key.split('_')
                strategy_id = parts[1]
                condition_number = int(parts[2])
                cron_expression = value
                is_enabled = request.form.get(f'enabled_{strategy_id}_{condition_number}') == 'True'
                schedules.append({
                    'strategy_id': strategy_id,
                    'condition_number': condition_number,
                    'cron_expression': cron_expression,
                    'is_enabled': is_enabled
                })
        
        if Logic.save_condition_schedules(schedules):
            return jsonify({'success': True, 'message': '개별 조건 스케줄이 저장되었습니다.'})
        else:
            return jsonify({'success': False, 'message': '개별 조건 스케줄 저장에 실패했습니다.'})

    except Exception as e:
        logger.error(f"Save condition schedules error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# 로그 페이지
@blueprint.route('/log')
def log():
    """로그 페이지"""
    return render_template(f'{package_name}_log.html')


# 도움말 페이지
@blueprint.route('/help')
def help_page():
    """도움말 페이지"""
    return render_template(f'{package_name}_help.html')