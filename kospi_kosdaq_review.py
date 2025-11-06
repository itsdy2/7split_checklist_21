import pandas as pd
import requests
from pykrx import stock
from datetime import datetime, timedelta
import traceback
import numpy as np
import time

# -----------------------------------------------------------------
# (설정)
# 1. Discord 웹훅 URL을 여기에 "정확하게" 입력하세요. (필수!)
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1433311443352031296/FUa5evWJ4wT8ZTWKu2FWXSzgnRZj6XMyx-qZjUBJsdHbBsDV81I5LzR85mQtrSOqdoxi"

# 2. 조회할 시장 (KOSPI, KOSDAQ, ALL)
# [!!! 수정 !!!] "ALL"로 변경하여 KOSPI, KOSDAQ, KONEX 전체 조회
MARKET_TO_SEARCH = "ALL"  

# 3. 조회할 상위 N개 종목
TOP_N = 30  # (10개씩 분할되어 전송됨)

# 4. [!!! 신규 추가 !!!] 시장 구분 열 표시 여부 (True: 켜기, False: 끄기)
# True로 설정하면 Discord 테이블에 "KOSPI", "KOSDAQ" 열이 추가됩니다.
# (테이블이 너무 넓어져 보기 불편할 경우 False로 변경하세요)
SHOW_MARKET_COLUMN = True

# 5. [!!! 신규 추가 !!!] 각 리포트 전송 여부 설정 (True: 켜기, False: 끄기)
SEND_INSIGHT_REPORT = True  # 📈 연속 수익률 상위 리포트
SEND_1DAY_REPORT = True     # 📅 1일 순매수 리포트
SEND_1WEEK_REPORT = True    # 📅 1주 순매수 리포트
SEND_1MONTH_REPORT = True   # 📅 1개월 순매수 리포트
# -----------------------------------------------------------------


# --- [!!! 수정 !!!] market_map_df, show_market_column 인자 추가 ---
def get_consecutive_ror_insight(market, end_date, day_ago, week_ago, month_ago, top_n,
                                market_map_df, show_market_column):
    """
    (수정) market="ALL"로 조회하고, market_map_df를 join하여 시장 구분 표시
    """
    print("\n🚀 연속 수익률 상위 종목(1일/1주/1개월) 인사이트 조회 중...")
    print(f" (시장: {market} / 1일: {day_ago} / 1주: {week_ago} / 1개월: {month_ago} ~ {end_date})")
    print("-" * 60)
    
    try:
        # [!!! 수정 !!!] market 변수("ALL")를 그대로 사용
        df_1d = stock.get_market_price_change_by_ticker(day_ago, end_date, market)
        df_1w = stock.get_market_price_change_by_ticker(week_ago, end_date, market)
        df_1m = stock.get_market_price_change_by_ticker(month_ago, end_date, market)

        top_1d_tickers = set(df_1d.nlargest(top_n, '등락률').index)
        top_1w_tickers = set(df_1w.nlargest(top_n, '등락률').index)
        top_1m_tickers = set(df_1m.nlargest(top_n, '등락률').index)

        consecutive_top_tickers = list(top_1d_tickers & top_1w_tickers & top_1m_tickers)
        
        if not consecutive_top_tickers:
            print(f"[{market}] 1일/1주/1개월 연속 Top {top_n} 수익률 종목이 없습니다.")
            return None

        print(f"✅ 연속 상위 종목 발견: {consecutive_top_tickers}")

        content = ""
        merged_df = pd.DataFrame(index=consecutive_top_tickers)
        merged_df['종목명'] = merged_df.index.map(stock.get_market_ticker_name)
        merged_df['ror_1d'] = df_1d.loc[consecutive_top_tickers, '등락률']
        merged_df['ror_1w'] = df_1w.loc[consecutive_top_tickers, '등락률']
        merged_df['ror_1m'] = df_1m.loc[consecutive_top_tickers, '등락률']
        
        # [!!! 신규 !!!] 시장 구분 맵 조인
        if not market_map_df.empty:
            merged_df = merged_df.join(market_map_df, how='left')
            merged_df['시장구분'].fillna('기타', inplace=True)
            
        merged_df.sort_values(by='ror_1m', ascending=False, inplace=True)

        for ticker, row in merged_df.iterrows():
            # [!!! 수정 !!!] show_market_column에 따라 시장 구분 표시
            market_str = ""
            if show_market_column and '시장구분' in row and pd.notna(row['시장구분']):
                market_str = f" / {row['시장구분']}"
                
            content += (
                f"- **{row['종목명']}** ({ticker}{market_str}): "
                f"`1일 {row['ror_1d']:+.1f}%` / "
                f"`1주 {row['ror_1w']:+.1f}%` / "
                f"`1개월 {row['ror_1m']:+.1f}%`\n"
            )
        
        if len(content) > 1024:
            print("[Warning] 연속 수익률 인사이트가 1024자를 초과합니다. 일부가 잘릴 수 있습니다.")
            content = content[:1020] + "..."

        insight_field = {
            "name": f"📈 연속 수익률 상위 (1일/1주/1개월 Top {top_n})",
            "value": content,
            "inline": False
        }
        return insight_field

    except Exception as e:
        print(f"[Error] 연속 수익률 인사이트 생성 중 오류 발생: {e}")
        traceback.print_exc()
        return None

