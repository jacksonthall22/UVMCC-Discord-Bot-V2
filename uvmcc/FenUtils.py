from typing import List
import enum
import chess


class FenComponent(enum.IntEnum):
    BOARD_FEN = 0
    ACTIVE_COLOR = 1
    CASTLING_RIGHTS = 2
    EN_PASSANT_TARGET_SQUARE = 3
    HALFMOVE_CLOCK = 4
    FULLMOVE_NUM = 5


class FenUtils:

    __b = chess.Board()

    @staticmethod
    def validate(fen: str,
                 *,
                 raise_: bool = True) -> bool:
        try:
            FenUtils.__b.set_fen(fen)
            return FenUtils.validate_no_extra_whitespace(fen, raise_=raise_)
        except ValueError:
            if raise_:
                raise
            return False

    @staticmethod
    def validate_no_extra_whitespace(fen: str,
                                     *,
                                     raise_: bool = True) -> bool:
        is_stripped = fen.strip() == fen

        if not is_stripped and raise_:
            raise ValueError(f'Invalid FEN (please strip leading/trailing whitespace): "{fen}"')

        return is_stripped

    @staticmethod
    def split_components(fen: str,
                         *,
                         validate: bool = True) -> List[str]:
        """
        Return the 6 FEN components as a list of strings. If ``validate``,
        may raise ``ValueError`` via ``FenUtils.validate(fen)``.
        """
        if validate:
            FenUtils.validate(fen, raise_=True)

        return fen.split()

    @staticmethod
    def get_component(fen: str,
                      component: FenComponent,
                      *,
                      validate: bool = True) -> str:
        """
        Get a specified component of the FEN as a string. If ``validate``,
        may raise ``ValueError`` via ``FenUtils.validate(fen)``.
        """
        return FenUtils.split_components(fen, validate=validate)[component]

    @staticmethod
    def index_of_component_start(fen: str,
                                 component: FenComponent,
                                 *,
                                 validate: bool = True) -> int:
        """
        Get the index of the first character of the specified component in the FEN.
        """
        components = FenUtils.split_components(fen, validate=validate)

        idx = sum(len(c) for c in components[:component]) + component
        assert FenUtils.get_component(fen, component, validate=False)[0] == components[component][0], 'Bad logic :('
        return idx

    @staticmethod
    def index_of_component_end(fen: str,
                               component: FenComponent,
                               *,
                               validate: bool = True) -> int:
        """
        Get the index of the last character of the specified component in the FEN.
        """
        components = FenUtils.split_components(fen, validate=validate)

        idx = sum(len(c) for c in components[:component + 1]) + component - 1
        assert FenUtils.get_component(fen, component, validate=False)[-1] == components[component][-1], 'Bad logic :('
        return idx

    @staticmethod
    def indices_of_component_delimeters(fen: str,
                                        component: FenComponent,
                                        *,
                                        validate: bool = True) -> (int, int):
        """
        Get the (index of the first char, index of the last char + 1) of the specified component in the FEN.
        """
        start_idx = FenUtils.index_of_component_start(fen, component, validate=validate)
        end_idx = len(FenUtils.get_component(fen, component, validate=False)) + start_idx
        return start_idx, end_idx
