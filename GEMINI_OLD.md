# FlaskFarm 플러그인 개발 가이드

이 가이드는 FlaskFarm 플랫폼을 위한 커스텀 플러그인을 개발하는 방법을 안내합니다.

## 목차

1.  [플러그인 아키텍처](https://www.google.com/search?q=%231-%ED%94%8C%EB%9F%AC%EA%B7%B8%EC%9D%B8-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98)
2.  [프로젝트 구조](https://www.google.com/search?q=%232-%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8-%EA%B5%AC%EC%A1%B0)
3.  [핵심 파일 상세](https://www.google.com/search?q=%233-%ED%95%B5%EC%8B%AC-%ED%8C%8C%EC%9D%BC-%EC%83%81%EC%84%B8)
      * `info.yaml`
      * `setup.py`
      * `mod_*.py` (모듈 클래스)
4.  [DB - 설정 저장 (`ModelSetting`)](https://www.google.com/search?q=%234-db---%EC%84%A4%EC%A0%95-%EC%A0%80%EC%9E%A5-modelsetting)
      * 동작 원리 (초기화, 로드, 저장)
      * UI 연동 (`macro.html`)
5.  [DB - 커스텀 테이블 (`ModelBase`)](https://www.google.com/search?q=%235-db---%EC%BB%A4%EC%8A%A4%ED%85%80-%ED%85%8C%EC%9D%B4%EB%B8%94-modelbase)
      * 모델 정의 (`model.py`)
      * 커스텀 AJAX를 통한 저장
      * `web_list`를 이용한 목록 표시
6.  [모듈과 페이지 (심화)](https://www.google.com/search?q=%236-%EB%AA%A8%EB%93%88%EA%B3%BC-%ED%8E%98%EC%9D%B4%EC%A7%80-%EC%8B%AC%ED%99%94-pluginpagebase)
      * `PluginPageBase` 개념
      * 모듈에 페이지 등록
7.  [Celery 사용](https://www.google.com/search?q=%237-celery-%EC%82%AC%EC%9A%A9)
8.  [디버깅, 배포, 및 체크리스트](https://www.google.com/search?q=%238-%EB%94%94%EB%B2%84%EA%B9%85-%EB%B0%B0%ED%8F%AC-%EB%B0%8F-%EC%B2%B4%ED%81%AC%EB%A6%AC%EC%8A%A4%ED%8A%B8)

-----

## 1\. 플러그인 아키텍처

FlaskFarm의 플러그인은 **모듈(Module)** 과 선택적으로 **페이지(Page)** 로 구성됩니다.

  * **모듈 (Module)**: `PluginModuleBase`를 상속받는 기능 단위입니다. (예: `mod_setting.py`). `setup.py`의 메뉴 구조에서 상위 레벨(depth 1)을 담당합니다. (예: `system` 플러그인의 `setting` 모듈)
  * **페이지 (Page)**: (선택 사항) `PluginPageBase`를 상속받으며, 하나의 모듈에 종속되어 하위 기능을 세분화합니다. (예: `system` 플러그인의 `tool` 모듈 하위 `command` 페이지)
  * **플러그인 (Plugin)**: 이 모듈과 페이지들을 `setup.py`로 묶어 정의한 하나의 패키지입니다.

<!-- end list -->

```
플러그인 (plugin_name)
├── 모듈 (mod_base.py)
│   └── 페이지 (page_sub1.py) - 선택
│   └── 페이지 (page_sub2.py) - 선택
└── 모듈 (mod_feature.py)
```

-----

## 2\. 프로젝트 구조

```
plugin_name/
├── __init__.py
├── info.yaml                # 플러그인 메타데이터 (필수)
├── setup.py                 # 플러그인 설정 및 모듈/메뉴 등록 (필수)
├── mod_base.py              # 'base' 모듈 클래스
├── mod_feature.py           # 'feature' 모듈 클래스
├── page_utils.py            # 'base' 모듈에 속할 'utils' 페이지 클래스 (선택)
├── model.py                 # SQLAlchemy DB 모델 (선택)
├── requirements.txt         # 의존성 패키지 (선택)
└── templates/               # HTML 템플릿 (필수)
    ├── plugin_name_base_setting.html   # mod_base.py / 'setting' 메뉴
    └── plugin_name_base_utils.html     # page_utils.py / 'utils' 메뉴
```

-----

## 3\. 핵심 파일 상세

### `info.yaml`

플러그인의 정보를 정의합니다.

```yaml
title: "플러그인 한글 이름"
version: "1.0.0"
package_name: "plugin_name" # 디렉토리명과 일치
developer: "개발자명"
description: "플러그인 설명"
home: "https://github.com/developer/plugin_name"
```

### `setup.py`

플러그인의 **진입점**입니다. (참고: `lib/system/setup.py`)

```python
# -*- coding: utf-8 -*-
from plugin import * # create_plugin_instance, PluginModuleBase, PluginPageBase

# 1. 플러그인 기본 설정
setting = {
    'filepath' : __file__,       # (필수) 현재 파일 경로
    'use_db': True,              # True: plugin_name.db 파일 생성
    'use_default_setting': True, # True: ModelSetting 사용 (권장)
    'home_module': 'base',       # /plugin_name 접속 시 리다이렉트할 모듈
    'menu': {
        'uri': __package__,
        'name': '플러그인명',
        'list': [
            # 'base' 모듈 메뉴 정의
            {'uri': 'base', 'name': '기본 설정', 'list': [
                {'uri': 'setting', 'name': '설정'},
                {'uri': 'utils', 'name': '유틸리티'} # 'utils' 페이지 메뉴
            ]},
            # 'feature' 모듈 메뉴 정의
            {'uri': 'feature', 'name': '기능', 'list': [
                {'uri': 'list', 'name': '목록'}
            ]}
        ]
    },
    'default_route': 'normal', # 'normal' 또는 'single'
}

# 2. 플러그인 인스턴스 생성
P = create_plugin_instance(setting)

try:
    # 3. 모듈 임포트 및 등록
    from .mod_base import ModuleBase
    from .mod_feature import ModuleFeature
    
    P.set_module_list([ModuleBase, ModuleFeature])

    # 4. (선택) ModelSetting 참조 변수 생성
    # 다른 파일에서 from .setup import PluginModelSetting 형태로 사용
    PluginModelSetting = P.ModelSetting 

except Exception as e:
    P.logger.error(f'Exception:{str(e)}')
    P.logger.error(traceback.format_exc())
```

### `mod_*.py` (모듈 클래스)

`PluginModuleBase`를 상속받습니다. (참고: `lib/system/mod_setting.py`)

```python
# mod_base.py
from plugin import PluginModuleBase
from .setup import P
# (선택) 페이지를 사용한다면 페이지 클래스 임포트
from .page_utils import PageUtils 

class ModuleBase(PluginModuleBase):
    def __init__(self, P):
        # 1. 부모 클래스 초기화
        # name: 모듈명 (setup.py의 uri와 일치)
        # first_menu: 이 모듈의 하위 메뉴 중 기본으로 보여줄 메뉴
        super(ModuleBase, self).__init__(P, name='base', first_menu='setting')
        
        # 2. ModelSetting 기본값 정의
        self.db_default = {
            'api_key': 'default_api_key',
            f'{self.name}_interval': '10' # base_interval
        }
        
        # 3. (선택) 이 모듈에 페이지(Page) 등록
        # lib/system/mod_tool.py 참고
        self.set_page_list([PageUtils])

    # 4. 메뉴 처리
    def process_menu(self, page, req):
        # page: 하위 메뉴 uri (예: 'setting' 또는 'utils')
        try:
            arg = P.ModelSetting.to_dict()
            arg['is_include'] = F.scheduler.is_include(self.get_scheduler_name())
            arg['is_running'] = F.scheduler.is_running(self.get_scheduler_name())

            # 4-1. 페이지(Page)가 처리해야 하는 경우
            # self.page_list에 등록된 페이지가 있는지 확인
            if self.page_list is not None:
                # get_page(page)는 page 이름과 일치하는 페이지 인스턴스를 찾음
                page_ins = self.get_page(page) 
                if page_ins is not None:
                    # 페이지의 process_menu 호출 (page_utils.py 참고)
                    return page_ins.process_menu(req) 

            # 4-2. 모듈이 직접 처리하는 경우 (예: 'setting' 메뉴)
            # 템플릿 규칙: {package_name}_{module_name}_{page}.html
            return render_template(f'{P.package_name}_{self.name}_{page}.html', arg=arg)
        
        except Exception as e:
            P.logger.error(f'Exception:{str(e)}')
            return "Error"

    # 5. AJAX 처리 (모듈)
    def process_ajax(self, sub, req):
        # URL: /ajax/base/{sub}
        pass

    # 6. 스케줄링 (모듈)
    def scheduler_function(self):
        P.logger.info("모듈 스케줄러 실행됨")
```

-----

## 4\. DB - 설정 저장 (`ModelSetting`)

플러그인의 '설정' 페이지(Key-Value)를 위한 자동화된 DB 저장 방식입니다.

### 동작 원리 (초기화, 로드, 저장)

1.  **초기화 (`logic.py` -\> `db_init`)**:

      * 플러그인 로드 시 `mod_*.py`의 `self.db_default` 딕셔너리를 읽음.
      * `P.ModelSetting.get(key)`로 DB에 값이 있는지 확인.
      * 값이 없으면 `P.ModelSetting.set(key, value)`로 기본값 저장.

2.  **로드 (`logic_module_base.py` -\> `process_menu`)**:

      * 사용자가 설정 메뉴 진입 시 `process_menu` 호출.
      * `arg = P.ModelSetting.to_dict()`가 DB의 모든 K-V를 `arg` 딕셔너리로 로드.
      * `render_template(..., arg=arg)`로 템플릿에 전달.

3.  **저장 (`route.py` -\> `ajax(sub)`)**:

      * 사용자가 `globalSettingSaveBtn` 버튼 클릭.
      * JS가 `<form id='setting'>` 데이터를 `/ajax/{plugin_name}/setting_save`로 POST 전송.
      * `route.py`의 `ajax` 함수가 `sub == 'setting_save'`를 감지.
      * `P.ModelSetting.setting_save(request)` 호출.
      * `model_setting.py`의 `setting_save`는 폼 데이터를 순회하며 **값이 변경된 `key`만** DB에 업데이트.
      * 저장 후 `mod_*.py`의 `setting_save_after(change_list)` 호출.

### UI 연동 (`macro.html`)

`ModelSetting`은 `macro.html`과 완벽하게 연동됩니다.

  * `form` 태그: `<form id='setting' name='setting'>`
  * 저장 버튼: `{{ macros.m_button_group([['globalSettingSaveBtn', '설정 저장']])}}`

<!-- end list -->

```html
{% extends "base.html" %}
{% block content %}

{{ macros.m_button_group([['globalSettingSaveBtn', '설정 저장']])}}
{{ macros.m_hr() }}

<form id='setting' name='setting'>
  {{ macros.setting_input_text(
      'api_key', 
      'API 키', 
      value=arg.api_key
  )}}

  {{ macros.setting_checkbox(
      'auto_start', 
      '자동 시작', 
      value=arg.auto_start
  )}}
  
  {{ macros.global_setting_scheduler_button(arg.is_include, arg.is_running)}}
  
  {{ macros.setting_input_text(
      'base_interval', 
      '실행 주기', 
      value=arg.base_interval, 
      desc='분 단위 또는 Cron 표현식'
  )}}

</form>
{% endblock %}
```

-----

## 5\. DB - 커스텀 테이블 (`ModelBase`)

`ModelSetting`(K-V)이 아닌, 정형화된 데이터(로그, 목록 등)를 저장할 때 사용합니다.

### 모델 정의 (`model.py`)

  * `ModelBase` (`lib/plugin/model_base.py`) 상속.
  * `(필수)` `P = P` : `ModelBase`의 로거(`cls.P.logger`) 등을 사용하기 위해 `setup.py`의 `P` 객체를 클래스 변수로 할당.
  * `(필수)` `__bind_key__ = P.package_name` : 이 모델이 `plugin_name.db` 파일을 사용하도록 지정.

<!-- end list -->

```python
# model.py
from .setup import P
from plugin import ModelBase
from sqlalchemy import or_

class MyDataTable(ModelBase):
    P = P # (필수) 로거 등을 위해 P 인스턴스 연결
    __tablename__ = f'{P.package_name}_data_table'
    __bind_key__ = P.package_name # (필수) 플러그인 DB 사용

    # 컬럼 정의
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    value = db.Column(db.String)
    created_time = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, name, value):
        self.name = name
        self.value = value

    # (선택) web_list를 위한 검색 쿼리 오버라이딩
    @classmethod
    def make_query(cls, req, order='desc', search='', option1='all', option2='all'):
        with F.app.app_context():
            query = F.db.session.query(cls)
            if search:
                query = query.filter(cls.name.like(f'%{search}%'))
            if order == 'desc':
                query = query.order_by(db.desc(cls.id))
            else:
                query = query.order_by(cls.id)
            return query
```

### 커스텀 AJAX를 통한 저장 📤

`ModelBase`는 `globalSettingSaveBtn`을 사용하지 않습니다. **별도 버튼**과 **커스텀 AJAX**가 필요합니다.

1.  **UI (`..._feature_list.html`)**

      * `globalSettingSaveBtn` 대신 일반 버튼 (예: `save_data_btn`)을 만듭니다.

    <!-- end list -->

    ```html
    {{ macros.setting_input_text_and_buttons(
        'data_name_input', 
        '데이터 이름', 
        [['save_data_btn', '저장']], 
        value=''
    )}}

    <script>
    $("body").on('click', '#save_data_btn', function(e){ 
      e.preventDefault();
      $.ajax({
          url: '/{{ P.package_name }}/feature/ajax/save_data', // 모듈: feature, sub: save_data
          type: 'POST',
          data: { name: $('#data_name_input').val() },
          success: function(response) {
              if (response.ret === 'success') notify('저장 완료', 'success');
              else notify('저장 실패', 'warning');
          }
      });
    });
    </script>
    ```

2.  **모듈 (`mod_feature.py`)**

      * `process_ajax(self, sub, req)` 메서드를 구현합니다.
      * `sub`가 `save_data`인 경우, `MyDataTable` 모델을 임포트하여 `save()` 합니다.

    <!-- end list -->

    ```python
    # mod_feature.py
    from .model import MyDataTable # 정의한 모델 임포트

    class ModuleFeature(PluginModuleBase):
        # ... ( __init__, process_menu ) ...

        def process_ajax(self, sub, req):
            try:
                if sub == 'save_data':
                    name = req.form.get('name')
                    new_data = MyDataTable(name=name, value='some_value')
                    new_data.save() # ModelBase에 정의된 save()
                    return jsonify({'ret': 'success'})
            except Exception as e:
                P.logger.error(f"AJAX error: {str(e)}")
                return jsonify({'ret': 'error', 'msg': str(e)})
    ```

### `web_list`를 이용한 목록 표시 🔄

`ModelBase`는 페이징과 검색을 자동화하는 `web_list` 기능을 제공합니다.

1.  **모듈 (`mod_feature.py`)**

      * `__init__`에서 `self.web_list_model` 변수에 모델 클래스(`MyDataTable`)를 연결합니다.

    <!-- end list -->

    ```python
    # mod_feature.py
    class ModuleFeature(PluginModuleBase):
        def __init__(self, P):
            super(ModuleFeature, self).__init__(P, name='feature', first_menu='list')
            
            # (필수) 이 모듈이 'web_list'로 사용할 모델을 지정
            self.web_list_model = MyDataTable
    ```

2.  **라우터 (`route.py` - 프레임워크 제공)**

      * `/ajax/{module_name}/web_list` 엔드포인트는 `self.web_list_model.web_list(request)`를 자동으로 호출합니다.
      * `web_list(req)`는 `req.form`의 `page`, `keyword` 등을 기반으로 `make_query` (우리가 오버라이딩한)를 호출하여 페이징된 JSON(list, paging)을 반환합니다.

3.  **UI (`..._feature_list.html`)**

      * `web_list`를 호출하여 목록을 동적으로 그리는 JS를 작성합니다.

    <!-- end list -->

    ```html
    <div id="data_list_container"></div>
    <script>
    $(document).ready(function() { load_list(1); });

    function load_list(page) {
        $.ajax({
            url: '/{{ P.package_name }}/feature/ajax/web_list',
            type: 'POST',
            data: { page: page, keyword: '' },
            success: function(response) {
                $('#data_list_container').empty();
                response.list.forEach(function(item) {
                    let row = j_row_start('5'); // ff_ui1.js
                    row += j_col('2', item.id);
                    row += j_col('8', item.name);
                    row += j_row_end();
                    $('#data_list_container').append(row);
                });
                // response.paging으로 페이징 UI 그리기 (생략)
            }
        });
    }
    </script>
    ```

-----

## 6\. 모듈과 페이지 (심화): `PluginPageBase`

모듈(`PluginModuleBase`) 하나가 너무 복잡해질 때, 하위 기능을 `PluginPageBase`로 분리할 수 있습니다. (참고: `lib/plugin/logic_module_base.py`, `lib/system/mod_tool.py`)

### `PluginPageBase` 개념

  * `PluginPageBase`는 `PluginModuleBase`와 거의 동일한 구조(db\_default, process\_menu, process\_ajax 등)를 가집니다.
  * 차이점은 `PluginPageBase`는 **부모 모듈(`parent`)** 을 통해 `P` 인스턴스에 접근한다는 것입니다 (`self.P = parent.P`).
  * 라우팅은 부모 모듈을 거쳐서 페이지로 위임됩니다.

### 모듈에 페이지 등록

1.  **페이지 클래스 정의 (`page_utils.py`)**

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

        # 페이지의 메뉴 처리
        def process_menu(self, req):
            arg = self.P.ModelSetting.to_dict()
            # 템플릿: {pkg_name}_{module_name}_{page_name}.html
            return render_template(f'{self.P.package_name}_{self.parent.name}_{self.name}.html', arg=arg)

        # 페이지의 AJAX 처리
        def process_ajax(self, sub, req):
            # URL: /ajax/{module_name}/{page_name}/{sub}
            if sub == 'run_util':
                return jsonify({'ret': 'success', 'msg': '유틸리티 실행'})
    ```

2.  **모듈에 페이지 등록 (`mod_base.py`)**

      * `__init__`에서 `self.set_page_list()`를 호출하여 페이지 클래스를 등록합니다.

    <!-- end list -->

    ```python
    # mod_base.py
    from .page_utils import PageUtils 

    class ModuleBase(PluginModuleBase):
        def __init__(self, P):
            super(ModuleBase, self).__init__(P, name='base', first_menu='setting')
            # ... db_default ...
            
            # (필수) 페이지 리스트 등록
            self.set_page_list([PageUtils])
    ```

3.  **라우팅 위임 (`logic_module_base.py` - 프레임워크 제공)**

      * 사용자가 `/plugin_name/base/utils` (페이지)에 접근하면 `ModuleBase`의 `process_menu`가 호출됩니다.
      * `process_menu`는 `page_ins = self.get_page(page)` (page='utils')를 통해 `PageUtils` 인스턴스를 찾습니다.
      * `return page_ins.process_menu(req)`를 호출하여 `PageUtils`의 `process_menu`로 처리를 위임합니다.
      * AJAX(`process_ajax`)도 `route.py`의 `sub_ajax` 라우터를 통해 동일한 방식으로 페이지의 `process_ajax`로 위임됩니다.

-----

## 7\. Celery 사용

가이드 초안의 내용이 정확합니다. 시간이 오래 걸리는 작업(I/O, API 호출)은 반드시 Celery 태스크로 분리해야 합니다.

```python
# mod_feature.py
from framework import celery
from .setup import P, PluginModelSetting # P와 ModelSetting 임포트

class ModuleFeature(PluginModuleBase):
    # ... (init, process_menu 등) ...

    # 예: 1회 실행 버튼으로 Celery 작업 호출
    def process_ajax(self, sub, req):
        if sub == 'start_heavy_task':
            P.logger.debug("Celery 작업 요청")
            if F.config['use_celery']:
                api_key = PluginModelSetting.get('api_key') # 인자로 전달
                self.task.apply_async((api_key,))
            else:
                self.task(PluginModelSetting.get('api_key')) # Celery 미사용 시
            return jsonify({'ret': 'success', 'msg': '작업 시작'})

    @staticmethod
    @celery.task
    def task(api_key):
        """
        (주의) Celery 워커에서 실행됨 (별도 프로세스)
        - self, P 인스턴스에 직접 접근 불가
        - 필요한 값(api_key)은 인자로 받아야 함
        - DB 접근이 필요하면 task 내에서 ModelSetting을 임포트 (from .setup import PluginModelSetting)
        """
        P.logger.info(f"Celery 작업 실행... API Key: {api_key}")
        # ... (시간이 오래 걸리는 작업) ...
        P.logger.info("Celery 작업 완료")
```

-----

## 8\. 디버깅, 배포, 및 체크리스트

### 디버깅 및 문제 해결

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

  데이터베이스(DB) 처리와 설정 저장 로직에 대해 FlaskFarm 소스 코드를 기반으로 훨씬 더 구체적으로 설명해 드리겠습니다.

FlaskFarm의 데이터 처리는 크게 두 가지로 나뉩니다.

ModelSetting: 플러그인의 '설정' 페이지를 위한 Key-Value 저장소

ModelBase: 로그나 게시물처럼 정형화된 데이터를 저장하기 위한 커스텀 테이블

이 두 가지가 UI 및 서버 로직과 어떻게 연결되는지 상세히 분석해 드립니다.

1. ModelSetting을 이용한 설정 페이지 (핵심)
플러그인의 '설정' 페이지(예: API 키, 스케줄링 간격 입력)는 ModelSetting을 통해 매우 간단하게 구현됩니다. 전체적인 데이터 흐름은 다음과 같습니다.

💡 1단계: (최초 1회) DB 초기화
플러그인이 처음 로드될 때, db_default에 정의된 값으로 DB를 초기화합니다.

모듈 정의 (mod_base.py)

__init__ 메서드에서 self.db_default 딕셔너리를 정의합니다. 이 key들이 DB의 key가 됩니다.

Python

# mod_base.py
class ModuleBase(PluginModuleBase):
    def __init__(self, P):
        super(ModuleBase, self).__init__(P, name='base', first_menu='setting')

        # 1. 이 모듈이 사용할 설정값들의 기본값 정의
        self.db_default = {
            'api_key': 'DEFAULT_KEY_PLEASE_CHANGE',
            'auto_start': 'False',
            f'{self.name}_interval': '30' # 스케줄러 간격
        }
플러그인 로드 (logic.py)

plugin_load()가 호출되면 내부적으로 db_init()를 실행합니다.

db_init()는 self.db_default를 순회하며 P.ModelSetting.get(key)로 DB에 값이 있는지 확인합니다.

만약 값이 없다면 (최초 실행), P.ModelSetting.set(key, value)를 호출하여 기본값으로 DB에 저장합니다.

📥 2단계: (페이지 진입 시) DB 값 로드 및 UI 바인딩
사용자가 설정 페이지에 접근하면 DB의 값을 읽어와 HTML에 채워 넣습니다.

메뉴 처리 (mod_base.py)

process_menu가 호출됩니다.

arg = P.ModelSetting.to_dict(): 이 플러그인의 _setting 테이블에 있는 모든 Key-Value를 딕셔너리로 가져옵니다.

render_template(..., arg=arg): 이 arg 딕셔너리를 HTML 템플릿으로 전달합니다.

Python

# mod_base.py
def process_menu(self, page, req):
    try:
        # 1. DB에서 모든 설정값을 'arg' 딕셔너리로 로드
        arg = P.ModelSetting.to_dict() 

        # 2. 스케줄러 버튼 상태 추가
        arg['is_include'] = F.scheduler.is_include(self.get_scheduler_name())
        arg['is_running'] = F.scheduler.is_running(self.get_scheduler_name())

        # 3. 템플릿에 'arg' 전달
        return render_template(f'{P.package_name}_{self.name}_{page}.html', arg=arg)
    except Exception as e:
        # ... (에러 처리) ...
UI 템플릿 (..._base_setting.html)

macro.html의 매크로를 사용합니다.

id와 name을 ModelSetting의 key와 반드시 일치시킵니다.

value=arg['api_key']처럼 arg 딕셔너리의 값을 value에 바인딩합니다.

HTML

{% extends "base.html" %}
{% block content %}

<form id='setting' name='setting'>
  {{ macros.setting_input_text(
      'api_key', 
      'API 키', 
      value=arg.api_key, 
      desc=['발급받은 API 키를 입력하세요.']
  )}}

  {{ macros.setting_checkbox(
      'auto_start', 
      '자동 시작', 
      value=arg.auto_start
  )}}
</form>
{% endblock %}
💾 3단계: (저장 버튼 클릭 시) UI 값 DB에 저장
사용자가 UI에서 '설정 저장' 버튼을 누르면, 폼 데이터가 서버로 전송되어 DB에 업데이트됩니다.

UI 템플릿 (..._base_setting.html)

base.html에 이미 포함된 globalSettingSaveBtn 버튼을 사용합니다.

{{ macros.m_button_group([['globalSettingSaveBtn', '설정 저장']])}}

Global JavaScript (ff_global1.js - 프레임워크 제공)

사용자가 globalSettingSaveBtn 버튼을 클릭하면, 이 JS가 <form id='setting'> 내부의 모든 input, select, textarea의 name과 value를 수집합니다.

수집된 데이터를 POST 방식으로 /ajax/{plugin_name}/setting_save 엔드포인트로 전송합니다.

(예: {'api_key': 'new_value_123', 'auto_start': 'True'})

라우터 (route.py - 프레임워크 제공)

default_route(P)에 의해 자동 생성된 /ajax/<sub> 라우터가 요청을 받습니다.

sub가 setting_save이므로 P.ModelSetting.setting_save(request)를 호출합니다.

Python

# lib/plugin/route.py
@P.blueprint.route('/ajax/<sub>', methods=['GET', 'POST'])
@login_required
def ajax(sub):
    try:
        if sub == 'setting_save':
            # 1. ModelSetting의 setting_save 메서드 호출
            ret, change_list = P.ModelSetting.setting_save(request) 

            # 2. 저장 후, 각 모듈의 'setting_save_after' 실행
            for module in P.module_list:
                module.setting_save_after(change_list) 
            return jsonify(ret)
모델 (model_setting.py - 프레임워크 제공)

setting_save(req) 메서드가 실제 DB 작업을 수행합니다.

req.form.items()를 순회하며 key와 value를 가져옵니다.

global로 시작하거나 scheduler 같은 시스템 예약어는 건너뜁니다.

ModelSetting.get(key) != value : 값이 변경되었는지 확인합니다.

값이 변경된 경우에만 DB의 value를 업데이트하고 change_list에 key를 추가합니다.

저장 후 로직 (mod_base.py)

setting_save_after(self, change_list) 메서드가 호출됩니다.

플러그인은 change_list를 보고 특정 설정이 변경되었을 때 추가 작업을 수행할 수 있습니다. (예: 스케줄러 재시작)

Python

# mod_base.py
def setting_save_after(self, change_list):
    P.logger.debug(f"설정 저장 완료. 변경된 키: {change_list}")

    # 만약 스케줄링 간격이 변경되었다면
    if f'{self.name}_interval' in change_list:
        P.logger.info("스케줄링 간격이 변경되어 스케줄러를 재시작합니다.")
        # P.logic은 스케줄러를 중지/시작하는 헬퍼 함수를 제공
        P.logic.scheduler_stop(self.name)
        P.logic.scheduler_start(self.name)
2. ModelBase를 이용한 커스텀 데이터 다루기
로그, 데이터 목록 등 Key-Value로 저장하기 어려운 정형 데이터는 ModelBase를 상속받아 별도 테이블을 만듭니다.

1. 모델 정의 (model.py)
ModelBase (lib/plugin/model_base.py)를 상속받습니다.

P = P : ModelBase에 내장된 로거(cls.P.logger) 등이 올바르게 동작하려면 setup.py의 P 객체를 클래스 변수로 할당해야 합니다.

__bind_key__ = P.package_name : 매우 중요. 이 모델이 plugin_name.db 파일을 사용하도록 SQLAlchemy에 알려줍니다.

Python

# model.py
from .setup import P # setup.py의 P 인스턴스 임포트
from plugin import ModelBase
from sqlalchemy import or_ # 검색 쿼리용

class MyLogTable(ModelBase):
    P = P # 로거 등을 위해 P 인스턴스 연결
    __tablename__ = f'{P.package_name}_log_table' # DB 테이블명
    __bind_key__ = P.package_name # 이 모델이 사용할 DB 바인딩

    # 테이블 컬럼 정의
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(10))
    message = db.Column(db.String)
    created_time = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, level, message):
        self.level = level
        self.message = message

    # ModelBase의 'make_query'를 오버라이딩하여 검색 기능 구현
    @classmethod
    def make_query(cls, req, order='desc', search='', option1='all', option2='all'):
        with F.app.app_context():
            query = F.db.session.query(cls)
            
            # 검색어 처리
            if search is not None and search != '':
                if search.find('|') != -1: # 여러 키워드 (OR)
                    conditions = []
                    for tt in search.split('|'):
                        if tt.strip() != '':
                            conditions.append(cls.message.like(f'%{tt.strip()}%'))
                    query = query.filter(or_(*conditions))
                else: # 단일 키워드 (AND)
                    query = query.filter(cls.message.like(f'%{search.strip()}%'))

            # 옵션 처리 (예: 로그 레벨)
            if option1 != 'all':
                query = query.filter(cls.level == option1)

            # 정렬
            if order == 'desc':
                query = query.order_by(db.desc(cls.id))
            else:
                query = query.order_by(cls.id)
            
            return query
2. 데이터 저장 (커스텀 AJAX 사용) 📤
커스텀 테이블 저장은 globalSettingSaveBtn을 사용하지 않습니다. 대신 커스텀 AJAX를 구현해야 합니다.

UI (..._feature_list.html)

macro.html의 setting_input_text_and_buttons 등을 사용하여 '저장' 버튼을 만듭니다.

HTML

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

  // 'process_ajax'의 'sub'로 'save_log'를, 
  // 폼 데이터(log_message_input)를 함께 전송
  $.ajax({
      url: '/{{ P.package_name }}/base/ajax/save_log', // /plugin_name/base/ajax/save_log
      type: 'POST',
      data: { 
          message: $('#log_message_input').val() 
      },
      success: function(response) {
          if (response.ret === 'success') {
              notify('로그 저장 완료', 'success');
              // (선택) 목록 새로고침
          } else {
              notify('저장 실패: ' + response.msg, 'warning');
          }
      }
  });
});
</script>
모듈 (mod_base.py)

process_ajax(self, sub, req) 메서드를 구현합니다.

sub 값이 save_log인 경우를 처리합니다.

MyLogTable 모델을 임포트하여 save() 합니다.

Python

# mod_base.py
from .model import MyLogTable # 정의한 모델 임포트

class ModuleBase(PluginModuleBase):
    # ... ( __init__, process_menu ) ...

    # 커스텀 AJAX 처리
    def process_ajax(self, sub, req):
        try:
            if sub == 'save_log':
                msg = req.form.get('message')
                if msg:
                    # 1. 모델 인스턴스 생성
                    new_log = MyLogTable(level='info', message=msg)
                    # 2. DB에 저장 (ModelBase의 save() 메서드)
                    new_log.save()
                    return jsonify({'ret': 'success'})
                else:
                    return jsonify({'ret': 'error', 'msg': '메시지 없음'})

        except Exception as e:
            P.logger.error(f"AJAX error: {str(e)}")
            return jsonify({'ret': 'error', 'msg': str(e)})
3. 데이터 목록 표시 (web_list 활용) 🔄
ModelBase에는 web_list라는 강력한 목록 관리 기능이 내장되어 있습니다.

모듈 (mod_base.py)

__init__에서 self.web_list_model 변수에 목록으로 사용할 모델 클래스(MyLogTable)를 연결합니다. 이것이 핵심입니다.

Python

# mod_base.py
from .model import MyLogTable

class ModuleBase(PluginModuleBase):
    def __init__(self, P):
        super(ModuleBase, self).__init__(P, name='base', first_menu='setting')
        self.db_default = { ... }

        # 1. 이 모듈이 'web_list' 기능으로 사용할 모델을 지정
        self.web_list_model = MyLogTable
라우터 (route.py - 프레임워크 제공)

/ajax/<module_name>/web_list 엔드포인트가 이미 정의되어 있습니다.

이 엔드포인트는 module.web_list_model.web_list(request)를 자동으로 호출합니다.

web_list 메서드는 req.form에서 page, keyword, order 등을 자동으로 추출합니다.

MyLogTable.make_query (우리가 오버라이딩한 메서드)를 호출하여 쿼리를 생성합니다.

페이징 처리된 데이터 목록(list)과 페이징 정보(paging)를 JSON으로 반환합니다.

UI (..._base_setting.html)

페이지 로드 시 또는 '검색' 버튼 클릭 시 /ajax/base/web_list를 호출하는 JavaScript를 작성합니다.

반환된 JSON 데이터를 파싱하여 ff_ui1.js의 j_row_start, j_col 등으로 HTML을 동적으로 생성하여 목록을 그립니다.

HTML

<h3>로그 목록</h3>
<div id="log_list_container">
    </div>
<div id="paging_container">
    </div>

<script>
$(document).ready(function() {
    // 페이지 로드 시 첫 페이지 로드
    load_list(1);
});

function load_list(page) {
    $.ajax({
        url: '/{{ P.package_name }}/base/ajax/web_list',
        type: 'POST',
        data: { 
            page: page,
            keyword: '', // (선택) 검색어
            option1: 'all' // (선택) 옵션
        },
        success: function(response) {
            // 1. 목록 그리기
            $('#log_list_container').empty();
            response.list.forEach(function(item) {
                let row = j_row_start('5'); // ff_ui1.js
                row += j_col('1', item.id);
                row += j_col('2', item.level);
                row += j_col('7', item.message);
                row += j_col('2', item.created_time);
                row += j_row_end();
                $('#log_list_container').append(row);
            });

            // 2. 페이징 그리기 (별도 함수 필요 - 생략)
            // response.paging 객체를 사용하여 페이징 UI 생성
        }
    });
}
</script>
이처럼 FlaskFarm은 **ModelSetting과 globalSettingSaveBtn**을 통해 '설정 페이지'를, **ModelBase와 web_list**를 통해 '데이터 목록 페이지'를 반자동으로 구현할 수 있는 강력한 프레임워크를 제공합니다.


1. 플러그인 아키텍처
FlaskFarm의 플러그인은 하나 이상의 모듈(Module) 로 구성됩니다.

모듈 (Module): 특정 기능 단위입니다. (예: 설정 페이지, 데이터 목록 페이지). PluginModuleBase 클래스를 상속받아 구현합니다.

플러그인 (Plugin): 하나 이상의 모듈을 묶은 패키지입니다. setup.py 파일이 이 모듈들을 등록하고 메뉴 구조를 정의합니다.

프레임워크 (Framework): 플러그인들을 로드하고 웹 인터페이스, DB, 스케줄러 등 공통 기능을 제공합니다.

2. 프로젝트 구조
권장되는 기본 디렉토리 구조입니다.

plugin_name/
├── __init__.py              # 패키지 초기화 (비어있어도 됨)
├── info.yaml                # 플러그인 메타데이터 (필수)
├── setup.py                 # 플러그인 설정 및 모듈 등록 (필수)
├── mod_base.py              # 'base' 모듈 (설정 페이지 등)
├── mod_feature.py           # 'feature' 모듈 (추가 기능)
├── model.py                 # SQLAlchemy DB 모델 (선택)
├── requirements.txt         # 의존성 패키지 (선택)
└── templates/               # HTML 템플릿 (필수)
    ├── plugin_name_base_setting.html
    └── plugin_name_feature_list.html
3. 핵심 파일 상세
info.yaml
플러그인의 정보를 정의합니다. (예: lib/system/info.yaml - 실제로는 없지만 create_plugin.py가 시스템 플러그인을 예외 처리함)

YAML

title: "플러그인 한글 이름"
version: "1.0.0"
package_name: "plugin_name" # 프로젝트 디렉토리명과 일치
developer: "개발자명"
description: "플러그인에 대한 간략한 설명"
home: "https://github.com/developer/plugin_name"
setup.py
플러그인의 진입점입니다. 프레임워크가 이 파일을 실행하여 플러그인을 초기화합니다. (참고: lib/system/setup.py)

Python

# -*- coding: utf-8 -*-
from plugin import * # create_plugin_instance, PluginModuleBase 등 임포트

# 1. 플러그인 기본 설정
setting = {
    'filepath' : __file__,       # 현재 파일 경로 (필수)
    'use_db': True,              # True로 설정 시 plugin_name.db 파일 생성
    'use_default_setting': True, # True로 설정 시 ModelSetting 사용 (권장)
    'home_module': 'base',       # /plugin_name 접속 시 리다이렉트할 모듈명
    'menu': {
        'uri': __package__,
        'name': '플러그인명', # 사이드바에 보일 이름
        'list': [
            # 'base' 모듈 메뉴 정의
            {'uri': 'base', 'name': '설정', 'list': [
                {'uri': 'setting', 'name': '기본 설정'},
                {'uri': 'log', 'name': '로그'}
            ]},
            # 'feature' 모듈 메뉴 정의
            {'uri': 'feature', 'name': '기능', 'list': [
                {'uri': 'list', 'name': '목록'}
            ]}
        ]
    },
    'default_route': 'normal', # 'normal' 또는 'single'
}

# 2. 플러그인 인스턴스 생성
P = create_plugin_instance(setting)

try:
    # 3. 모듈 임포트 및 등록
    from .mod_base import ModuleBase
    from .mod_feature import ModuleFeature
    
    P.set_module_list([ModuleBase, ModuleFeature])

except Exception as e:
    P.logger.error(f'Exception:{str(e)}')
    P.logger.error(traceback.format_exc())

# 4. (선택) ModelSetting 참조 변수 생성
# 다른 모듈에서 from .setup import PluginModelSetting 형태로 사용 가능
PluginModelSetting = P.ModelSetting 
mod_*.py (모듈 클래스)
실제 기능이 구현되는 파일입니다. PluginModuleBase를 상속받습니다. (참고: lib/system/mod_setting.py)

Python

# mod_base.py
from plugin import PluginModuleBase
from .setup import P # setup.py에서 생성한 P 인스턴스

class ModuleBase(PluginModuleBase):
    def __init__(self, P):
        # 1. 부모 클래스 초기화
        # P: 플러그인 인스턴스
        # name: 모듈명 (uri와 일치해야 함. 예: 'base')
        # first_menu: 이 모듈의 하위 메뉴 중 기본으로 보여줄 메뉴 (예: 'setting')
        super(ModuleBase, self).__init__(P, name='base', first_menu='setting')
        
        # 2. 이 모듈에서 사용할 기본 설정값 정의
        # ModelSetting에 값이 없을 경우 이 값으로 자동 초기화됨
        self.db_default = {
            f'{self.name}_auto_start': 'False',
            f'{self.name}_interval': '10',
            'api_key': 'default_api_key'
        }

    # 3. 필수 구현 메서드 (process_menu)
    def process_menu(self, page, req):
        # page: 하위 메뉴 uri (예: 'setting')
        # req: Flask request 객체
        try:
            # ModelSetting 값들을 딕셔너리로 가져와 템플릿에 전달
            arg = P.ModelSetting.to_dict()
            
            # 스케줄러 상태 추가 (macro.html의 스케줄러 버튼용)
            arg['is_include'] = F.scheduler.is_include(self.get_scheduler_name())
            arg['is_running'] = F.scheduler.is_running(self.get_scheduler_name())
            
            # 템플릿 렌더링
            # 규칙: {package_name}_{module_name}_{page}.html
            return render_template(f'{P.package_name}_{self.name}_{page}.html', arg=arg)
        except Exception as e:
            P.logger.error(f'Exception:{str(e)}')
            P.logger.error(traceback.format_exc())
            return "Error"

    # 4. (선택) AJAX/커맨드 처리 메서드
    def process_ajax(self, sub, req):
        # sub: AJAX 요청의 마지막 경로 (예: /ajax/base/custom_ajax)
        try:
            if sub == 'custom_ajax':
                data = req.form.to_dict()
                P.logger.debug(f"Custom AJAX 호출됨: {data}")
                return jsonify({'ret': 'success', 'msg': '커스텀 AJAX 성공'})
        except Exception as e:
            P.logger.error(f'Exception:{str(e)}')
            return jsonify({'ret': 'error', 'msg': str(e)})

    # 5. (선택) 스케줄링 메서드
    def scheduler_function(self):
        P.logger.info("스케줄러가 실행되었습니다.")
        # 주기적으로 실행할 작업 구현
model.py (데이터베이스 모델)
ModelSetting 외에 별도 테이블이 필요할 때 사용합니다. (참고: lib/plugin/model_base.py)

Python

# model.py
from plugin import ModelBase
from .setup import P # P 인스턴스 임포트

class CustomTable(ModelBase):
    __tablename__ = f'{P.package_name}_custom_table' # 테이블명
    __bind_key__ = P.package_name # 사용할 DB (플러그인 DB)

    # 컬럼 정의
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    created_time = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, name):
        self.name = name

    # ModelBase가 save(), get_by_id() 등 기본 CRUD 메서드 제공
4. 모듈 개발 (PluginModuleBase)
PluginModuleBase (lib/plugin/logic_module_base.py)는 플러그인 모듈의 핵심입니다.

초기화 (__init__)
super().__init__(P, name, first_menu)를 호출하여 모듈명과 첫 페이지를 설정하고, self.db_default를 정의하여 ModelSetting의 기본값을 설정합니다.

메뉴 처리 (process_menu)
setup.py의 메뉴 구조와 process_menu의 page 인자를 통해 적절한 HTML 템플릿을 렌더링합니다. P.ModelSetting.to_dict()로 설정값을 받아 arg 변수로 템플릿에 전달하는 것이 기본 패턴입니다.

AJAX 처리 (process_ajax, process_command)
FlaskFarm은 두 가지 방식의 AJAX 처리를 제공합니다. (참고: lib/plugin/route.py의 second_ajax 라우트)

process_ajax(self, sub, req):

URL: /ajax/{module_name}/{sub}

용도: 커스텀 AJAX 로직을 구현할 때 사용합니다.

JS 호출: globalSendCommand('{sub}', ...) 또는 직접 $.ajax 호출

process_command(self, command, arg1, arg2, arg3, req):

URL: /ajax/{module_name}/command

용도: req.form['command'] 값에 따라 분기 처리. (구버전 스타일)

JS 호출: globalSendCommand('command', '{command}', ...)

권장 방식: process_ajax를 사용하고 sub 값으로 기능을 분기하는 것이 더 명확합니다.

Python

# 예: /ajax/base/get_data
def process_ajax(self, sub, req):
    if sub == 'get_data':
        item_id = req.form.get('item_id')
        # 로직 처리...
        return jsonify({'item_id': item_id, 'value': 'some_data'})
스케줄링 (scheduler_function)
scheduler_function(self) 메서드를 정의하면, macro.html의 스케줄링 버튼(global_setting_scheduler_button)과 연동됩니다. 'On'으로 설정하면 setup.py의 P.ModelSetting에 저장된 {module_name}_interval 값(예: base_interval)을 주기로 이 함수를 실행합니다.

라이프사이클 메서드
plugin_load(self): 플러그인이 로드될 때 1회 실행됩니다. (참고: lib/plugin/logic.py의 plugin_load)

plugin_unload(self): 플러그인이 언로드될 때 실행됩니다.

setting_save_after(self, change_list): 설정 저장 후 변경된 키 목록(change_list)과 함께 호출됩니다.

migration(self): plugin_load 시 실행됩니다. DB 스키마 변경 등 버전 업그레이드 로직을 넣습니다.

5. 데이터베이스 사용
설정 저장 (ModelSetting)
플러그인의 모든 설정은 ModelSetting (lib/plugin/model_setting.py)을 통해 Key-Value 형태로 플러그인 고유의 DB(plugin_name.db)에 저장됩니다.

저장: P.ModelSetting.set(key, value)

조회: P.ModelSetting.get(key)

타입별 조회: P.ModelSetting.get_int(key), P.ModelSetting.get_bool(key)

전체 조회: P.ModelSetting.to_dict() (템플릿 전달 시 유용)

HTML 연동: templates에서 macros.setting_input_text 등 매크로 사용 시 id와 name이 ModelSetting의 key와 일치하면 자동으로 값이 바인딩됩니다.

커스텀 DB 모델 (ModelBase)
Key-Value가 아닌 정형 데이터(예: 로그, 목록)는 ModelBase (lib/plugin/model_base.py)를 상속받아 커스텀 모델을 만듭니다.

Python

# model.py
from .setup import P
from plugin import ModelBase

class LogTable(ModelBase):
    P = P # 로거 등을 사용하기 위해 P 인스턴스 연결
    __tablename__ = f'{P.package_name}_log'
    __bind_key__ = P.package_name

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String)
    created_time = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, message):
        self.message = message

# 사용 예시
from .model import LogTable
new_log = LogTable("새로운 로그 메시지")
new_log.save() # DB에 저장

all_logs = LogTable.get_list() # 전체 조회
log_1 = LogTable.get_by_id(1) # ID로 조회
6. UI 개발 (HTML/Jinja2/JS)
템플릿 명명 규칙
{package_name}_{module_name}_{page}.html (예: plugin_name_base_setting.html)

이 규칙을 따라야 process_menu에서 render_template 호출 시 정상적으로 파일을 찾을 수 있습니다.

macro.html 활용 (핵심)
FlaskFarm은 lib/framework/templates/macro.html에 정의된 Jinja2 매크로를 통해 UI를 일관되게 구성합니다. HTML을 직접 작성하기보다 매크로 사용을 강력히 권장합니다.

주요 매크로:

{{ macros.m_button_group([...]) }}: 버튼 그룹을 생성합니다.

{{ macros.setting_input_text(id, left, value, desc) }}: 텍스트 입력 필드를 생성합니다.

id: ModelSetting의 key와 일치시킵니다.

left: 좌측 라벨 텍스트

value: arg.id (예: arg.api_key)

desc: 하단 설명

{{ macros.setting_checkbox(id, left, value, desc) }}: 토글 스위치 형태의 체크박스를 생성합니다. (value에 arg.auto_start 등 전달)

{{ macros.setting_input_textarea(id, left, value, row, desc) }}: 여러 줄 텍스트 입력

{{ macros.setting_select(id, title, options, value, desc) }}: 선택 드롭다운

{{ macros.global_setting_scheduler_button(is_include, is_running) }}: 스케줄러 버튼 (가장 중요)

예시 (system_setting_basic.html 참고):

HTML

{% extends "base.html" %}
{% block content %}

{{ macros.m_button_group([['globalSettingSaveBtn', '설정 저장']])}}
{{ macros.m_hr() }}

<form id='setting' name='setting'>
  {{ macros.setting_input_text_and_buttons(
      'ddns', 
      'DDNS', 
      [['ddns_test_btn', '테스트']], 
      value=arg['ddns'], 
      desc=['외부에서 사용할 DDNS 주소']
  )}}

  {{ macros.setting_checkbox(
      'restart_notify', 
      '시작시 알림', 
      value=arg['restart_notify'], 
      desc=['시스템 시작 시 알림을 보냅니다.']
  )}}
</form>

<script type="text/javascript">
// 4. 커스텀 버튼 (ddns_test_btn) 이벤트 처리
$("body").on('click', '#ddns_test_btn', function(e){ 
  e.preventDefault();
  // /ajax/system/setting/command 로 요청
  // command: ddns_test, arg1: $('#ddns').val()
  globalSendCommand('ddns_test', $('#ddns').val()); 
});
</script>    
{% endblock %}
JavaScript (ff_ui1.js) 활용
lib/framework/static/js/ff_ui1.js에는 UI 생성을 위한 헬퍼 함수들이 있습니다. (예: j_button, j_row_start, j_col 등) 동적으로 테이블이나 목록을 생성할 때 유용합니다.

AJAX 통신 (Global 버튼 연동)
base.html에 포함된 ff_global1.js는 macro.html의 'Global' 버튼들과 연동됩니다.

globalSettingSaveBtn (설정 저장):

form[id="setting"]의 모든 데이터를 직렬화하여 /ajax/system/setting_save (시스템 플러그인의 경우) 또는 /ajax/{plugin_name}/setting_save로 전송합니다.

ModelSetting.setting_save(req)가 호출되어 값이 DB에 저장됩니다.

globalSchedulerSwitchBtn (스케줄링 On/Off):

/ajax/{module_name}/scheduler로 scheduler=true/false 값을 전송합니다.

P.logic.scheduler_start(module_name) 또는 scheduler_stop(module_name)이 호출됩니다.

global_one_execute_sub_btn (1회 실행):

/ajax/{module_name}/one_execute로 요청합니다.

P.logic.one_execute(module_name)가 호출되어 scheduler_function()을 1회 실행합니다.

커스텀 AJAX 호출: globalSendCommand(command, arg1, arg2, arg3) 함수를 사용하면 현재 모듈의 process_command로 요청을 보낼 수 있습니다. (예: system_setting_basic.html의 ddns_test_btn) 또는 process_ajax에 정의된 sub를 사용해 직접 $.ajax를 호출할 수도 있습니다.

7. Celery 사용
가이드 초안의 내용이 정확합니다. 시간이 오래 걸리는 작업(I/O, API 호출)은 반드시 Celery 태스크로 분리하여 메인 스레드를 차단하지 않도록 해야 합니다.

Python

# mod_feature.py
from framework import celery
from .setup import P

class ModuleFeature(PluginModuleBase):
    # ... (init, process_menu 등) ...

    def scheduler_function(self):
        P.logger.debug("Celery 작업 요청")
        if F.config['use_celery']:
            # 비동기 호출
            self.task.apply_async()
        else:
            # Celery 미사용 시 직접 실행 (테스트용)
            self.task()

    @staticmethod
    @celery.task
    def task():
        """
        실제 작업 로직 (Celery 워커에서 실행됨)
        주의: 이 함수는 P 인스턴스나 self에 접근할 수 없습니다.
        필요한 값은 인자로 전달받아야 합니다.
        설정값 조회가 필요하면 ModelSetting.get()을 사용해야 합니다.
        """
        from .setup import PluginModelSetting # task 내부에서 임포트
        
        api_key = PluginModelSetting.get('api_key')
        P.logger.info(f"Celery 작업 실행 중... API Key: {api_key}")
        # ... (시간이 오래 걸리는 작업) ...
        P.logger.info("Celery 작업 완료")
8. 디버깅 및 배포
디버깅
로그 확인: 플러그인 로그는 data/log/{plugin_name}.log 파일에 저장됩니다.

로그 레벨 변경: [설정] > [일반설정] > [기본] > [로그 레벨]을 'DEBUG'로 변경합니다.

AJAX 오류: 브라우저 개발자 도구(F12)의 [Network] 탭에서 AJAX 요청이 404 또는 500 오류를 반환하는지 확인합니다.

템플릿 오류: plugin_name_module_name 텍스트만 보인다면 process_menu가 템플릿을 렌더링하는 데 실패한 것입니다. (파일 경로, arg 변수 등 확인)

배포
requirements.txt에 플러그인이 의존하는 Python 패키지를 명시합니다. (Flask, Celery 등 프레임워크 기본 내장 패키지는 제외)

프로젝트 전체를 zip 파일로 압축하거나 GitHub 저장소에 푸시합니다.

FlaskFarm의 [설정] > [플러그인] > [설치]에서 해당 파일을 업로드하거나 Git URL을 입력하여 설치합니다.