# --- [!!! 수정 !!!] market_map_df 인자 추가 ---
def get_top_netbuy_by_period(market, start_date, end_date, top_n,
                             market_map_df):
    """
    (수정) market="ALL"로 조회하고, market_map_df를 join하여 '시장구분' 컬럼 추가
    """
    try:
        # 1. 티커 및 종목명 (market="ALL" 사용)
        tickers_list = stock.get_market_ticker_list(end_date, market=market)
        if not tickers_list:
            print(f"[{end_date}] {market}의 티커 정보를 가져올 수 없습니다.")
            return None, None
        tickers_df = pd.DataFrame(tickers_list, columns=['티커'])
        tickers_df['종목명'] = tickers_df['티커'].map(stock.get_market_ticker_name)
        tickers_df.set_index('티커', inplace=True)

        # 2. 기간 누적 순매수 (market="ALL" 사용)
        print("  - 기관합계 순매수 데이터 조회 중...")
        df_inst = stock.get_market_net_purchases_of_equities_by_ticker(
            start_date, end_date, market, "기관합계"
        )
        if df_inst.empty: df_inst = pd.DataFrame(columns=['기관합계'])
        else:
            df_inst = df_inst[['순매수거래대금']]; df_inst.rename(columns={'순매수거래대금': '기관합계'}, inplace=True)

        print("  - 외국인 순매수 데이터 조회 중...")
        df_fgn = stock.get_market_net_purchases_of_equities_by_ticker(
            start_date, end_date, market, "외국인"
        )
        if df_fgn.empty: df_fgn = pd.DataFrame(columns=['외국인'])
        else:
            df_fgn = df_fgn[['순매수거래대금']]; df_fgn.rename(columns={'순매수거래대금': '외국인'}, inplace=True)

        df = pd.concat([df_inst, df_fgn], axis=1)
        df.dropna(how='all', inplace=True); df.fillna(0, inplace=True)
        if df.empty:
            print(f"  [{market}] 기관/외국인 순매수 데이터가 없습니다."); return None, None

        # 3. 시가총액 및 종가 (market="ALL" 사용)
        print("  - 시가총액 및 종가 데이터 조회 중...")
        marcap_df = stock.get_market_cap_by_ticker(end_date, market=market)
        if marcap_df.empty:
            print(f"[{end_date}] {market}의 시가총액 정보를 가져올 수 없습니다."); return None, None
        marcap_df.rename(columns={'현재가': '조회일 종가'}, inplace=True)
        if '조회일 종가' not in marcap_df.columns and '종가' in marcap_df.columns:
             marcap_df.rename(columns={'종가': '조회일 종가'}, inplace=True)
        if '조회일 종가' not in marcap_df.columns:
             print("[Error] '조회일 종가' 또는 '종가' 컬럼을 찾을 수 없습니다."); return None, None
        marcap_df = marcap_df[['시가총액', '조회일 종가']]

        # 4. 기간 수익률 (market="ALL" 사용)
        print("  - 기간 수익률 데이터 조회 중...")
        df_ror = stock.get_market_price_change_by_ticker(start_date, end_date, market)
        if df_ror.empty:
            df_ror = pd.DataFrame(columns=['수익률']); df_ror['수익률'] = 0.0
        else:
            df_ror = df_ror[['등락률']]; df_ror.rename(columns={'등락률': '수익률'}, inplace=True)

        # 5. 모든 데이터 병합
        merged_df = tickers_df.join(df, how='inner').join(marcap_df, how='inner').join(df_ror, how='left')
        merged_df['수익률'] = merged_df['수익률'].fillna(0.0) 
        merged_df.dropna(inplace=True) 
        if merged_df.empty:
            print(f"데이터 병합 결과가 비어있습니다 (기간: {start_date}~{end_date})."); return None, None
        
        # [!!! 신규 !!!] 시장 구분 맵 조인
        if not market_map_df.empty:
            merged_df = merged_df.join(market_map_df, how='left')
            # KOSPI/KOSDAQ/KONEX 맵에 없는 티커 (예: ETF, ETN 등)는 '기타'로 표시
            merged_df['시장구분'].fillna('기타', inplace=True)
        else:
            # 맵 생성이 실패했을 경우를 대비해 빈 컬럼 생성
            merged_df['시장구분'] = 'N/A'
            
        # 6. 투자자별 Top N 선정
        final_inst_df = merged_df.nlargest(top_n, '기관합계')
        final_fgn_df = merged_df.nlargest(top_n, '외국인')
        
        print(f"✅ {market} {start_date}~{end_date} 데이터 처리 완료.")
        return final_inst_df, final_fgn_df

    except Exception as e:
        print(f"[Error] get_top_netbuy_by_period 함수 오류: {e}")
        traceback.print_exc()
        return None, None

