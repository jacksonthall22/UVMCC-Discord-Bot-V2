from uvmcc import __version__

from typing import Callable

import dotenv
import logging
import os
import berserk


# Discord bot token
dotenv.load_dotenv()
TOKEN = os.getenv('TOKEN')

# Client session
BERSERK_CLIENT = berserk.Client()

# Text strings
LINK_TO_CODE = 'https://github.com/jacksonthall22/UVMCC-Discord-Bot'
EMBED_FOOTER = f'♟  I\'m a bot, beep boop  ♟  Click my icon for the code  ♟  v{__version__}  ♟'
LICHESS_GAME_LINK: Callable[[str], str] = lambda game_id: f'https://lichess.org/{game_id}'

# Logging stuff
LOG_FILENAME = '.uvmcc.log'
LOGGING_LEVEL = logging.DEBUG
DISCORD_LOG_FILENAME = '.discord.log'
DISCORD_LOGGING_LEVEL = logging.DEBUG

# Explicit type annotations
SanStrT = str
UciStrT = str

# Database stuff
DB_FILE = 'data.db'

# Other
LICHESS_BROWN_HEX = 0xB58863
