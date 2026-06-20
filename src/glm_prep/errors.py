class ParseError(Exception):
    def __init__(
        self,
        message: str,
        path: list[str] | None = None,
        expected: str | None = None,
        received: object | None = None,
    ):
        self.message = message
        self.path = path or []
        self.expected = expected
        self.received = received

        super().__init__(self._format())

    def _format(self) -> str:
        parts = ["Invalid policy"]

        if self.path:
            parts.append(f"Location: {'.'.join(self.path)}")

        parts.append(f"\n{self.message}")

        if self.expected is not None:
            parts.append(f"\nExpected: {self.expected}")

        if self.received is not None:
            parts.append(f"\nReceived: {self.received!r}")

        return "\n".join(parts)


class DataContractError(RuntimeError):
    pass

class PolicyDefinitionError(RuntimeError):
    pass
