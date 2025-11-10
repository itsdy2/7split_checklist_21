#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
21가지 체크리스트 기능 테스트 실행 스크립트
"""

import os
import sys
import subprocess
from pathlib import Path

def run_test():
    """테스트 실행"""
    print("="*60)
    print("21가지 체크리스트 기능 테스트를 시작합니다.")
    print("="*60)
    
    # current_dir = D:\7split\7split_checklist_21\TEST
    current_dir = Path(__file__).parent
    
    # plugin_dir = D:\7split\7split_checklist_21
    plugin_dir = current_dir.parent
    
    # <<< 수정된 부분: PYTHONPATH를 패키지의 부모로 설정 >>>
    # project_root = D:\7split
    project_root = plugin_dir.parent
    
    # 1. 현재 환경변수를 복사합니다.
    env = os.environ.copy()
    
    # 2. PYTHONPATH에 *프로젝트 루트*를 추가합니다.
    #    이렇게 하면 '7split_checklist_21'을 패키지로 인식합니다.
    env['PYTHONPATH'] = str(project_root)
    # <<< 수정 완료 >>>

    # 테스트 스크립트 실행
    try:
        result = subprocess.run([
            sys.executable, 
            "-m",  # 모듈로 실행
            
            # <<< 수정: '7split_checklist_21'을 포함한 전체 모듈 경로
            "7split_checklist_21.TEST.test_21_checklist"
        ], 
        check=True, 
        capture_output=True, 
        text=True, 
        
        # <<< 수정: 실행 위치를 프로젝트 루트로 변경
        cwd=str(project_root), 
        env=env                # 수정된 환경변수(env)를 전달
        )
        
        print("테스트 실행 로그:")
        print(result.stdout)
        
        if result.stderr:
            print("에러 발생:")
            print(result.stderr)
        
        print("="*60)
        print("테스트 실행 완료!")
        print(f"결과는 {current_dir} 폴더의 CSV 파일에 저장되었습니다.")
        print("="*60)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"테스트 실행 중 오류 발생: {e}")
        print("\n--- STDOUT (표준 출력) ---")
        print(e.stdout)
        print("\n--- STDERR (오류 원인) ---")
        print(e.stderr)
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)