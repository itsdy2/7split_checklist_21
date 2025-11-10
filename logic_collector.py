# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Data Collector (Improved)
OpenDartReader 개선 버전 적용
"""
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import requests

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
    def __init__(self, dart_api_key=None):
        self.dart_api_key = dart_api_key
        self.dart = odr.OpenDartReader(dart_api_key) if dart_api_key and odr else None

    def get_all_tickers(self):
        logger.info("전체 종목 코드 수집 시작...")
        # ... (existing logic)
        tickers = []
        if fdr:
            df_krx = fdr.StockListing('KRX')
            for _, row in df_krx.iterrows():
                tickers.append({'code': row['Code'], 'name': row['Name'], 'market': row['Market']})
        logger.info(f"총 {len(tickers)}개 종목 수집 완료.")
        return tickers

    def get_all_data_for_ticker(self, code, required_data):
        logger.debug(f"[{code}] 모든 데이터 수집 시작... 필요한 데이터: {required_data}")
        stock_data = {'code': code}
        
        if 'market' in required_data:
            stock_data.update(self.get_market_data(code))
        if 'financial' in required_data:
            stock_data.update(self.get_financial_data(code))
        if 'disclosure' in required_data:
            stock_data.update(self.get_disclosure_info(code))
        if 'major_shareholder' in required_data:
            stock_data['major_shareholder_ratio'] = self.get_major_shareholder(code)
            
        logger.debug(f"[{code}] 모든 데이터 수집 완료.")
        return stock_data

    def get_market_data(self, code):
        logger.debug(f"[{code}] 시장 데이터 수집...")
        # ... (existing logic)
        data = {'market_cap': 0, 'trading_value': 0, 'per': 0, 'pbr': 0, 'div_yield': 0}
        try:
            if pykrx_stock:
                today = datetime.now().strftime('%Y%m%d')
                df_fund = pykrx_stock.get_market_fundamental_by_ticker(today, market='ALL')
                if code in df_fund.index:
                    data['per'] = df_fund.loc[code, 'PER']
                    data['pbr'] = df_fund.loc[code, 'PBR']
                    data['div_yield'] = df_fund.loc[code, 'DIV']
            logger.debug(f"[{code}] 시장 데이터: {data}")
        except Exception as e:
            logger.warning(f"[{code}] 시장 데이터 수집 오류: {e}")
        return data

    def get_financial_data(self, code):
        logger.debug(f"[{code}] 재무 데이터 수집...")
        # ... (existing logic)
        data = {'debt_ratio': 0, 'roe': [0,0,0]}
        logger.debug(f"[{code}] 재무 데이터: {data}")
        return data

    def get_disclosure_info(self, code):
        logger.debug(f"[{code}] 공시 정보 수집...")
        # ... (existing logic)
        info = {'has_cb_bw': False, 'has_paid_increase': False}
        logger.debug(f"[{code}] 공시 정보: {info}")
        return info

    def get_major_shareholder(self, code):
        logger.debug(f"[{code}] 최대주주 정보 수집...")
        # ... (existing logic)
        ratio = 0.0
        logger.debug(f"[{code}] 최대주주 정보: {ratio}")
        return ratio