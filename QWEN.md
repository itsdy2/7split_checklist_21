# FlaskFarm 플러그인 개발 가이드

이 가이드는 FlaskFarm 플랫폼을 위한 커스텀 플러그인을 개발하는 방법을 안내합니다.

## 목차

1. [플러그인 아키텍처](#1-플러그인-아키텍처)
2. [프로젝트 구조](#2-프로젝트-구조)
3. [핵심 파일 상세](#3-핵심-파일-상세)
4. [데이터베이스 - 설정 저장 (ModelSetting)](#4-데이터베이스---설정-저장-modelsetting)
5. [데이터베이스 - 커스텀 테이블 (ModelBase)](#5-데이터베이스---커스텀-테이블-modelbase)
6. [모듈과 페이지 (심화)](#6-모듈과-페이지-심화)
7. [Celery 사용](#7-celery-사용)
8. [디버깅, 배포 및 체크리스트](#8-디버깅-배포-및-체크리스트)

---

## 1. 플러그인 아키텍처

FlaskFarm의 플러그인은 **모듈(Module)**과 선택적으로 **페이지(Page)**로 구성됩니다.

### 구성 요소

- **모듈 (Module)**: `PluginModuleBase`를 상속받는 기능 단위입니다. `setup.py`의 메뉴 구조에서 상위 레벨(depth 1)을 담당합니다.
  - 예: `system` 플러그인의 `setting` 모듈
  
- **페이지 (Page)**: (선택 사항) `PluginPageBase`를 상속받으며, 하나의 모듈에 종속되어 하위 기능을 세분화합니다.
  - 예: `system` 플러그인의 `tool` 모듈 하위 `command` 페이지
  
- **플러그인 (Plugin)**: 이 모듈과 페이지들을 `setup.py`로 묶어 정의한 하나의 패키지입니다.

### 구조도

```
플러그인 (plugin_name)
├── 모듈 (mod_base.py)
│   ├── 페이지 (page_sub1.py) - 선택
│   └── 페이지 (page_sub2.py) - 선택
└── 모듈 (mod_feature.py)
```

---

## 2. 프로젝트 구조

```
plugin_name/
├── __init__.py              # 패키지 초기화 (비어있어도 됨)
├── info.yaml                # 플러그인 메타데이터 (필수)
├── setup.py                 # 플러그인 설정 및 모듈 등록 (필수)
├── mod_base.py              # 'base' 모듈 클래스
├── mod_feature.py           # 'feature' 모듈 클래스
├── page_utils.py            # 'base' 모듈에 속할 'utils' 페이지 클래스 (선택)
├── model.py                 # SQLAlchemy DB 모델 (선택)
├── requirements.txt         # 의존성 패키지 (선택)
└── templates/               # HTML 템플릿 (필수)
    ├── plugin_name_base_setting.html
    └── plugin_name_base_utils.html
```

---

## 3. 핵심 파일 상세

### 3.1 info.yaml

플러그인의 정보를 정의합니다.

```yaml
title: "플러그인 한글 이름"
version: "1.0.0"
package_name: "plugin_name"  # 디렉토리명과 일치
developer: "개발자명"
description: "플러그인 설명"
home: "https://github.com/developer/plugin_name"
```

### 3.2 setup.py

플러그인의 **진입점**입니다. 프레임워크가 이 파일을 실행하여 플러그인을 초기화합니다.

```python
# -*- coding: utf-8 -*-
from plugin import *  # create_plugin_instance, PluginModuleBase 등 임포트

# 1. 플러그인 기본 설정
setting = {
    'filepath': __file__,        # 현재 파일 경로 (필수)
    'use_db': True,              # True: plugin_name.db 파일 생성
    'use_default_setting': True, # True: ModelSetting 사용 (권장)
    'home_module': 'base',       # /plugin_name 접속 시 리다이렉트할 모듈명
    'menu': {
        'uri': __package__,
        'name': '플러그인명',    # 사이드바에 보일 이름
        'list': [
            # 'base' 모듈 메뉴 정의
            {
                'uri': 'base',
                'name': '설정',
                'list': [
                    {'uri': 'setting', 'name': '기본 설정'},
                    {'uri': 'log', 'name': '로그'}
                ]
            },
            # 'feature' 모듈 메뉴 정의
            {
                'uri': 'feature',
                'name': '기능',
                'list': [
                    {'uri': 'list', 'name': '목록'}
                ]
            }
        ]
    },
    'default_route': 'normal',  # 'normal' 또는 'single'
}

# 2. 플러그인 인스턴스 생성
P = create_plugin_instance(setting)

try:
    # 3. 모듈 임포트 및 등록
    from .mod_base import ModuleBase
    from .mod_feature import ModuleFeature
    
    P.set_module_list([ModuleBase, ModuleFeature])

    # 4. (선택) ModelSetting 참조 변수 생성
    # 다른 모듈에서 from .setup import PluginModelSetting 형태로 사용 가능
    PluginModelSetting = P.ModelSetting

except Exception as e:
    P.logger.error(f'Exception:{str(e)}')
    P.logger.error(traceback.format_exc())
```

### 3.3 mod_*.py (모듈 클래스)

실제 기능이 구현되는 파일입니다. `PluginModuleBase`를 상속받습니다.

**참고**: `lib/system/mod_setting.py`

```python
# mod_base.py
from plugin import PluginModuleBase
from .setup import P  # setup.py에서 생성한 P 인스턴스
from .page_utils import PageUtils  # (선택) 페이지를 사용한다면 페이지 클래스 임포트

class ModuleBase(PluginModuleBase):
    def __init__(self, P):
        # 1. 부모 클래스 초기화
        # name: 모듈명 (setup.py의 uri와 일치해야 함. 예: 'base')
        # first_menu: 이 모듈의 하위 메뉴 중 기본으로 보여줄 메뉴 (예: 'setting')
        super(ModuleBase, self).__init__(P, name='base', first_menu='setting')
        
        # 2. ModelSetting 기본값 정의
        self.db_default = {
            'api_key': 'default_api_key',
            f'{self.name}_interval': '10'  # base_interval
        }
        
        # 3. (선택) 이 모듈에 페이지(Page) 등록
        self.set_page_list([PageUtils])

    # 4. 메뉴 처리
    def process_menu(self, page, req):
        """
        페이지 렌더링을 담당합니다.
        
        Args:
            page: 하위 메뉴 uri (예: 'setting' 또는 'utils')
            req: Flask request 객체
        """
        try:
            # 4-1. ModelSetting 값들을 딕셔너리로 가져와 템플릿에 전달
            arg = P.ModelSetting.to_dict()
            
            # 스케줄러 상태 추가 (macro.html의 스케줄러 버튼용)
            arg['is_include'] = F.scheduler.is_include(self.get_scheduler_name())
            arg['is_running'] = F.scheduler.is_running(self.get_scheduler_name())

            # 4-2. 페이지(Page)가 처리해야 하는 경우
            if self.page_list is not None:
                page_ins = self.get_page(page)
                if page_ins is not None:
                    return page_ins.process_menu(req)

            # 4-3. 모듈이 직접 처리하는 경우 (예: 'setting' 메뉴)
            # 템플릿 규칙: {package_name}_{module_name}_{page}.html
            return render_template(
                f'{P.package_name}_{self.name}_{page}.html',
                arg=arg
            )
        
        except Exception as e:
            P.logger.error(f'Exception:{str(e)}')
            P.logger.error(traceback.format_exc())
            return "Error"

    # 5. AJAX 처리 (모듈)
    def process_ajax(self, sub, req):
        """
        커스텀 AJAX 요청을 처리합니다.
        URL: /ajax/{module_name}/{sub}
        """
        try:
            if sub == 'custom_ajax':
                data = req.form.to_dict()
                P.logger.debug(f"Custom AJAX 호출됨: {data}")
                return jsonify({'ret': 'success', 'msg': '커스텀 AJAX 성공'})
        except Exception as e:
            P.logger.error(f'Exception:{str(e)}')
            return jsonify({'ret': 'error', 'msg': str(e)})

    # 6. 스케줄링 (모듈)
    def scheduler_function(self):
        """주기적으로 실행될 작업을 정의합니다."""
        P.logger.info("모듈 스케줄러 실행됨")

    # 7. 설정 저장 후 처리
    def setting_save_after(self, change_list):
        """
        설정 저장 후 호출됩니다.
        
        Args:
            change_list: 변경된 설정 키 목록
        """
        P.logger.debug(f"설정 저장 완료. 변경된 키: {change_list}")
        
        # 스케줄링 간격이 변경되었다면 스케줄러 재시작
        if f'{self.name}_interval' in change_list:
            P.logic.scheduler_stop(self.name)
            P.logic.scheduler_start(self.name)
```

---

## 4. 데이터베이스 - 설정 저장 (ModelSetting)

플러그인의 '설정' 페이지(Key-Value)를 위한 자동화된 DB 저장 방식입니다.

### 4.1 동작 원리

#### 1단계: DB 초기화 (최초 1회)

플러그인이 처음 로드될 때, `mod_*.py`의 `self.db_default` 딕셔너리로 DB를 초기화합니다.

```python
# mod_base.py의 __init__
self.db_default = {
    'api_key': 'DEFAULT_KEY_PLEASE_CHANGE',
    'auto_start': 'False',
    f'{self.name}_interval': '30'
}
```

프레임워크는 `plugin_load()` 시 내부적으로 `db_init()`을 실행하여:
1. `P.ModelSetting.get(key)`로 DB에 값이 있는지 확인
2. 값이 없으면 `P.ModelSetting.set(key, value)`로 기본값 저장

#### 2단계: DB 값 로드 및 UI 바인딩 (페이지 진입 시)

사용자가 설정 메뉴 진입 시 `process_menu`가 호출되어:

```python
# mod_base.py의 process_menu
arg = P.ModelSetting.to_dict()  # DB의 모든 Key-Value를 딕셔너리로 로드
return render_template(f'{P.package_name}_{self.name}_{page}.html', arg=arg)
```

#### 3단계: UI 값 DB에 저장 (저장 버튼 클릭 시)

사용자가 'globalSettingSaveBtn' 버튼 클릭 시:

1. **JavaScript** (ff_global1.js): `<form id='setting'>` 데이터를 `/ajax/{plugin_name}/setting_save`로 POST 전송
2. **라우터** (route.py): `P.ModelSetting.setting_save(request)` 호출
3. **모델** (model_setting.py): 
   - `req.form.items()` 순회하며 key와 value 가져옴
   - `ModelSetting.get(key) != value`로 값이 변경되었는지 확인
   - 변경된 경우에만 DB 업데이트하고 `change_list`에 key 추가
4. **모듈** (mod_base.py): `setting_save_after(change_list)` 호출

### 4.2 UI 연동 (macro.html)

`ModelSetting`은 `macro.html`과 완벽하게 연동됩니다.

```html
{% extends "base.html" %}
{% block content %}

<!-- 설정 저장 버튼 -->
{{ macros.m_button_group([['globalSettingSaveBtn', '설정 저장']])}}
{{ macros.m_hr() }}

<form id='setting' name='setting'>
  <!-- 텍스트 입력 -->
  {{ macros.setting_input_text(
      'api_key',
      'API 키',
      value=arg.api_key,
      desc=['발급받은 API 키를 입력하세요.']
  )}}

  <!-- 체크박스 -->
  {{ macros.setting_checkbox(
      'auto_start',
      '자동 시작',
      value=arg.auto_start
  )}}
  
  <!-- 스케줄러 버튼 -->
  {{ macros.global_setting_scheduler_button(arg.is_include, arg.is_running)}}
  
  <!-- 스케줄링 간격 -->
  {{ macros.setting_input_text(
      'base_interval',
      '실행 주기',
      value=arg.base_interval,
      desc='분 단위 또는 Cron 표현식'
  )}}
</form>

{% endblock %}
```

**중요**: HTML 입력 요소의 `id`와 `name`은 `db_default`의 key와 반드시 일치해야 합니다.

---

## 5. 데이터베이스 - 커스텀 테이블 (ModelBase)

`ModelSetting`(K-V)이 아닌, 정형화된 데이터(로그, 목록 등)를 저장할 때 사용합니다.

### 5.1 모델 정의 (model.py)

```python
# model.py
from .setup import P  # setup.py의 P 인스턴스 임포트
from plugin import ModelBase
from sqlalchemy import or_

class MyLogTable(ModelBase):
    P = P  # (필수) 로거 등을 위해 P 인스턴스 연결
    __tablename__ = f'{P.package_name}_log_table'
    __bind_key__ = P.package_name  # (필수) 플러그인 DB 사용

    # 컬럼 정의
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(10))
    message = db.Column(db.String)
    created_time = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, level, message):
        self.level = level
        self.message = message

    # (선택) web_list를 위한 검색 쿼리 오버라이딩
    @classmethod
    def make_query(cls, req, order='desc', search='', option1='all', option2='all'):
        with F.app.app_context():
            query = F.db.session.query(cls)
            
            # 검색어 처리
            if search:
                query = query.filter(cls.message.like(f'%{search}%'))
            
            # 옵션 처리 (예: 로그 레벨)
            if option1 != 'all':
                query = query.filter(cls.level == option1)
            
            # 정렬
            if order == 'desc':
                query = query.order_by(db.desc(cls.id))
            else:
                query = query.order_by(cls.id)
            
            return query
```

**필수 요소**:
- `P = P`: `ModelBase`의 로거 등을 사용하기 위해 필요
- `__bind_key__ = P.package_name`: 이 모델이 `plugin_name.db` 파일을 사용하도록 지정

### 5.2 데이터 저장 (커스텀 AJAX 사용)

커스텀 테이블 저장은 `globalSettingSaveBtn`을 사용하지 않습니다. **별도 버튼**과 **커스텀 AJAX**가 필요합니다.

#### UI 템플릿

```html
<!-- ..._feature_list.html -->
<form id="custom_form">
  {{ macros.setting_input_text_and_buttons(
      'log_message_input',
      '로그 메시지',
      [['custom_save_btn', '로그 저장']],
      value='',
      desc=['저장할 로그 메시지를 입력하세요.']
  )}}
</form>

<script>
// '로그 저장' 버튼 클릭 이벤트
$("body").on('click', '#custom_save_btn', function(e){ 
  e.preventDefault();

  $.ajax({
      url: '/{{ P.package_name }}/base/ajax/save_log',
      type: 'POST',
      data: { 
          message: $('#log_message_input').val() 
      },
      success: function(response) {
          if (response.ret === 'success') {
              notify('로그 저장 완료', 'success');
          } else {
              notify('저장 실패: ' + response.msg, 'warning');
          }
      }
  });
});
</script>
```

#### 모듈 AJAX 처리

```python
# mod_base.py
from .model import MyLogTable  # 정의한 모델 임포트

class ModuleBase(PluginModuleBase):
    # ... (__init__, process_menu) ...

    def process_ajax(self, sub, req):
        try:
            if sub == 'save_log':
                msg = req.form.get('message')
                if msg:
                    # 모델 인스턴스 생성
                    new_log = MyLogTable(level='info', message=msg)
                    # DB에 저장 (ModelBase의 save() 메서드)
                    new_log.save()
                    return jsonify({'ret': 'success'})
                else:
                    return jsonify({'ret': 'error', 'msg': '메시지 없음'})
        except Exception as e:
            P.logger.error(f"AJAX error: {str(e)}")
            return jsonify({'ret': 'error', 'msg': str(e)})
```

### 5.3 데이터 목록 표시 (web_list 활용)

`ModelBase`는 페이징과 검색을 자동화하는 `web_list` 기능을 제공합니다.

#### 모듈 설정

```python
# mod_base.py
from .model import MyLogTable

class ModuleBase(PluginModuleBase):
    def __init__(self, P):
        super(ModuleBase, self).__init__(P, name='base', first_menu='setting')
        self.db_default = { ... }
        
        # (필수) 이 모듈이 'web_list' 기능으로 사용할 모델을 지정
        self.web_list_model = MyLogTable
```

#### 라우터 자동 처리

프레임워크의 `route.py`에서 `/ajax/{module_name}/web_list` 엔드포인트가 자동으로:
1. `module.web_list_model.web_list(request)` 호출
2. `req.form`에서 `page`, `keyword` 등 자동 추출
3. `MyLogTable.make_query` (오버라이딩한 메서드) 호출
4. 페이징 처리된 데이터 목록(list)과 페이징 정보(paging)를 JSON으로 반환

#### UI 템플릿

```html
<!-- ..._base_setting.html -->
<h3>로그 목록</h3>
<div id="log_list_container"></div>
<div id="paging_container"></div>

<script>
$(document).ready(function() {
    load_list(1);  // 페이지 로드 시 첫 페이지 로드
});

function load_list(page) {
    $.ajax({
        url: '/{{ P.package_name }}/base/ajax/web_list',
        type: 'POST',
        data: { 
            page: page,
            keyword: '',     // (선택) 검색어
            option1: 'all'   // (선택) 옵션
        },
        success: function(response) {
            // 목록 그리기
            $('#log_list_container').empty();
            response.list.forEach(function(item) {
                let row = j_row_start('5');  // ff_ui1.js
                row += j_col('1', item.id);
                row += j_col('2', item.level);
                row += j_col('7', item.message);
                row += j_col('2', item.created_time);
                row += j_row_end();
                $('#log_list_container').append(row);
            });

            // 페이징 그리기 (별도 함수 필요 - 생략)
            // response.paging 객체를 사용하여 페이징 UI 생성
        }
    });
}
</script>
```

---

## 6. 모듈과 페이지 (심화)

모듈(`PluginModuleBase`) 하나가 너무 복잡해질 때, 하위 기능을 `PluginPageBase`로 분리할 수 있습니다.

**참고**: `lib/plugin/logic_module_base.py`, `lib/system/mod_tool.py`

### 6.1 PluginPageBase 개념

- `PluginPageBase`는 `PluginModuleBase`와 거의 동일한 구조를 가집니다
- 차이점: **부모 모듈(`parent`)**을 통해 `P` 인스턴스에 접근합니다
- 라우팅은 부모 모듈을 거쳐서 페이지로 위임됩니다

### 6.2 페이지 구현 예제

#### 페이지 클래스 정의

```python
# page_utils.py
from plugin import PluginPageBase

class PageUtils(PluginPageBase):
    def __init__(self, P, parent):
        # name: 페이지 이름 (setup.py 메뉴 uri와 일치)
        super(PageUtils, self).__init__(P, parent, name='utils')
        
        # 페이지 전용 ModelSetting 기본값 정의
        self.db_default = {
            'util_option_1': 'True'
        }

    def process_menu(self, req):
        """페이지의 메뉴 처리"""
        arg = self.P.ModelSetting.to_dict()
        # 템플릿: {pkg_name}_{module_name}_{page_name}.html
        return render_template(
            f'{self.P.package_name}_{self.parent.name}_{self.name}.html',
            arg=arg
        )

    def process_ajax(self, sub, req):
        """페이지의 AJAX 처리"""
        # URL: /ajax/{module_name}/{page_name}/{sub}
        if sub == 'run_util':
            return jsonify({'ret': 'success', 'msg': '유틸리티 실행'})
```

#### 모듈에 페이지 등록

```python
# mod_base.py
from .page_utils import PageUtils

class ModuleBase(PluginModuleBase):
    def __init__(self, P):
        super(ModuleBase, self).__init__(P, name='base', first_menu='setting')
        self.db_default = { ... }
        
        # (필수) 페이지 리스트 등록
        self.set_page_list([PageUtils])
```

#### 라우팅 위임 (프레임워크 자동 처리)

사용자가 `/plugin_name/base/utils` 접근 시:
1. `ModuleBase`의 `process_menu` 호출
2. `page_ins = self.get_page('utils')` 실행
3. `return page_ins.process_menu(req)` 호출
4. `PageUtils`의 `process_menu`로 처리 위임

AJAX도 동일한 방식으로 위임됩니다.

---

## 7. Celery 사용

시간이 오래 걸리는 작업(I/O, API 호출)은 반드시 Celery 태스크로 분리하여 메인 스레드를 차단하지 않도록 해야 합니다.

```python
# mod_feature.py
from framework import celery
from .setup import P, PluginModelSetting

class ModuleFeature(PluginModuleBase):
    # ... (init, process_menu 등) ...

    def scheduler_function(self):
        """스케줄러에서 Celery 작업 호출"""
        P.logger.debug("Celery 작업 요청")
        if F.config['use_celery']:
            # 비동기 호출
            api_key = PluginModelSetting.get('api_key')
            self.task.apply_async((api_key,))
        else:
            # Celery 미사용 시 직접 실행 (테스트용)
            self.task(PluginModelSetting.get('api_key'))

    @staticmethod
    @celery.task
    def task(api_key):
        """
        실제 작업 로직 (Celery 워커에서 실행됨)
        
        주의:
        - 이 함수는 P 인스턴스나 self에 접근할 수 없습니다
        - 필요한 값은 인자로 전달받아야 합니다
        - 설정값 조회가 필요하면 ModelSetting.get()을 사용해야 합니다
        """
        P.logger.info(f"Celery 작업 실행 중... API Key: {api_key}")
        # ... (시간이 오래 걸리는 작업) ...
        P.logger.info("Celery 작업 완료")
```

**중요 사항**:
- Celery 태스크는 별도 프로세스에서 실행되므로 `self`나 `P` 인스턴스에 직접 접근 불가
- 필요한 값은 반드시 인자로 전달
- DB 접근이 필요하면 task 내부에서 `from .setup import PluginModelSetting` 임포트

---

## 8. 디버깅, 배포 및 체크리스트

### 8.1 디버깅

#### 일반적인 문제와 해결 방법

1.  **페이지가 `plugin_name - module_name` 텍스트만 표시됨**

      * **원인**: `process_menu()`가 `render_template`을 실행하지 못함.
      * **해결**:
          * `mod_*.py`의 `__init__`에서 `first_menu`가 `setup.py`의 메뉴 `uri`와 일치하는지 확인.
          * `process_menu`의 `render_template` 경로가 `templates/` 안의 파일명(`{pkg_name}_{mod_name}_{page_name}.html`)과 일치하는지 확인.

2.  **템플릿을 찾을 수 없음 (Template Not Found)**

      * **원인**: `templates/` 디렉토리 안의 HTML 파일명이 명명 규칙과 다름.
      * **해결**: 파일명이 `plugin_name_base_setting.html` 형식인지 확인.

3.  **설정 저장이 안 됨**

      * **원인**: `id` 불일치.
      * **해결**:
          * HTML이 `{% extends "base.html" %}`를 포함하는지 확인.
          * `<form id='setting'>`이 올바르게 선언되었는지 확인.
          * `macros.setting_input_text`의 `id` (예: `api_key`)가 `mod_*.py`의 `self.db_default`에 정의된 `key`와 일치하는지 확인.

4.  **AJAX 요청이 실패 (404 Not Found)**

      * **원인**: JS의 AJAX URL이 `route.py`의 규칙과 다름.
      * **해결**:
          * `ModelSetting` 저장: `/ajax/{plugin_name}/setting_save` (자동)
          * `web_list`: `/ajax/{module_name}/web_list`
          * 커스텀 AJAX (모듈): `/ajax/{module_name}/ajax/{sub}`
          * 커스텀 AJAX (페이지): `/ajax/{module_name}/{page_name}/{sub}`

5.  **Celery 작업이 실행되지 않음**

      * **원인**: Celery 워커가 실행되지 않았거나 `@celery.task` 데코레이터가 없음.
      * **해결**: FlaskFarm 실행 로그에서 Celery 워커가 정상적으로 시작되었는지 확인.

### 배포 체크리스트

  * [ ] `info.yaml` 정보 (특히 `package_name`)가 정확한가?
  * [ ] `setup.py`의 `menu` 구조가 `mod_*.py` 및 `page_*.py`의 `name`, `first_menu`와 일치하는가?
  * [ ] `templates/` 안의 모든 `html` 파일명이 명명 규칙(`{pkg}_{mod}_{page}.html`)을 준수하는가?
  * [ ] `ModelSetting`을 사용하는 모든 `html` 매크로의 `id`가 `db_default`의 `key`와 일치하는가?
  * [ ] `ModelBase`를 상속받은 커스텀 모델에 `P = P`와 `__bind_key__ = P.package_name`이 정의되었는가?
  * [ ] `requirements.txt`에 FlaskFarm 기본 패키지 외의 의존성을 추가했는가?
  * [ ] Celery 작업(`@celery.task`)이 `self`나 `P`를 직접 참조하지 않고 인자로 값을 받도록 수정했는가?
  * [ ] `README.md`를 작성했는가?