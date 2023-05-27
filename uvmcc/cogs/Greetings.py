import discord
from discord.ext import commands


class Greetings(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(name='hello', description='Says hi!')
    async def hello(self, ctx: discord.ApplicationContext):
        await ctx.respond(f'Hi, {ctx.author}!')

    @discord.slash_command() # we can also add application commands
    async def goodbye(self, ctx):
        await ctx.respond('Goodbye!')

    @discord.user_command(description='test description!')
    async def greetings(self, ctx: discord.ApplicationContext, member: discord.Member):
        await ctx.respond(f'{ctx.author.mention} says hello to {member.mention}!')

def setup(bot: discord.Bot):
    bot.add_cog(Greetings(bot))
