# -*- coding: utf-8 -*-
import traceback
from plugin import *
from .setup import P, F
from framework import db
from .trading_trend_analyzer import analyze_trading_trends
from .logic_notifier import Notifier

class ModuleTrend(PluginModuleBase):
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
        'trend_market': 'ALL',  # KOSPI, KOSDAQ, ALL
        'trend_top_n': '30',
        'trend_show_market_column': 'True',
        'trend_send_discord': 'True',
        'trend_send_insight': 'True',
        'trend_send_1day': 'True',
        'trend_send_1week': 'True',
        'trend_send_1month': 'True',
    }

    def __init__(self, P):
        super(ModuleTrend, self).__init__(P, name='trend', first_menu='setting')
        self.db_default = ModuleTrend._db_default
        P.logger.info("ModuleTrend initialized")

    def process_menu(self, page, req):
        P.logger.info(f"ModuleTrend.process_menu called: page={page}")
        try:
            arg = P.ModelSetting.to_dict()
            
            if page is None:
                page = 'setting'

            if page == 'setting':
                template_name = f'{P.package_name}_{self.name}_{page}.html'
                return render_template(template_name, arg=arg, P=P)

            elif page == 'daily':
                template_name = f'{P.package_name}_{self.name}_{page}.html'
                
                # Perform analysis and get results
                from pykrx import stock
                from datetime import datetime
                
                # Get the most recent business day
                today_str = datetime.now().strftime("%Y%m%d")
                end_date_str = stock.get_nearest_business_day_in_a_week(today_str)
                end_date_obj = datetime.strptime(end_date_str, "%Y%m%d")
                
                # Get settings
                market = P.ModelSetting.get('trend_market', 'ALL')
                top_n = int(P.ModelSetting.get('trend_top_n', '30'))
                show_market_column = P.ModelSetting.get('trend_show_market_column', 'True') == 'True'
                
                # Perform analysis
                results = analyze_trading_trends(
                    market=market,
                    top_n=top_n,
                    send_discord=False,  # Don't send to Discord from web view
                    show_market_column=show_market_column,
                    send_insight=P.ModelSetting.get('trend_send_insight', 'True') == 'True',
                    send_1day=P.ModelSetting.get('trend_send_1day', 'True') == 'True',
                    send_1week=P.ModelSetting.get('trend_send_1week', 'True') == 'True',
                    send_1month=P.ModelSetting.get('trend_send_1month', 'True') == 'True'
                )
                
                arg['analysis_date'] = end_date_obj.strftime('%Y-%m-%d')
                arg['results'] = results
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
            if sub == 'run_trend_analysis':
                # Get settings
                market = P.ModelSetting.get('trend_market', 'ALL')
                top_n = int(P.ModelSetting.get('trend_top_n', '30'))
                send_discord = P.ModelSetting.get('trend_send_discord', 'True') == 'True'
                show_market_column = P.ModelSetting.get('trend_show_market_column', 'True') == 'True'
                
                # Perform analysis
                results = analyze_trading_trends(
                    market=market,
                    top_n=top_n,
                    send_discord=send_discord,
                    show_market_column=show_market_column,
                    send_insight=P.ModelSetting.get('trend_send_insight', 'True') == 'True',
                    send_1day=P.ModelSetting.get('trend_send_1day', 'True') == 'True',
                    send_1week=P.ModelSetting.get('trend_send_1week', 'True') == 'True',
                    send_1month=P.ModelSetting.get('trend_send_1month', 'True') == 'True'
                )
                
                if results:
                    return jsonify({'ret': 'success', 'msg': '매매 동향 분석이 완료되었습니다.', 'data': results})
                else:
                    return jsonify({'ret': 'error', 'msg': '분석 중 오류가 발생했습니다.'})
            
            elif sub == 'manual_run_trend':
                # Run trend analysis with default parameters, sending to Discord
                from .setup import PluginModelSetting
                
                market = PluginModelSetting.get('trend_market', 'ALL')
                top_n = int(PluginModelSetting.get('trend_top_n', '30'))
                send_discord = PluginModelSetting.get('trend_send_discord', 'True') == 'True'
                show_market_column = PluginModelSetting.get('trend_show_market_column', 'True') == 'True'
                
                results = analyze_trading_trends(
                    market=market,
                    top_n=top_n,
                    send_discord=send_discord,
                    show_market_column=show_market_column,
                    send_insight=PluginModelSetting.get('trend_send_insight', 'True') == 'True',
                    send_1day=PluginModelSetting.get('trend_send_1day', 'True') == 'True',
                    send_1week=PluginModelSetting.get('trend_send_1week', 'True') == 'True',
                    send_1month=PluginModelSetting.get('trend_send_1month', 'True') == 'True'
                )
                
                if results:
                    # Send notification if enabled
                    if PluginModelSetting.get('notification_discord') == 'True':
                        webhook_url = PluginModelSetting.get('discord_webhook_url')
                        notifier = Notifier(webhook_url=webhook_url)
                        notifier.send_screening_result(
                            [], 0, 0, f"매매동향_{results['date']}"  # Pass empty results for this notification
                        )
                    
                    return jsonify({'ret': 'success', 'msg': '매매 동향 분석 및 알림 전송이 완료되었습니다.', 'data': results})
                else:
                    return jsonify({'ret': 'error', 'msg': '분석 중 오류가 발생했습니다.'})

        except Exception as e:
            P.logger.error(f"Exception in process_ajax: {str(e)}")
            P.logger.error(traceback.format_exc())
            return jsonify({'ret': 'error', 'msg': str(e)})

    def get_scheduler_interval(self):
        """스케줄러 간격을 분 단위로 반환"""
        try:
            # 모듈명_interval 키로 설정된 간격 가져오기 (예: trend_interval)
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
        """주기적으로 실행될 작업 정의"""
        P.logger.info("Trend module scheduler executed")
        try:
            # Only run if auto-start is enabled
            if P.ModelSetting.get('auto_start', 'False') == 'True':
                # Trigger the analysis
                from .setup import PluginModelSetting
                
                market = PluginModelSetting.get('trend_market', 'ALL')
                top_n = int(PluginModelSetting.get('trend_top_n', '30'))
                send_discord = PluginModelSetting.get('trend_send_discord', 'True') == 'True'
                show_market_column = PluginModelSetting.get('trend_show_market_column', 'True') == 'True'
                
                results = analyze_trading_trends(
                    market=market,
                    top_n=top_n,
                    send_discord=send_discord,
                    show_market_column=show_market_column,
                    send_insight=PluginModelSetting.get('trend_send_insight', 'True') == 'True',
                    send_1day=PluginModelSetting.get('trend_send_1day', 'True') == 'True',
                    send_1week=PluginModelSetting.get('trend_send_1week', 'True') == 'True',
                    send_1month=PluginModelSetting.get('trend_send_1month', 'True') == 'True'
                )
                
                if results:
                    P.logger.info(f"Trend analysis completed for {results['date']}")
                else:
                    P.logger.error("Trend analysis failed")
        except Exception as e:
            P.logger.error(f"Error in scheduler_function: {str(e)}")
            P.logger.error(traceback.format_exc())

    def setting_save_after(self, change_list):
        """
        설정 저장 후 호출됩니다.
        
        Args:
            change_list: 변경된 설정 키 목록
        """
        P.logger.debug(f"Trend module setting saved. Changed keys: {change_list}")
        
        # 스케줄링 간격이 변경되었다면 스케줄러 재시작
        if f'{self.name}_interval' in change_list:
            P.logic.scheduler_stop(self.name)
            P.logic.scheduler_start(self.name)