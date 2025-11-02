# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin Setup
FlaskFarm 플러그인 설정
"""
# from plugin import *

setting = {
    'filepath': __file__,
    'use_db': True,
    'use_default_setting': True,
    'home_module': None,
    'menu': {
        'uri': __package__,
        'name': '세븐스플릿 스크리닝',
        'list': [
            {
                'uri': 'basic',
                'name': '기본',
                'list': [
                    {'uri': 'setting', 'name': '설정'},
                ]
            },
            {
                'uri': 'screening',
                'name': '스크리닝',
                'list': [
                    {'uri': 'strategies', 'name': '전략 선택'},
                    {'uri': 'manual', 'name': '수동 실행'},
                    {'uri': 'list', 'name': '결과 조회'},
                    {'uri': 'history', 'name': '실행 이력'},
                    {'uri': 'statistics', 'name': '통계'},
                ]
            },
            {
                'uri': 'log',
                'name': '로그'
            }
        ]
    },
    'setting_menu': None,
    'default_route': 'screening'
}

# P = create_plugin_instance(setting)
from .plugin import P 
P.setup(setting)

try:
    from .mod_basic import ModuleBasic
    from .mod_screening import ModuleScreening
    
    P.set_module_list([ModuleBasic, ModuleScreening])
    
except Exception as e:
    P.logger.error(f'Exception:{str(e)}')
    P.logger.error(traceback.format_exc())