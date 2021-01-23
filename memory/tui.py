import os
import sys

from .decorated_str import *


class _TuiBlock(object):
    def __init__(self, title: typing.Union[str, DecoratedStr], content: typing.List[typing.Union[str, DecoratedStr]],
                 keep_alive: bool):
        self.title = title if isinstance(title, DecoratedStr) else DecoratedStr(title)
        self.content = [line if isinstance(line, DecoratedStr) else DecoratedStr(line) for line in content]
        self.keep_alive = keep_alive


def fold_string(content: DecoratedStr, max_length) -> str:
    return content.content if len(content) <= max_length else content.content[:max_length - 3] + "..."


class _TUI(object):

    def __init__(self):
        self.tui_blocks = {}  # type: typing.Dict[str, _TuiBlock]

    def register_tui_block(self, title: str, content: typing.List[typing.Union[str, DecoratedStr]], keep_alive: bool):
        self.tui_blocks[title] = _TuiBlock(title, content, keep_alive)

    def unregister_tui_block(self, title: str):
        if self.tui_blocks.get(title, None) is not None:
            del self.tui_blocks[title]

    def _draw(self):
        width = os.get_terminal_size().columns
        is_first_block = True
        for block in self.tui_blocks.values():
            print('{}═══  {}  '.format("╔" if is_first_block else "╠", block.title).ljust(width, '═'))
            is_first_block = False
            buf = DecoratedStr("")
            for line in block.content:
                if len(buf):
                    buf += "\n"
                buf += fold_string(DecoratedStr("║  ") + line, width)
            print(buf)
        print('╚'.ljust(width, '═'))

    def refresh(self):
        os.system('cls' if sys.platform == "win32" else 'clear')
        self._draw()
        self.tui_blocks = {key: block for key, block in self.tui_blocks.items() if block.keep_alive}
