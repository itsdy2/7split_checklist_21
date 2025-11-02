from unittest.mock import MagicMock
from . import logger

db = MagicMock()
socketio = MagicMock()

def get_logger():
    return MagicMock()