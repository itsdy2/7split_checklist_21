# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin
플러그인 초기화 및 메인 진입점
"""
from flask import Blueprint, request, render_template, jsonify, redirect, url_for
from .setup import *

# 플러그인 인스턴스 (setup.py에서 생성됨)
# P는 setup.py에서 이미 생성되어 있음

def plugin_load():
    """플러그인 로드 시 호출"""
    P.logger.info('7split_checklist_21 plugin loaded')
    
    # DB 초기화
    from .logic import Logic
    Logic.db_init()
    
    # 스케줄러 시작
    if P.ModelSetting.get_bool('basic_auto_start'):
        Logic.scheduler_start()

def plugin_unload():
    """플러그인 언로드 시 호출"""
    P.logger.info('7split_checklist_21 plugin unloaded')
    
    # 스케줄러 중지
    from .logic import Logic
    Logic.scheduler_stop()