from constants import TOKEN
import discord


bot = discord.Bot()


@bot.event
async def on_ready():
    print(f'{bot.user} is ready and online!')

# you'll have to manually add the manually created Slash Command group
bot.add_application_command(math)

bot.run(TOKEN)
