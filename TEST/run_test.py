#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
21가지 체크리스트 기능 테스트 실행 스크립트
"""

import os
import sys
from pathlib import Path

def run_test():
    """테스트 실행"""
    print("="*60)
    print("21가지 체크리스트 기능 테스트를 시작합니다.")
    print("="*60)
    
    # 현재 디렉토리 설정
    current_dir = Path(__file__).parent
    
    # 테스트 스크립트 실행
    import subprocess
    try:
        result = subprocess.run([
            sys.executable, 
            str(current_dir / "test_21_checklist.py")
        ], check=True, capture_output=True, text=True, cwd=str(current_dir))
        
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
        print(f"출력: {e.output if hasattr(e, 'output') else 'N/A'}")
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)