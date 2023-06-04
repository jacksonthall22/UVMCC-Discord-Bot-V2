import uvmcc.constants as C
import uvmcc.utils as U

from typing import Callable


def _tag_bug_fixers(e: str) -> str:
    return e + '\n\nPaging Bug Fixers: ' + ''.join([U.format_discord_user_tag(e) for e in C.BUG_FIXERS.values()])


DB_ERROR_MSG = _tag_bug_fixers('There was a database error :(')
DB_INTEGRITY_ERROR_MSG = _tag_bug_fixers('There was a database integrity error :(')
USERNAME_IN_DB_NOT_FOUND_MSG = \
    _tag_bug_fixers('There was a database integrity error :( Our database contained a username not found '
                    'on any supported chess sites. Was the account deleted (TODO: support this)?')
INTERNAL_ERROR_MSG = _tag_bug_fixers('There was an internal error (some code may need debugging) :(')
SITE_NOT_YET_SUPPORTED_FOR_ACTION_MSG: Callable[[str], str] \
    = lambda site: f'`{site}` is not yet supported for this action :('
HTTPS_STATUS_ERROR_MSG: Callable[[int], str] \
    = lambda status: _tag_bug_fixers(f'There was an unhandled HTTPS error (status {status}) :(')
