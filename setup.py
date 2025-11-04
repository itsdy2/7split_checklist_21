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
            { 'uri': 'base/setting', 'name': '설정' },
            { 'uri': 'base/help', 'name': '도움말' },
            { 'uri': 'screening/strategies', 'name': '전략선택' },
            { 'uri': 'screening/scaffold', 'name': '전략 스캐폴딩' },
            { 'uri': 'screening/manual', 'name': '수동실행' },
            { 'uri': 'screening/list', 'name': '결과조회' },
            { 'uri': 'screening/history', 'name': '실행이력' },
            { 'uri': 'screening/statistics', 'name': '통계' },
            { 'uri': 'log', 'name': '로그' }
        ]
        # ^ ^ ^ 수정: 메뉴 리스트 구조 변경 ^ ^ ^
    },
    'setting_menu': None,
    'default_route': 'normal',
}

P = create_plugin_instance(setting)

try:
    from .mod_base import ModuleBase
    from .mod_screening import ModuleScreening
    
    P.set_module_list([ModuleBase, ModuleScreening])
    
except Exception as e:
    P.logger.error(f'Exception:{str(e)}')
    P.logger.error(traceback.format_exc())
