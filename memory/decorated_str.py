import typing

PINK = '\033[95m'
BLUE = '\033[94m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
END = '\033[0m'


class DecoratedStr(object):
    def __init__(self, content: str, decorators: typing.List[str] = None):
        if decorators is None:
            decorators = []
        self.content = "{}{}{}".format("".join(decorators), content, END if len(decorators) else "")
        self.decoration_len = sum([len(decorator) for decorator in decorators]) + (len(END) if len(decorators) else 0)

    def __add__(self, other: typing.Union["DecoratedStr", str]) -> "DecoratedStr":
        if isinstance(other, str):
            res = DecoratedStr(self.content + other)
            res.decoration_len = self.decoration_len
        else:
            res = DecoratedStr(self.content + other.content)
            res.decoration_len = self.decoration_len + other.decoration_len
        return res

    def __str__(self):
        return self.content

    def __len__(self):
        return len(self.content) - self.decoration_len
