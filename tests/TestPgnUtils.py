# Generated with ChatGPT!

import unittest
from uvmcc.PgnUtils import PgnUtils


class TestPgnUtils(unittest.TestCase):
    def test_extract_tag_value(self):
        pgn = """
        [Event "Casual Game"]
        [Site "Internet"]
        [Date "2023.05.25"]
        [Round "-"]
        [White "Player1"]
        [Black "Player2"]
        [Result "1/2-1/2"]
        [WhiteElo "2400"]
        [BlackElo "2200"]

        1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5 5. exd5 Na5 6. Bb5+ c6 7. dxc6 bxc6 8. Bd3 Ng4
        """

        white_elo = PgnUtils.extract_tag_value(pgn, "WhiteElo")
        black_elo = PgnUtils.extract_tag_value(pgn, "BlackElo")
        event = PgnUtils.extract_tag_value(pgn, "Event")
        site = PgnUtils.extract_tag_value(pgn, "Site")

        self.assertEqual(white_elo, "2400")
        self.assertEqual(black_elo, "2200")
        self.assertEqual(event, "Casual Game")
        self.assertEqual(site, "Internet")

if __name__ == '__main__':
    unittest.main()
