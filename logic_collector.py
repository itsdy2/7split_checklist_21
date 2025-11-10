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

from .setup import P
logger = P.logger

# --- 라이브러리 임포트 및 로깅 ---
try:
    from pykrx import stock as pykrx_stock
    logger.info("Successfully imported 'pykrx'")
except ImportError:
    pykrx_stock = None
    logger.warning("Failed to import 'pykrx'. Some market data functionality will be unavailable.")

try:
    import FinanceDataReader as fdr
    logger.info("Successfully imported 'FinanceDataReader'")
except ImportError:
    fdr = None
    logger.warning("Failed to import 'FinanceDataReader'. Ticker listing might not work.")

try:
    import OpenDartReader as odr
    logger.info("Successfully imported 'OpenDartReader'")
except ImportError:
    odr = None
    logger.warning("Failed to import 'OpenDartReader'. Financial data functionality will be unavailable.")
# ------------------------------------


class DataCollector:
    def __init__(self, dart_api_key=None):
        self.dart_api_key = dart_api_key
        if dart_api_key and odr:
            self.dart = odr.OpenDartReader(dart_api_key)
            logger.info("OpenDartReader initialized.")
        else:
            self.dart = None
            if not odr:
                logger.warning("OpenDartReader not initialized because the library is not available.")
            if not dart_api_key:
                logger.warning("OpenDartReader not initialized because DART API key is missing.")

    def get_all_tickers(self):
        logger.info("전체 종목 코드 수집 시작...")
        if not fdr:
            logger.error("FinanceDataReader is not available. Cannot fetch tickers.")
            return []
        # ... (rest of the logic)
        tickers = []
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
        # ... (other data collection calls)
            
        logger.debug(f"[{code}] 모든 데이터 수집 완료.")
        return stock_data

    def get_market_data(self, code):
        logger.debug(f"[{code}] 시장 데이터 수집...")
        if not pykrx_stock:
            logger.warning(f"[{code}] pykrx is not available. Cannot fetch market data.")
            return {}
        # ... (rest of the logic)
        return {'per': 10, 'pbr': 1} # Dummy data

    # ... (other get_* methods)
