import uvmcc.error_msgs as E
from uvmcc.uvmcc_logging import logger

from typing import Tuple, Any, List

import discord

import enum
import aiosqlite


DB_FILE = 'data.db'

class QueryExitCode(enum.Enum):
    SUCCESS = 0
    UNKNOWN_FAILURE = 1
    INTEGRITY_ERROR = 2

async def db_query(query: str,
                   *,
                   params: Tuple[str | Any, ...] = None,
                   db_file: str = DB_FILE,
                   auto_respond_on_fail: discord.ApplicationContext | None = None) \
        -> Tuple[QueryExitCode, List[Any] | None]:
    """
    Connect with the given sqlite3 database ``db_file`` via ``aiosqlite`` and execute ``query``.
    Return a custom ``QueryExitCode`` and ``cur.fetchall()`` for the command. Providing a
    ``discord.ApplicationContext`` for ``auto_respond_on_fail`` responds to the context with
    an appropriate message if the query is not successful.
    """

    # Remove big whitespaces (just for logging; shouldn't be necessary for ``db.execute()``)
    query = ' '.join(query.split())

    async with aiosqlite.connect(db_file) as db:
        try:
            logger.info(f'Executing: db_query(db_file={db_file},query={query},params={params})')

            async with db.execute(query, params) as cursor:
                query_result = await cursor.fetchall()
            await db.commit()

            logger.info('Query succeeded.')
            return QueryExitCode.SUCCESS, query_result

        except aiosqlite.IntegrityError as e:
            logger.warning(
                f'Query FAILED: aiosqlite.IntegrityError. Maybe due to insertion of duplicate primary key? '
                f'Stack trace:\n{e}')
            if auto_respond_on_fail:
                await auto_respond_on_fail.respond(E.INTERNAL_ERROR_MSG)
            return QueryExitCode.INTEGRITY_ERROR, None

        except Exception as e:
            logger.error(f'Query FAILED: {type(e).__name__}. Stack trace:\n{e}')
            exit_code = QueryExitCode.UNKNOWN_FAILURE
            if auto_respond_on_fail:
                await auto_respond_on_fail.respond(E.DB_ERROR_MSG(exit_code))
            return exit_code, None

