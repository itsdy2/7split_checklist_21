# FlaskFarm 플러그인 개발 가이드

## 목차
1. [플러그인 구조 이해](#플러그인-구조-이해)
2. [프로젝트 구조](#프로젝트-구조)
3. [핵심 파일 설명](#핵심-파일-설명)
4. [모듈 개발](#모듈-개발)
5. [UI 개발](#ui-개발)
6. [Celery 사용](#celery-사용)
7. [디버깅 및 문제 해결](#디버깅-및-문제-해결)

---

## 플러그인 구조 이해

### 기본 개념
```
일반 Python 코드 + 모듈 베이스 코드 + UI HTML 파일 = 모듈
모듈 + 모듈 = 플러그인
플러그인 + ... + 기본플러그인(system, command, mod) + Framework = FlaskFarm
```

### 권장 개발 순서
1. 개별 기능(모듈) 먼저 개발
2. 여러 모듈을 조합하여 플러그인 구성
3. 테스트 및 배포

---

## 프로젝트 구조

### 기본 디렉토리 구조
```
plugin_name/
├── __init__.py              # 패키지 초기화
├── info.yaml                # 플러그인 메타데이터
├── setup.py                 # 플러그인 설정 및 메뉴 구조
├── mod_base.py              # 기본 모듈 (설정 등)
├── mod_feature.py           # 기능 모듈
├── logic.py                 # 비즈니스 로직
├── model.py                 # 데이터베이스 모델
├── requirements.txt         # 의존성 패키지
├── templates/              # HTML 템플릿
│   ├── plugin_name_base_setting.html
│   └── plugin_name_feature_list.html
└── static/                 # 정적 파일 (선택)
    ├── css/
    └── js/
```

---

## 핵심 파일 설명

### 1. info.yaml
```yaml
title: "플러그인 이름"
version: "1.0.0"
package_name: "plugin_name"
developer: "개발자명"
description: "플러그인 설명"
home: "https://github.com/username/plugin_name"
more: "https://raw.githubusercontent.com/username/plugin_name/main/README.md"
```

### 2. setup.py
```python
# -*- coding: utf-8 -*-
import traceback
from plugin import *

setting = {
    'filepath': __file__,
    'use_db': True,
    'use_default_setting': True,
    'home_module': None,
    'menu': {
        'uri': __package__,
        'name': '플러그인명',
        'list': [
            {'uri': 'base/setting', 'name': '설정'},
            {'uri': 'feature/list', 'name': '목록'},
            {'uri': 'log', 'name': '로그'}
        ]
    },
    'setting_menu': None,
    'default_route': 'normal',
}

P = create_plugin_instance(setting)

try:
    from .mod_base import ModuleBase
    from .mod_feature import ModuleFeature
    
    P.set_module_list([ModuleBase, ModuleFeature])
    
except Exception as e:
    P.logger.error(f'Exception:{str(e)}')
    P.logger.error(traceback.format_exc())
```

### 3. 모듈 클래스 (__init__.py에서 참조)

#### 구 방식 (SJVA 스타일)
```python
mod_info = {
    'mod_class': LogicClientNoti,
    'sub': ['client_noti', '클리앙 알림'],
    'sub2': [['setting', '설정']],
    'version': '1.0.0',
}
```

#### 신 방식 (FlaskFarm 표준)
```python
# setup.py에서 직접 정의
setting = {
    'menu': {
        'list': [
            {'uri': 'module/submenu', 'name': '메뉴명'}
        ]
    }
}
```

---

## 모듈 개발

### ModuleBase 클래스 상속
```python
from plugin import PluginModuleBase

class ModuleBase(PluginModuleBase):
    def __init__(self, P):
        super(ModuleBase, self).__init__(P, name='base', first_menu=None)
        self.db_default = {
            'api_key': '',
            'auto_start': 'False',
            'interval': '30'
        }
        P.logger.info("ModuleBase initialized")
```

### 필수 메서드

#### 1. process_menu(self, sub, req)
화면 메뉴 요청 처리
```python
def process_menu(self, sub, req):
    P.logger.info(f"process_menu called: sub={sub}")
    arg = P.ModelSetting.to_dict()
    
    if sub == 'setting':
        # 설정 페이지 렌더링
        return render_template(
            f'{P.package_name}_{self.name}_{sub}.html',
            arg=arg
        )
    
    return "Not Implemented"
```

#### 2. process_command(self, command, arg1, arg2, arg3, req)
사용자 액션 처리 (버튼 클릭 등)
```python
def process_command(self, command, arg1, arg2, arg3, req):
    P.logger.info(f"process_command: {command}")
    
    try:
        if command == 'save_settings':
            form_data = req.form.to_dict()
            # 설정 저장 로직
            return jsonify({'ret': 'success', 'msg': '저장 완료'})
        
        elif command == 'start_task':
            # 작업 시작
            return jsonify({'ret': 'success', 'msg': '작업 시작'})
            
    except Exception as e:
        P.logger.error(f"Command error: {str(e)}")
        return jsonify({'ret': 'error', 'msg': str(e)})
```

#### 3. process_api(self, sub, req)
API 엔드포인트 처리 (API 키 포함)
```python
def process_api(self, sub, req):
    P.logger.info(f"process_api: sub={sub}")
    
    try:
        if sub == 'data':
            # JSON 데이터 반환
            return jsonify({'data': 'example'})
        
        elif sub == 'download':
            # 파일 다운로드
            return send_file(file_path)
            
    except Exception as e:
        P.logger.error(f"API error: {str(e)}")
        return jsonify({'error': str(e)})
```

#### 4. scheduler_function(self)
스케줄링 실행 함수
```python
def scheduler_function(self):
    """1회 실행 버튼 또는 스케줄러에 의해 호출"""
    P.logger.info("Scheduler function called")
    
    # Celery 사용 여부 확인
    if F.config['use_celery']:
        result = self.task.apply_async()
        result.get()
    else:
        self.task()

@staticmethod
@celery.task
def task():
    """실제 작업 수행"""
    # 작업 로직
    pass
```

### 선택적 메서드

```python
def reset_db(self):
    """DB 초기화 버튼 클릭 시"""
    # DB 초기화 로직
    return True

def plugin_load(self):
    """플러그인 로드 시 실행"""
    pass

def plugin_unload(self):
    """플러그인 언로드 시 실행"""
    pass

def setting_save_after(self):
    """설정 저장 후 실행"""
    pass

def migration(self):
    """버전 업데이트 시 마이그레이션"""
    pass
```

---

## UI 개발

### 템플릿 파일 명명 규칙
```
{package_name}_{module_name}_{sub}.html

예시:
- 7split_checklist_21_base_setting.html
- 7split_checklist_21_screening_list.html
```

### 기본 템플릿 구조
```html
{% extends "base.html" %}
{% block content %}

<div class="container-fluid">
    <h3>페이지 제목</h3>
    
    <form id="setting_form">
        <!-- 폼 필드 -->
        <div class="form-group">
            <label>API Key</label>
            <input type="text" class="form-control" name="api_key" value="{{ arg.api_key }}">
        </div>
        
        <button type="submit" class="btn btn-primary">저장</button>
    </form>
</div>

<script>
$(document).ready(function() {
    $('#setting_form').on('submit', function(e) {
        e.preventDefault();
        
        $.ajax({
            url: '/plugin_name/base/command/save_settings',
            type: 'POST',
            data: $(this).serialize(),
            success: function(response) {
                if (response.ret === 'success') {
                    notify(response.msg, 'success');
                } else {
                    notify(response.msg, 'warning');
                }
            }
        });
    });
});
</script>

{% endblock %}
```

### Macros 사용 (FlaskFarm 스타일)
```html
{{ macros.m_button_group([
    ['save_btn', '저장'],
    ['execute_btn', '실행'],
    ['reset_btn', '초기화']
])}}

{{ macros.setting_input_text(
    'api_key',
    'API 키',
    value=arg.api_key,
    desc=['API 키를 입력하세요']
)}}

{{ macros.setting_checkbox(
    'auto_start',
    '자동 시작',
    value=arg.auto_start,
    desc='플러그인 로드 시 자동으로 시작합니다.'
)}}

{{ macros.setting_scheduler_interval(
    'interval',
    '실행 주기',
    value=arg.interval,
    desc='분 단위 또는 Cron 표현식'
)}}
```

### AJAX 호출 패턴

#### Command 방식 (권장)
```javascript
// URL 패턴: /plugin_name/module/command/command_name/arg1/arg2/arg3
$.ajax({
    url: '/7split_checklist_21/screening/command/start/seven_split_21',
    type: 'POST',
    data: {key: 'value'},
    success: function(response) {
        if (response.ret === 'success') {
            notify(response.msg, 'success');
        }
    }
});
```

#### API 방식
```javascript
// URL 패턴: /plugin_name/api/module/sub?apikey=xxx
$.ajax({
    url: '/plugin_name/api/feature/download_csv',
    type: 'GET',
    success: function(data) {
        // 처리
    }
});
```

### Global 버튼 (자동 처리)
```html
<!-- 이 버튼들은 base.html에서 자동으로 처리됨 -->
{{ macros.m_button_group([
    ['global_setting_save_btn', '설정 저장'],
    ['global_one_execute_sub_btn', '1회 실행'],
    ['global_reset_db_sub_btn', 'DB 초기화']
])}}
```
- `global_setting_save_btn`: 자동으로 폼 데이터 수집 및 저장
- `global_one_execute_sub_btn`: `scheduler_function()` 호출
- `global_reset_db_sub_btn`: `reset_db()` 호출

---

## Celery 사용

### Celery를 사용해야 하는 경우

1. **파일 I/O 작업**: 파일 읽기/쓰기, 복사, 이동 등
2. **네트워크 I/O**: API 호출, 웹 스크래핑 (시간이 오래 걸리는 경우)
3. **CPU 집약적 작업**: 대량 데이터 처리

### 기본 사용법

```python
from framework import celery

class Logic:
    @staticmethod
    def scheduler_function():
        # Celery 사용 여부 확인
        if F.config['use_celery']:
            result = Logic.task.apply_async()
            result.get()  # 결과 대기
        else:
            Logic.task()  # 직접 실행
    
    @staticmethod
    @celery.task
    def task():
        """실제 작업"""
        # 작업 로직
        pass
```

### UI 업데이트가 필요한 Celery 작업

```python
class Logic:
    @staticmethod
    def start_work(entity):
        if F.config['use_celery']:
            result = Logic.work_task.apply_async((entity,))
            # callback으로 중간 상태 받기
            result.get(on_message=Logic.update_callback, propagate=True)
        else:
            Logic.work_task(None, entity)
    
    @staticmethod
    @celery.task(bind=True)
    def work_task(self, entity):
        """작업 수행"""
        for i in range(100):
            # 작업 수행
            entity['progress'] = i
            
            # UI 업데이트 알림
            Logic.update_ui(self, entity)
    
    @staticmethod
    def update_ui(celery_inst, entity):
        """UI 업데이트 전송"""
        if F.config['use_celery']:
            # Celery를 통해 메인 프로세스에 알림
            celery_inst.update_state(
                state='PROGRESS',
                meta={'data': entity}
            )
        else:
            # 직접 UI 업데이트
            Logic.send_to_ui(entity)
    
    @staticmethod
    def update_callback(arg):
        """메인 프로세스의 callback"""
        if arg['status'] == 'PROGRESS':
            result = arg['result']
            Logic.send_to_ui(result['data'])
    
    @staticmethod
    def send_to_ui(entity):
        """SocketIO로 UI에 전송"""
        socketio.emit('progress_update', entity, namespace='/framework', broadcast=True)
```

### Framework의 Celery 유틸리티

```python
import framework.common.celery as celery_shutil

# 파일 작업
celery_shutil.move(source_path, target_path)
celery_shutil.copytree(source_path, target_path)
celery_shutil.copy(source_path, target_path)
celery_shutil.rmtree(source_path)
```

### Celery 사용 시 주의사항

#### ❌ 잘못된 예: 전역 변수 사용
```python
class Logic:
    sleep_time = 1  # 메인/워커 프로세스 간 공유 안 됨
    
    @staticmethod
    @celery.task
    def task():
        Logic.sleep_time += 1  # 워커에서만 증가, 메인은 모름
        time.sleep(Logic.sleep_time)
```

#### ✅ 올바른 예: DB 사용
```python
class Logic:
    @staticmethod
    @celery.task
    def task():
        # DB에서 값 읽기
        sleep_time = ModelSetting.get('sleep_time')
        time.sleep(int(sleep_time))
        
        # DB에 값 저장
        ModelSetting.set('sleep_time', str(int(sleep_time) + 1))
```

**핵심**: 메인 프로세스와 Celery 워커는 별도 메모리 공간을 사용하므로, 공유 데이터는 반드시 DB에 저장!

---

## 디버깅 및 문제 해결

### 로깅
```python
# 로깅 레벨
P.logger.debug("디버그 메시지")
P.logger.info("정보 메시지")
P.logger.warning("경고 메시지")
P.logger.error("에러 메시지")

# Traceback 출력
import traceback
try:
    # 코드
    pass
except Exception as e:
    P.logger.error(f"Error: {str(e)}")
    P.logger.error(traceback.format_exc())
```

### 일반적인 문제 해결

#### 1. 페이지가 "plugin_name - module_name" 텍스트만 표시
**원인**: `process_menu()`가 호출되지 않음
```python
# 해결: first_menu 설정 확인
super(ModuleBase, self).__init__(P, name='base', first_menu=None)

# sub가 None인 경우 처리
if not sub or sub == 'base':
    sub = 'setting'
```

#### 2. 템플릿을 찾을 수 없음
**원인**: 템플릿 파일명 불일치
```python
# 올바른 명명: {package_name}_{module_name}_{sub}.html
template_name = f'{P.package_name}_{self.name}_{sub}.html'

# 파일 확인
templates/7split_checklist_21_base_setting.html  # ✅
templates/7split_base_setting.html              # ❌
```

#### 3. AJAX 요청이 실패
**원인**: URL 패턴 불일치
```javascript
// FlaskFarm 표준
url: '/plugin_name/module/command/command_name'  // ✅
url: '/plugin_name/api/module/command_name'      // ❌
```

#### 4. import 오류
**원인**: 상대 경로 import 문제
```python
from .setup import *           # ✅ 같은 패키지
from strategies import xxx     # ✅ 서브패키지
from setup import *            # ❌ 절대 경로
```

#### 5. Celery 작업이 실행되지 않음
**원인**: Celery 워커가 실행되지 않음
```bash
# Celery 워커 시작 확인
celery -A framework.celery worker --loglevel=info

# 또는 no_celery 모드에서 테스트
# setup.py에서
if not F.config['use_celery']:
    Logic.task()  # 직접 실행
```

### 디버깅 팁

1. **로그 레벨 조정**
```python
P.logger.setLevel(logging.DEBUG)
```

2. **SocketIO 이벤트 확인**
```javascript
// 브라우저 콘솔에서
socket.on('event_name', function(data) {
    console.log('Received:', data);
});
```

3. **DB 직접 확인**
```python
# ModelSetting 값 확인
from model import ModelSetting
settings = ModelSetting.get_list()
for s in settings:
    print(f"{s.key}: {s.value}")
```

4. **메뉴 구조 확인**
```python
# setup.py의 setting['menu'] 출력
import json
print(json.dumps(setting['menu'], indent=2, ensure_ascii=False))
```

---

## 배포

### requirements.txt 작성
```txt
# 필수 패키지만 명시
requests>=2.28.0
pandas>=1.5.0

# FlaskFarm 내장 패키지는 제외
# flask
# sqlalchemy
# celery
```

### 플러그인 패키징
```bash
# 1. Git 저장소 생성
git init
git add .
git commit -m "Initial commit"

# 2. GitHub에 푸시
git remote add origin https://github.com/username/plugin_name
git push -u origin main

# 3. FlaskFarm에서 설치
# [시스템] → [플러그인] → GitHub URL 입력
```

### 버전 업데이트
```yaml
# info.yaml 수정
version: "1.0.1"
```

```python
# model.py에 마이그레이션 추가
def migration(self):
    try:
        # 버전 확인
        current_version = ModelSetting.get('db_version')
        
        if current_version == '1':
            # 1 → 2 마이그레이션
            ModelSetting.set('new_setting', 'default_value')
            ModelSetting.set('db_version', '2')
            
    except Exception as e:
        P.logger.error(f"Migration error: {str(e)}")
```

---

## 참고 자료

### 공식 문서
- FlaskFarm: https://github.com/flaskfarm/flaskfarm
- Flask: https://flask.palletsprojects.com/
- Celery: https://docs.celeryproject.org/

### 샘플 플러그인
- https://github.com/byorial/plugin_sample
- https://github.com/flaskfarm (공식 플러그인들)

### 유틸리티 라이브러리
- `tool_base`: 기본 유틸리티 함수
- `tool_expand`: 확장 유틸리티 함수

```python
from tool_base import ToolBaseNotify
from tool_expand import ToolExpandFileProcess

# 텔레그램 알림
ToolBaseNotify.send_telegram_message("메시지")

# 디스코드 알림
ToolBaseNotify.send_discord_message("메시지")
```

---

## 체크리스트

### 플러그인 개발 완료 전 확인사항

- [ ] `info.yaml` 정보 정확히 작성
- [ ] `setup.py` 메뉴 구조 확인
- [ ] 템플릿 파일명 규칙 준수
- [ ] 모든 `process_menu()` 테스트
- [ ] 모든 `process_command()` 테스트
- [ ] DB 모델 정의 및 마이그레이션
- [ ] Celery 사용 시 no_celery 모드 테스트
- [ ] 로깅 적절히 추가
- [ ] 에러 핸들링 구현
- [ ] `requirements.txt` 작성
- [ ] `README.md` 작성
- [ ] 라이선스 파일 추가

---

이 가이드를 따라 FlaskFarm 플러그인을 개발하시면 됩니다. 추가 질문이나 막히는 부분이 있으면 FlaskFarm 커뮤니티에 문의하세요!

sample은 flaskfarm_plugin_sample 폴더를 확인해주세요. 