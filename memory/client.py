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


def fold_string(content, max_length=100):
    return content if len(content) <= max_length else content[:max_length - 3] + "..."


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
            fold_string("[content] {}".format(self.selected.one_line_content))], True)
        self.cmd_ls("")
        self.cmd_cat('')

    def cmd_exit(self, params: str):
        if params == '-h':
            self.cmd_help('exit')
            return

        if params != '':
            raise ErrorCmdParams(params)
        exit(0)

    def cmd_ls(self, params):
        if params == '-h':
            self.cmd_help('ls')
            return

        if params != '':
            raise ErrorCmdParams(params)
        self.listing = self.selected.sub_nodes
        if not self.listing:
            self.tui.unregister_tui_block('listing...')
            return
        self.tui.register_tui_block('listing...', ['[{:0>2d}] {}: {}'.format(idx, node.name, "".join(node.content))
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
        if params == '-h':
            self.cmd_help('select')
            return

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

    def search(self, under: ConceptNode, title='filtering') -> typing.Optional[ConceptNode]:

        self.tui.unregister_tui_block('listing...')

        def get_node_with_depth(_root: ConceptNode, _depth: int = 0, is_last=False) \
                -> typing.List[typing.Tuple[ConceptNode, int, bool]]:
            res = [(_root, _depth, is_last)]
            for _node in after[_root]:
                res += get_node_with_depth(_node, _depth + 1, _node == after[_root][-1])
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
                tree_decoration = ""
                last_depth = None
                last_is_last_sub = False
                for (idx, item) in enumerate(node_with_depth):
                    node, depth, is_last_sub = item
                    assert isinstance(node, ConceptNode)
                    tmp = '[{:0>2d}] '.format(idx)
                    if not depth and node.parent is not None:
                        tmp += node.parent.path + os.path.sep

                    if last_depth is not None:
                        if depth > last_depth:
                            tree_decoration += "   " if last_is_last_sub else "║  "
                        elif depth < last_depth:
                            tree_decoration = tree_decoration[:-3 * (last_depth - depth)]
                    last_depth = depth
                    last_is_last_sub = is_last_sub

                    tmp += (tree_decoration + ("╠═ " if not is_last_sub else "╚═ "))[3:]
                    tmp += "{}: {}".format(node.name, node.one_line_content)
                    filtered_tui.append(fold_string(tmp))

                self.tui.register_tui_block('select.filtering...', filtered_tui, False)
                self.tui.refresh()

                # more key word
                keyword = input('[{}] (enter idx or more keyword)  >  '.format(title)).lower()
                if keyword == ":q":
                    self.tui.register_tui_block('select.message', ['aborted'], False)
                    return None
                if keyword.isdigit() and 0 <= int(keyword) < len(node_with_depth):
                    return node_with_depth[int(keyword)][0]

                # update filtered
                parsed_keyword = ""
                for char in keyword:
                    if char in ['-', ' ', '_', '.']:
                        continue
                    parsed_keyword += char
                keyword = parsed_keyword
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
        if params == '-h':
            self.cmd_help('cd')
            return

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
        if params == '-h':
            self.cmd_help('mkdir')
            return

        dir_name = params
        if not dir_name:
            raise ErrorCmdParams('pls input dirname.')
        path = os.path.join(self.selected.abs_path, dir_name)
        if os.path.exists(path):
            raise ErrorCmdParams('{} already exists under {}'.format(dir_name, self.selected.path))
        os.mkdir(path)
        new_node = ConceptNode(dir_name, self.config, self.selected)
        os.system("{} '{}'".format(EDITOR, new_node.content_abs_path))
        new_node.refresh()
        if not os.path.exists(new_node.content_abs_path):
            self.tui.register_tui_block('mkdir.message', ['remove node as content unsaved or empty'], False)
            os.rmdir(new_node.abs_path)
        self.selected.refresh()
        self.cmd_ls('')

    def cmd_cat(self, params: str):
        if params == '-h':
            self.cmd_help('cat')
            return

        if params.isdigit():
            target = self.select_from_listing(int(params))
        else:
            target = self.selected
        self.tui.register_tui_block('content of {}'.format(target.path), target.content, False)

    def cmd_rm(self, params: str):
        if params == '-h':
            self.cmd_help('rm')
            return

        target = self.select_from_listing(params)
        if ask_confirm('delete {}'.format(target.path)):
            self.tui.register_tui_block('rm.message', ['deleted: {}'.format(target.path)], False)
            shutil.rmtree(target.abs_path)
        else:
            self.tui.register_tui_block('rm.message', ['canceled, nothing happened'], False)
        self.selected.refresh()
        self.cmd_ls('')

    def cmd_vim(self, params: str):
        if params == '-h':
            self.cmd_help('vim')
            return

        if params.isdigit():
            target = self.select_from_listing(params)
        elif not params:
            target = self.selected
        else:
            raise ErrorCmdParams('unknown params: {}'.format(params))
        os.system("{} '{}'".format(EDITOR, target.content_abs_path))
        target.refresh()
        self.select(self.selected)

    def cmd_clear(self, params):
        if params:
            raise ErrorCmdParams('unknown params: {}'.format(params))
        os.system(CLEAR_CMD)

    def cmd_mv(self, params: str):
        if params == '-h':
            self.cmd_help('mv')
            return

        params = [param.strip() for param in params.split(' ') if param.strip()]

        if len(params) not in [0, 1, 2]:
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

        def notify(msg: typing.List[str]):
            self.tui.register_tui_block('mv.message', msg, False)

        if len(params) == 0:
            target = self.selected
            new_parent = self.search(self.root, 'where you want to move to ?')
        elif len(params) == 1:
            target = select_from_param(params[0])
            new_parent = self.search(self.root, 'where you want to move to ?')
        else:
            target = select_from_param(params[0])
            new_parent = select_from_param(params[1])

        if not isinstance(target, ConceptNode) or not isinstance(new_parent, ConceptNode):
            notify(['Canceled.'])
            return

        if target.is_ancestor_of(new_parent):
            notify(["Failed: you can't move a node into anywhere under itself."])
            return

        if target.name in [node.name for node in new_parent.sub_nodes]:
            notify(['Failed: {} already exist under {}'.format(target.name, new_parent.path)])
            return

        shutil.move(target.abs_path, new_parent.abs_path)
        old_parent = target.parent
        target.parent = new_parent
        new_parent.refresh()
        if old_parent is not None:
            old_parent.refresh()
        self.cmd_ls('')
        self.select(self.selected)
        notify(['Succeed: node({}) moved to path({})'.format(target.name, new_parent.path)])

    def cmd_help(self, params):
        help_msg = []
        if not params or params == 'cd':
            help_msg += ['─' * 4] if len(help_msg) > 0 else []
            help_msg += ['cd                                navigate',
                         '  1. cd [idx]                     navigate to child node',
                         '  2. cd /                         navigate to root node']

        if not params or params == 'mkdir':
            help_msg += ['─' * 4] if len(help_msg) > 0 else []
            help_msg += ['mkdir, create, c                  create concept',
                         '  1. c                            create concept under current node']

        if not params or params == 'ls':
            help_msg += ['─' * 4] if len(help_msg) > 0 else []
            help_msg += ['ls, list, l                       list child nodes',
                         '  1.  l                           list child nodes of current node']

        if not params or params == 'vim':
            help_msg += ['─' * 4] if len(help_msg) > 0 else []
            help_msg += ['vim, edit, note, notepad          edit content',
                         '  1.  vim                         edit content of current node',
                         '  2.  vim [idx]                   edit content of child node']

        if not params or params == 'select':
            help_msg += ['─' * 4] if len(help_msg) > 0 else []
            help_msg += ['select, search, s                 search & select node',
                         '  1.  s                           search & select node under current node',
                         '  2.  s /                         search & select node under root node',
                         '  3.  s [idx]                     search & select node under child node']

        if not params or params == 'rm':
            help_msg += ['─' * 4] if len(help_msg) > 0 else []
            help_msg += ['rm, remove                        remove all nodes',
                         '  1.  rm [idx]                    remove all nodes under child node']

        if not params or params == 'cat':
            help_msg += ['─' * 4] if len(help_msg) > 0 else []
            help_msg += ['cat, print, p                     print content',
                         '  1.  p                           print content of current node',
                         '  2.  p [idx]                     print content of child node']

        if not params or params == 'mv':
            help_msg += ['─' * 4] if len(help_msg) > 0 else []
            help_msg += ['mv, move                          move',
                         '  1.  move [idx] [idx]            move a child node to ano child node',
                         '  2.  move [idx] ..               move a child node up']

        if not params or params == 'exit':
            help_msg += ['─' * 4] if len(help_msg) > 0 else []
            help_msg += ['exit, quit, q, :q                 exit memory']

        self.tui.register_tui_block('help.message', help_msg, False)

    def run(self):
        cmd_map = {}  # type: typing.Dict[str, typing.Callable]
        cmd_map.update({name: self.cmd_help for name in ['h', 'help']})
        cmd_map.update({name: self.cmd_cd for name in ['cd']})
        cmd_map.update({name: self.cmd_mkdir for name in ['mkdir', 'c', 'create']})
        cmd_map.update({name: self.cmd_vim for name in ['vim', 'edit', 'note', 'notepad']})
        cmd_map.update({name: self.cmd_select for name in ['select', 's', 'search']})
        cmd_map.update({name: self.cmd_rm for name in ['rm', 'remove']})
        cmd_map.update({name: self.cmd_cat for name in ['cat', 'p', 'print']})
        cmd_map.update({name: self.cmd_ls for name in ['ls', 'l', 'list']})
        cmd_map.update({name: self.cmd_mv for name in ['mv', 'move']})
        cmd_map.update({name: self.cmd_exit for name in [':q', 'exit', 'quit', 'q']})

        cmd_map.update({name: self.cmd_clear for name in ['clear']})

        help_msg = ['help, h                           show help document',
                    '  2. h                            show help document of all commands',
                    '  2. h [command]                  show help document of [command]',
                    '  3. [command] -h                 show help document of [command]']
        self.tui.register_tui_block('help.message', help_msg, False)

        while True:
            try:
                self.cmd_clear('')
                self.tui.refresh()
                cmd = input('memory > ')
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
