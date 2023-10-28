#!/usr/bin/env python3

import argparse
import json
from typing import Any, \
                   Dict, \
                   List, \
                   Optional, \
                   Sequence, \
                   Union

##
## Helpers
##

class Stream:
    """
    A class which wraps around a :class:`Sequence <typing.Sequence>`
    to provide helpful methods for interaction.
    """

    _data: Sequence
    _cursor: int
    _end: int

    def __init__(self, data: Sequence):
        """
        Initializes an instance of :class:`Stream <.Stream>`.

        :param data: The data to initialize the stream with.
        :type data: :class:`Sequence <typing.Sequence>`
        """

        self._data = data
        self._cursor = 0
        self._end = len(data)

    def peek(self) -> Optional[Sequence]:
        """
        Peeks at the next element in the stream.

        :return: The next element, if any.
        :rtype: Optional[:class:`Sequence <typing.Sequence>`]
        """

        if self._cursor < 0 or self._cursor >= self._end:
            return None

        return self._data[self._cursor]

    def next(self) -> Sequence:
        """
        Gets the next element in the stream, or
        raises an exeption if there isn't one.

        :raises: :exc:`IndexError`
        :return: The next element.
        :rtype: :class:`Sequence <typing.Sequence>`
        """

        next_ = self._data[self._cursor]
        self._cursor += 1

        return next_


def skip_whitespace(stream: Stream) -> None:
    """
    A helper function for skipping over whitespace.

    Only to be used by the tokenizer.

    :param stream: The stream to skip whitespace for.
    :type stream: :class:`Stream <.Stream>`
    """

    while True:
        char = stream.peek()

        if char is None or char.isspace() is False:
            break

        # Otherwise, consume
        stream.next()


def consume(stream: Stream, expected: Sequence) -> None:
    """
    Consumes an element from the stream, ensuring it matches
    the expected value.

    :raises: :exc:`ValueError`
    :param stream: The stream to consume from.
    :type stream: :class:`Stream <.Stream>`
    :param expected: The expected value.
    :type expected: :class:`Sequence <typing.Sequence>`
    """

    if (actual := stream.next()) != expected:
        raise ValueError(
            f"Expected '{expected}', got '{actual}'"
        )


##
## Tokenizer
##

def tokenize_str(stream: Stream) -> str:
    """
    Tokenizes a string.

    :param stream: The stream to tokenize.
    :type stream: :class:`Stream <.Stream>`
    :return: The tokenized string.
    :rtype: :class:`str`
    """

    string = ["\""]

    # Consume first quote of string
    consume(stream, "\"")

    # Keep appending until end of string
    while True:
        char = stream.next()
        string.append(char)

        if char == "\"":
            break

    return "".join(string)


def tokenize_num(stream: Stream) -> Union[int, float]:
    """
    Tokenizes a number.

    :param stream: The stream to tokenize.
    :type stream: :class:`Stream <.Stream>`
    :return: The tokenized number.
    :rtype: Union[:class:`int`, :class:`float`]
    """

    num = []
    is_float = False

    # Keep tokenizing until non-numeric
    while True:
        char = stream.peek()

        if char.isnumeric() is True:
            num.append(stream.next())

        elif char == ".":
            if is_float is True:
                raise ValueError(f"Invalid numeric at index '{stream._cursor}'")

            is_float = True
            num.append(stream.next())

        else:
            break

    joined = "".join(num)

    if is_float is True:
        return float(joined)

    return int(joined)


def tokenize(stream: Stream) -> List[str]:
    """
    Entry point for tokenizing a stream.

    :param stream: The stream to tokenize.
    :type stream: :class:`Stream <.Stream>`
    :return: The tokens.
    :rtype: List[:class:`str`]
    """

    tokens = []

    while True:
        # Ignore whitespace
        skip_whitespace(stream)

        # If at end, stop
        if stream._cursor >= stream._end:
            break

        # Check what is being tokenized
        char = stream.peek()

        # Tokenize single chars
        if char in "{}[]:,":
            token = stream.next()

        # Tokenize strings
        elif char == "\"":
            token = tokenize_str(stream)

        # Tokenize numbers
        elif char.isnumeric() is True:
            token = tokenize_num(stream)

        # Otherwise, fail
        else:
            raise ValueError(
                f"Unexpected char '{char}' at index '{stream._cursor}'"
            )

        # Append token
        tokens.append(token)

    # Return all tokens after finishing
    return tokens


