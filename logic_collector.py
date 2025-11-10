# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Data Collector (Improved)
OpenDartReader 개선 버전 적용
"""
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import requests  # 추가

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

from .setup import *

logger = P.logger             


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
                logger.info(f"Attempting to initialize OpenDartReader with API key: {'*' * len(dart_api_key) if dart_api_key else 'None'}")
                self.dart = odr.OpenDartReader(dart_api_key)
                logger.info("OpenDartReader initialized successfully")
            except Exception as e:
                logger.error(f"OpenDartReader initialization failed: {str(e)}")
                logger.error(traceback.format_exc())
    
    
    def get_all_tickers(self):
        """
        전체 종목 코드 수집 (KOSPI + KOSDAQ)
        
        Returns:
            list: [{code, name, market, sector, status}, ...]
        """
        logger.info("Starting to collect all tickers...")
        tickers = []
        
        try:
            if fdr:
                logger.debug("Using FDR to collect tickers...")
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
                logger.debug("Using pykrx to collect tickers...")
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
            else:
                logger.warning("Neither FDR nor pykrx_stock is available for ticker collection")
            
            logger.info(f"Final ticker count: {len(tickers)}")
            return tickers
            
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error(f"Failed to get tickers: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    
    def get_market_data(self, code, required_data):
        """
        시장 데이터 수집
        """
        logger.debug(f"[{code}] 'market' 데이터 수집 시작...")
        data = {
            'market_cap': 0, 'trading_value': 0, 'per': None,
            'pbr': None, 'div_yield': None
        }
        if 'market' not in required_data:
            logger.debug(f"[{code}] 'market' 데이터 불필요. 건너뜁니다.")
            return data
        
        # ... (기존 로직)
        logger.debug(f"[{code}] 'market' 데이터 수집 완료: {data}")
        return data

    def get_financial_data(self, code, required_data):
        """
        재무제표 데이터 수집
        """
        logger.debug(f"[{code}] 'financial' 데이터 수집 시작...")
        data = {
            'debt_ratio': None, 'current_ratio': None, 'roe': [], 'net_income': [],
            'revenue': [], 'operating_cashflow': None, 'capital': None,
            'capital_surplus': None, 'retained_earnings': None,
            'dividend_history': [], 'dividend_payout': None
        }
        if 'financial' not in required_data:
            logger.debug(f"[{code}] 'financial' 데이터 불필요. 건너뜁니다.")
            return data
        if not self.dart:
            logger.warning(f"[{code}] DART API가 초기화되지 않아 'financial' 데이터를 수집할 수 없습니다.")
            return data

        # ... (기존 로직)
        logger.debug(f"[{code}] 'financial' 데이터 수집 완료: {data}")
        return data

    def get_disclosure_info(self, code, required_data):
        """
        공시 정보 수집
        """
        logger.debug(f"[{code}] 'disclosure' 데이터 수집 시작...")
        info = {'has_cb_bw': False, 'has_paid_increase': False}
        if 'disclosure' not in required_data:
            logger.debug(f"[{code}] 'disclosure' 데이터 불필요. 건너뜁니다.")
            return info
        if not self.dart:
            logger.warning(f"[{code}] DART API가 초기화되지 않아 'disclosure' 데이터를 수집할 수 없습니다.")
            return info

        # ... (기존 로직)
        logger.debug(f"[{code}] 'disclosure' 데이터 수집 완료: {info}")
        return info

    def get_major_shareholder(self, code, required_data):
        """
        최대주주 지분율 조회
        """
        logger.debug(f"[{code}] 'major_shareholder' 데이터 수집 시작...")
        if 'major_shareholder' not in required_data:
            logger.debug(f"[{code}] 'major_shareholder' 데이터 불필요. 건너뜁니다.")
            return 0.0
        if not self.dart:
            logger.warning(f"[{code}] DART API가 초기화되지 않아 'major_shareholder' 데이터를 수집할 수 없습니다.")
            return 0.0

        # ... (기존 로직)
        # logger.debug(f"[{code}] 'major_shareholder' 데이터 수집 완료: {ratio}")
        # return ratio
        pass

    def get_all_data_for_ticker(self, code, required_data):
        """
        한 종목에 대한 모든 데이터를 수집하고 병합합니다.
        """
        logger.debug(f"[{code}] 모든 데이터 수집 시작...")
        
        stock_data = {'code': code}
        
        market_data = self.get_market_data(code, required_data)
        stock_data.update(market_data)
        
        financial_data = self.get_financial_data(code, required_data)
        stock_data.update(financial_data)
        
        disclosure_info = self.get_disclosure_info(code, required_data)
        stock_data.update(disclosure_info)
        
        major_shareholder_ratio = self.get_major_shareholder(code, required_data)
        stock_data['major_shareholder_ratio'] = major_shareholder_ratio
        
        logger.debug(f"[{code}] 모든 데이터 수집 완료.")
        return stock_data
    
    def _extract_value(self, df, account_name):
        # ... (기존 로직)
        pass
