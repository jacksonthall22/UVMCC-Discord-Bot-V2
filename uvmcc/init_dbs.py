import uvmcc.constants as C
import uvmcc.utils as U
from uvmcc.uvmcc_logging import logger


async def init_dbs(db_file: str = C.DB_FILE):
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
                await U.db_query(q)
            logger.info('DONE')
            logger.info('======================================')
        except AssertionError:
            logger.info('ATTEMPTED TO RESET VOTE CHESS TABLES FROM ANOTHER FILE. Please run '
                        'init_dbs.py as \'__main__\' to delete & reset tables.')

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
        await U.db_query(query, db_file=db_file)

    logger.info('-------------------')
    logger.info('Finished init_dbs()')
    logger.info('===================')
