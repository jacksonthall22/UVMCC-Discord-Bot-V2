import uvmcc.error_msgs as E
from uvmcc.uvmcc_logging import logger

from typing import Tuple, Any, List

import discord

import enum
import os
import psycopg2
import re


# This environment var should be set automatically by Heroku.
# Locally, we have to define it to be hosted on a local port.
# See:
# https://www.enterprisedb.com/docs/postgresql_journey/04_developing/connecting_to_postgres/python/01_psycopg2/
DATABASE_URL = os.environ.get('DATABASE_URL')


def replace_password_in_postgres_db_url(url: str) -> str:
    """
    Replace the password in a PostgreSQL database url with "******".
    """
    return re.sub(r'(://[^:]*:)[^@]+', r'\g<1>******', url)


class QueryExitCode(enum.IntEnum):
    SUCCESS = 0
    UNKNOWN_FAILURE = 1
    INTEGRITY_ERROR = 2


async def db_query(query: str,
                   *,
                   params: Tuple[str | Any, ...] = None,
                   db_url: str = DATABASE_URL,
                   auto_respond_on_fail: discord.ApplicationContext | None = None) \
        -> Tuple[QueryExitCode, List[Any] | None]:
    """
    Connect with the given PostgreSQL database by its url ``db_url`` and execute ``query``.
    Return a custom ``QueryExitCode`` and ``cur.fetchall()`` for the command. Providing a
    ``discord.ApplicationContext`` for ``auto_respond_on_fail`` responds to the context with
    an appropriate message if the query is not successful.
    """

    # Remove big whitespaces (just for logging; shouldn't be necessary for ``db.execute()``)
    query_minified = ' '.join(query.split())

    conn = psycopg2.connect(db_url, sslmode='allow')
    conn.autocommit = True

    try:
        with conn.cursor() as cursor:
            logger.info(f'Executing: '
                        f'db_query(db_url={replace_password_in_postgres_db_url(db_url)},'
                        f'query={query_minified},'
                        f'params={params})')

            cursor.execute(query, params)
            try:
                results = cursor.fetchall()
            except psycopg2.ProgrammingError:
                # No results to fetch
                results = None

            logger.info('Query succeeded.')
            return QueryExitCode.SUCCESS, results
    except psycopg2.IntegrityError as e:
        logger.warning(
            f'Query FAILED: aiosqlite.IntegrityError. Maybe due to insertion of duplicate primary key? '
            f'Stack trace:\n{e}')

        if auto_respond_on_fail:
            await auto_respond_on_fail.respond(E.DB_INTEGRITY_ERROR_MSG)

        return QueryExitCode.INTEGRITY_ERROR, None
    except Exception as e:
        logger.error(f'Query FAILED: {type(e).__name__}. Stack trace:\n{e}')

        exit_code = QueryExitCode.UNKNOWN_FAILURE
        if auto_respond_on_fail:
            await auto_respond_on_fail.respond(E.DB_ERROR_MSG(exit_code))
        return exit_code, None


