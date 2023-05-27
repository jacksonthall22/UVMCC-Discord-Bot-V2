import re

class PgnUtils:
    @staticmethod
    def extract_tag_value(pgn_string: str, tag_name: str) -> str | None:
        pattern = r'\[{0}\s+"(.*?)"\]'.format(tag_name)
        match = re.search(pattern, pgn_string)
        if match and match.group(1):
            return match.group(1)
        else:
            return None
