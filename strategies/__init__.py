# -*- coding: utf-8 -*-
"""
7split_checklist_21 Plugin - Strategies Module
투자 전략 모듈
"""
import os
import importlib
from strategies.base_strategy import BaseStrategy

AVAILABLE_STRATEGIES = {}

def _discover_strategies():
    """Dynamically discover and import strategies."""
    global AVAILABLE_STRATEGIES
    if AVAILABLE_STRATEGIES:
        return

    strategies_dir = os.path.dirname(__file__)
    for filename in os.listdir(strategies_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = f'strategies.{filename[:-3]}'
            module = importlib.import_module(module_name)
            for item_name in dir(module):
                item = getattr(module, item_name)
                if isinstance(item, type) and issubclass(item, BaseStrategy) and item is not BaseStrategy:
                    AVAILABLE_STRATEGIES[item().strategy_id] = item

_discover_strategies()
def get_strategy(strategy_id):
    """
    전략 ID로 전략 인스턴스 가져오기
    
    Args:
        strategy_id (str): 전략 ID
    
    Returns:
        BaseStrategy: 전략 인스턴스 또는 None
    """
    strategy_class = AVAILABLE_STRATEGIES.get(strategy_id)
    
    if strategy_class:
        return strategy_class()
    
    return None


def get_all_strategies():
    """
    모든 사용 가능한 전략 목록
    
    Returns:
        dict: {strategy_id: strategy_instance}
    """
    return {
        strategy_id: strategy_class()
        for strategy_id, strategy_class in AVAILABLE_STRATEGIES.items()
    }


def get_strategies_info():
    """
    모든 전략의 정보 목록
    
    Returns:
        list: [strategy_info_dict, ...]
    """
    strategies = get_all_strategies()
    return [strategy.get_info() for strategy in strategies.values()]


__all__ = [
    'BaseStrategy',
    'SevenSplit21Strategy',
    'SevenSplitMiniStrategy',
    'DividendStrategy',
    'ValueInvestingStrategy',
    'AVAILABLE_STRATEGIES',
    'get_strategy',
    'get_all_strategies',
    'get_strategies_info'
]