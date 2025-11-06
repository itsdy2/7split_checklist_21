# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Backtesting Module
백테스팅 및 성능 검증 모듈
"""
import traceback
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from .setup import P, F
from framework import db
from .model import StockScreeningResult
from .logic_collector import DataCollector
from .strategies import get_strategy
from .logic_calculator import Calculator

logger = P.logger


class BacktestingEngine:
    """백테스팅 엔진 클래스"""
    
    def __init__(self, dart_api_key=None):
        """
        Args:
            dart_api_key (str): DART API 키
        """
        self.collector = DataCollector(dart_api_key=dart_api_key) if dart_api_key else None
        self.calculator = Calculator()
        
    def run_backtest(self, strategy_id, start_date, end_date, initial_capital=100000000, rebalance_interval='monthly'):
        """
        백테스트 실행
        
        Args:
            strategy_id (str): 전략 ID
            start_date (str): 시작 날짜 (YYYY-MM-DD)
            end_date (str): 종료 날짜 (YYYY-MM-DD)
            initial_capital (int): 초기 자본
            rebalance_interval (str): 리밸런싱 주기 ('daily', 'weekly', 'monthly', 'quarterly')
        
        Returns:
            dict: 백테스트 결과
        """
        logger.info(f"Starting backtest: strategy={strategy_id}, period={start_date} to {end_date}")
        
        try:
            # 전략 로드
            strategy = get_strategy(strategy_id)
            if not strategy:
                return {'success': False, 'error': f'전략이 존재하지 않습니다: {strategy_id}'}
            
            logger.info(f"Loaded strategy: {strategy.strategy_name}")
            
            # 백테스트 기간 설정
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # 백테스트 결과 초기화
            results = {
                'strategy_id': strategy_id,
                'strategy_name': strategy.strategy_name,
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': initial_capital,
                'rebalance_interval': rebalance_interval,
                'portfolio_values': [],
                'buy_signals': [],
                'sell_signals': [],
                'performance_metrics': {},
                'trades': []
            }
            
            # 백테스트 실행 - 단순화된 버전
            # 실제 구현에서는 과거 시점별 데이터를 가져와야 하지만, 
            # pykrx는 실시간 데이터만 제공하므로 시뮬레이션 방식으로 구현
            portfolio_value = initial_capital
            cash = initial_capital  # 현금 보유액
            current_holdings = {}  # 현재 보유 주식 {'code': {'quantity': int, 'avg_price': float, 'name': str}}
            
            # 실제 백테스트처럼 과거 데이터를 시뮬레이션하기 위해
            # 현재 시점의 종목들로 시작하고 수익률을 시뮬레이션
            logger.info("Starting backtest simulation...")
            
            # 거래일 기준으로 시뮬레이션 (간단화 버전)
            current_date = start_dt
            day_count = 0  # 거래일 카운터
            
            # 임시로 252거래일(1년) 단위로 리밸런싱 시뮬레이션
            rebalance_points = []
            temp_date = start_dt
            while temp_date <= end_dt:
                rebalance_points.append(temp_date.strftime('%Y-%m-%d'))
                # 다음 리밸런싱 날짜 계산 - 매월 첫 거래일로 가정
                if rebalance_interval == 'monthly':
                    if temp_date.month == 12:
                        temp_date = temp_date.replace(year=temp_date.year + 1, month=1)
                    else:
                        temp_date = temp_date.replace(month=temp_date.month + 1)
                elif rebalance_interval == 'weekly':
                    temp_date += timedelta(days=7)
                elif rebalance_interval == 'daily':
                    temp_date += timedelta(days=1)
                elif rebalance_interval == 'quarterly':
                    # 분기별 (3개월마다)
                    for _ in range(3):
                        if temp_date.month == 12:
                            temp_date = temp_date.replace(year=temp_date.year + 1, month=1)
                        else:
                            temp_date = temp_date.replace(month=temp_date.month + 1)
                
                # 범위를 벗어나면 종료
                if temp_date > end_dt:
                    break
            
            # 리밸런싱 포인트별 시뮬레이션
            for rebalance_date in rebalance_points:
                # 현재 리밸런싱 날짜로 설정
                current_date_str = rebalance_date
                
                # 현재 시점의 종목 데이터 가져오기 (실제 백테스트에서는 과거 데이터를 가져와야 하지만 
                # pykrx 제약으로 현재 데이터 사용)
                tickers = self.collector.get_all_tickers() if self.collector else []
                
                # 전략 필터 적용 - 현재 시점 기준으로만 적용 (제한된 백테스트 방식)
                passed_stocks = []
                for i, ticker in enumerate(tickers[:30]):  # 상위 30개만 사용하여 성능 향상
                    if len(passed_stocks) >= 10:  # 최대 10개로 제한
                        break
                        
                    try:
                        code = ticker['code']
                        name = ticker['name']
                        
                        # 현재 시점의 데이터 수집
                        market_data = self.collector.get_market_data(code, strategy.required_data) if self.collector else {}
                        financial_data = self.collector.get_financial_data(code, strategy.required_data) if self.collector else {}
                        disclosure_info = self.collector.get_disclosure_info(code, strategy.required_data) if self.collector else {}
                        major_shareholder = self.collector.get_major_shareholder(code, strategy.required_data) if self.collector else 0
                        
                        stock_data = {
                            'code': code,
                            'name': name,
                            'market': ticker.get('market', ''),
                            'status': ticker.get('status', ''),
                            'market_cap': market_data.get('market_cap', 0),
                            'trading_value': market_data.get('trading_value', 0),
                            'per': market_data.get('per'),
                            'pbr': market_data.get('pbr'),
                            'div_yield': market_data.get('div_yield'),
                            # Financial data
                            'debt_ratio': financial_data.get('debt_ratio'),
                            'current_ratio': financial_data.get('current_ratio'),
                            'roe_avg_3y': self.calculator.calculate_roe_average_3y(financial_data.get('roe', [])),
                            'net_income_3y': financial_data.get('net_income', []),
                            'fscore': self.calculator.calculate_fscore(financial_data),
                            'has_cb_bw': disclosure_info.get('has_cb_bw', False),
                            'has_paid_increase': disclosure_info.get('has_paid_increase', False),
                            'major_shareholder_ratio': major_shareholder,
                            'dividend_history': financial_data.get('dividend_history', []),
                            'dividend_payout': financial_data.get('dividend_payout')
                        }
                        
                        # 전략 적용
                        passed, detail = strategy.apply_filters(stock_data)
                        if passed:
                            # 시뮬레이션을 위해 현재가격 사용 (백테스트에서는 실제 과거 가격이 필요)
                            current_price = market_data.get('close_price', market_data.get('market_cap', 10000) / 1000000) or 10000
                            passed_stocks.append({
                                'code': code,
                                'name': name,
                                'market': ticker.get('market', ''),
                                'current_price': current_price if current_price > 0 else 10000
                            })
                            
                    except Exception as e:
                        logger.debug(f"Error processing {ticker.get('code', 'N/A')} in backtest: {e}")
                        continue
                        
                # 현재 보유 주식 평가 손익 반영
                for stock_code, holding in current_holdings.items():
                    # 이 부분은 실제 백테스트에서는 해당 날짜의 실제 가격으로 평가해야 함
                    # 현재는 간단화를 위해 시뮬레이션 수익률 적용
                    simulated_return = np.random.normal(0.0005, 0.02)  # 평균 0.05%, 표준편차 2%의 일간 수익률
                    new_price = holding['avg_price'] * (1 + simulated_return)
                    holding['current_price'] = new_price
                
                # 포트폴리오 가치 계산 (보유 주식 평가액 + 현금)
                holdings_value = sum(holding['quantity'] * holding.get('current_price', holding['avg_price']) 
                                   for holding in current_holdings.values())
                total_value = cash + holdings_value
                
                # 리밸런싱
                if passed_stocks:
                    # 동일 비중 분배
                    weight = 1.0 / len(passed_stocks)
                    target_allocation = int(total_value * weight)
                    
                    # 기존 보유 종목 매도 (만기 또는 리밸런싱)
                    stocks_to_sell = []
                    for stock_code in list(current_holdings.keys()):
                        should_hold = any(s['code'] == stock_code for s in passed_stocks)
                        if not should_hold:
                            stocks_to_sell.append(stock_code)
                    
                    # 매도 처리
                    for stock_code in stocks_to_sell:
                        holding = current_holdings.pop(stock_code)
                        sell_value = holding['quantity'] * holding.get('current_price', holding['avg_price'])
                        cash += sell_value
                        
                        results['sell_signals'].append({
                            'date': current_date_str,
                            'code': stock_code,
                            'name': holding['name'],
                            'action': 'SELL',
                            'quantity': holding['quantity'],
                            'price': holding.get('current_price', holding['avg_price']),
                            'amount': sell_value
                        })
                    
                    # 신규 종목 매수
                    for stock in passed_stocks:
                        # 이미 보유한 종목은 skip
                        if stock['code'] in current_holdings:
                            continue
                            
                        # 자금이 충분한 경우만 매수
                        required_amount = min(target_allocation, cash)
                        if required_amount >= stock['current_price']:  # 최소 1주 매수 가능
                            quantity = min(int(required_amount / stock['current_price']), int(cash / stock['current_price']))
                            if quantity > 0:
                                cost = quantity * stock['current_price']
                                if cost <= cash:
                                    current_holdings[stock['code']] = {
                                        'quantity': quantity,
                                        'avg_price': stock['current_price'],
                                        'name': stock['name'],
                                        'current_price': stock['current_price']
                                    }
                                    cash -= cost
                                    
                                    results['buy_signals'].append({
                                        'date': current_date_str,
                                        'code': stock['code'],
                                        'name': stock['name'],
                                        'action': 'BUY',
                                        'quantity': quantity,
                                        'price': stock['current_price'],
                                        'amount': cost
                                    })
                
                # 포트폴리오 가치 기록
                holding_value = sum(holding['quantity'] * holding.get('current_price', holding['avg_price']) 
                                  for holding in current_holdings.values())
                total_value = cash + holding_value
                
                results['portfolio_values'].append({
                    'date': current_date_str,
                    'value': total_value,
                    'cash': cash,
                    'holdings_value': holding_value
                })
                
                # 다음 리밸런싱 날짜로 이동
                day_count += 1
            
            # 백테스트 기간 종료 시 모든 주식 청산 시뮬레이션
            for stock_code, holding in current_holdings.items():
                # 시뮬레이션 수익률 적용
                simulated_return = np.random.normal(0.0005, 0.02)
                final_price = holding['avg_price'] * (1 + simulated_return)
                sell_amount = holding['quantity'] * final_price
                cash += sell_amount
                
                results['sell_signals'].append({
                    'date': end_dt.strftime('%Y-%m-%d'),
                    'code': stock_code,
                    'name': holding['name'],
                    'action': 'SELL',
                    'quantity': holding['quantity'],
                    'price': final_price,
                    'amount': sell_amount
                })
            
            # 성과 지표 계산
            results['performance_metrics'] = self._calculate_performance_metrics(
                results['portfolio_values'], start_date, end_date
            )
            
            logger.info(f"Backtest completed. Final portfolio value: {cash + holding_value:,.0f}")
            
            return {'success': True, 'results': results}
            
        except Exception as e:
            logger.error(f"Backtest error: {str(e)}")
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def _calculate_performance_metrics(self, portfolio_values, start_date, end_date):
        """
        성과 지표 계산
        
        Args:
            portfolio_values (list): 포트폴리오 가치 리스트
            start_date (str): 시작 날짜
            end_date (str): 종료 날짜
        
        Returns:
            dict: 성과 지표
        """
        if len(portfolio_values) < 2:
            return {}
        
        initial_value = portfolio_values[0]['value']
        final_value = portfolio_values[-1]['value']
        
        total_return = (final_value - initial_value) / initial_value * 100
        num_years = (datetime.strptime(end_date, '%Y-%m-%d') - 
                     datetime.strptime(start_date, '%Y-%m-%d')).days / 365.25
        
        if num_years > 0:
            cagr = (final_value / initial_value) ** (1/num_years) - 1
            cagr *= 100  # percentage
        else:
            cagr = 0
        
        # Calculate daily returns for volatility
        daily_returns = []
        for i in range(1, len(portfolio_values)):
            prev_value = portfolio_values[i-1]['value']
            curr_value = portfolio_values[i]['value']
            if prev_value != 0:
                daily_return = (curr_value - prev_value) / prev_value
                daily_returns.append(daily_return)
        
        if daily_returns:
            daily_volatility = np.std(daily_returns) * 100
            annual_volatility = daily_volatility * np.sqrt(252)  # 252 trading days per year
        else:
            daily_volatility = 0
            annual_volatility = 0
        
        # Simple sharpe ratio (assuming 0% risk-free rate)
        if annual_volatility != 0:
            sharpe_ratio = cagr / annual_volatility if annual_volatility > 0 else 0
        else:
            sharpe_ratio = 0
        
        return {
            'total_return': round(total_return, 2),
            'cagr': round(cagr, 2),
            'annual_volatility': round(annual_volatility, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': 0,  # This would require more complex calculation
            'initial_value': initial_value,
            'final_value': final_value,
            'num_years': round(num_years, 2)
        }


class BacktestingHistory(db.Model):
    """백테스팅 이력 모델"""
    P = P
    __tablename__ = f'{P.package_name}_backtesting_history'
    __bind_key__ = P.package_name

    id = db.Column(db.Integer, primary_key=True)
    strategy_id = db.Column(db.String(50), nullable=False)
    strategy_name = db.Column(db.String(100))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    initial_capital = db.Column(db.Integer)
    final_value = db.Column(db.Float)
    total_return = db.Column(db.Float)
    cagr = db.Column(db.Float)
    sharpe_ratio = db.Column(db.Float)
    status = db.Column(db.String(20), default='completed')
    created_at = db.Column(db.DateTime, default=datetime.now)
    backtest_data = db.Column(db.Text)  # JSON으로 저장

    def __repr__(self):
        return f'<BacktestingHistory {self.strategy_id} {self.start_date} to {self.end_date}>'