# --- [!!! 수정 !!!] show_market_column 인자 추가 및 조건부 렌더링 ---
def format_data_for_discord(df, investor_type, rank_start=1, show_market_column=True):
    """
    (수정) show_market_column=True일 경우 '시장' 열을 포함한 테이블 생성
    """
    if df is None or df.empty:
        if rank_start > 1: return "" 
        return f"{investor_type} 순매수 상위 데이터가 없습니다."
    
    try:
        if investor_type not in df.columns:
            print(f"[Format Error] '{investor_type}' 컬럼이 DataFrame에 없습니다.")
            return f"{investor_type} 데이터 포맷팅 중 오류가 발생했습니다."
            
        df['순매수억'] = df[investor_type] / 1_0000_0000
        df['시총비(%)'] = (df[investor_type].divide(df['시가총액']).replace([np.inf, -np.inf], 0)) * 100
        
        header = ""
        if rank_start == 1:
            if show_market_column:
                # [!!! 수정 !!!] '시장' 열 추가 (KOSDAQ 이름이 길므로 정렬 변경)
                header = (
                    "| 순위 | 시장 | 종목명 | 현재가 | 누적(억) | 시총비(%) | 수익률(%) |\n"
                    "|:---:|:------|:------|-------:|---------:|----------:|----------:|\n"
                )
            else:
                # [기존]
                header = (
                    "| 순위 | 종목명 | 현재가 | 누적(억) | 시총비(%) | 수익률(%) |\n"
                    "|:---:|:------|-------:|---------:|----------:|----------:|\n"
                )
        
        content = ""
        
        for index, row in df.iterrows():
            rank = list(df.index).index(index) + rank_start
            
            name = f"{row['종목명']}"
            price = f"{row['조회일 종가']:,}"
            netbuy = f"{row['순매수억']:,.1f}"
            cap_ratio = f"{row['시총비(%)']:.3f}"
            ror = f"{row['수익률']:+.2f}"
            
            # [!!! 수정 !!!] show_market_column에 따라 '시장' 열 추가
            if show_market_column:
                market_name = row.get('시장구분', 'N/A')
                content += f"| {rank} | {market_name} | {name} | {price} | {netbuy} | {cap_ratio} | {ror} |\n"
            else:
                content += f"| {rank} | {name} | {price} | {netbuy} | {cap_ratio} | {ror} |\n"

        full_table = header + content
        
        if len(full_table) > 1024:
            print(f"[Warning] {investor_type} 테이블(Rank {rank_start}-)이 1024자를 초과합니다. 일부가 잘릴 수 있습니다.")
            return full_table[:1020] + "..." 

        return full_table

    except Exception as e:
        print(f"[Error] format_data_for_discord 함수 오류: {e}")
        traceback.print_exc()
        return f"{investor_type} 데이터 포맷팅 중 오류 발생: {e}"


