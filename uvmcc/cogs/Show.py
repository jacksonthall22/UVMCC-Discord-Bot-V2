import uvmcc.constants as C
import uvmcc.utils as U
import uvmcc.error_msgs as E
import uvmcc.database_utils as D
from uvmcc.uvmcc_logging import logger

from typing import Dict, List, Any

import chess
import chess.pgn
import discord
from discord.ext import commands

import io
import re


class Show(commands.Cog):
    STREAM_GAME_MOVES_AFTER_SHOW = True
    EMBED_BOARD_SIZE_PX = 500

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @staticmethod
    async def _show_usernames(ctx: discord.ApplicationContext,
                              e: discord.Embed,
                              usernames: List[str],
                              *,
                              stream_new_moves: bool = False,
                              only_live: bool = False):
        user_statuses = C.BERSERK_CLIENT.users.get_realtime_statuses(*usernames, with_game_ids=True)
        playing = [d for d in user_statuses if d.get('playing')]
        online = [d for d in user_statuses if not d.get('playing') and d.get('online')]
        offline = [d for d in user_statuses if not d.get('playing') and not d.get('online')]

        featured_game_description = ''


        if playing:
            '''
            Highlight a featured game - whichever live game has 
            the highest rated player (on either side)

            If two players in ``usernames`` are playing each other, max rating of
            either player will be the same, so the sort key also sorts by the rating
            of the player (to show the game from the higher-rated player's POV).
            '''

            def _max_rating(live_game_data: dict) -> int:
                """ Get the higher rating of the white/black side. """
                return max(live_game_data['players']['white']['rating'],
                           live_game_data['players']['black']['rating'])

            def _username_rating(live_game_data: dict, username: str) -> int:
                """ Get the rating of the side with the given username. """
                user_color = chess.COLOR_NAMES[live_game_data['players']['white']['user']['name'] == username]
                return live_game_data['players'][user_color]['rating']

            # Note - relying here on the berserk api preserving order
            # between input ids list and output data list
            live_games_data = dict(zip([d['name'] for d in playing],
                                       [*C.BERSERK_CLIENT.games.export_multi(*(d['playingId'] for d in playing))]))

            # _up in lambda below is (username_proper_caps, pgn)
            live_games_data: Dict[str, Dict[str, Any]] \
                = dict(sorted(live_games_data.items(),
                              key=lambda _up: (_max_rating(_up[1]), _username_rating(_up[1], _up[0])),
                              reverse=True))
            playing.sort(key=lambda _u: [*live_games_data.keys()].index(_u['name']))

            ''' Set the discord embed field '''
            lines = []
            for i, (username, live_game_data) in enumerate(live_games_data.items()):
                shown_below = 'Shown below - ' if i == 0 else ''
                url = C.LICHESS_GAME_LINK(live_game_data['id'])

                time_ctrl = U.format_lichess_time_control(live_game_data['clock'])

                if live_game_data['variant'] == 'standard':
                    variant = ''
                else:
                    variant = f' {live_game_data["variant"].capitalize()}'

                lines.append(f'**`{username}`**: Playing {time_ctrl}{variant} on Lichess '
                             f'({shown_below}[Spectate]({url}))')

            # To be able to update the ``discord.EmbedField`` when streaming subsequent moves,
            # store a reference to the field and get its index in ``e.fields`` (a list)
            # TODO - update the footer description with result when game ends
            e.add_field(name='In Game  ⚔️', value='\n'.join(lines), inline=False)
            in_game_embed_field_idx = len(e.fields) - 1
            in_game_embed_field = e.fields[-1]
            in_game_embed_field_lines = lines

            ''' Set data about the featured player and their live game '''
            featured_player_status_data = playing[0]
            featured_player_username = featured_player_status_data['name']

            featured_game_data = live_games_data[featured_player_username]
            featured_game_id = featured_game_data['id']
            featured_game_obj = chess.pgn.read_game(io.StringIO(featured_game_data['moves'])) \
                                or chess.pgn.Game()  # read_game() -> None if reading empty string

            featured_game_fen = featured_game_obj.end().board().fen()
            featured_game_orientation = chess.COLOR_NAMES[
                featured_game_obj.headers['White'] == featured_player_username]
            if featured_game_obj.end().move is None:
                # No moves in this game yet
                featured_game_last_move_uci = None
            else:
                featured_game_last_move_uci = featured_game_obj.end().move.uci()
            featured_game_img = U.get_board_image_url(featured_game_fen,
                                                      orientation=featured_game_orientation,
                                                      last_move_uci=featured_game_last_move_uci,
                                                      size=Show.EMBED_BOARD_SIZE_PX)
            e.set_image(url=featured_game_img)

            # Set the string that will be prepended to embed's footer at end of function
            w_username = featured_game_data['players']['white']['user']['name']
            b_username = featured_game_data['players']['black']['user']['name']
            w_elo = featured_game_data['players']['white']['rating']
            b_elo = featured_game_data['players']['black']['rating']
            w_title = featured_game_data['players']['white']['user'].get('title')
            b_title = featured_game_data['players']['black']['user'].get('title')
            featured_game_description = f'{{}}{f"{w_title} " if w_title else ""}{w_username} ({w_elo}{{}}) ' \
                                        f'- {f"{b_title} " if b_title else ""}{b_username} ({b_elo}{{}}) ' \
                                        f'on Lichess\n\n'
        elif only_live:
            top_live_username = C.BERSERK_CLIENT.tv.get_current_games()['Blitz']['user']['name']
            e.add_field(name='No players with live games :(',
                        value=f'How about `/watch player:{top_live_username}`?')

        if online and not only_live:
            lines = [f'**`{u["name"]}`**: Active on Lichess' for u in online]
            e.add_field(name='Active  ⚡', value='\n'.join(lines), inline=False)

        if offline and not only_live:
            lines = [f'**`{u["name"]}`**' for u in offline]
            e.add_field(name='Offline  💤', value='\n'.join(lines), inline=False)

        e.set_footer(text=featured_game_description.format('', '', '') + C.EMBED_FOOTER)

        # await ctx.respond(embed=e)
        msg = await ctx.respond(embed=e)

        if not stream_new_moves or not playing:
            return

        '''
        After response is sent, stream featured game moves
        and update the embed image until game is over
        '''
        try:
            featured_game_obj
            try:
                featured_game_id
                featured_game_fen
                featured_game_last_move_uci
                featured_game_orientation
                featured_player_username
                in_game_embed_field
                in_game_embed_field_lines
                in_game_embed_field_idx
            except NameError:
                print(E.INTERNAL_ERROR_MSG + 'Failed to set all featured_game_... vars')
                return
        except NameError:
            print('test: no featured_game_obj')
            return

        # We want to skip packets until we get to the one where the FEN and last move are
        # the same as in the initial packet (**not** until it's the same as the FEN set in the
        # current embed image - ex. for <=bullet games, maybe several moves have been played
        # since the last API call, and we don't want to update the image for every one of those)
        async for packet, is_new_move in U.stream_moves_lichess(featured_game_id):

            if not is_new_move:
                continue

            # Update the embed image
            new_board_img_url = U.get_board_image_url(packet['fen'],
                                                      orientation=featured_game_orientation,
                                                      last_move_uci=packet.get('lm'),
                                                      size=Show.EMBED_BOARD_SIZE_PX)
            e.set_image(url=new_board_img_url)
            # await ctx.interaction.edit_original_response(embed=e)
            await msg.edit(embed=e)

        try:
            packet
        except NameError:
            return

        # At this point the game is over, and we have the last packet with info about result
        if packet.get('winner') is None:
            result = '1/2-1/2'
        elif packet['winner'] == 'white':
            result = '1-0'
        else:
            assert packet['winner'] == 'black'
            result = '0-1'

        if featured_game_orientation == packet.get('winner'):
            featured_player_won = True
            emoji = '<:winner:971525261835264081>'
        elif packet.get('winner') is None:
            featured_player_won = None
            if featured_game_orientation == 'white':
                emoji = '<:draw_white:971525015654789230>'
            else:
                emoji = '<:draw_black:971524998961434714>'
        else:
            featured_player_won = False
            if featured_game_orientation == 'white':
                emoji = '<:resign_white:971525080460951612>'
            else:
                emoji = '<:resign_black:971525057379721226>'

        # Update name and value in the appropriate EmbedField
        # https://github.com/lichess-org/lila/blob/master/ui/game/src/status.ts
        STATUS_ID_MAP = {
            25: ('Aborted',),
            30: ('{} got checkmated', '{} won by checkmate'),
            31: ('{} resigned', '{} won by resignation'),
            32: ('Draw by stalemate',),
            33: ('{} lost by timeout', '{} won by timeout'),
            34: ('Draw by repetition',),
            35: ('{} lost on time', '{} won on time'),
            36: ('{} lost due to cheating', '{} won, opponent cheated'),
            37: ('{} lost by forfeit', '{} won, opponent forfeited'),
            60: ('{} lost', '{} won'),

        }
        status_id = packet['status']['id']
        end_msg = STATUS_ID_MAP[status_id][featured_player_won or 0].format(featured_player_username)

        lines = []
        for i, line in enumerate(in_game_embed_field_lines):
            if 'Shown below - ' in line:
                line = re.sub(r'\(Shown below - \[.*?\]\((.*?)\)\)',
                              f'(Shown below - [{end_msg}](\\1))',
                              line)
                lines.append(line)
                lines.extend(in_game_embed_field_lines[i+1:])
                break
            lines.append(line)

        in_game_embed_field.name = f'Game Over {emoji}'
        in_game_embed_field.value = '\n'.join(lines)

        e.set_footer(text=featured_game_description.format(
            '',  # f'{result} - ',
            f'{packet["players"]["white"]["ratingDiff"]:+}' if packet.get('rated') else '',
            f'{packet["players"]["black"]["ratingDiff"]:+}' if packet.get('rated') else '')
                          + C.EMBED_FOOTER)

        return await msg.edit(embed=e)

    @staticmethod
    async def _get_usernames(ctx, player, site) -> List[str]:
        """
        Return a non-empty list of usernames to show in a response based on user's given arguments.

        We want a list ``usernames`` to search on Lichess/Chess.com. If user entered
        a value for ``player`` and it's not a Discord tag/ID, it should be interpreted
        as a chess username (so we can set ``usernames`` right away). For other cases,
        we need to do a ``db_query()`` to get the appropriate usernames.

        TODO: use ``site`` to handle Lichess/chess.com APIs differently.
        """
        if not player:
            # Show all players in db
            _, results = await D.db_query('SELECT username FROM ChessUsernames '
                                          'WHERE site = ?'
                                          'ORDER BY username',
                                          params=(U.SupportedSites.LICHESS,),
                                          auto_respond_on_fail=ctx)
            usernames = [e for e, in results]
            if not usernames:
                return await ctx.respond(f'There are no players in our database. Add yourselves with '
                                         f'`/add player:<username> site:<{"/".join(U.SupportedSites)}>`!')
        elif player.lower() == 'me':
            # Show chess accounts linked to the author's discord_id
            _, results = await D.db_query('SELECT username FROM ChessUsernames '
                                          'WHERE discord_id = ?',
                                          params=(str(ctx.author),),
                                          auto_respond_on_fail=ctx)
            usernames = [e for e, in results]
            if not usernames:
                return await ctx.respond(f'You don\'t have any chess usernames linked to your Discord '
                                         f'account in our database. Use `/add player:<username> '
                                         f'site:<{"/".join(U.SupportedSites)}>`, then '
                                         f'`/iam player:<username> site:<{"/".join(U.SupportedSites)}>` to link one!')
        elif U.is_valid_discord_tag(player):
            # Show one player by looking up chess accounts linked to their discord_id
            _, results = await D.db_query('SELECT username FROM ChessUsernames '
                                          'WHERE discord_id = ?',
                                          params=(player,),
                                          auto_respond_on_fail=ctx)
            usernames = [e for e, in results]
            if not usernames:
                return await ctx.respond(f'`{player}` doesn\'t have any chess usernames linked to their Discord '
                                         f'account in our database. They can use `/add player:<username> '
                                         f'site:<{"/".join(U.SupportedSites)}>`, then `/iam player:<username> '
                                         f'site:<{"/".join(U.SupportedSites)}>` to link one!')
        else:
            # Show one player by a chess username (not necessarily one in the db)
            usernames = [player]

        try:
            assert usernames, E.INTERNAL_ERROR_MSG + ' `usernames` should not be empty here'
        except AssertionError:
            logger.error(E.INTERNAL_ERROR_MSG, exc_info=True)
            return await ctx.respond(E.INTERNAL_ERROR_MSG)

        return usernames

    @discord.slash_command(name='show',
                           description='Show player statuses on Lichess (Chess.com support coming soon!)')
    async def show(self,
                   ctx: discord.ApplicationContext,
                   player: discord.Option(str,
                                          description='Enter a chess username, a Discord tag, or "me"') = None,
                   site: discord.Option(str,
                                        description='Which chess site?',
                                        choices=U.SUPPORTED_SITES_LIST) = None):
        e = discord.Embed(title='Lichess Player Statuses',
                          color=C.LICHESS_BROWN_HEX)
        e.set_author(name=self.bot.user.name,
                     url=C.LINK_TO_CODE)

        await ctx.response.defer(invisible=False)
        usernames = await Show._get_usernames(ctx, player, site)
        await Show._show_usernames(ctx,
                                   e,
                                   usernames,
                                   stream_new_moves=False,
                                   only_live=False)


    @discord.slash_command(name='watch',
                           description='Watch a game unfold live! (Might be buggy)')
    async def watch(self,
                    ctx: discord.ApplicationContext,
                    player: discord.Option(str,
                                           description='Enter a chess username, a Discord tag, or "me"') = None,
                    site: discord.Option(str,
                                         description='Which chess site?',
                                         choices=U.SUPPORTED_SITES_LIST) = None):
        e = discord.Embed(title='Watching Live',
                          color=C.LICHESS_BROWN_HEX)
        e.set_author(name=self.bot.user.name,
                     url=C.LINK_TO_CODE)

        await ctx.response.defer(invisible=False)
        usernames = await Show._get_usernames(ctx, player, site)
        await Show._show_usernames(ctx,
                                   e,
                                   usernames,
                                   stream_new_moves=True,
                                   only_live=True)


def setup(bot: discord.Bot):
    bot.add_cog(Show(bot))

