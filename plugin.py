# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin
세븐스플릿 21가지 체크리스트 기반 종목 스크리닝
"""
from framework.logger import get_logger

logger = get_logger(__name__)

# 플러그인 패키지명
package_name = '7split_checklist_21'

# 플러그인 정보
plugin_info = {
    'version': '1.0.0',
    'name': '세븐스플릿 스크리닝',
    'category': '투자',
    'icon': 'trending_up',
    'developer': 'FlaskFarm Community',
    'description': '세븐스플릿의 21가지 체크리스트를 기반으로 KOSPI/KOSDAQ 종목을 자동 스크리닝하는 플러그인입니다.',
    'home': f'/{package_name}',
    'more': 'https://github.com/itsdy2/7split_checklist_21',
    
    # GitHub 설치 정보
    'zip': 'https://github.com/itsdy2/7split_checklist_21/archive/refs/heads/main.zip',
    'path': '7split_checklist_21-main'
}


def plugin_load():
    """
    플러그인 로드 시 초기화
    - DB 테이블 생성
    - 기본 설정 초기화
    - 스케줄러 등록
    """
    try:
        logger.info(f'{package_name} plugin loading...')
        
        # 프레임워크 초기화
        from framework.init_plugin import framework_init
        framework_init(package_name, __file__)
        
        # DB 초기화
        from .logic import Logic
        Logic.db_init()
        
        # 스케줄러 시작
        Logic.scheduler_start()
        
        logger.info(f'{package_name} plugin loaded successfully')
        
    except Exception as e:
        logger.error(f'Plugin load error: {str(e)}')
        logger.error(f'Exception: {e}')


def plugin_unload():
    """
    플러그인 언로드 시 정리
    - 스케줄러 중지
    """
    try:
        logger.info(f'{package_name} plugin unloading...')
        
        # 스케줄러 중지
        from .logic import Logic
        Logic.scheduler_stop()
        
        logger.info(f'{package_name} plugin unloaded')
        
    except Exception as e:
        logger.error(f'Plugin unload error: {str(e)}')


def plugin_menu():
    """
    플러그인 메뉴 구조 정의
    """
    return {
        'main': [
            ['설정', f'/{package_name}/setting'],
            ['전략 선택', f'/{package_name}/strategies'],
            ['스크리닝 실행', f'/{package_name}/manual'],
            ['결과 조회', f'/{package_name}/list'],
            ['실행 이력', f'/{package_name}/history'],
            ['통계', f'/{package_name}/statistics']
        ],
        'sub': [
            ['로그', f'/{package_name}/log'],
            ['도움말', f'/{package_name}/help']
        ],
        'category': '투자'
    }


# 플러그인 정보 함수 (FlaskFarm 호환)
def get_plugin_info():
    """플러그인 정보 반환"""
    return plugin_info