# --- [수정 없음] 개별 메시지 전송 함수 (정상) ---
def send_to_discord(webhook_url, embed_fields, title, footer_text):
    """
    Discord 웹훅으로 포맷팅된 메시지(Embed)를 전송합니다.
    """
    if not webhook_url or "discord.com/api/webhooks/" not in webhook_url:
        print("[Error] Discord 웹훅 URL이 유효하지 않습니다. DISCORD_WEBHOOK_URL을 확인하세요.")
        return

    if not embed_fields:
        print("[Info] Discord로 전송할 데이터가 없습니다.")
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
            "username": "주식 시장 리포터",
            "avatar_url": "https://i.imgur.com/v0e4vXw.png",
            "embeds": [embed]
        }
        response = requests.post(webhook_url, json=data)
        
        if 200 <= response.status_code < 300:
            print(f"\n🚀 Discord로 메시지를 성공적으로 전송했습니다. (Title: {title})")
        else:
            print(f"[Error] Discord 전송 실패: {response.status_code}, {response.text}")

    except Exception as e:
        print(f"[Error] send_to_discord 함수 오류: {e}")
        traceback.print_exc()

# --- [!!! 수정 !!!] main 로직에 market_map_df 생성 및 인자 전달 ---
def main():
    try:
        print("="*60)
        print(f"📈 {MARKET_TO_SEARCH} 시장 분석 스크립트 실행...")
        
        # 1. 기준 날짜 계산 (공통)
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
        print(f" (데이터 기준일: {end_date_obj.strftime('%Y년 %m월 %d일')})")
        
        # [!!! 신규 !!!] KOSPI/KOSDAQ/KONEX 티커 맵 생성 (Full Name 사용)
        print(" (KOSPI/KOSDAQ/KONEX 시장 구분 맵 생성 중...)")
        try:
            kospi_tickers = stock.get_market_ticker_list(end_date_str, market="KOSPI")
            kosdaq_tickers = stock.get_market_ticker_list(end_date_str, market="KOSDAQ")
            konex_tickers = stock.get_market_ticker_list(end_date_str, market="KONEX")
            
            # [!!! 수정 !!!] Full Name 사용
            k_map = pd.DataFrame(kospi_tickers, columns=['티커']); k_map['시장구분'] = 'KOSPI'
            q_map = pd.DataFrame(kosdaq_tickers, columns=['티커']); q_map['시장구분'] = 'KOSDAQ'
            n_map = pd.DataFrame(konex_tickers, columns=['티커']); n_map['시장구분'] = 'KONEX'
            
            market_map_df = pd.concat([k_map, q_map, n_map]).set_index('티커')
            print(f" (시장 맵 생성 완료: KOSPI {len(k_map)}, KOSDAQ {len(q_map)}, KONEX {len(n_map)})")
        except Exception as e:
            print(f"[Error] 시장 구분 맵 생성 실패: {e}. '시장구분' 없이 계속합니다.")
            market_map_df = pd.DataFrame(columns=['시장구분']) # 빈 맵 생성
        print("="*60)


        # 2. [!!! 수정 !!!] 연속 수익률 상위 인사이트 (개별 전송)
        if SEND_INSIGHT_REPORT:
            ror_insight_field = get_consecutive_ror_insight(
                MARKET_TO_SEARCH,
                end_date_str, day_ago, week_ago, month_ago,
                TOP_N,
                market_map_df, # [!!! 추가 !!!]
                SHOW_MARKET_COLUMN # [!!! 추가 !!!]
            )
            if ror_insight_field:
                # [!!! 수정 !!!] MARKET_TO_SEARCH 변수 사용
                insight_title = f"📈 {MARKET_TO_SEARCH} 연속 수익률 상위 (Top {TOP_N})"
                insight_footer = f"pykrx analysis bot | 데이터 조회 기준: {footer_date_str}"
                
                send_to_discord(
                    DISCORD_WEBHOOK_URL,
                    [ror_insight_field],
                    insight_title,
                    insight_footer
                )
                time.sleep(1) 

        # 3. [!!! 수정 !!!] 기간별 순매수 리포트 (개별 전송)
        
        periods_to_run = {}
        if SEND_1DAY_REPORT: periods_to_run["1일"] = day_ago
        if SEND_1WEEK_REPORT: periods_to_run["1주"] = week_ago
        if SEND_1MONTH_REPORT: periods_to_run["1개월"] = month_ago

        chunk_size = 10 
        
        for period_label, start_date_str in periods_to_run.items():
            
            print(f"\n📅 {period_label} ({start_date_str} ~ {end_date_str}) 순매수 데이터 조회 중...")
            print("-"*60)
            
            # (B-1) 데이터 조회 (Top N개)
            inst_df_full, fgn_df_full = get_top_netbuy_by_period(
                MARKET_TO_SEARCH, start_date_str, end_date_str, TOP_N,
                market_map_df # [!!! 추가 !!!]
            )
            
            period_embed_fields = [] 
            
            # (B-2) 기관 데이터: 10개씩 분할
            if inst_df_full is not None and not inst_df_full.empty:
                for i in range(0, TOP_N, chunk_size):
                    # [!!! 수정 !!!] .copy() 추가하여 SettingWithCopyWarning 방지
                    chunk_df = inst_df_full.iloc[i : i + chunk_size].copy() 
                    if chunk_df.empty: continue
                    
                    rank_start = i + 1; rank_end = i + len(chunk_df)
                    inst_title = f"💎 기관합계 ({period_label}) Top {rank_start}-{rank_end}"
                    
                    # [!!! 수정 !!!] show_market_column 인자 전달
                    inst_content = format_data_for_discord(
                        chunk_df, "기관합계", rank_start=rank_start, show_market_column=SHOW_MARKET_COLUMN
                    )
                    period_embed_fields.append({"name": inst_title, "value": inst_content, "inline": False})
            else: 
                inst_title = f"💎 기관합계 ({period_label}) Top {TOP_N}"
                inst_content = format_data_for_discord(None, "기관합계", rank_start=1, show_market_column=SHOW_MARKET_COLUMN)
                period_embed_fields.append({"name": inst_title, "value": inst_content, "inline": False})

            # (B-3) 외국인 데이터: 10개씩 분할
            if fgn_df_full is not None and not fgn_df_full.empty:
                for i in range(0, TOP_N, chunk_size):
                    # [!!! 수정 !!!] .copy() 추가하여 SettingWithCopyWarning 방지
                    chunk_df = fgn_df_full.iloc[i : i + chunk_size].copy() 
                    if chunk_df.empty: continue
                        
                    rank_start = i + 1; rank_end = i + len(chunk_df)
                    fgn_title = f"🌍 외국인 ({period_label}) Top {rank_start}-{rank_end}"
                    
                    # [!!! 수정 !!!] show_market_column 인자 전달
                    fgn_content = format_data_for_discord(
                        chunk_df, "외국인", rank_start=rank_start, show_market_column=SHOW_MARKET_COLUMN
                    )
                    period_embed_fields.append({"name": fgn_title, "value": fgn_content, "inline": False})
            else:
                fgn_title = f"🌍 외국인 ({period_label}) Top {TOP_N}"
                fgn_content = format_data_for_discord(None, "외국인", rank_start=1, show_market_column=SHOW_MARKET_COLUMN)
                period_embed_fields.append({"name": fgn_title, "value": fgn_content, "inline": False})
            
            # (B-4) [!!! 수정 !!!] 이 기간의 리포트를 개별 전송
            if period_embed_fields:
                # [!!! 수정 !!!] MARKET_TO_SEARCH 변수 사용
                period_title = f"📊 {MARKET_TO_SEARCH} {period_label} 순매수 리포트"
                period_footer = f"pykrx analysis bot | 기간: {start_date_str} ~ {end_date_str}"
                
                send_to_discord(
                    DISCORD_WEBHOOK_URL,
                    period_embed_fields,
                    period_title,
                    period_footer
                )
                time.sleep(1) 
            else:
                print(f"[{period_label}] 전송할 데이터가 없습니다.")

        print("\n" + "="*60)
        print("✅ 모든 작업 완료.")

    except Exception as e:
        print(f"[Fatal Error] main 함수 실행 중 치명적 오류 발생: {e}")
        traceback.print_exc()
        try:
            error_title = "🚨 스크립트 실행 오류"
            error_footer = f"Time: {datetime.now().isoformat()}"
            error_field = [{"name": "오류 내용", "value": f"```\n{e}\n```", "inline": False}]
            send_to_discord(DISCORD_WEBHOOK_URL, error_field, error_title, error_footer)
        except:
            pass 

if __name__ == "__main__":
    main()