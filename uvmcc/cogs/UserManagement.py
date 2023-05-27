import uvmcc.utils as U
import uvmcc.error_msgs as E
import uvmcc.constants as C
from uvmcc.uvmcc_logging import logger

from typing import List

import discord
from discord.ext import commands
import berserk

import json
import requests


class UserManagement(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def _autocomplete_added_username(ctx: discord.AutocompleteContext) -> List[str]:
        """ Query the Lichess/Chess.com (to do) APIs for autocomplete suggestions for the given partial username. """
        partial_usernames = ctx.options['username']

        # Note: Not yet supported in berserk
        url = f'https://lichess.org/api/player/autocomplete?term={partial_usernames}'
        headers = {'Accept': 'application/x-ndjson'}
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            logger.error(f'Failed to get autocomplete suggestions for username {partial_usernames} from Lichess API ('
                         f'response.status_code={response.status_code})')
            return []

        return json.loads(response.text)

    @staticmethod
    async def _autocomplete_chess_usernames_in_db(ctx: discord.AutocompleteContext) -> List[str]:
        """ Get a list of matching  """
        partial_usernames = ctx.options['username']

        # Get all chess usernames in database that start with the given username (a partial match)
        exit_code, results = await U.db_query('SELECT username FROM ChessUsernames '
                                              'WHERE username LIKE ?',
                                              params=(f'{partial_usernames}%',))
        # exit_code, results = await U.db_query('SELECT username FROM ChessUsernames')

        if exit_code != U.QueryExitCode.SUCCESS:
            logger.error('Failed to get all chess usernames in database for autocomplete context')
            return []

        return [e for e, in results]

    @staticmethod
    async def _autocomplete_sites_for_db_username(ctx: discord.AutocompleteContext) -> List[str]:
        """
        Search the database for any entries with this username and return the sites they're for.
        If there are none, return a list of all supported sites.
        """
        partial_username = ctx.options['username']

        exit_code, results = await U.db_query('SELECT site FROM ChessUsernames '
                                              'WHERE username = ?',
                                              params=(partial_username,))

        if exit_code != U.QueryExitCode.SUCCESS:
            logger.error(f'Failed to get sites for username {partial_username} for autocomplete context')
            return []

        if results:
            return [e for e, in results]

        # If username isn't in the database for any site, give the illusion of choice
        return U.SUPPORTED_SITES_LIST

    @discord.slash_command(name='add',
                           description='Add your chess username to our database')
    async def add(self,
                  ctx: discord.ApplicationContext,
                  username: discord.Option(str,
                                           description='Your chess username',
                                           autocomplete=discord.utils.basic_autocomplete(_autocomplete_added_username)),
                  site: discord.Option(str,
                                       description='What site is this username for?',
                                       choices=U.SUPPORTED_SITES_LIST + ['both'])):

        site = site.lower()
        if site == U.SupportedSites.LICHESS:
            response = C.BERSERK_CLIENT.users.get_realtime_statuses(username)

            if not response:
                # Not an existing username
                return await ctx.respond(f'`{username}` wasn\'t found on Lichess.')

            user_data = response[0]

            # Response will give correct capitalization of username
            username_proper_caps: str = user_data['name']

            ''' Insert username  '''
            exit_code, _ = await U.db_query('INSERT INTO ChessUsernames(username, site) '
                                            'VALUES (?, ?)',
                                            params=(username_proper_caps,
                                                    U.SupportedSites.LICHESS))
            if exit_code == U.QueryExitCode.INTEGRITY_ERROR:
                # Probably trying to insert duplicate primary key, the (username, site) pair
                # Let's verify what's happening and send an appropriate error msg
                exit_code, results = await U.db_query('SELECT username, site FROM ChessUsernames '
                                                      'WHERE username LIKE ? '
                                                      '      AND site = ?',
                                                      params=(username_proper_caps,
                                                              U.SupportedSites.LICHESS))

                if not results:  # it wasn't a dupe primary key
                    return await ctx.respond(E.DB_INTEGRITY_ERROR_MSG)

                return await ctx.respond(f'`{username_proper_caps}` is already in the Lichess database!')
            elif exit_code != U.QueryExitCode.SUCCESS:
                return await ctx.respond(E.DB_ERROR_MSG)

            ''' Insertion successful ╰(*°▽°*)╯ '''
            return await ctx.respond(f'Added `{username_proper_caps}` ({U.SupportedSites.LICHESS}) to the database. '
                                     f'Use `/show` to see who\'s online!')
        elif site == U.SupportedSites.CHESS_COM:
            return await ctx.respond('Chess.com is not currently supported, but it will be soon!')
        else:
            return await ctx.respond(E.SITE_NOT_YET_SUPPORTED_FOR_ACTION_MSG(site))

    @discord.slash_command(name='remove',
                           description='Remove your chess username from our database')
    async def remove(self,
                     ctx: discord.ApplicationContext,
                     username: discord.Option(str,
                                              description='Chess username to remove',
                                              autocomplete=discord.utils.basic_autocomplete(_autocomplete_chess_usernames_in_db)),
                     site: discord.Option(str,
                                          description='What site is this username for? '
                                                      '(leave blank to remove for all sites)',
                                          autocomplete=discord.utils.basic_autocomplete(_autocomplete_sites_for_db_username)) = None):
        # Decide which sites to remove for this username
        sites = (site,) if site is not None else tuple(U.SUPPORTED_SITES_LIST)

        # First get the matching database entries
        exit_code, results = await U.db_query('SELECT username, site FROM ChessUsernames '
                                              'WHERE username LIKE ? '
                                              '      AND site IN (SELECT site FROM json_each(?))',
                                              params=(username, json.dumps(sites)))


        if exit_code != U.QueryExitCode.SUCCESS:
            return await ctx.respond(E.DB_ERROR_MSG)

        if not results:
            return await ctx.respond(f'`{username}`{f" {(sites[0])}" if len(sites) == 1 else ""} '
                                     f'is not in the database.')

        # Remove the matching database entries
        exit_code, _ = await U.db_query('DELETE FROM ChessUsernames '
                                        'WHERE username LIKE ? '
                                        '      AND site IN (SELECT site FROM json_each(?))',
                                        params=(username, json.dumps(sites)))

        if exit_code != U.QueryExitCode.SUCCESS:
            return await ctx.respond(E.DB_ERROR_MSG)

        # Success!
        await ctx.respond(f'Removed `{username}`{f" ({site})" if len(sites) == 1 else ""} '
                            f'from the database.')

    @discord.slash_command(name='iam',
                           description='Link your Discord tag to a chess username so you can use `/show me`')
    async def iam(self,
                  ctx: discord.ApplicationContext,
                  username: discord.Option(str,
                                         description='Chess username to link',
                                         autocomplete=discord.utils.basic_autocomplete(_autocomplete_chess_usernames_in_db)),
                  site: discord.Option(str,
                                       description='What site is this username for?',
                                       autocomplete=discord.utils.basic_autocomplete(_autocomplete_sites_for_db_username))):
        exit_code, results = await U.db_query('SELECT username FROM ChessUsernames '
                                              'WHERE username LIKE ? '
                                              'AND site = ?',
                                              params=(username, site))

        if exit_code != U.QueryExitCode.SUCCESS:
            return await ctx.respond(E.DB_ERROR_MSG)

        if not results:
            return await ctx.respond(f'Please run `/add {username} '
                                     f'{f"({site})" if site is not None else "<site>"}` first!')

        if len(results) != 1:
            return await ctx.respond(E.DB_INTEGRITY_ERROR_MSG +
                                     f' There are multiple records for `{username}` ({site})')

        site = site.lower()
        if site == U.SupportedSites.LICHESS:
            # Update the discord_id for the given username in ChessUsernames
            discord_id = str(ctx.author)
            exit_code, results = await U.db_query('UPDATE ChessUsernames '
                                                  'SET discord_id = ? '
                                                  'WHERE username LIKE ?',
                                                  params=(discord_id, username))

            if exit_code != U.QueryExitCode.SUCCESS:
                return await ctx.respond(E.DB_ERROR_MSG)

            await ctx.respond(f'Linked `{username}` ({site}) to `{discord_id}`. Use `/show me` to see your live games!')
        elif site == U.SupportedSites.CHESS_COM:
            return await ctx.respond('Chess.com is not currently supported, but it will be soon!')
        else:
            return await ctx.respond(E.SITE_NOT_YET_SUPPORTED_FOR_ACTION_MSG(site))


def setup(bot: discord.Bot):
    bot.add_cog(UserManagement(bot))
