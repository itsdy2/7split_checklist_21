import pandas as pd
import requests
from datetime import datetime, timedelta
import traceback
import numpy as np
import time
import os
from .setup import P, F
from framework import db

logger = P.logger

# --- Core functionality adapted from the original script ---

def get_consecutive_ror_insight(market, end_date, day_ago, week_ago, month_ago, top_n,
                                market_map_df, show_market_column):
    """
    (Modified) Analyze top performers based on consecutive returns
    """
    logger.info(f"\\n🚀 Analyzing top performers for returns insight...")
    logger.info(f" (Market: {market} / 1-day: {day_ago} / 1-week: {week_ago} / 1-month: {month_ago} ~ {end_date})")
    logger.info("-" * 60)
    
    try:
        from pykrx import stock
        
        df_1d = stock.get_market_price_change_by_ticker(day_ago, end_date, market)
        df_1w = stock.get_market_price_change_by_ticker(week_ago, end_date, market)
        df_1m = stock.get_market_price_change_by_ticker(month_ago, end_date, market)

        top_1d_tickers = set(df_1d.nlargest(top_n, '등락률').index)
        top_1w_tickers = set(df_1w.nlargest(top_n, '등락률').index)
        top_1m_tickers = set(df_1m.nlargest(top_n, '등락률').index)

        consecutive_top_tickers = list(top_1d_tickers & top_1w_tickers & top_1m_tickers)
        
        if not consecutive_top_tickers:
            logger.info(f"[{market}] No consecutive Top {top_n} return performers found.")
            return None

        logger.info(f"✅ Found consecutive top performers: {consecutive_top_tickers}")

        content = ""
        merged_df = pd.DataFrame(index=consecutive_top_tickers)
        merged_df['종목명'] = merged_df.index.map(stock.get_market_ticker_name)
        merged_df['ror_1d'] = df_1d.loc[consecutive_top_tickers, '등락률']
        merged_df['ror_1w'] = df_1w.loc[consecutive_top_tickers, '등락률']
        merged_df['ror_1m'] = df_1m.loc[consecutive_top_tickers, '등락률']
        
        # Join the market classification map
        if not market_map_df.empty:
            merged_df = merged_df.join(market_map_df, how='left')
            merged_df['시장구분'].fillna('기타', inplace=True)
            
        merged_df.sort_values(by='ror_1m', ascending=False, inplace=True)

        for ticker, row in merged_df.iterrows():
            # Show market classification based on show_market_column setting
            market_str = ""
            if show_market_column and '시장구분' in row and pd.notna(row['시장구분']):
                market_str = f" / {row['시장구분']}"
                
            content += (
                f"- **{row['종목명']}** ({ticker}{market_str}): "
                f"`1-day {row['ror_1d']:+.1f}%` / "
                f"`1-week {row['ror_1w']:+.1f}%` / "
                f"`1-month {row['ror_1m']:+.1f}%`\\n"
            )
        
        if len(content) > 1024:
            logger.warning("[Warning] Continuous returns insight exceeds 1024 characters. It may be truncated.")
            content = content[:1020] + "..."

        insight_field = {
            "name": f"📈 Top performers (1-day/1-week/1-month Top {top_n})",
            "value": content,
            "inline": False
        }
        return insight_field

    except Exception as e:
        logger.error(f"[Error] Error in continuous returns analysis: {e}")
        traceback.print_exc()
        return None


