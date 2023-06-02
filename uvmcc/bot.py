import uvmcc.constants as C
import uvmcc.database_utils as D
from uvmcc.uvmcc_logging import logger

import discord


bot = discord.Bot()


@bot.event
async def on_ready():
    logger.info(f'=============' + '='*len(str(bot.user)))
    logger.info(f'Logged in as {bot.user}')
    logger.info(f'=============' + '='*len(str(bot.user)))

    await D.init_dbs()

    print(f'{bot.user} is ready and online!')


COGS = [
    'Greetings',
    'Show',
    'UserManagement',
    'Voice'
]
for cog in COGS:
    bot.load_extension(f'cogs.{cog}')


try:
    bot.run(C.BOT_TOKEN)  # run the bot with the token
except Exception as e:
    logger.error(f'bot.run() FAILED: {type(e).__name__}. Stack trace:\n{e}')
