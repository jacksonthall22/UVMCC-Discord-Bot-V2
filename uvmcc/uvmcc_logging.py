import uvmcc.constants as C

import logging


'''
Formatter (can be used by multiple loggers)
'''
_LOGGING_FORMAT = '%(asctime)s:%(levelname)s:%(name)s - %(message)s'
_FORMATTER = logging.Formatter(_LOGGING_FORMAT)

'''
Discord/Pycord Logger
https://docs.pycord.dev/en/stable/logging.html#logging-setup
'''
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(C.LOGGING_LEVEL)
discord_handler = logging.FileHandler(filename=C.DISCORD_LOG_FILENAME, encoding='utf-8', mode='w')
discord_handler.setFormatter(_FORMATTER)
discord_logger.addHandler(discord_handler)

'''
UVMCC Logger 
'''
logger = logging.getLogger(__name__)
logger.setLevel(C.LOGGING_LEVEL)
handler = logging.FileHandler(filename=C.LOG_FILENAME, encoding='utf-8', mode='a')
handler.setFormatter(_FORMATTER)
logger.addHandler(handler)