def get_top_netbuy_by_period(market, start_date, end_date, top_n, market_map_df):
    """
    (Modified) Get top net purchases by period
    """
    try:
        from pykrx import stock
        
        # 1. Tickers and names (using market="ALL")
        tickers_list = stock.get_market_ticker_list(end_date, market=market)
        if not tickers_list:
            logger.info(f"[{end_date}] Could not retrieve tickers for {market}")
            return None, None
        tickers_df = pd.DataFrame(tickers_list, columns=['티커'])
        tickers_df['종목명'] = tickers_df['티커'].map(stock.get_market_ticker_name)
        tickers_df.set_index('티커', inplace=True)

        # 2. Period cumulative net purchases (using market="ALL")
        logger.debug("  - Retrieving institutional net purchase data...")
        df_inst = stock.get_market_net_purchases_of_equities_by_ticker(
            start_date, end_date, market, "기관합계"
        )
        if df_inst.empty: df_inst = pd.DataFrame(columns=['기관합계'])
        else:
            df_inst = df_inst[['순매수거래대금']]; df_inst.rename(columns={'순매수거래대금': '기관합계'}, inplace=True)

        logger.debug("  - Retrieving foreign net purchase data...")
        df_fgn = stock.get_market_net_purchases_of_equities_by_ticker(
            start_date, end_date, market, "외국인"
        )
        if df_fgn.empty: df_fgn = pd.DataFrame(columns=['외국인'])
        else:
            df_fgn = df_fgn[['순매수거래대금']]; df_fgn.rename(columns={'순매수거래대금': '외국인'}, inplace=True)

        df = pd.concat([df_inst, df_fgn], axis=1)
        df.dropna(how='all', inplace=True); df.fillna(0, inplace=True)
        if df.empty:
            logger.info(f"  [{market}] No institutional/foreign net purchase data found."); return None, None

        # 3. Market cap and closing price (using market="ALL")
        logger.debug("  - Retrieving market cap and closing price data...")
        marcap_df = stock.get_market_cap_by_ticker(end_date, market=market)
        if marcap_df.empty:
            logger.info(f"[{end_date}] Could not retrieve market cap data for {market}."); return None, None
        marcap_df.rename(columns={'현재가': '조회일 종가'}, inplace=True)
        if '조회일 종가' not in marcap_df.columns and '종가' in marcap_df.columns:
             marcap_df.rename(columns={'종가': '조회일 종가'}, inplace=True)
        if '조회일 종가' not in marcap_df.columns:
             logger.error("[Error] Could not find '조회일 종가' or '종가' columns."); return None, None
        marcap_df = marcap_df[['시가총액', '조회일 종가']]

        # 4. Period returns (using market="ALL")
        logger.debug("  - Retrieving period returns data...")
        df_ror = stock.get_market_price_change_by_ticker(start_date, end_date, market)
        if df_ror.empty:
            df_ror = pd.DataFrame(columns=['수익률']); df_ror['수익률'] = 0.0
        else:
            df_ror = df_ror[['등락률']]; df_ror.rename(columns={'등락률': '수익률'}, inplace=True)

        # 5. All data merge
        merged_df = tickers_df.join(df, how='inner').join(marcap_df, how='inner').join(df_ror, how='left')
        merged_df['수익률'] = merged_df['수익률'].fillna(0.0) 
        merged_df.dropna(inplace=True) 
        if merged_df.empty:
            logger.info(f"Data merge result is empty (Period: {start_date}~{end_date})."); return None, None
        
        # Join the market classification map
        if not market_map_df.empty:
            merged_df = merged_df.join(market_map_df, how='left')
            merged_df['시장구분'].fillna('기타', inplace=True)
        else:
            merged_df['시장구분'] = 'N/A'
            
        # Select top N for each investor type
        final_inst_df = merged_df.nlargest(top_n, '기관합계')
        final_fgn_df = merged_df.nlargest(top_n, '외국인')
        
        logger.info(f"✅ Processed {market} data for {start_date}~{end_date}.")
        return final_inst_df, final_fgn_df

    except Exception as e:
        logger.error(f"[Error] in get_top_netbuy_by_period function: {e}")
        traceback.print_exc()
        return None, None


def format_data_for_web(df, investor_type, rank_start=1, show_market_column=True):
    """
    Format data for web display
    """
    if df is None or df.empty:
        if rank_start > 1: return [] 
        return []
    
    try:
        if investor_type not in df.columns:
            logger.error(f"[Format Error] '{investor_type}' column not found in DataFrame.")
            return []
            
        df['순매수억'] = df[investor_type] / 1_0000_0000
        df['시총비(%)'] = (df[investor_type].divide(df['시가총액']).replace([np.inf, -np.inf], 0)) * 100
        
        formatted_data = []
        
        for index, row in df.iterrows():
            rank = list(df.index).index(index) + rank_start
            
            name = f"{row['종목명']}"
            price = f"{row['조회일 종가']:,}"
            netbuy = f"{row['순매수억']:,.1f}"
            cap_ratio = f"{row['시총비(%)']:.3f}"
            ror = f"{row['수익률']:+.2f}"
            
            # Include market column based on show_market_column setting
            if show_market_column:
                market_name = row.get('시장구분', 'N/A')
                formatted_data.append({
                    'rank': rank,
                    'market': market_name,
                    'name': name,
                    'price': price,
                    'netbuy': netbuy,
                    'cap_ratio': cap_ratio,
                    'ror': ror
                })
            else:
                formatted_data.append({
                    'rank': rank,
                    'name': name,
                    'price': price,
                    'netbuy': netbuy,
                    'cap_ratio': cap_ratio,
                    'ror': ror
                })

        return formatted_data

    except Exception as e:
        logger.error(f"[Error] in format_data_for_web function: {e}")
        traceback.print_exc()
        return []


