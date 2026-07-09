"""shared-logic 共通例外。"""


class SharedLogicError(Exception):
    """shared-logic 処理の基底例外。"""


class IncompleteFeatureVectorError(SharedLogicError):
    """MVP 8 軸 Feature が揃っていない。"""

    def __init__(self, missing_codes: tuple[str, ...]) -> None:
        self.missing_codes = missing_codes
        super().__init__(
            f"feature vector is incomplete; missing codes: {', '.join(missing_codes)}"
        )
