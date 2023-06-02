import uvmcc.database_utils as D

from typing import Dict

import discord
from discord.ext import commands


class BlindfoldChess(commands.Cog):

    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.active_games: Dict[discord.Member, ]

    @staticmethod
    async def _make_move(ctx: discord.ApplicationContext,
                         san: str | None = None,
                         uci: str | None = None) -> bool:
        """
        Make the move in the user's ongoing game. Return ``True`` iff
        the move was made successfully.
        """
        ...
