from uvmcc import __version__

from typing import Callable

import chess
import discord

import dotenv
import logging
import os
import berserk


# Discord bot token
dotenv.load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Discord users to mention for bugs (right click on profile in Discord, "Copy User ID")
BUG_FIXERS = {
    'Cubigami#3114': '397943957625110540',
}

# Colors for Discord embed messages
LICHESS_BROWN_COLOR = discord.Color(0xB58863)
ACTION_REQUESTED_COLOR = discord.Color.blurple()
ACTION_SUCCEEDED_COLOR = discord.Color.green()
ACTION_FAILED_COLOR = discord.Color.red()

# Berserk client session
BERSERK_CLIENT = berserk.Client()

# Logging stuff
LOG_FILENAME = '.uvmcc.log'
LOGGING_LEVEL = logging.DEBUG
DISCORD_LOG_FILENAME = '.discord.log'
DISCORD_LOGGING_LEVEL = logging.DEBUG

# Explicit type annotations
SanStrT = str
UciStrT = str

# Other
LINK_TO_CODE = 'https://github.com/jacksonthall22/UVMCC-Discord-Bot'
EMBED_FOOTER = f'♟  I\'m a bot, beep boop  ♟  Click my icon for the code  ♟  v{__version__}  ♟'
LICHESS_GAME_LINK: Callable[[str, chess.Color], str] \
    = lambda game_id, color: f'https://lichess.org/{game_id}/{chess.COLOR_NAMES[color]}'
LICHESS_BIO_LINK: Callable[[str], str] \
    = lambda username: f'https://lichess.org/@/{username}'
