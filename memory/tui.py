import os
import sys
import typing


class _TuiBlock(object):
    def __init__(self, title: str, content: typing.List[str], keep_alive: bool):
        self.title = title
        self.content = content
        self.keep_alive = keep_alive


class _TUI(object):

    def __init__(self):
        self.tui_blocks = {}  # type: typing.Dict[str, _TuiBlock]

    def register_tui_block(self, title: str, content: typing.List[str], keep_alive: bool):
        self.tui_blocks[title] = _TuiBlock(title, content, keep_alive)

    def _draw(self):
        width = 100
        is_first_block = True
        for block in self.tui_blocks.values():
            print('{}═══  {}  '.format("╔" if is_first_block else "╠", block.title).ljust(width, '═'))
            is_first_block = False
            print('║  {}'.format("\n║  ".join(block.content)))
        print('╚'.ljust(width, '═'))

    def refresh(self):
        os.system('cls' if sys.platform == "win32" else 'clear')
        self._draw()
        self.tui_blocks = {key: block for key, block in self.tui_blocks.items() if block.keep_alive}
