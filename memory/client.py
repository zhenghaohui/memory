import os
import shutil
import sys

import typing

from .concept import ConceptNode, Config
from .tui import _TUI
from .errors import *

IS_WIN = sys.platform == "win32"
EDITOR = "notepad" if IS_WIN else "vim"
CLEAR_CMD = "cls" if IS_WIN else "clear"


def ask_confirm(msg: str):
    while True:
        res = input("[ {} ? (y/n) >  ".format(msg))
        if res in ['y', 'yes']:
            return True
        if res in ['n', 'no']:
            return False


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
        self.cmd_cat('')

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

    def select_from_listing(self, idx: typing.Union[int, str]) -> ConceptNode:
        if isinstance(idx, str):
            if not idx.isdigit():
                raise ErrorCmdParams('unknown params: {}'.format(idx))
            idx = int(idx)
        if not 0 <= idx < len(self.listing):
            raise ErrorCmdParams("error index: {}, please select from [0, {})".format(idx, len(self.listing)))
        return self.listing[idx]

    def cmd_select(self, params: str):
        if params in ['/', '\\']:
            target = self.search(self.root)
        elif params.isdigit():
            target = self.search(self.select_from_listing(params))
        elif params in ['.'] or not params:
            target = self.search(self.selected)
        elif params in ['..'] and self.selected.parent is not None:
            target = self.selected.parent
        else:
            raise ErrorCmdParams('unknown params: {}'.format(params))
        if target is not None:
            self.select(target)

    def search(self, under: ConceptNode) -> typing.Optional[ConceptNode]:

        def get_node_with_depth(_root: ConceptNode, _depth: int = 0) -> typing.List[typing.Tuple[ConceptNode, int]]:
            res = [(_root, _depth)]
            for _node in after[_root]:
                res += get_node_with_depth(_node, _depth + 1)
            return res

        filtered = under.all_nodes_below
        try:
            while True:
                self.cmd_clear('')

                # build filtered tree
                after = {}
                filtered_set = set(filtered)
                for node in filtered:
                    after[node] = []
                roots = []
                for node in filtered:
                    if node.parent in filtered_set:
                        after[node.parent].append(node)
                    else:
                        roots.append(node)

                node_with_depth = []
                for root in roots:
                    node_with_depth += get_node_with_depth(root)

                filtered_tui = []
                for (idx, item) in enumerate(node_with_depth):
                    node, depth = item
                    assert isinstance(node, ConceptNode)
                    tmp = '[{:0>2d}] '.format(idx)
                    if not depth and node.parent is not None:
                        tmp += node.parent.path + os.path.sep
                    tmp += "  " * depth
                    tmp += "" if depth == 0 else "L "
                    tmp += "{}: {}".format(node.name, "".join(node.content))
                    filtered_tui.append(tmp)

                self.tui.register_tui_block('select.filtering...', filtered_tui, False)
                self.tui.refresh()

                # more key word
                keyword = input('[filtering] (enter idx or more keyword)  >  ').lower()
                if keyword == ":q":
                    self.tui.register_tui_block('select.message', ['aborted'], False)
                    return None
                if keyword.isdigit() and 0 <= int(keyword) < len(node_with_depth):
                    return node_with_depth[int(keyword)][0]

                # update filtered
                next_filtered = []
                for node in filtered:
                    if node.searchable.find(keyword) != -1:
                        next_filtered.append(node)
                if not next_filtered:
                    self.tui.register_tui_block('select.message', ['keyword miss: ' + keyword], False)
                    continue
                filtered = next_filtered
        except KeyboardInterrupt as e:
            return None

    def cmd_cd(self, params: str):
        if params.isdigit():
            self.select(self.select_from_listing(int(params)))
            return

        if params == '..':
            if self.selected.parent is None:
                raise ErrorCmdParams("can't go upper any more.")
            self.select(self.selected.parent)
            return

        if params == '/':
            self.select(self.root)
            return

        raise ErrorCmdParams('unknown params: {}'.format(params))

    def cmd_mkdir(self, params: str):
        dir_name = params
        if not dir_name:
            raise ErrorCmdParams('pls input dirname.')
        path = os.path.join(self.selected.abs_path, dir_name)
        if os.path.exists(path):
            raise ErrorCmdParams('{} already exists under {}'.format(dir_name, self.selected.path))
        os.mkdir(path)
        new_node = ConceptNode(dir_name, self.config, self.selected)
        os.system("{} {}".format(EDITOR, new_node.content_abs_path))
        new_node.refresh()
        if not os.path.exists(new_node.content_abs_path) or not new_node.content:
            self.tui.register_tui_block('mkdir.message', ['remove node as content unsaved or empty'], False)
            os.rmdir(new_node.abs_path)
        self.selected.refresh()
        self.cmd_ls('')

    def cmd_cat(self, params: str):
        if params.isdigit():
            target = self.select_from_listing(int(params))
        else:
            target = self.selected
        self.tui.register_tui_block('content of {}'.format(target.path),
                                    [target.name, ''] + target.content, False)

    def cmd_rm(self, params: str):
        target = self.select_from_listing(params)
        if ask_confirm('delete {}'.format(target.path)):
            self.tui.register_tui_block('rm.message', ['deleted: {}'.format(target.path)], False)
            shutil.rmtree(target.abs_path)
        else:
            self.tui.register_tui_block('rm.message', ['canceled, nothing happened'], False)
        self.selected.refresh()
        self.cmd_ls('')

    def cmd_vim(self, params: str):
        if params.isdigit():
            target = self.select_from_listing(params)
        elif not params:
            target = self.selected
        else:
            raise ErrorCmdParams('unknown params: {}'.format(params))
        os.system("{} {}".format(EDITOR, target.abs_path))
        target.refresh()

    def cmd_clear(self, params):
        if params:
            raise ErrorCmdParams('unknown params: {}'.format(params))
        os.system(CLEAR_CMD)

    def cmd_mv(self, params: str):
        params = [param.strip() for param in params.split(' ')]

        if len(params) != 2:
            raise ErrorCmdParams('unknown params: {}'.format(params))

        def select_from_param(param: str) -> ConceptNode:
            if param.isdigit():
                return self.select_from_listing(param)
            elif param == '.':
                return self.selected
            elif param == '..':
                if not self.selected.parent:
                    raise ErrorCmdParams("you can't use '..' at root node.")
                return self.selected.parent

        target = select_from_param(params[0])
        new_parent = select_from_param(params[1])

        if target.is_ancestor_of(new_parent):
            raise ErrorCmdParams("you can't move a node into anywhere under itself.")
        shutil.move(target.abs_path, new_parent.abs_path)
        old_parent = target.parent

        target.parent = new_parent
        new_parent.refresh()
        if old_parent is not None:
            old_parent.refresh()
        self.cmd_ls('')
        self.tui.register_tui_block('mv.message',
                                    ['node({}) moved to path({})'.format(target.name, new_parent.path)], False)

    def run(self):
        cmd_map = {}  # type: typing.Dict[str, typing.Callable]
        cmd_map.update({name: self.cmd_exit for name in [':q', 'exit', 'quit', 'q']})
        cmd_map.update({name: self.cmd_ls for name in ['ls', 'l']})
        cmd_map.update({name: self.cmd_select for name in ['select', 's', 'search']})
        cmd_map.update({name: self.cmd_cd for name in ['cd']})
        cmd_map.update({name: self.cmd_mkdir for name in ['mkdir', 'c', 'create']})
        cmd_map.update({name: self.cmd_cat for name in ['cat', 'p', 'print']})
        cmd_map.update({name: self.cmd_rm for name in ['rm', 'delete', 'd']})
        cmd_map.update({name: self.cmd_vim for name in ['vim', 'edit', 'note', 'notepad']})
        cmd_map.update({name: self.cmd_clear for name in ['clear']})
        cmd_map.update({name: self.cmd_mv for name in ['mv']})

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
