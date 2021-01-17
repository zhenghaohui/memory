import os
import sys

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
        self.listing = []  # type: typing.List[ConceptNode]

        # use self.select() to modify this value
        self.selected = None  # type: typing.Optional[ConceptNode]
        self.tui = _TUI()

        self.select(self.root)

    def select(self, new_node: ConceptNode):
        self.selected = new_node
        self.tui.register_tui_block('selected', [
            '[path   ] {}'.format(self.selected.path),
            "[content] {}".format("".join(self.selected.content))], True)
        self.cmd_ls("")

    def cmd_exit(self, params: str):
        if params != '':
            raise ErrorCmdParams(params)
        exit(0)

    def cmd_ls(self, params):
        if params != '':
            raise ErrorCmdParams(params)
        self.listing = self.selected.sub_nodes
        self.tui.register_tui_block('sub nodes', ['[{:0>2d}] {}: {}'.format(idx, node.name, "".join(node.content))
                                                  for (idx, node) in enumerate(self.listing)], True)

    def cmd_select(self, params: str):
        pass

    def cmd_cd(self, params: str):
        if params.isdigit():
            idx = int(params)
            if idx >= len(self.listing):
                raise ErrorCmdParams("error index: {}, please select from [0, {})".format(idx, len(self.listing)))
            self.select(self.listing[idx])
            return

        if params == '..':
            if self.selected.parent is None:
                raise ErrorCmdParams("can't go upper any more.")
            self.select(self.selected.parent)
            return

        if params == '/':
            self.select(self.root)
            return

    def cmd_mkdir(self, params: str):
        dir_name = params
        if not dir_name:
            raise ErrorCmdParams('pls input dirname.')
        path = os.path.join(self.selected.abs_path, dir_name)
        if os.path.exists(path):
            raise ErrorCmdParams('{} already exists under {}'.format(dir_name, self.selected.path))
        os.mkdir(path)
        new_node = ConceptNode(dir_name, self.config, self.selected)
        os.system("{} {}".format("notepad" if sys.platform == "win32" else "vim", new_node.content_abs_path))
        new_node.refresh()
        if not os.path.exists(new_node.content_abs_path) or not new_node.content:
            self.tui.register_tui_block('mkdir.message', ['remove node as content unsaved or empty'], False)
            os.rmdir(new_node.abs_path)

    def cmd_cat(self, params):
        self.tui.register_tui_block('content of {}'.format(self.selected.path),
                                    [self.selected.name, ''] + self.selected.content, False)

    def run(self):
        cmd_map = {}  # type: typing.Dict[str, typing.Callable]
        cmd_map.update({name: self.cmd_exit for name in [':q', 'exit', 'quit', 'q']})
        cmd_map.update({name: self.cmd_ls for name in ['ls', 'l']})
        cmd_map.update({name: self.cmd_select for name in ['select', 's', 'search']})
        cmd_map.update({name: self.cmd_cd for name in ['cd']})
        cmd_map.update({name: self.cmd_mkdir for name in ['mkdir', 'c', 'create']})
        cmd_map.update({name: self.cmd_cat for name in ['cat', 'p', 'print']})
        while True:
            try:
                self.tui.refresh()
                cmd = input('cmd > ')
                cmd = cmd.strip()
                cmd_name = cmd[:(cmd + " ").find(' ')].strip()
                cmd_params = cmd[len(cmd_name):].strip()
                cmd_func = cmd_map.get(cmd_name, None)

                if cmd_func is None:
                    # select from listing ?
                    if cmd_name.isdigit() and not cmd_params:
                        cmd_func = self.cmd_cd
                        cmd_params = cmd_name
                    else:
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
