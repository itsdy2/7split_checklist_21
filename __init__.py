# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin
패키지 초기화 및 의존성 설치
"""
import os

# 필수 패키지 자동 설치
required_packages = [
    'pykrx',
    'finance-datareader',
    'opendart',
    'lxml'
]

for package in required_packages:
    try:
        __import__(package.replace('-', '_'))
    except ImportError:
        os.system(f"pip install {package}")