def format_data_for_discord(df, investor_type, rank_start=1, show_market_column=True):
    """
    (Modified) Format data for Discord with option to include market column
    """
    if df is None or df.empty:
        if rank_start > 1: return "" 
        return f"No top {investor_type} purchase data found."
    
    try:
        if investor_type not in df.columns:
            logger.error(f"[Format Error] '{investor_type}' column not found in DataFrame.")
            return f"Error formatting {investor_type} data."
            
        df['순매수억'] = df[investor_type] / 1_0000_0000
        df['시총비(%)'] = (df[investor_type].divide(df['시가총액']).replace([np.inf, -np.inf], 0)) * 100
        
        header = ""
        if rank_start == 1:
            if show_market_column:
                header = (
                    "| Rank | Market | Name | Price | Net Buy(B) | Cap Ratio(%) | Return(%) |\\n"
                    "|:---:|:------|:------|-------:|---------:|----------:|----------:|\\n"
                )
            else:
                header = (
                    "| Rank | Name | Price | Net Buy(B) | Cap Ratio(%) | Return(%) |\\n"
                    "|:---:|:------|-------:|---------:|----------:|----------:|\\n"
                )
        
        content = ""
        
        for index, row in df.iterrows():
            rank = list(df.index).index(index) + rank_start
            
            name = f"{row['종목명']}"
            price = f"{row['조회일 종가']:,}"
            netbuy = f"{row['순매수억']:,.1f}"
            cap_ratio = f"{row['시총비(%)']:.3f}"
            ror = f"{row['수익률']:+.2f}"
            
            if show_market_column:
                market_name = row.get('시장구분', 'N/A')
                content += f"| {rank} | {market_name} | {name} | {price} | {netbuy} | {cap_ratio} | {ror} |\\n"
            else:
                content += f"| {rank} | {name} | {price} | {netbuy} | {cap_ratio} | {ror} |\\n"

        full_table = header + content
        
        if len(full_table) > 1024:
            logger.warning(f"[Warning] {investor_type} table (Rank {rank_start}-) exceeds 1024 characters. It may be truncated.")
            return full_table[:1020] + "..."

        return full_table

    except Exception as e:
        logger.error(f"[Error] in format_data_for_discord function: {e}")
        traceback.print_exc()
        return f"Error formatting {investor_type} data: {e}"


def send_to_discord(webhook_url, embed_fields, title, footer_text):
    """
    Send formatted message (Embed) to Discord webhook.
    """
    if not webhook_url or "discord.com/api/webhooks/" not in webhook_url:
        logger.error("[Error] Discord webhook URL is invalid. Check DISCORD_WEBHOOK_URL.")
        return

    if not embed_fields:
        logger.info("[Info] No data to send to Discord.")
        return

    try:
        embed = {
            "title": title,
            "color": 5814783, 
            "fields": embed_fields,
            "footer": { "text": footer_text },
            "timestamp": datetime.utcnow().isoformat()
        }
        data = {
            "username": "Stock Market Reporter",
            "avatar_url": "https://i.imgur.com/v0e4vXw.png",
            "embeds": [embed]
        }
        response = requests.post(webhook_url, json=data)
        
        if 200 <= response.status_code < 300:
            logger.info(f"\\n🚀 Successfully sent message to Discord. (Title: {title})")
        else:
            logger.error(f"[Error] Discord send failed: {response.status_code}, {response.text}")

    except Exception as e:
        logger.error(f"[Error] in send_to_discord function: {e}")
        traceback.print_exc()


