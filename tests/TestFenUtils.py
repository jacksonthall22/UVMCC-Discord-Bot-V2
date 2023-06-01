# Generated with ChatGPT!

import unittest
from uvmcc.FenUtils import FenUtils, FenComponent


class TestFenUtils(unittest.TestCase):
    def test_validate_valid_fen(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = FenUtils.validate(fen)
        self.assertTrue(result)

    def test_validate_invalid_fen(self):
        fen = "invalid fen"
        with self.assertRaises(ValueError):
            FenUtils.validate(fen)

    def test_validate_invalid_fen_no_raise(self):
        fen = "invalid fen"
        result = FenUtils.validate(fen, raise_=False)
        self.assertFalse(result)

    def test_validate_no_extra_whitespace_valid_fen(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = FenUtils.validate_no_extra_whitespace(fen)
        self.assertTrue(result)

    def test_validate_no_extra_whitespace_invalid_fen(self):
        fen = "   rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1   "
        with self.assertRaises(ValueError):
            FenUtils.validate_no_extra_whitespace(fen)

    def test_validate_no_extra_whitespace_invalid_fen_no_raise(self):
        fen = "   rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1   "
        result = FenUtils.validate_no_extra_whitespace(fen, raise_=False)
        self.assertFalse(result)

    def test_split_components(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        expected_components = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
            "w",
            "KQkq",
            "-",
            "0",
            "1"
        ]
        result = FenUtils.split_components(fen)
        self.assertEqual(result, expected_components)

    def test_get_component(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        component = FenComponent.BOARD_FEN
        expected_result = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
        result = FenUtils.get_component(fen, component)
        self.assertEqual(result, expected_result)

    def test_index_of_component_start(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        component = FenComponent.CASTLING_RIGHTS
        expected_index = 46
        result = FenUtils.index_of_component_start(fen, component)
        self.assertEqual(result, expected_index)

    def test_index_of_component_end(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        component = FenComponent.EN_PASSANT_TARGET_SQUARE
        expected_index = 51
        result = FenUtils.index_of_component_end(fen, component)
        self.assertEqual(result, expected_index)

    def test_indices_of_component_delimeters(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        component = FenComponent.BOARD_FEN
        expected_indices = (0, 43)
        result = FenUtils.indices_of_component_delimiters(fen, component)
        self.assertEqual(result, expected_indices)


if __name__ == '__main__':
    unittest.main()
