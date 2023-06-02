# https://github.com/Pycord-Development/pycord/issues/2043#issuecomment-1536563439

import discord
from discord.ext import commands
from uvmcc.custom_sinks_core import StreamSink


class Voice(commands.Cog):

    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.connections = {}
        self.stream_sink = StreamSink()

    @commands.Cog.listener()
    async def on_voice_state_update(self,
                                    member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState):
        from icecream import ic


        # ic(member)
        # ic(self.bot.user)

        # if the member is the bot, ignore it.
        if member == self.bot.user:
            return

        # if the member is not in the same guild as the bot, ignore it.
        if member.guild not in self.bot.guilds:
            return
        # if member.guild != self.bot.voice_clients[0].guild:
        #     return

        # if the member just left a voice channel, ignore it.
        if not after.channel:
            return

        # if the member is not in the same voice channel as the bot, ignore it.
        ic(self.bot.voice_clients)
        # if after.channel != self.bot.voice_clients[0].channel:
        #     return

        # send a message to the channel the member is in.
        if before.requested_to_speak_at != after.requested_to_speak_at:
            if after.requested_to_speak_at:
                await after.channel.send('You requested to speak')
            else:
                await after.channel.send('Your request to speak was accepted')

        if before.self_mute != after.self_mute:
            if after.self_mute:
                await after.channel.send('You muted yourself')
            else:
                await after.channel.send('You unmuted yourself')

        if before.mute != after.mute:
            if after.mute:
                await after.channel.send('The server muted you')
            else:
                await after.channel.send('The server unmuted you')

        if before.self_deaf != after.self_deaf:
            if after.self_deaf:
                await after.channel.send('You deafened yourself')
            else:
                await after.channel.send('You undeafened yourself')

        if before.deaf != after.deaf:
            if after.deaf:
                await after.channel.send('The server deafened you')
            else:
                await after.channel.send('The server undeafened you')

    @discord.slash_command(name='rec', description='Starts recording in your voice channel')
    async def rec(self, ctx: discord.ApplicationContext):
        voice = ctx.author.voice

        if not voice:
            return await ctx.respond('You aren\'t in a voice channel, please connect to one first.')

        # connect to the voice channel the author is in.
        self.stream_sink.set_user(ctx.author.id)
        vc = await voice.channel.connect()
        # updating the cache with the guild and channel.
        self.connections.update({ctx.guild.id: vc})

        vc.start_recording(
            self.stream_sink,               # the sink type to use.
            Voice.rec_finished_callback,    # callback when user stops recording.
            ctx.channel                     # the channel to disconnect from.
        )

        await ctx.respond('Started listening.')

    # our voice client already passes these in.
    @staticmethod
    async def rec_finished_callback(sink: discord.sinks,
                                    channel: discord.TextChannel,
                                    *args):
        await sink.vc.disconnect()  # disconnect from the voice channel.
        print('Stopped listening.')

        # we can now access the audio data from the sink.
        # Use it with replicate.run() to get the transcript.
        import replicate
        output = replicate.run(
            'openai/whisper:e39e354773466b955265e969568deb7da217804d8e771ea8c9cd0cef6591f8bc',
            input={
                'audio': open('output1.mp3', 'rb'),
                'language': 'en',
                # 'initial_prompt': 'You are about to hear a chess move in Standard Algebraic Notation (SAN). '
                #                   'For example, I might say "bishop F 3", "knight B 4", "H 4", '
                #                   '"E takes F 5" or "pawn takes f 5", "castles", or "F 1 equals queen". '
                #                   'Please provide the transcript, and make sure not to mistake square names '
                #                   'for words (e.g. "B 4" sounds like "before").',
                'initial_prompt': 'Bishop F 3. Knight B 4. H 4. E takes F 5. Pawn takes E 2. Castles. '
                                  'F 1 equals queen. ',
            },
        )
        await channel.send(output)

    @discord.slash_command(name='stop_rec', description='Stops recording')
    async def stop_rec(self, ctx: discord.ApplicationContext):
        await ctx.response.defer(invisible=True)
        if ctx.guild.id not in self.connections:
            # respond with this if we aren't listening
            return await ctx.respond(f'I am currently not listening here.')

        vc = self.connections[ctx.guild.id]
        # stop recording, and call the callback (rec_finished_callback).
        vc.stop_recording()
        del self.connections[ctx.guild.id]  # remove the guild from the cache.


def setup(bot: discord.Bot):
    bot.add_cog(Voice(bot))
