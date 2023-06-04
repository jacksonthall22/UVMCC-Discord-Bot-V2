import uvmcc.constants as C
import uvmcc.FenUtils as F

from typing import Tuple, Any, Sequence, Iterable, Dict, AsyncIterator, TypedDict, NotRequired

import chess
import chess.pgn

import enum
import itertools
import aiohttp
import ndjson
import random
import datetime


class SupportedSites(enum.StrEnum):
    LICHESS = 'lichess.org'
    CHESS_COM = 'chess.com'
SUPPORTED_SITES_LIST = [*SupportedSites]


class ClockJson(TypedDict):
    """
    Game clock description (following Lichess API's output).
    """
    initial: int
    increment: int
    totalTime: NotRequired[int]


def random_code(length: int,
                *,
                alphabet: str = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ') -> str:
    """
    Return a random string of the given length using the given alphabet.
    """
    return ''.join(random.choices(alphabet, k=length))


def format_discord_user_tag(user_id: str) -> str:
    return f'<@{user_id}>'

def format_discord_relative_time(unix_time: int | float = datetime.datetime.now().timestamp(),
                                 *,
                                 td: datetime.timedelta | None = None) -> str:
    """
    Return a string that can be pasted in a Discord message to show an updating time
    like "2 days ago" or "in 2 days" from the given the Unix timestamp, and optionally
    a ``datetime.timedelta`` object to add to it.
    """
    if td is not None:
        unix_time += td.total_seconds()
    return f'<t:{round(unix_time)}:R>'

def format_lichess_time_control(clock_json: ClockJson) -> str:
    """
    Get a string like "5+3" from the Lichess API's clock description JSON format.
    For times where ``initial`` is less than 60 seconds are formatted as a fraction
    (¼, ½, or ¾) and raise an error if ``initial`` is not equal to 3 or not divisible
    by 15.

    Examples:
    >>> format_lichess_time_control({'initial': 300, 'increment': 3})
    '5+3'
    >>> format_lichess_time_control({'initial': 180, 'increment': 2})
    '3+2'
    >>> format_lichess_time_control({'initial': 45, 'increment': 0})
    '¾+0'
    >>> format_lichess_time_control({'initial': 3, 'increment': 1})
    '0+1'
    >>> format_lichess_time_control({'initial': 20, 'increment': 0})
    Traceback (most recent call last):
    ...
    ValueError: Invalid initial time. clock_json:
    {'initial': 20, 'increment': 0}
    >>> format_lichess_time_control({'initial': 15, 'increment': 0})
    '¼+0'
    """
    init = clock_json['initial']
    incr = clock_json['increment']

    if init < 60:
        if init == 3:
            return f'0+{incr}'

        if init == 15:
            return f'¼+{incr}'
        elif init == 30:
            return f'½+{incr}'
        elif init == 45:
            return f'¾+{incr}'
        else:
            raise ValueError(f'Invalid initial time. clock_json:\n{clock_json}')
    else:
        # Integer-divide only if initial is a multiple of 60
        return f'{init // 60 if init % 60 == 0 else init / 60}+{incr}'

def grouper(iterable: Iterable, n: int, fillvalue: Any = None):
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)

def is_valid_discord_tag(maybe_tag: str) -> bool:
    import re
    return bool(re.match(re.compile('^.{2,32}#[0-9]{4}$'), maybe_tag))

def get_board_image_url(fen: str,
                        *,
                        orientation: chess.COLOR_NAMES = chess.COLOR_NAMES[chess.WHITE],
                        last_move_uci: str = None,
                        size: int = 360) -> str:
    """
    Return a URL for a PNG image of a chess board with the given ``fen`` highlighting the last move (optional).
    Uses [web-boardimage](https://github.com/niklasf/web-boardimage).
    """

    # Validate that fen is possible
    # TODO use instead ex. ``constants._temp_board``
    b = chess.Board(fen)

    # Truncate FEN to just the board layout part
    fen_trunc = b.board_fen()

    # TODO - what happens if we change 'png' to 'svg'?
    return f'https://backscattering.de/web-boardimage/board.png' \
           f'?fen={fen_trunc}' \
           f'&orientation={orientation}' \
           f'{"&lastMove=" + last_move_uci if last_move_uci is not None else ""}' \
           f'&size={size}'

