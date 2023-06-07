import uvmcc.utils as U
import uvmcc.error_msgs as E
import uvmcc.constants as C
import uvmcc.database_utils as D
from uvmcc.uvmcc_logging import logger

from typing import List

import discord
from discord.ext import commands

import aiohttp
import asyncio
import datetime
import json
import time


class UserManagement(commands.Cog):

    VALIDATE_IAM_RANDOM_CODE_LEN = 6


    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def _autocomplete_adding_username(ctx: discord.AutocompleteContext) -> List[str]:
        """
        Query the Lichess/Chess.com APIs for autocomplete suggestions for the given partial username.

        TODO - Merge Chess.com username autocompletion results, but first check if
               ``site`` was already was inputted (we can get this through ctx somehow)
        """
        partial_usernames = ctx.options['username']

        # Note: Not yet supported in berserk
        url = f'https://lichess.org/api/player/autocomplete?term={partial_usernames}'
        headers = {'Accept': 'application/x-ndjson'}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f'Failed to get autocomplete suggestions for username {partial_usernames} from '
                                 f'Lichess API (response.status={response.status})')
                    return []

                return json.loads(await response.text())

    @staticmethod
    async def _autocomplete_chess_usernames_in_db(ctx: discord.AutocompleteContext) -> List[str]:
        """ Get a list of matching  """
        partial_usernames = ctx.options['username']

        # Get all chess usernames in database that start with the given username (a partial match)
        exit_code, results = await D.db_query('SELECT username FROM chess_usernames '
                                              'WHERE username LIKE %s',
                                              params=(f'{partial_usernames}%',))
        # exit_code, results = await D.db_query('SELECT username FROM ChessUsernames')

        if exit_code != D.QueryExitCode.SUCCESS:
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

        exit_code, results = await D.db_query('SELECT site FROM chess_usernames '
                                              'WHERE username = %s',
                                              params=(partial_username,))

        if exit_code != D.QueryExitCode.SUCCESS:
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
                                           autocomplete=discord.utils.basic_autocomplete(_autocomplete_adding_username)),
                  site: discord.Option(str,
                                       description='What site is this username for?',
                                       choices=U.SUPPORTED_SITES_LIST)):

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
            exit_code, _ = await D.db_query('INSERT INTO chess_usernames(username, site) '
                                            'VALUES (%s, %s)',
                                            params=(username_proper_caps,
                                                    U.SupportedSites.LICHESS))
            if exit_code == D.QueryExitCode.INTEGRITY_ERROR:
                # Probably trying to insert duplicate primary key, the (username, site) pair
                # Let's verify what's happening and send an appropriate error msg
                exit_code, results = await D.db_query('SELECT username, site FROM chess_usernames '
                                                      'WHERE username LIKE %s '
                                                      '      AND site = %s',
                                                      params=(username_proper_caps,
                                                              U.SupportedSites.LICHESS))

                if not results:  # it wasn't a dupe primary key
                    return await ctx.respond(E.DB_INTEGRITY_ERROR_MSG)

                return await ctx.respond(f'`{username_proper_caps}` is already in the Lichess database!')
            elif exit_code != D.QueryExitCode.SUCCESS:
                return await ctx.respond(E.DB_ERROR_MSG(exit_code))

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
        exit_code, results = await D.db_query('SELECT username, site FROM chess_usernames '
                                              'WHERE username LIKE %s '
                                              '      AND site IN (SELECT site FROM json_each(%s))',
                                              params=(username, json.dumps(sites)))


        if exit_code != D.QueryExitCode.SUCCESS:
            return await ctx.respond(E.DB_ERROR_MSG(exit_code))

        if not results:
            return await ctx.respond(f'`{username}`{f" {(sites[0])}" if len(sites) == 1 else ""} '
                                     f'is not in the database.')

        # Remove the matching database entries
        exit_code, _ = await D.db_query('DELETE FROM chess_usernames '
                                        'WHERE username LIKE %s '
                                        '      AND site IN (SELECT site FROM json_each(%s))',
                                        params=(username, json.dumps(sites)))

        if exit_code != D.QueryExitCode.SUCCESS:
            return await ctx.respond(E.DB_ERROR_MSG(exit_code))

        # Success!
        await ctx.respond(f'Removed `{username}`{f" ({site})" if len(sites) == 1 else ""} '
                            f'from the database.')

    @discord.slash_command(name='iam',
                           description='Link your Discord tag to a chess username so you can use `/show player:me`')
    async def iam(self,
                  ctx: discord.ApplicationContext,
                  username: discord.Option(str,
                                         description='Chess username to link',
                                         autocomplete=discord.utils.basic_autocomplete(_autocomplete_chess_usernames_in_db)),
                  site: discord.Option(str,
                                       description='What site is this username for?',
                                       autocomplete=discord.utils.basic_autocomplete(_autocomplete_sites_for_db_username))):
        exit_code, results = await D.db_query('SELECT username, discord_id FROM chess_usernames '
                                              'WHERE username LIKE %s '
                                              'AND site = %s',
                                              params=(username, site))

        if exit_code != D.QueryExitCode.SUCCESS:
            return await ctx.respond(E.DB_ERROR_MSG(exit_code))

        if not results:
            return await ctx.respond(f'Please run `/add player:{username} '
                                     f'site:<{"/".join(U.SupportedSites) if site is None else site}>` first!')

        assert len(results) == 1, E.DB_INTEGRITY_ERROR_MSG + ' There are multiple records for `{username}` ({site})'

        # Now check if the user's profile is already linked to this entry in the database
        if results[0][1] == str(ctx.author):
            e = discord.Embed(title=f'Already linked {username} (Lichess) to {ctx.author}',
                              description=f'Use `/show player:me` to see your status!')
            return await ctx.respond(embed=e)

        site = site.lower()
        if site == U.SupportedSites.LICHESS:
            random_code = U.random_code(UserManagement.VALIDATE_IAM_RANDOM_CODE_LEN)
            code_expires = datetime.timedelta(minutes=5)
            delay_seconds = 10

            e = discord.Embed(title=f'Verify that you are {username} on Lichess',
                              description=f'1. Paste the code `{random_code}` somewhere in '
                                          f'[your Lichess bio](https://lichess.org/account/profile) to verify your '
                                          f'identity. The code expires '
                                          f'{U.format_discord_relative_time(unix_time=time.time(), td=code_expires)}.\n'
                                          f'2. Save your changes and this message will update within '
                                          f'{delay_seconds} seconds.\n'
                                          f'3. Once verified, you can remove the code from your bio.',
                              color=C.ACTION_REQUESTED_COLOR)
            await ctx.respond(embed=e, ephemeral=True)

            '''
            Get public profile data repeatedly at an interval, asynchronously
            
            Don't look too hard at the code below, it might hurt
            '''

            URL = f'https://lichess.org/api/user/{username}'
            async def check_bio(session: aiohttp.ClientSession) -> bool:
                async with session.get(URL) as response:
                    data = await response.json()
                    try:
                        bio = data['profile']['bio']
                    except KeyError:
                        logger.warning('`data[\'profile\'][\'bio\']` not found when requesting user public data')

                    if random_code in bio:
                        return True

            async def check_bio_loop() -> bool:
                while True:
                    async with aiohttp.ClientSession() as session:
                        code_found = await check_bio(session)
                        if code_found:
                            return True
                    await asyncio.sleep(delay_seconds)

            try:
                code_found = await asyncio.wait_for(check_bio_loop(), code_expires.total_seconds())
                if code_found:
                    raise asyncio.CancelledError
            except asyncio.TimeoutError:
                # Timed out, check bio one last time (last check might have been 9s ago)
                async with aiohttp.ClientSession() as session:
                    code_found = await check_bio(session)
            except asyncio.CancelledError:
                # Found the code, stopping early
                pass

            ''' okay, you can look again '''
            if not code_found:
                e = discord.Embed(title=f'Cound not verify {username} on Lichess',
                                  description=f'Code expired. Please try again.',
                                  color=C.ACTION_FAILED_COLOR)
                return await ctx.interaction.edit_original_response(embed=e)

            # Update the discord_id for the given username in ChessUsernames
            discord_id = str(ctx.author)
            exit_code, results = await D.db_query('UPDATE chess_usernames '
                                                  'SET discord_id = %s '
                                                  'WHERE username LIKE %s',
                                                  params=(discord_id, username))

            if exit_code != D.QueryExitCode.SUCCESS:
                e = discord.Embed(title='Could not link username',
                                  description=f'{E.DB_ERROR_MSG(exit_code)}',
                                  color=C.ACTION_FAILED_COLOR)
                return await ctx.interaction.edit_original_response(embed=e)

            e = discord.Embed(title=f'Linked `{username}` (Lichess) to `{ctx.author}`',
                              description='Use `/show player:me` to see your status!',
                              color=C.ACTION_SUCCEEDED_COLOR)
            return await ctx.interaction.edit_original_response(embed=e)
        elif site == U.SupportedSites.CHESS_COM:
            return await ctx.respond('Chess.com is not currently supported, but it will be soon!')
        else:
            return await ctx.respond(E.SITE_NOT_YET_SUPPORTED_FOR_ACTION_MSG(site))


def setup(bot: discord.Bot):
    bot.add_cog(UserManagement(bot))
