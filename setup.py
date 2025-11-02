# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin Setup
FlaskFarm 플러그인 설정
"""

# 먼저 setting 딕셔너리 정의
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
                'uri': 'base/setting',
                'name': '설정',
            },
            {
                'uri': 'screening',
                'name': '스크리닝',
                'list': [
                    {'uri': 'screening/strategies', 'name': '전략 선택'},
                    {'uri': 'screening/manual', 'name': '수동 실행'},
                    {'uri': 'screening/list', 'name': '결과 조회'},
                    {'uri': 'screening/history', 'name': '실행 이력'},
                    {'uri': 'screening/statistics', 'name': '통계'},
                ]
            },
            {
                'uri': 'log',
                'name': '로그'
            }
        ]
    },
    'setting_menu': None,
    'default_route': 'normal',
}

# plugin 모듈 임포트
from plugin import *

# P 인스턴스 생성
P = create_plugin_instance(setting)

# 모듈 임포트 및 등록
try:
    from .mod_base import ModuleBase
    from .mod_screening import ModuleScreening
    
    P.set_module_list([ModuleBase, ModuleScreening])
    
except Exception as e:
    P.logger.error(f'Exception:{str(e)}')
    P.logger.error(traceback.format_exc())
