# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Data Collector (Improved)
OpenDartReader 개선 버전 적용
"""
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

try:
    from pykrx import stock as pykrx_stock
except ImportError:
    pykrx_stock = None

try:
    import FinanceDataReader as fdr
except ImportError:
    fdr = None

try:
    import OpenDartReader as odr
except ImportError:
    odr = None

from framework.logger import get_logger

logger = get_logger(__name__)


class DataCollector:
    """데이터 수집 클래스 (개선 버전)"""
    
    def __init__(self, dart_api_key=None):
        """
        Args:
            dart_api_key (str): DART API 키
        """
        self.dart_api_key = dart_api_key
        self.dart = None
        
        if dart_api_key and odr:
            try:
                self.dart = odr.OpenDartReader(dart_api_key)
                logger.info("OpenDartReader initialized successfully")
            except Exception as e:
                logger.error(f"OpenDartReader initialization failed: {str(e)}")
    
    
    def get_all_tickers(self):
        """
        전체 종목 코드 수집 (KOSPI + KOSDAQ)
        
        Returns:
            list: [{code, name, market, sector, status}, ...]
        """
        tickers = []
        
        try:
            if fdr:
                df_krx = fdr.StockListing('KRX')
                
                for _, row in df_krx.iterrows():
                    tickers.append({
                        'code': row['Code'],
                        'name': row['Name'],
                        'market': row['Market'],
                        'sector': row.get('Sector', ''),
                        'status': row.get('Status', '')
                    })
                
                logger.info(f"Total tickers collected via FDR: {len(tickers)}")
                
            elif pykrx_stock:
                today = datetime.now().strftime('%Y%m%d')
                
                kospi_tickers = pykrx_stock.get_market_ticker_list(today, market='KOSPI')
                kosdaq_tickers = pykrx_stock.get_market_ticker_list(today, market='KOSDAQ')
                
                for code in kospi_tickers:
                    name = pykrx_stock.get_market_ticker_name(code)
                    tickers.append({
                        'code': code,
                        'name': name,
                        'market': 'KOSPI',
                        'sector': '',
                        'status': ''
                    })
                
                for code in kosdaq_tickers:
                    name = pykrx_stock.get_market_ticker_name(code)
                    tickers.append({
                        'code': code,
                        'name': name,
                        'market': 'KOSDAQ',
                        'sector': '',
                        'status': ''
                    })
                
                logger.info(f"Total tickers collected via pykrx: {len(tickers)}")
            
            return tickers
            
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error(f"Failed to get tickers: {str(e)}")
            return []
    
    
    def get_market_data(self, code, required_data):
        """
        시장 데이터 수집
        
        Args:
            code (str): 종목코드
            required_data (set): 필요한 데이터 종류
        
        Returns:
            dict: 시장 데이터
        """
        data = {
            'market_cap': 0,
            'trading_value': 0,
            'per': None,
            'pbr': None,
            'div_yield': None
        }

        if 'market' not in required_data:
            return data
        
        try:
            if pykrx_stock:
                today = datetime.now().strftime('%Y%m%d')
                
                # 시가총액, 거래대금
                try:
                    df_cap = pykrx_stock.get_market_cap_by_ticker(today, market='ALL')
                    if code in df_cap.index:
                        data['market_cap'] = df_cap.loc[code, '시가총액']
                        data['trading_value'] = df_cap.loc[code, '거래대금']
                except Exception as e:
                    logger.debug(f"Market cap error for {code}: {str(e)}")
                
                # PER, PBR, 배당수익률
                try:
                    df_fund = pykrx_stock.get_market_fundamental_by_ticker(today, market='ALL')
                    if code in df_fund.index:
                        data['per'] = df_fund.loc[code, 'PER']
                        data['pbr'] = df_fund.loc[code, 'PBR']
                        data['div_yield'] = df_fund.loc[code, 'DIV']
                        
                        # 음수나 이상치 제거
                        if data['per'] and (data['per'] < 0 or data['per'] > 1000):
                            data['per'] = None
                        if data['pbr'] and (data['pbr'] < 0 or data['pbr'] > 100):
                            data['pbr'] = None
                except Exception as e:
                    logger.debug(f"Fundamental error for {code}: {str(e)}")
            
            # FDR로 보완
            if fdr and (data['per'] is None or pd.isna(data['per'])):
                try:
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=7)
                    df_price = fdr.DataReader(code, start_date, end_date)
                    
                    if not df_price.empty:
                        if 'PER' in df_price.columns:
                            per_value = df_price['PER'].iloc[-1]
                            if per_value and 0 < per_value < 1000:
                                data['per'] = per_value
                        
                        if 'PBR' in df_price.columns:
                            pbr_value = df_price['PBR'].iloc[-1]
                            if pbr_value and 0 < pbr_value < 100:
                                data['pbr'] = pbr_value
                                
                except Exception as e:
                    logger.debug(f"FDR market data error for {code}: {str(e)}")
            
            return data
            
        except (KeyError, AttributeError, requests.exceptions.RequestException, ValueError) as e:
            logger.error(f"Market data collection error for {code}: {str(e)}")
            return data
    
    
    def get_financial_data(self, code, required_data):
        """
        재무제표 데이터 수집 (OpenDartReader 개선)
        
        Args:
            code (str): 종목코드
            required_data (set): 필요한 데이터 종류
        
        Returns:
            dict: 재무 데이터
        """
        data = {
            'debt_ratio': None,
            'current_ratio': None,
            'roe': [],
            'net_income': [],
            'revenue': [],
            'operating_cashflow': None,
            'capital': None,
            'capital_surplus': None,
            'retained_earnings': None,
            'dividend_history': [],
            'dividend_payout': None
        }

        if 'financial' not in required_data:
            return data
        
        if not self.dart:
            return data
        
        try:
            current_year = datetime.now().year
            
            # 1. 재무비율 직접 조회 (ROE, 부채비율 등)
            try:
                df_ratio = self.dart.finstate_ratio(code, current_year - 1)
                
                if not df_ratio.empty and 'roe' in df_ratio.columns:
                    # ROE 3년치
                    roe_list = df_ratio['roe'].tolist()
                    data['roe'] = [float(x) if pd.notna(x) else 0 for x in roe_list[:3]]
                
                if not df_ratio.empty and 'debt_ratio' in df_ratio.columns:
                    debt_value = df_ratio['debt_ratio'].iloc[0]
                    if pd.notna(debt_value):
                        data['debt_ratio'] = float(debt_value)
                        
                if not df_ratio.empty and 'current_ratio' in df_ratio.columns:
                    current_value = df_ratio['current_ratio'].iloc[0]
                    if pd.notna(current_value):
                        data['current_ratio'] = float(current_value)
                        
            except Exception as e:
                logger.debug(f"Ratio data error for {code}: {str(e)}")
            
            # 2. 배당 정보
            try:
                df_div = self.dart.dividends(code, current_year - 3, current_year)
                
                if not df_div.empty and 'div' in df_div.columns:
                    div_list = df_div['div'].tolist()
                    data['dividend_history'] = [float(x) if pd.notna(x) else 0 for x in div_list]
                
                if not df_div.empty and 'dps' in df_div.columns:
                    # 배당성향 계산
                    dps = df_div['dps'].iloc[0] if len(df_div) > 0 else 0
                    eps = df_div.get('eps', [0]).iloc[0] if len(df_div) > 0 else 0
                    if eps and eps > 0:
                        data['dividend_payout'] = (dps / eps) * 100
                        
            except Exception as e:
                logger.debug(f"Dividend data error for {code}: {str(e)}")
            
            # 3. 재무제표 (손익계산서, 재무상태표)
            for year in range(current_year - 2, current_year + 1):
                try:
                    df_fs = self.dart.finstate_all(code, year, reprt_code='11011')
                    
                    if df_fs.empty:
                        continue
                    
                    # 당기순이익
                    net_income = self._extract_value(df_fs, '당기순이익')
                    if net_income:
                        data['net_income'].append(net_income)
                    
                    # 매출액
                    revenue = self._extract_value(df_fs, '매출액')
                    if revenue:
                        data['revenue'].append(revenue)
                    
                    # 영업현금흐름
                    if data['operating_cashflow'] is None:
                        cfo = self._extract_value(df_fs, '영업활동으로인한현금흐름')
                        if cfo:
                            data['operating_cashflow'] = cfo
                    
                    # 자본 정보 (유보율 계산용)
                    if data['capital'] is None:
                        data['capital'] = self._extract_value(df_fs, '자본금')
                        data['capital_surplus'] = self._extract_value(df_fs, '자본잉여금')
                        data['retained_earnings'] = self._extract_value(df_fs, '이익잉여금')
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.debug(f"Financial statement error for {code} year {year}: {str(e)}")
                    continue
            
            return data
            
        except (KeyError, AttributeError, requests.exceptions.RequestException, ValueError) as e:
            logger.error(f"Financial data collection error for {code}: {str(e)}")
            return data
    
    
    def get_disclosure_info(self, code, required_data):
        """
        공시 정보 수집 (CB/BW, 유상증자)
        
        Args:
            code (str): 종목코드
            required_data (set): 필요한 데이터 종류
        
        Returns:
            dict: {'has_cb_bw': bool, 'has_paid_increase': bool}
        """
        info = {
            'has_cb_bw': False,
            'has_paid_increase': False
        }

        if 'disclosure' not in required_data:
            return info
        
        if not self.dart:
            return info
        
        try:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            end_date = datetime.now().strftime('%Y%m%d')
            
            df_list = self.dart.list(code, start=start_date, end=end_date)
            
            if df_list.empty:
                return info
            
            # CB/BW 발행 확인
            cb_keywords = ['전환사채', '신주인수권부사채', 'CB', 'BW']
            for keyword in cb_keywords:
                if df_list['report_nm'].str.contains(keyword, na=False).any():
                    info['has_cb_bw'] = True
                    break
            
            # 유상증자 확인 (개선: capital_changes 사용)
            try:
                df_capital = self.dart.capital_changes(code)
                if not df_capital.empty:
                    recent_changes = df_capital[
                        df_capital['change_date'] >= start_date
                    ]
                    
                    if not recent_changes.empty:
                        # 유상증자인지 확인 (감자가 아닌 증자)
                        for _, row in recent_changes.iterrows():
                            if '유상증자' in str(row.get('change_reason', '')):
                                info['has_paid_increase'] = True
                                break
            except Exception as e:
                logger.debug(f"Capital changes error for {code}: {str(e)}")
                
                # Fallback: 공시 리스트에서 확인
                if df_list['report_nm'].str.contains('유상증자', na=False).any():
                    info['has_paid_increase'] = True
            
            return info
            
        except (KeyError, AttributeError, requests.exceptions.RequestException, ValueError) as e:
            logger.error(f"Disclosure info error for {code}: {str(e)}")
            return info
    
    
    def get_major_shareholder(self, code, required_data):
        """
        최대주주 지분율 조회
        
        Args:
            code (str): 종목코드
            required_data (set): 필요한 데이터 종류
        
        Returns:
            float: 최대주주 지분율 (%)
        """
        if 'major_shareholder' not in required_data:
            return 0.0
        if not self.dart:
            return 0.0
        
        try:
            df_major = self.dart.major_shareholders(code)
            
            if df_major.empty:
                return 0.0
            
            # 첫 번째 행이 최대주주
            ratio = df_major.iloc[0]['지분율']
            
            # '%' 제거 및 float 변환
            if isinstance(ratio, str):
                ratio = float(ratio.replace('%', '').replace(',', ''))
            
            return float(ratio)
            
        except (KeyError, AttributeError, requests.exceptions.RequestException, ValueError) as e:
            logger.debug(f"Major shareholder error for {code}: {str(e)}")
            return 0.0
    
    
    def _extract_value(self, df, account_name):
        """
        재무제표에서 특정 계정과목 값 추출
        
        Args:
            df (DataFrame): 재무제표 DataFrame
            account_name (str): 계정과목명
        
        Returns:
            float: 값 (없으면 0)
        """
        try:
            if 'account_nm' not in df.columns:
                return 0
            
            matched = df[df['account_nm'].str.contains(account_name, na=False)]
            
            if matched.empty:
                return 0
            
            value_col = 'thstrm_amount' if 'thstrm_amount' in df.columns else df.columns[-1]
            value = matched.iloc[0][value_col]
            
            if pd.isna(value):
                return 0
            
            return float(value)
            
        except Exception as e:
            logger.debug(f"Extract value error for {account_name}: {str(e)}")
            return 0