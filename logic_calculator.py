# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Calculator
F-Score, 유보율 등 재무지표 계산
"""
import pandas as pd
import numpy as np
from .setup import *

logger = P.logger  


class Calculator:
    """재무지표 계산 클래스"""
    
    @staticmethod
    def calculate_fscore(financial_data):
        """
        피오트로스키 F-Score 계산 (9가지 지표)
        
        Args:
            financial_data (dict): 재무제표 데이터
                {
                    'net_income': [최신, 1년전, 2년전],
                    'roa': [최신, 1년전],
                    'cfo': [최신, 1년전],  # 영업현금흐름
                    'accrual': float,
                    'debt_ratio': [최신, 1년전],
                    'current_ratio': [최신, 1년전],
                    'shares': [최신, 1년전],
                    'gross_margin': [최신, 1년전],
                    'asset_turnover': [최신, 1년전]
                }
        
        Returns:
            int: F-Score (0-9점)
        """
        score = 0
        
        try:
            # 1. 수익성 (Profitability) - 4점
            # 1-1. ROA > 0
            if financial_data.get('roa', [0])[0] > 0:
                score += 1
            
            # 1-2. 영업현금흐름 > 0
            if financial_data.get('cfo', [0])[0] > 0:
                score += 1
            
            # 1-3. ROA 증가
            roa = financial_data.get('roa', [0, 0])
            if len(roa) >= 2 and roa[0] > roa[1]:
                score += 1
            
            # 1-4. 발생액 < 영업현금흐름 (품질)
            cfo = financial_data.get('cfo', [0])[0]
            net_income = financial_data.get('net_income', [0])[0]
            if cfo > net_income:
                score += 1
            
            # 2. 레버리지/유동성 (Leverage, Liquidity) - 3점
            # 2-1. 부채비율 감소
            debt = financial_data.get('debt_ratio', [0, 0])
            if len(debt) >= 2 and debt[0] < debt[1]:
                score += 1
            
            # 2-2. 유동비율 증가
            current = financial_data.get('current_ratio', [0, 0])
            if len(current) >= 2 and current[0] > current[1]:
                score += 1
            
            # 2-3. 신주 미발행
            shares = financial_data.get('shares', [0, 0])
            if len(shares) >= 2 and shares[0] <= shares[1]:
                score += 1
            
            # 3. 운영효율성 (Operating Efficiency) - 2점
            # 3-1. 매출총이익률 증가
            gross_margin = financial_data.get('gross_margin', [0, 0])
            if len(gross_margin) >= 2 and gross_margin[0] > gross_margin[1]:
                score += 1
            
            # 3-2. 자산회전율 증가
            asset_turnover = financial_data.get('asset_turnover', [0, 0])
            if len(asset_turnover) >= 2 and asset_turnover[0] > asset_turnover[1]:
                score += 1
            
            logger.debug(f"F-Score calculated: {score}/9")
            return score
            
        except Exception as e:
            logger.error(f"F-Score calculation error: {str(e)}")
            return 0
    
    
    @staticmethod
    def calculate_retention_ratio(equity_data):
        """
        유보율 계산
        유보율 = (자본잉여금 + 이익잉여금) / 자본금 × 100
        
        Args:
            equity_data (dict): 자본 관련 데이터
                {
                    'capital': 자본금,
                    'capital_surplus': 자본잉여금,
                    'retained_earnings': 이익잉여금
                }
        
        Returns:
            float: 유보율 (%)
        """
        try:
            capital = equity_data.get('capital', 0)
            if capital == 0:
                return 0.0
            
            capital_surplus = equity_data.get('capital_surplus', 0)
            retained_earnings = equity_data.get('retained_earnings', 0)
            
            retention_ratio = ((capital_surplus + retained_earnings) / capital) * 100
            
            logger.debug(f"Retention ratio: {retention_ratio:.2f}%")
            return round(retention_ratio, 2)
            
        except Exception as e:
            logger.error(f"Retention ratio calculation error: {str(e)}")
            return 0.0
    
    
    @staticmethod
    def calculate_roe_average_3y(roe_data):
        """
        ROE 3년 평균 계산
        
        Args:
            roe_data (list): ROE 데이터 [최신, 1년전, 2년전]
        
        Returns:
            float: ROE 3년 평균 (%)
        """
        try:
            if not roe_data or len(roe_data) < 3:
                return 0.0
            
            # None 값 제거
            valid_roe = [x for x in roe_data[:3] if x is not None]
            
            if len(valid_roe) == 0:
                return 0.0
            
            avg_roe = sum(valid_roe) / len(valid_roe)
            
            logger.debug(f"ROE 3Y avg: {avg_roe:.2f}%")
            return round(avg_roe, 2)
            
        except Exception as e:
            logger.error(f"ROE average calculation error: {str(e)}")
            return 0.0
    
    
    @staticmethod
    def check_consecutive_losses(net_income_data):
        """
        3년 연속 적자 여부 확인
        
        Args:
            net_income_data (list): 당기순이익 [최신, 1년전, 2년전]
        
        Returns:
            bool: True면 3년 연속 적자
        """
        try:
            if not net_income_data or len(net_income_data) < 3:
                return False
            
            # 3년치 데이터 모두 음수인지 확인
            recent_3y = net_income_data[:3]
            consecutive_loss = all(x < 0 for x in recent_3y if x is not None)
            
            if consecutive_loss:
                logger.debug("3년 연속 적자 확인")
            
            return consecutive_loss
            
        except Exception as e:
            logger.error(f"Consecutive loss check error: {str(e)}")
            return False
    
    
    @staticmethod
    def calculate_pcr(market_cap, operating_cashflow):
        """
        PCR (Price to Cash Flow Ratio) 계산
        PCR = 시가총액 / 영업현금흐름
        
        Args:
            market_cap (float): 시가총액
            operating_cashflow (float): 영업현금흐름
        
        Returns:
            float: PCR
        """
        try:
            if operating_cashflow <= 0:
                return 999.99  # 음수이거나 0이면 매우 큰 값 반환
            
            pcr = market_cap / operating_cashflow
            return round(pcr, 2)
            
        except Exception as e:
            logger.error(f"PCR calculation error: {str(e)}")
            return 999.99
    
    
    @staticmethod
    def calculate_psr(market_cap, revenue):
        """
        PSR (Price to Sales Ratio) 계산
        PSR = 시가총액 / 매출액
        
        Args:
            market_cap (float): 시가총액
            revenue (float): 매출액
        
        Returns:
            float: PSR
        """
        try:
            if revenue <= 0:
                return 999.99
            
            psr = market_cap / revenue
            return round(psr, 2)
            
        except Exception as e:
            logger.error(f"PSR calculation error: {str(e)}")
            return 999.99