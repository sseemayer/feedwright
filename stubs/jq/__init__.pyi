from typing import Any, Iterable, Iterator, List, Mapping, Optional


class Result(Iterable[Any]):
    """Represents the results of running a compiled jq program.

    The real implementation is an iterator-like object with convenience
    methods to obtain the first element, all elements as a list, or a
    JSON-serialized text representation.
    """

    def first(self) -> Any: ...

    def text(self) -> str: ...

    def all(self) -> List[Any]: ...

    def iter(self) -> Iterator[Any]: ...

    def __iter__(self) -> Iterator[Any]: ...


class CompiledProgram:
    """A compiled jq program.

    Attributes
    ----------
    program_string: str
        The original program string passed to compile().
    """

    program_string: str

    def input_value(self, value: Any) -> Result: ...

    def input_values(self, values: Iterable[Any]) -> Result: ...

    def input_text(self, text: str, slurp: bool = False) -> Result: ...

    def input(self, *args: Any, text: Optional[str] = None) -> Result: ...


def compile(program: str, args: Optional[Mapping[str, Any]] = ...) -> CompiledProgram: ...

# Convenience single-call functions
def first(program: str, input: Any = ..., text: Optional[str] = ...) -> Any: ...

def text(program: str, input: Any = ..., text: Optional[str] = ...) -> str: ...

def all(program: str, input: Any = ..., text: Optional[str] = ...) -> List[Any]: ...

def iter(program: str, input: Any = ..., text: Optional[str] = ...) -> Iterator[Any]: ...
