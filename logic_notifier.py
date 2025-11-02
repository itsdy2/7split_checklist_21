# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Notifier
Discord Webhook을 통한 알림 전송
"""
import json
import requests
from datetime import datetime
from framework.logger import get_logger

logger = get_logger(__name__)


class Notifier:
    """알림 전송 클래스"""
    
    def __init__(self, webhook_url=None):
        """
        Args:
            webhook_url (str): Discord Webhook URL
        """
        self.webhook_url = webhook_url
    
    
    def send_screening_result(self, passed_stocks, total_stocks, execution_time, strategy_name="기본 전략"):
        """
        스크리닝 결과를 Discord로 전송
        
        Args:
            passed_stocks (list): 통과한 종목 리스트
            total_stocks (int): 전체 종목 수
            execution_time (float): 실행 시간 (초)
            strategy_name (str): 사용된 전략 이름
        
        Returns:
            bool: 전송 성공 여부
        """
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured")
            return False
        
        try:
            # Embed 메시지 생성
            embeds = []
            
            # 1. 요약 Embed
            summary_embed = {
                "title": "🎯 세븐스플릿 스크리닝 결과",
                "description": f"**{len(passed_stocks)}개 종목**이 21가지 조건을 모두 통과했습니다.",
                "color": 3066993,  # 초록색
                "fields": [
                    {
                        "name": "📊 전체 종목 수",
                        "value": f"{total_stocks:,}개",
                        "inline": True
                    },
                    {
                        "name": "✅ 통과 종목 수",
                        "value": f"{len(passed_stocks):,}개",
                        "inline": True
                    },
                    {
                        "name": "⏱️ 실행 시간",
                        "value": f"{execution_time:.1f}초",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                },
                "timestamp": datetime.now().isoformat()
            }
            embeds.append(summary_embed)
            
            # 2. 통과 종목 상세 (최대 10개까지만)
            if len(passed_stocks) > 0:
                stock_fields = []
                
                for i, stock in enumerate(passed_stocks[:10]):
                    # 종목 정보 필드
                    field_value = (
                        f"**시가총액**: {stock.get('market_cap', 0) // 100000000:,}억원\n"
                        f"**PER**: {stock.get('per', 0):.2f} | **PBR**: {stock.get('pbr', 0):.2f}\n"
                        f"**ROE**: {stock.get('roe_avg_3y', 0):.2f}% | **F-Score**: {stock.get('fscore', 0)}점\n"
                        f"**배당수익률**: {stock.get('div_yield', 0):.2f}%"
                    )
                    
                    stock_fields.append({
                        "name": f"{i+1}. {stock.get('name', '')} ({stock.get('code', '')})",
                        "value": field_value,
                        "inline": False
                    })
                
                # 종목 상세 Embed
                detail_embed = {
                    "title": "📈 통과 종목 목록",
                    "color": 5814783,  # 파란색
                    "fields": stock_fields
                }
                embeds.append(detail_embed)
                
                # 10개 이상이면 추가 메시지
                if len(passed_stocks) > 10:
                    more_embed = {
                        "description": f"*나머지 {len(passed_stocks) - 10}개 종목은 웹 페이지에서 확인하세요.*",
                        "color": 15844367  # 주황색
                    }
                    embeds.append(more_embed)
            
            # Discord Webhook 전송
            payload = {
                "username": "세븐스플릿 Bot",
                "embeds": embeds
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 204:
                logger.info("Discord notification sent successfully")
                return True
            else:
                logger.error(f"Discord notification failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {str(e)}")
            return False
    
    
    def send_error_notification(self, error_message):
        """
        에러 알림 전송
        
        Args:
            error_message (str): 에러 메시지
        
        Returns:
            bool: 전송 성공 여부
        """
        if not self.webhook_url:
            return False
        
        try:
            embed = {
                "title": "⚠️ 스크리닝 실행 실패",
                "description": f"```{error_message}```",
                "color": 15158332,  # 빨간색
                "footer": {
                    "text": f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
            
            payload = {
                "username": "세븐스플릿 Bot",
                "embeds": [embed]
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 204
            
        except Exception as e:
            logger.error(f"Failed to send error notification: {str(e)}")
            return False
    
    
    def send_start_notification(self, total_stocks):
        """
        스크리닝 시작 알림
        
        Args:
            total_stocks (int): 전체 종목 수
        
        Returns:
            bool: 전송 성공 여부
        """
        if not self.webhook_url:
            return False
        
        try:
            embed = {
                "title": "🚀 스크리닝 시작",
                "description": f"{total_stocks:,}개 종목 분석을 시작합니다.",
                "color": 3447003,  # 파란색
                "footer": {
                    "text": f"시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
            
            payload = {
                "username": "세븐스플릿 Bot",
                "embeds": [embed]
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 204
            
        except Exception as e:
            logger.debug(f"Failed to send start notification: {str(e)}")
            return False
    
    
    @staticmethod
    def format_number(num):
        """
        숫자 포맷팅 (억원 단위)
        
        Args:
            num (int): 숫자
        
        Returns:
            str: 포맷팅된 문자열
        """
        if num >= 100_000_000:
            return f"{num // 100_000_000:,}억"
        else:
            return f"{num:,}"