async def init_dbs(db_url: str = DATABASE_URL,
                   *,
                   reset_vote_chess_tables: bool = False,
                   reset_all_tables: bool = False):
    logger.info('==================')
    logger.info('Calling init_dbs()')
    logger.info('------------------')

    if reset_all_tables:
        try:
            assert __name__ == '__main__'

            logger.info('===============================')
            logger.info('DELETING & RESETTING ALL TABLES')
            logger.info('-------------------------------')

            TABLES = [
                'discord_users',
                'guilds',
                'guild_discord_users',
                'chess_sites',
                'chess_usernames',
                'vote_match_status_types',
                'vote_match_team_types',
                'vote_match_result_types',
                'vote_match_termination_types',
                'vote_matches',
                'vote_match_pairings',
                'vote_match_votes'
            ]

            for t in TABLES:
                await db_query(f'DROP TABLE {t} CASCADE')

            logger.info('DONE')
            logger.info('======================================')
        except AssertionError:
            logger.info(f'ATTEMPTED TO RESET ALL TABLES FROM ANOTHER FILE. Please run '
                        f'`{__name__}.py` as \'__main__\' to delete & reset tables.')
    elif reset_vote_chess_tables:
        try:
            assert __name__ == '__main__'

            logger.info('======================================')
            logger.info('DELETING & RESETTING VOTE CHESS TABLES')
            logger.info('--------------------------------------')

            TABLES = [
                'vote_match_status_types',
                'vote_match_team_types',
                'vote_match_result_types',
                'vote_match_termination_types',
                'vote_matches',
                'vote_match_pairings',
                'vote_match_votes'
            ]

            for t in TABLES:
                await db_query(f'DROP TABLE {t} CASCADE')

            logger.info('DONE')
            logger.info('======================================')
        except AssertionError:
            logger.info(f'ATTEMPTED TO RESET VOTE CHESS TABLES FROM ANOTHER FILE. Please run '
                        f'`{__name__}.py` as \'__main__\' to delete & reset tables.')



    QUERIES = [
        'CREATE TABLE IF NOT EXISTS discord_users ('
        '    discord_id TEXT PRIMARY KEY'
        ')',

        'CREATE TABLE IF NOT EXISTS guilds '
        '    (guild_id TEXT PRIMARY KEY)',

        'CREATE TABLE IF NOT EXISTS guild_discord_users ('
        '    guild_id TEXT, '
        '    discord_id TEXT, '
        '    PRIMARY KEY(guild_id, discord_id),'
        '    FOREIGN KEY(guild_id) REFERENCES guilds(guild_id), '
        '    FOREIGN KEY(discord_id) REFERENCES discord_users(discord_id)'
        ')',

        'CREATE TABLE IF NOT EXISTS chess_sites ('
        '    site CITEXT PRIMARY KEY'
        ')',

        'INSERT INTO chess_sites(site) '
        'VALUES '
        '    (\'lichess.org\'),'
        '    (\'chess.com\') '
        'ON CONFLICT DO NOTHING',

        'CREATE TABLE IF NOT EXISTS chess_usernames ('
        '    username CITEXT PRIMARY KEY, '
        '    site CITEXT, '
        '    FOREIGN KEY(site) REFERENCES chess_sites(site),'
        '    guild_id TEXT, '
        '    discord_id TEXT, '
        '    FOREIGN KEY(guild_id, discord_id) REFERENCES guild_discord_users(guild_id, discord_id)'
        ')',

        # ========== Vote Chess Tables ==========
        # ----- Types -----
        # These could be enums but then we can't verify them as foreign keys in other tables
        'CREATE TABLE IF NOT EXISTS vote_match_status_types ('
        '    status CITEXT PRIMARY KEY'
        ')',

        'INSERT INTO vote_match_status_types(status) '
        'VALUES '
        '    (\'Not Started\'), '
        '    (\'Aborted\'), '
        '    (\'In Progress\'), '
        '    (\'Abandoned\'), '
        '    (\'Complete\') '
        'ON CONFLICT DO NOTHING',

        'CREATE TABLE IF NOT EXISTS vote_match_team_types ('
        '    team CITEXT PRIMARY KEY'
        ')',

        'INSERT INTO vote_match_team_types(team) '
        'VALUES '
        '    (\'Black\'), '
        '    (\'White\'), '
        '    (\'Both\'), '
        '    (\'random\') '
        'ON CONFLICT DO NOTHING',

        'CREATE TABLE IF NOT EXISTS vote_match_result_types ('
        '    result CITEXT PRIMARY KEY'
        ')',

        'INSERT INTO vote_match_result_types(result) '
        'VALUES '
        '    (\'Checkmate\'), '
        '    (\'Resignation\'), '
        '    (\'Abandonment\'), '
        '    (\'Stalemate\'), '
        '    (\'Threefold Repetition\'), '
        '    (\'Mutual Agreement\'), '
        '    (\'50-Move Rule\'), '
        '    (\'Unknown\') '
        'ON CONFLICT DO NOTHING',

        'CREATE TABLE IF NOT EXISTS vote_match_termination_types ('
        '    termination CITEXT PRIMARY KEY'
        ')',

        'INSERT INTO vote_match_termination_types '
        'VALUES '
        '    (\'1-0\'), '
        '    (\'0-1\'), '
        '    (\'1/2-1/2\'), '
        '    (\'*\') '
        'ON CONFLICT DO NOTHING',

        # ----- Matches, pairings, votes -----
        'CREATE TABLE IF NOT EXISTS vote_matches ('
        '    match_code CITEXT, '
        '    guild_id TEXT NOT NULL, '
        '    FOREIGN KEY(guild_id) REFERENCES guilds(guild_id), '
        '    PRIMARY KEY(match_code, guild_id), '
        '    match_name TEXT, '
        '    pgn TEXT, '
        '    starting_fen TEXT NOT NULL DEFAULT \'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1\','
        '    keep_votes_secret BOOLEAN NOT NULL DEFAULT TRUE, '
        '    seconds_between_auto_moves INTEGER DEFAULT 1 NOT NULL, '
        '    unix_time_last_move INTEGER, '
        '    unix_time_created INTEGER NOT NULL, '
        '    unix_time_started INTEGER, '
        '    unix_time_ended INTEGER, '
        '    status CITEXT NOT NULL DEFAULT \'Not Started\', '
        '    FOREIGN KEY(status) REFERENCES vote_match_status_types(status), '
        '    result CITEXT DEFAULT NULL, '
        '    FOREIGN KEY(result) REFERENCES vote_match_result_types(result), '
        '    termination CITEXT NOT NULL DEFAULT \'*\', '
        '    FOREIGN KEY(termination) REFERENCES vote_match_termination_types(termination)'
        ')',

        'CREATE TABLE IF NOT EXISTS vote_match_pairings ('
        '    match_code CITEXT NOT NULL, '
        '    guild_id TEXT NOT NULL, '
        '    FOREIGN KEY (match_code, guild_id) REFERENCES vote_matches(match_code, guild_id), '
        '    discord_id TEXT NOT NULL, '
        '    FOREIGN KEY (guild_id) REFERENCES discord_users(discord_id), '
        '    PRIMARY KEY (match_code, guild_id, discord_id), '
        '    team CITEXT NOT NULL, '
        '    FOREIGN KEY(team) REFERENCES vote_match_team_types(team), '
        '    num_votes_cast INTEGER DEFAULT 0, '
        '    num_top_move_votes_cast INTEGER DEFAULT 0'
        ')',

        'CREATE TABLE IF NOT EXISTS vote_match_votes ('
        '    match_code CITEXT NOT NULL, '
        '    guild_id TEXT NOT NULL, '
        '    discord_id TEXT NOT NULL, '
        '    FOREIGN KEY(match_code, guild_id, discord_id) '
        '        REFERENCES vote_match_pairings(match_code, guild_id, discord_id), '
        '    ply_before INTEGER NOT NULL, '
        '    PRIMARY KEY(match_code, guild_id, discord_id, ply_before), '
        '    voted_move_san TEXT DEFAULT NULL, '  # Should init to NULL here, in case ex. a user votes to
                                                  # resign before voting for a move. We're assuming here
                                                  # that users can vote for a move **and** to resign/offer 
                                                  # a draw on each ply. If this feature changes, we might 
                                                  # need to change this schema.
        '    voted_resign BOOLEAN NOT NULL DEFAULT FALSE, '
        '    voted_draw BOOLEAN NOT NULL DEFAULT FALSE'
        ')',
    ]

    for query in QUERIES:
        await db_query(query, db_url=db_url)

    logger.info('-------------------')
    logger.info('Finished init_dbs()')
    logger.info('===================')