def analyze_trading_trends(market=None, top_n=None, send_discord=None, show_market_column=None, 
                           send_insight=None, send_1day=None, send_1week=None, send_1month=None):
    """
    Main function to analyze trading trends with proper integration to Flaskfarm settings
    If parameters are not provided, it will use plugin settings
    """
    from .setup import PluginModelSetting
    
    # Use plugin settings if parameters are not provided
    if market is None:
        market = PluginModelSetting.get('trend_market', 'ALL')
    if top_n is None:
        top_n = int(PluginModelSetting.get('trend_top_n', '30'))
    if send_discord is None:
        send_discord = PluginModelSetting.get('trend_send_discord', 'True') == 'True'
    if show_market_column is None:
        show_market_column = PluginModelSetting.get('trend_show_market_column', 'True') == 'True'
    if send_insight is None:
        send_insight = PluginModelSetting.get('trend_send_insight', 'True') == 'True'
    if send_1day is None:
        send_1day = PluginModelSetting.get('trend_send_1day', 'True') == 'True'
    if send_1week is None:
        send_1week = PluginModelSetting.get('trend_send_1week', 'True') == 'True'
    if send_1month is None:
        send_1month = PluginModelSetting.get('trend_send_1month', 'True') == 'True'
    """
    Main function to analyze trading trends
    """
    try:
        from pykrx import stock
        logger.info("="*60)
        logger.info(f"📈 Analyzing {market} market trends...")
        
        # 1. Calculate reference dates (common)
        today_str = datetime.now().strftime("%Y%m%d")
        end_date_str = stock.get_nearest_business_day_in_a_week(today_str)
        end_date_obj = datetime.strptime(end_date_str, "%Y%m%d")
        
        day_ago = stock.get_nearest_business_day_in_a_week(
            (end_date_obj - timedelta(days=1)).strftime("%Y%m%d")
        )
        week_ago = stock.get_nearest_business_day_in_a_week(
            (end_date_obj - timedelta(days=7)).strftime("%Y%m%d")
        )
        month_ago = stock.get_nearest_business_day_in_a_week(
            (end_date_obj - timedelta(days=30)).strftime("%Y%m%d")
        )
        
        footer_date_str = end_date_obj.strftime('%Y-%m-%d')
        logger.info(f" (Data reference date: {end_date_obj.strftime('%Y-%m-%d')})")
        
        # Create KOSPI/KOSDAQ/KONEX ticker map (using Full Name)
        logger.info(" (Creating KOSPI/KOSDAQ/KONEX market classification map...)")
        try:
            kospi_tickers = stock.get_market_ticker_list(end_date_str, market="KOSPI")
            kosdaq_tickers = stock.get_market_ticker_list(end_date_str, market="KOSDAQ")
            konex_tickers = stock.get_market_ticker_list(end_date_str, market="KONEX")
            
            k_map = pd.DataFrame(kospi_tickers, columns=['티커']); k_map['시장구분'] = 'KOSPI'
            q_map = pd.DataFrame(kosdaq_tickers, columns=['티커']); q_map['시장구분'] = 'KOSDAQ'
            n_map = pd.DataFrame(konex_tickers, columns=['티커']); n_map['시장구분'] = 'KONEX'
            
            market_map_df = pd.concat([k_map, q_map, n_map]).set_index('티커')
            logger.info(f" (Market map created: KOSPI {len(k_map)}, KOSDAQ {len(q_map)}, KONEX {len(n_map)})")
        except Exception as e:
            logger.error(f"[Error] Failed to create market classification map: {e}. Proceeding without market classification.")
            market_map_df = pd.DataFrame(columns=['시장구분']) # Create empty map
        logger.info("="*60)

        results = {
            'date': end_date_obj.strftime('%Y-%m-%d'),
            'insights': [],
            'periods_data': {}
        }

        # 2. Continuous return top performers insight (individual send)
        if send_insight:
            ror_insight_field = get_consecutive_ror_insight(
                market,
                end_date_str, day_ago, week_ago, month_ago,
                top_n,
                market_map_df,
                show_market_column
            )
            if ror_insight_field:
                insight_title = f"📈 {market} Top Performers (Top {top_n})"
                insight_footer = f"pykrx analysis bot | Data reference: {footer_date_str}"
                
                if send_discord:
                    send_to_discord(
                        webhook_url=PluginModelSetting.get('discord_webhook_url', ''),
                        embed_fields=[ror_insight_field],
                        title=insight_title,
                        footer_text=insight_footer
                    )
                    time.sleep(1)
                    
                results['insights'].append({
                    'title': insight_title,
                    'data': ror_insight_field
                })

        # 3. Periodic net buy reports (individual send)
        
        periods_to_run = {}
        if send_1day: periods_to_run["1-day"] = day_ago
        if send_1week: periods_to_run["1-week"] = week_ago
        if send_1month: periods_to_run["1-month"] = month_ago

        chunk_size = 10 
        
        for period_label, start_date_str in periods_to_run.items():
            
            logger.info(f"\\n📅 {period_label} ({start_date_str} ~ {end_date_str}) net buy data retrieval...")
            logger.info("-"*60)
            
            # (B-1) Data retrieval (Top N)
            inst_df_full, fgn_df_full = get_top_netbuy_by_period(
                market, start_date_str, end_date_str, top_n,
                market_map_df
            )
            
            # Format for web display
            inst_data = format_data_for_web(
                inst_df_full, "기관합계", rank_start=1, show_market_column=show_market_column
            )
            fgn_data = format_data_for_web(
                fgn_df_full, "외국인", rank_start=1, show_market_column=show_market_column
            )
            
            results['periods_data'][period_label] = {
                'institutional': inst_data,
                'foreign': fgn_data
            }
            
            if not send_discord:
                continue
                
            # Format for Discord
            period_embed_fields = [] 
            
            # (B-2) Institutional data: split into chunks of 10
            if inst_df_full is not None and not inst_df_full.empty:
                for i in range(0, top_n, chunk_size):
                    chunk_df = inst_df_full.iloc[i : i + chunk_size].copy() 
                    if chunk_df.empty: continue
                    
                    rank_start = i + 1; rank_end = i + len(chunk_df)
                    inst_title = f"💎 Institution ({period_label}) Top {rank_start}-{rank_end}"
                    
                    inst_content = format_data_for_discord(
                        chunk_df, "기관합계", rank_start=rank_start, show_market_column=show_market_column
                    )
                    period_embed_fields.append({"name": inst_title, "value": inst_content, "inline": False})
            else: 
                inst_title = f"💎 Institution ({period_label}) Top {top_n}"
                inst_content = format_data_for_discord(None, "기관합계", rank_start=1, show_market_column=show_market_column)
                period_embed_fields.append({"name": inst_title, "value": inst_content, "inline": False})

            # (B-3) Foreign data: split into chunks of 10
            if fgn_df_full is not None and not fgn_df_full.empty:
                for i in range(0, top_n, chunk_size):
                    chunk_df = fgn_df_full.iloc[i : i + chunk_size].copy() 
                    if chunk_df.empty: continue
                        
                    rank_start = i + 1; rank_end = i + len(chunk_df)
                    fgn_title = f"🌍 Foreign ({period_label}) Top {rank_start}-{rank_end}"
                    
                    fgn_content = format_data_for_discord(
                        chunk_df, "외국인", rank_start=rank_start, show_market_column=show_market_column
                    )
                    period_embed_fields.append({"name": fgn_title, "value": fgn_content, "inline": False})
            else:
                fgn_title = f"🌍 Foreign ({period_label}) Top {top_n}"
                fgn_content = format_data_for_discord(None, "외국인", rank_start=1, show_market_column=show_market_column)
                period_embed_fields.append({"name": fgn_title, "value": fgn_content, "inline": False})
            
            # (B-4) Send this period's report individually
            if period_embed_fields:
                period_title = f"📊 {market} {period_label} Net Buy Report"
                period_footer = f"pykrx analysis bot | Period: {start_date_str} ~ {end_date_str}"
                
                send_to_discord(
                    webhook_url=PluginModelSetting.get('discord_webhook_url', ''),
                    embed_fields=period_embed_fields,
                    title=period_title,
                    footer_text=period_footer
                )
                time.sleep(1) 
            else:
                logger.info(f"[{period_label}] No data to send.")

        logger.info("\\n" + "="*60)
        logger.info("✅ All tasks completed.")

        return results

    except Exception as e:
        logger.error(f"[Fatal Error] Critical error in analysis: {e}")
        traceback.print_exc()
        try:
            error_title = "🚨 Script execution error"
            error_footer = f"Time: {datetime.now().isoformat()}"
            error_field = [{"name": "Error details", "value": f"```\n{e}\n```", "inline": False}]
            send_to_discord(PluginModelSetting.get('discord_webhook_url', ''), error_field, error_title, error_footer)
        except:
            pass
        return None