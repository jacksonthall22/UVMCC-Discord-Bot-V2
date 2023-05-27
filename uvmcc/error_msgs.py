from typing import Callable

DB_ERROR_MSG = 'There was a database error :('
DB_INTEGRITY_ERROR_MSG = 'There was a database integrity error :('
USERNAME_IN_DB_NOT_FOUND_MSG = \
    DB_INTEGRITY_ERROR_MSG \
    + ' Our database contained a username not found on supported chess sites. ' \
      'Was the account deleted? (TODO: support this)'
INTERNAL_ERROR_MSG = 'There was an internal error (code may need debugging) :('
SITE_NOT_YET_SUPPORTED_FOR_ACTION_MSG: Callable[[str], str] \
    = lambda site: f'`{site}` is not yet supported for this action :('
HTTPS_STATUS_ERROR_MSG: Callable[[int], str] = lambda status: f'There was an HTTPS error (status {status}) :('