async def init_dbs(db_file: str = DB_FILE):
    logger.info('==================')
    logger.info('Calling init_dbs()')
    logger.info('------------------')

    RESET_VOTE_CHESS_TABLES = False
    if RESET_VOTE_CHESS_TABLES:
        try:
            assert __name__ == '__main__'

            logger.info('======================================')
            logger.info('DELETING & RESETTING VOTE CHESS TABLES')
            logger.info('--------------------------------------')

            DROP_QUERIES = [
                'DROP TABLE VoteMatches',
                'DROP TABLE VoteMatchPairings',
                'DROP TABLE VoteMatchVotes',
                'DROP TABLE VoteMatchDrawOffers',
                'DROP TABLE MatchStatuses',
                'DROP TABLE MatchSides',
                'DROP TABLE MatchResults',
                'DROP TABLE MatchTerminations',
            ]
            for q in DROP_QUERIES:
                await db_query(q)
            logger.info('DONE')
            logger.info('======================================')
        except AssertionError:
            logger.info(f'ATTEMPTED TO RESET VOTE CHESS TABLES FROM ANOTHER FILE. Please run '
                        f'`{__name__}.py` as \'__main__\' to delete & reset tables.')

    QUERIES = [
        'CREATE TABLE IF NOT EXISTS DiscordUsers (discord_id TEXT PRIMARY KEY)',
        'CREATE TABLE IF NOT EXISTS ChessSites (site TEXT PRIMARY KEY COLLATE NOCASE)',
        'INSERT OR IGNORE INTO ChessSites(site) VALUES ("lichess.org"), ("chess.com")',
        'CREATE TABLE IF NOT EXISTS ChessUsernames '
            '(username TEXT PRIMARY KEY, '
            'discord_id TEXT, '
            'site TEXT, '
            'FOREIGN KEY(discord_id) REFERENCES DiscordUsers(discord_id), '
            'FOREIGN KEY(site) REFERENCES ChessSites(site))',

        # Vote Chess tables
        'CREATE TABLE IF NOT EXISTS MatchStatuses '
            '(status TEXT PRIMARY KEY COLLATE NOCASE)',
        'INSERT OR IGNORE INTO MatchStatuses(status) VALUES '
            '("Not Started"), '
            '("Aborted"), '
            '("In Progress"), '
            '("Abandoned"), '
            '("Complete")',
        'CREATE TABLE IF NOT EXISTS MatchSides '
            '(side TEXT PRIMARY KEY COLLATE NOCASE)',
        'INSERT OR IGNORE INTO MatchSides(side) VALUES '
            '("Black"), '
            '("White"), '
            '("Both"), '
            '("random")',
        'CREATE TABLE IF NOT EXISTS MatchResults '
            '(result TEXT PRIMARY KEY COLLATE NOCASE)',
        'INSERT OR IGNORE INTO MatchResults(result) VALUES '
            '("checkmate"), '
            '("resignation"), '
            '("abandonment"), '
            '("stalemate"), '
            '("repetition"), '
            '("mutual agreement"), '
            '("50-move rule"), '
            '("unknown")',
        'CREATE TABLE IF NOT EXISTS MatchTerminations '
            '(termination TEXT PRIMARY KEY COLLATE NOCASE)',
        'INSERT OR IGNORE INTO MatchTerminations VALUES '
            '("1-0"), '
            '("0-1"), '
            '("1/2-1/2"), '
            '("*")',
        'CREATE TABLE IF NOT EXISTS VoteMatches '
            '(match_code TEXT PRIMARY KEY, '
            'match_name TEXT, '
            'pgn TEXT, '
            'starting_fen TEXT NOT NULL DEFAULT "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",'
            'status TEXT NOT NULL, '
            'hours_between_moves INTEGER DEFAULT 1 NOT NULL, '
            'last_move_unix_time INTEGER, '
            'unix_time_created INTEGER NOT NULL, '
            'unix_time_started INTEGER, '
            'unix_time_ended INTEGER, '
            'result TEXT DEFAULT NULL, '
            'termination TEXT NOT NULL DEFAULT "*", '
            'hide_votes INTEGER NOT NULL DEFAULT 1, '  # 1 == TRUE
            'FOREIGN KEY(status) REFERENCES MatchStatuses(status), '
            'FOREIGN KEY(result) REFERENCES MatchResults(result), '
            'FOREIGN KEY(termination) REFERENCES MatchTerminations(termination))',
        'CREATE TABLE IF NOT EXISTS VoteMatchPairings '
            '(match_code TEXT NOT NULL, '
            'discord_id TEXT NOT NULL, '
            'side TEXT NOT NULL, '
            'votes_cast INTEGER DEFAULT 0, '
            'top_move_votes_cast INTEGER DEFAULT 0, '
            'FOREIGN KEY(match_code) REFERENCES VoteMatches(match_code), '
            'FOREIGN KEY(discord_id) REFERENCES DiscordUsers(discord_id), '
            'PRIMARY KEY(match_code, discord_id), '
            'FOREIGN KEY(side) REFERENCES MatchSides(side))',
        'CREATE TABLE IF NOT EXISTS VoteMatchVotes '
            '(match_code TEXT NOT NULL, '
            'discord_id TEXT NOT NULL, '
            'ply_count INTEGER NOT NULL DEFAULT 0, '
            'vote TEXT, '
            'voted_resign INTEGER NOT NULL DEFAULT 0, '
            'voted_draw INTEGER NOT NULL DEFAULT 0, '
            'FOREIGN KEY(match_code, discord_id)'
            ' REFERENCES VoteMatchPlies(match_code, discord_id),'
            'PRIMARY KEY(match_code, discord_id, ply_count))',
        'CREATE TABLE IF NOT EXISTS VoteMatchDrawOffers '
            '(match_code TEXT NOT NULL, '
            'ply_count INTEGER NOT NULL, '
            'voted_draw INTEGER NOT NULL, '
            'FOREIGN KEY(match_code) REFERENCES VoteMatches(match_code), '
            'PRIMARY KEY(match_code, ply_count))',
    ]

    for query in QUERIES:
        await db_query(query, db_file=db_file)

    logger.info('-------------------')
    logger.info('Finished init_dbs()')
    logger.info('===================')
