import typing


class _MessageBlock(object):
    def __init__(self, title: str, content: typing.List[str], keep_alive=False):
        self.title = title
        self.content = content
        pass
