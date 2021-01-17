import os

import typing

from .concept import ConceptNode, Config
from .tui import _TUI
from .errors import *


def all_nodes_below(root: ConceptNode):
    res = [root]
    cur = 0
    while cur < len(res):
        res += res[cur].sub_nodes
        cur += 1
    return res


class Client(object):

    def __init__(self, root_path: str):
        workspace, root_name = os.path.split(root_path)
        self.config = Config(workspace)
        self.root = ConceptNode(root_name, self.config)

        # use self.select() to modify this value
        self.selected = None  # type: typing.Optional[ConceptNode]
        self.tui = _TUI()

        self.select(self.root)

    def select(self, new_node: ConceptNode):
        self.selected = new_node
        self.tui.register_tui_block('selected', [
            '[path   ] {}'.format(self.selected.path),
            "[content] {}".format("".join(self.selected.content))], True)

    def cmd_exit(self, params: str):
        if params != '':
            raise ErrorCmdParams(params)
        exit(0)

    def run(self):
        cmd_map = {}  # type: typing.Dict[str, typing.Callable]
        cmd_map.update({name: self.cmd_exit for name in [':q', 'exit', 'quit', 'q']})
        while True:
            try:
                self.tui.refresh()
                cmd = input('cmd > ')
                cmd = cmd.strip()
                cmd_name = cmd[:(cmd + " ").find(' ')].strip()
                cmd_params = cmd[len(cmd_name):].strip()
                cmd_func = cmd_map.get(cmd_name, None)

                if cmd_func is None:
                    raise CmdNotFound(cmd_name)
                cmd_func(cmd_params)

            except KeyboardInterrupt:
                continue

            except ErrorCmdParams as err:
                self.tui.register_tui_block('ERROR: {}'.format(ErrorCmdParams.__name__), [str(err)], False)
                continue

            except CmdNotFound as err:
                self.tui.register_tui_block('ERROR: {}'.format(CmdNotFound.__name__), [str(err)], False)
                continue
