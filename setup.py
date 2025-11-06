# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin Setup
FlaskFarm 플러그인 설정
"""
import traceback
from plugin import *

setting = {
    'filepath': __file__,
    'use_db': True,
    'use_default_setting': True,
    'home_module': 'base',  # <-- 수정: 'base' (설정 페이지)를 홈 모듈로 지정
    'menu': {
        'uri': __package__,
        'name': '세븐스플릿',
        # V V V 수정: 메뉴 리스트 구조 변경 V V V
        'list': [
            {
                'uri': 'base',
                'name': '설정',
                'list': [
                    { 'uri': 'setting', 'name': '환경설정' },
                    { 'uri': 'scheduler', 'name': '스케줄' },
                    { 'uri': 'help', 'name': '도움말' },
                    { 'uri': 'developer', 'name': '개발 정의서' }
                ]
            },
            {
                'uri': 'screening',
                'name': '스크리닝',
                'list': [
                    { 'uri': 'strategies', 'name': '전략선택' },
                    { 'uri': 'compare', 'name': '비교 보기' },
                    { 'uri': 'scaffold', 'name': '전략 스캐폴딩' },
                    { 'uri': 'import', 'name': '전략 가져오기' },
                    { 'uri': 'manual', 'name': '수동실행' },
                    { 'uri': 'list', 'name': '결과조회' },
                    { 'uri': 'history', 'name': '실행이력' },
                    { 'uri': 'statistics', 'name': '통계' }
                ]
            },
            { 'uri': 'log', 'name': '로그' }
        ]
        # ^ ^ ^ 수정: 메뉴 리스트 구조 변경 ^ ^ ^
    },
    'setting_menu': None,
    'default_route': 'normal',
}

P = create_plugin_instance(setting)

try:
    # Define PluginModelSetting right after creating P to make it available immediately
    PluginModelSetting = P.ModelSetting
    
    from .mod_base import ModuleBase
    from .mod_screening import ModuleScreening
    
    P.set_module_list([ModuleBase, ModuleScreening])
    
except Exception as e:
    P.logger.error(f'Exception:{str(e)}')
    P.logger.error(traceback.format_exc())