async def stream_moves_lichess(game_id: str = None) -> AsyncIterator[Tuple[Dict[str, Any], bool | None]]:
    """
    Asynchronously stream incoming moves of a live game on Lichess by its ``game_id``.
    Yields both the game data and a ``bool`` (or ``None``, for the first and last packets)
    indicating if the data is about a "new" move, i.e. one that was after the first API
    call was made.
    https://lichess.org/api#tag/Games/operation/streamGame
    """
    async with aiohttp.ClientSession(raise_for_status=False) as session:
        async with session.get(f'https://lichess.org/api/stream/game/{game_id}') as r:
            # TODO Currently there's a bug in this endpoint where the fullmove number
            #      in the FEN is `1` for every already-played move. New moves (played
            #      after the request is made) get the correct fullmove number, and the
            #      initial and final packets seem to both also have the correct number.
            #      Only fix currently is manually keeping track of fullmove number.
            #      https://github.com/lichess-org/lila/issues/12907
            actual_current_fullmove_num: int = 0  # pre-increments below
            past_already_played_moves: bool = False

            async for i, packet in aenumerate(r.content):
                packet = ndjson.loads(packet)[0]
                if i == 0:
                    # First packet
                    assert 'id' in packet, f'error: "game_id" not in first ndjson line: {packet}'
                    # TODO: keep this for when API bug fixed
                    # live_fullmove_num = int(F.FenUtils.get_component(packet['fen'],
                    #                                                  F.FenComponent.FULLMOVE_NUM,
                    #                                                  validate=False))
                    yield packet, None
                    continue
                elif 'id' in packet:
                    # Last packet
                    yield packet, None
                    break

                if past_already_played_moves:
                    # Fullmove number should be correct here, we can abandon
                    # keeping ``actual_current_fullmove_num`` updated
                    yield packet, True
                    continue

                fen = packet['fen']
                if F.FenUtils.get_component(fen,
                                            F.FenComponent.FULLMOVE_NUM,
                                            validate=False) != '1':
                    past_already_played_moves = True
                    continue

                # Fullmove number needs correcting
                if F.FenUtils.get_component(fen,
                                            F.FenComponent.ACTIVE_COLOR,
                                            validate=False) == 'w':
                    actual_current_fullmove_num += 1

                idx = F.FenUtils.index_of_component_start(fen,
                                                          F.FenComponent.FULLMOVE_NUM,
                                                          validate=False)
                packet['fen'] = fen[:idx] + str(actual_current_fullmove_num)

                yield packet, False

async def aenumerate(asequence: AsyncIterator[Any] | aiohttp.StreamReader,
                     start: int = 0) -> AsyncIterator[Tuple[int, Any]]:
    """
    Asynchronously enumerate an async iterator from a given start value.
    https://gist.github.com/tebeka/8c6b0589f5783bc4115a?permalink_comment_id=4247109#gistcomment-4247109
    """
    n = start
    async for elem in asequence:
        yield n, elem
        n += 1

def to_fullmoves(*, ply: int) -> int:
    """
    Convert the ``ply`` to its fullmove number. Note that plies are 0-indexed in ``python-chess``
    (ex. ``chess.pgn.Game().ply() == 0``) while fullmoves are typically 1-indexed (ex. when written).
    """
    return ply // 2 + 1


def format_move_number(*, ply: int) -> str:
    """ Get a string to prefix the move at the given ``ply``, like "1." or "1...". """
    return f'{to_fullmoves(ply=ply)}.{".." if ply % 2 == 1 else ""}'

def format_moves(sans: Sequence[C.SanStrT],
                 *,
                 first_ply: int = 0) -> str:
    """
    Return a string with the given ``sans`` line formatted with appropriate fullmove numbers,
     starting at the given ``first_ply``.

    >>> format_moves(['e4', 'e5', 'Nf3', 'Nc6', 'Bg5'], first_ply=0)
    '1.e4 e5 2.Nf3 Nc6 3.Bg5'
    >>> format_moves(['e4', 'e5', 'Nf3', 'Nc6', 'Bg5'], first_ply=1)
    '1...e4 2.e5 Nf3 3.Nc6 Bg5'
    """
    if not sans:
        return ''

    formatted_fullmoves = []
    remaining_sans = sans[:]

    if first_ply % 2 == 1:
        # Black's turn
        formatted_fullmoves.append(f'{format_move_number(ply=first_ply)}{sans[0]}')
        remaining_sans = remaining_sans[1:]
        first_ply += 1

    ply = first_ply
    for wb_sans in grouper(remaining_sans, 2):
        formatted_fullmoves.append(f'{format_move_number(ply=ply)}{" ".join((s for s in wb_sans if s is not None))}')
        ply += 2

    return ' '.join(formatted_fullmoves)
