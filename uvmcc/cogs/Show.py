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


class Show(commands.Cog):
    STREAM_GAME_MOVES_AFTER_SHOW = True
    EMBED_BOARD_SIZE_PX = 100

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @staticmethod
    async def _show_usernames(ctx: discord.ApplicationContext,
                              e: discord.Embed,
                              usernames: List[str]):
        user_statuses = C.BERSERK_CLIENT.users.get_realtime_statuses(*usernames, with_game_ids=True)
        playing = [d for d in user_statuses if d.get('playing')]
        online = [d for d in user_statuses if not d.get('playing') and d.get('online')]
        offline = [d for d in user_statuses if not d.get('playing') and not d.get('online')]
        playing_ids = {d['name']: d['playingId'] for d in playing}

        featured_game_description = ''

        # Build playing section
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

            # Note - relying here on the berserk api preserving order of input ids in output
            live_games_data = dict(zip([d['name'] for d in playing],
                                       [*C.BERSERK_CLIENT.games.export_multi(*playing_ids.values())]))
            # live_games_data = {d['name']: next(C.BERSERK_CLIENT.games.export_ongoing_by_player(d['name'],
            #                                                                                    pgn_in_json=True))
            #                    for d in playing}
            # live_games_data = {u['name']: lichess.api.current_game(u['name'], pgnInJson=True)
            #                    for u in playing}

            # _up in lambda below is (username_proper_caps, pgn)
            live_games_data: Dict[str, Dict[str, Any]] \
                = dict(sorted(live_games_data.items(),
                              key=lambda _up: (_max_rating(_up[1]), _username_rating(_up[1], _up[0])),
                              reverse=True))
            playing.sort(key=lambda _u: [*live_games_data.keys()].index(_u['name']))
            # Sort the items of playing_ids by the order of playing
            playing_ids = dict(sorted(playing_ids.items(),
                                      key=lambda _up: [*live_games_data.keys()].index(_up[0])))

            ''' Set the discord embed field '''
            lines = []
            for i, u in enumerate(playing):
                shown_below = 'Shown below - ' if i == 0 else ''
                username = u['name']
                url = C.LICHESS_GAME_LINK(playing_ids[username])
                lines.append(f'**`{username}`**: Playing now on Lichess ({shown_below}[Spectate]({url}))')

            # To be able to update the ``discord.EmbedField`` when streaming subsequent moves,
            # store a reference to the field and get its index in ``e.fields`` (a list)
            # TODO - update the footer description with result when game ends
            e.add_field(name='In Game  ⚔', value='\n'.join(lines), inline=False)
            in_game_embed_field_idx = len(e.fields) - 1
            in_game_embed_field = e.fields[-1]

            ''' Set data about the featured player and their live game '''
            featured_player_status_data = playing[0]
            featured_player_username = featured_player_status_data['name']

            featured_game_data = live_games_data[featured_player_username]
            featured_game_id = featured_game_data['id']
            featured_game_obj = chess.pgn.read_game(io.StringIO(featured_game_data['moves']))

            featured_game_fen = featured_game_obj.end().board().fen()
            featured_game_orientation = chess.COLOR_NAMES[
                featured_game_obj.headers['White'] == featured_player_username]
            try:
                featured_game_last_move_uci = featured_game_obj.end().move.uci()
            except StopIteration:
                # No moves in this game yet
                featured_game_last_move_uci = None
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
            w_title = featured_game_data['players']['black']['title']
            b_title = featured_game_data['players']['white']['title']
            featured_game_description = f'{f"{w_title} " if w_title else ""}{w_username} ({w_elo}) ' \
                                        f'- {f"{b_title} " if b_title else ""}{b_username} ({b_elo}) ' \
                                        f'on Lichess\n\n'

        if online:
            lines = [f'**`{u["name"]}`**: Active on Lichess' for u in online]
            e.add_field(name='Active  ⚡', value='\n'.join(lines), inline=False)

        if offline:
            lines = [f'**`{u["name"]}`**' for u in offline]
            e.add_field(name='Offline  💤', value='\n'.join(lines), inline=False)

        e.set_footer(text=featured_game_description + C.EMBED_FOOTER)

        # await ctx.respond(embed=e)
        msg = await ctx.respond(embed=e)

        if not Show.STREAM_GAME_MOVES_AFTER_SHOW or not playing:
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
            except NameError:
                print('test: failed to set all featured_game_<...> vars')
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

    @discord.slash_command(name='show',
                           description='Show player statuses on Lichess (Chess.com support coming soon!)')
    async def show(self,
                   ctx: discord.ApplicationContext,
                   player: discord.Option(str,
                                          description='Enter a chess username, a Discord tag, or "me"') = None,
                   site: discord.Option(str,
                                        description='Which chess site?',
                                        choices=U.SUPPORTED_SITES_LIST) = None):
        # TODO: use ``site`` to handle Lichess/chess.com APIs differently

        e = discord.Embed(title='Lichess Player Statuses',
                          color=C.LICHESS_BROWN_HEX)
        e.set_author(name=self.bot.user.name,
                     url=C.LINK_TO_CODE)
        await ctx.response.defer(invisible=False)

        '''
        Create a list of usernames to show based on arguments
        =====================================================
        We want a list ``usernames`` to search on Lichess/Chess.com. If user entered
        a value for ``player`` and it's not a Discord tag/ID, it should be interpreted
        as a chess username (so we can set ``usernames`` right away). For other cases,
        we need to do a ``db_query()`` to get the appropriate usernames.
        '''
        if not player:
            # Show all players in db
            _, results = await D.db_query('SELECT username FROM ChessUsernames '
                                          'WHERE site = ?'
                                          'ORDER BY username',
                                          params=(U.SupportedSites.LICHESS,),
                                          auto_respond_on_fail=ctx)
            usernames = [e for e, in results]
            if not usernames:
                return await ctx.respond('There are no players in our database. Add yourselves with `/add <username>`!')
        elif player.lower() == 'me':
            # Show chess accounts linked to the author's discord_id
            _, results = await D.db_query('SELECT username FROM ChessUsernames '
                                          'WHERE discord_id = ?',
                                          params=(str(ctx.author),),
                                          auto_respond_on_fail=ctx)
            usernames = [e for e, in results]
            if not usernames:
                return await ctx.respond('You don\'t have any chess usernames linked to your Discord '
                                         'account in our database. Use `/add <username> <site>`, '
                                         'then `/iam <username> <site>` to link one!')
        elif U.is_valid_discord_tag(player):
            # Show one player by looking up chess accounts linked to their discord_id
            _, results = await D.db_query('SELECT username FROM ChessUsernames '
                                          'WHERE discord_id = ?',
                                          params=(player,),
                                          auto_respond_on_fail=ctx)
            usernames = [e for e, in results]
            if not usernames:
                return await ctx.respond(f'`{player}` doesn\'t have any chess usernames linked to their Discord '
                                         f'account in our database. They can use `/add <username> <site>`, '
                                         f'then `/iam <username> <site>` to link one!')
        else:
            # Show one player by a chess username (not necessarily one in the db)
            usernames = [player]

        ''' Now we should have a list of ``usernames``, show them! '''
        try:
            assert usernames, E.INTERNAL_ERROR_MSG + ' `usernames` should not be empty here'
        except AssertionError:
            logger.error(E.INTERNAL_ERROR_MSG, exc_info=True)
            return await ctx.respond(E.INTERNAL_ERROR_MSG)

        await Show._show_usernames(ctx, e, usernames)


def setup(bot: discord.Bot):
    bot.add_cog(Show(bot))