##
## Parser
##

def parse_str(stream: Stream) -> str:
    """
    Parses a string.

    :param stream: The stream to parse.
    :type stream: :class:`Stream <.Stream>`
    :return: The string.
    :rtype: :class:`str`
    """

    return stream.next()[1:-1]


def parse_num(stream: Stream) -> Union[int, float]:
    """
    Parses a number.

    :param stream: The stream to parse.
    :type stream: :class:`Stream <.Stream>`
    :return: The number.
    :rtype: Union[:class:`int`, :class:`float`]
    """

    num = stream.next()

    if "." in num:
        return float(num)

    return int(num)


def parse_value(stream: Stream) -> Any:
    """
    Parses a JSON value.

    :param stream: The stream to parse.
    :type stream: :class:`Stream <.Stream>`
    :return: The value.
    :rtype: :obj:`Any <typing.Any>`
    """

    token = stream.peek()

    if token == "{":
        return parse_dict(stream)

    if token == "[":
        return parse_list(stream)

    if isinstance(token, int) or isinstance(token, float):
        return stream.next()

    if token[0] == "\"":
        return parse_str(stream)

    # Otherwise, invalid
    raise ValueError(
        f"Unexpected JSON value: '{token}'"
    )


def parse_dict(stream: Stream) -> Dict[Any, Any]:
    """
    Parses a dict.

    :param stream: The stream to parse.
    :type stream: :class:`Stream <.Stream>`
    :return: The dict.
    :rtype: Dict[:obj:`Any <typing.Any>`, :obj:`Any <typing.Any>`]
    """

    dict_ = {}

    # Consume dict start
    consume(stream, "{")

    # Handle possible values
    while True:
        key = parse_str(stream)
        consume(stream, ":")
        value = parse_value(stream)

        dict_[key] = value

        if stream.peek() == ",":
            stream.next()
        else:
            break

    # Consume dict end
    consume(stream, "}")

    return dict_


def parse_list(stream: Stream) -> List[Any]:
    """
    Parses a list.

    :param stream: The stream to parse.
    :type stream: :class:`Stream <.Stream>`
    :return: The list.
    :rtype: List[:obj:`Any <typing.Any>`]
    """

    list_ = []

    # Consume list start
    consume(stream, "[")

    # Handle values
    while stream.peek() != "]":
        list_.append(parse_value(stream))

        if stream.peek() == ",":
            stream.next()
        else:
            break

    # Consume list end
    consume(stream, "]")

    return list_


def parse(stream: Stream) -> Union[Dict[Any, Any], List[Any]]:
    """
    Parses a stream of tokens into an AST.

    :param stream: The stream to parse.
    :type stream: :class:`Stream <.Stream>`
    :return: The tree.
    :rtype: Union[Dict[:obj:`Any <typing.Any>`, :obj:`Any <typing.Any>`], List[:obj:`Any <typing.Any>`]]
    """

    token = stream.peek()

    if token == "{":
        tree = parse_dict(stream)

    elif token == "[":
        tree = parse_list(stream)

    else:
        raise ValueError(
            f"Unexpected token number '{stream._cursor}'"
        )

    # Ensure end of strem was reached
    if stream._cursor < stream._end:
        raise ValueError(
            f"Unexpected token at end of file: '{stream.peek()}'"
        )

    return tree

##
## Main
##

def main() -> None:
    parser = argparse.ArgumentParser(
        description="a JSON parser experiment",
        allow_abbrev=False
    )

    parser.add_argument(
        "file",
        help="the file to parse"
    )

    args = parser.parse_args()

    with open(args.file, "r") as f:
        data = f.read()

    tokens = tokenize(Stream(data))
    tree = parse(Stream(tokens))

    print(json.dumps(tree, indent=2))


if __name__ == "__main__":
    try:
        main()

    except (EOFError, KeyboardInterrupt):
        pass
