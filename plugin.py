# -*- coding: utf-8 -*-
import traceback
from framework.plugin import PluginBase
from framework import app, db

class P(PluginBase):
    def __init__(self, *args, **kwargs):
        super(P, self).__init__(*args, **kwargs)

P = P()

# setup.py에서 이 P 인스턴스를 임포트하여 설정할 것입니다.