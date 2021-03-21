import math
import os
import shutil
import sys

import typing

from .concept import ConceptNode
from .config import Config
from .search_engine import SearchEngine, SearchableNode
from .tui import _TUI
from .errors import *
from .decorated_str import *
from prompt_toolkit import prompt


IS_WIN = sys.platform == "win32"
EDITOR = "notepad" if IS_WIN else "vim"
CLEAR_CMD = "cls" if IS_WIN else "clear"


def ask_confirm(msg: typing.Union[str, DecoratedStr]):
    while True:
        res = prompt("[ {} ? (y/n) >  ".format(msg))
        if res in ['y', 'yes']:
            return True
        if res in ['n', 'no']:
            return False


class Client(object):

    def __init__(self, root_path: str):
        workspace, root_name = os.path.split(root_path)
        self.config = Config(workspace)
        self.root = ConceptNode(root_name, self.config)
        self.listing_nodes = []  # type: typing.List[ConceptNode]

        # use self.select() to modify this value
        self.selected = None  # type: typing.Optional[ConceptNode]
        self.tui = _TUI()

        self.select(self.root)

    def select(self, new_node: ConceptNode):
        self.selected = new_node
        self.tui.register_tui_block('selected', [
            '[path   ] {}'.format(self.selected.path),
            "[content] {}".format(self.selected.summary)], True)
        self.cmd_ls("")
        self.cmd_cat('')

    def cmd_exit(self, params: str):
        if params == '-h':
            self.cmd_help('exit')
            return

        if params != '':
            raise ErrorCmdParams(params)
        exit(0)

    def list(self, nodes: typing.List[ConceptNode]):
        self.listing_nodes = nodes
        self.tui.register_tui_block('listing...',
                                    ['[{:0>2d}] {}: {}'.format(idx, node.decorated_name, node.summary)
                                     for (idx, node) in enumerate(nodes)], True)

    def cancel_list(self):
        self.tui.unregister_tui_block('listing...')

    def cmd_ls(self, params):
        if params == '-h':
            self.cmd_help('ls')
            return
        if params != '':
            raise ErrorCmdParams(params)
        self.list(self.selected.sub_nodes[:15])

    def select_from_listing(self, idx: typing.Union[int, str]) -> ConceptNode:
        if isinstance(idx, str):
            if not idx.isdigit():
                raise ErrorCmdParams('unknown params: {}'.format(idx))
            idx = int(idx)
        if not 0 <= idx < len(self.listing_nodes):
            raise ErrorCmdParams("error index: {}, please select from [0, {})".format(idx, len(self.listing_nodes)))
        return self.listing_nodes[idx]

    def cmd_select(self, params: str):
        if params == '-h':
            self.cmd_help('select')
            return

        if params in ['/', '\\'] or not params:
            target = self.search(self.root)
        elif params.isdigit():
            target = self.search(self.select_from_listing(params))
        elif params in ['.']:
            target = self.search(self.selected)
        elif params in ['..'] and self.selected.parent is not None:
            target = self.selected.parent
        else:
            raise ErrorCmdParams('unknown params: {}'.format(params))
        if target is not None:
            self.select(target)

    def search(self, under: ConceptNode, title='filtering') -> typing.Optional[ConceptNode]:

        self.tui.unregister_tui_block('listing...')
        search_engine = SearchEngine(under, self.config.user_config['combines'])
        self.tui.register_tui_block('select.2 tips', [
            '1. Memory will split your input automatically into several keywords by space char. ',
            "2. Use ' ' if u are not sure. eg. choose 'test engine' but not 'testEngine'.",
            "3. Use 'Ctrl + C' or input ':q' to exit selecting"
        ], False)

        try:
            while True:
                self.cmd_clear('')
                alive_searchable_nodes = search_engine.get_alive_nodes_in_dfs_order()

                # build filtered tree
                filtered_tui = []
                tree_decoration = ""
                last_depth = None
                last_is_last_sub = False
                alive_searchable_nodes = alive_searchable_nodes[:self.config.max_showing_nodes_when_searching]
                for (idx, searchable_node) in enumerate(alive_searchable_nodes):
                    assert isinstance(searchable_node, SearchableNode)
                    is_last_sub = searchable_node.is_last_alive_sub_node
                    node = searchable_node.concept_node
                    depth = searchable_node.alive_depth
                    assert isinstance(node, ConceptNode)
                    tmp = DecoratedStr('[{:0>2d}] '.format(idx))

                    # if not depth and node.parent is not None:
                    #     tmp += node.parent.path + os.path.sep

                    if last_depth is not None:
                        if depth > last_depth:
                            tree_decoration += "   " if last_is_last_sub else "║  "
                        elif depth < last_depth:
                            tree_decoration = tree_decoration[:-3 * (last_depth - depth)]
                    last_depth = depth
                    last_is_last_sub = is_last_sub

                    tmp += (tree_decoration + ("╠═ " if not is_last_sub else "╚═ "))[3:]
                    tmp += "(🌡️{})".format(searchable_node.concept_node.click_count)
                    path = searchable_node.get_path_under_alive_parent()
                    tmp += path[:path.rfind('/') + 1] + searchable_node.concept_node.decorated_name.content
                    tmp += " " + node.summary
                    if len(searchable_node.matched_keyword) > 0:
                        tmp += " ("
                        tmp += DecoratedStr(" ".join(searchable_node.matched_keyword), [YELLOW])
                        tmp += ")"
                    filtered_tui.append(tmp)

                nodes_hidden = max(0, len(alive_searchable_nodes) - self.config.max_showing_nodes_when_searching)
                if nodes_hidden:
                    buf = " {} items hidden ".format(nodes_hidden)
                    decorator = '-' * int(math.floor((self.config.tui_width - 3 - len(buf)) / 2))
                    filtered_tui.append('{}{}{}'.format(decorator, buf, decorator))

                self.tui.register_tui_block('select.1 filtering...', filtered_tui, True)
                self.tui.register_tui_block('select.3 message', [
                    'keyword: {}'.format(", ".join(search_engine.keywords)),
                    'ignored: {}'.format(", ".join(search_engine.miss_keywords))
                ], True)
                self.tui.refresh()

                # more key word
                def thinking() -> typing.Union[ConceptNode, str, None]:
                    previewing = None
                    while True:
                        keyword = prompt('[{}] (enter idx or more keyword)  >  '.format(title))
                        if keyword.lower() in [":s", ":select"]:
                            if previewing is not None:
                                return previewing.concept_node
                            else:
                                return search_engine.alive_root.concept_node
                        if keyword.lower() in [":q", ":quit"]:
                            return None
                        if keyword.isdigit() and 0 <= int(keyword) < len(alive_searchable_nodes):
                            target_node = alive_searchable_nodes[int(keyword)]
                            if previewing is not None and target_node == previewing:
                                return previewing.concept_node
                            previewing = target_node
                            previewing.concept_node.after_click()
                            self.tui.register_tui_block('preview of {}'.format(previewing.concept_node.name),
                                                        [line.strip('\n') for line in previewing.concept_node.content],
                                                        False)
                            self.tui.refresh()
                            continue
                        return keyword

                think_result = thinking()
                if not isinstance(think_result, str):
                    self.tui.unregister_tui_block('select.1 filtering...')
                    self.tui.unregister_tui_block('select.3 message')
                if isinstance(think_result, ConceptNode):
                    return think_result
                if isinstance(think_result, str):
                    keyword = think_result
                    search_engine.add_keywords(keyword)
                    continue
                assert think_result is None
                raise KeyboardInterrupt()

        except KeyboardInterrupt as e:
            self.tui.unregister_tui_block('select.1 filtering...')
            self.tui.unregister_tui_block('select.3 message')
            self.tui.register_tui_block('select.message', ['aborted'], False)
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

        for node in self.listing_nodes:
            if node.name == params:
                self.select(node)
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
        with open(new_node.content_abs_path, 'w') as fd:
            print('\n'.join(['', '---', '']), file=fd)
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
        self.tui.register_tui_block('content of {}'.format(target.path),
                                    [line.strip('\n') for line in target.content], False)

    def cmd_rm(self, params: str):
        if params == '-h':
            self.cmd_help('rm')
            return

        target = self.select_from_listing(params)
        if ask_confirm(DecoratedStr('delete {}'.format(target.decorated_path), RED)):
            self.tui.register_tui_block('rm.message', ['deleted: {}'.format(target.decorated_path)], False)
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
        origin_params = params
        params = [param.strip() for param in params.split(' ') if param.strip()]

        if len(params) not in [0, 1, 2]:
            if params[0] == "." and len(params) > 1:
                params = ['.', origin_params[1:].strip()]
            else:
                raise ErrorCmdParams('unknown params: {}'.format(params))

        def select_from_param(param: str) -> typing.Optional[ConceptNode]:
            if param.isdigit():
                return self.select_from_listing(param)
            elif param == '.':
                return self.selected
            elif param == '..':
                if not self.selected.parent:
                    raise ErrorCmdParams("you can't use '..' at root node.")
                return self.selected.parent
            else:
                for node in self.listing_nodes:
                    if node.name != param:
                        continue
                    return node
            return None

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
            if new_parent is None and target.parent is not None:
                # rename
                new_name = params[1]
                confirm_msg = "move {} to {}".format(DecoratedStr(target.name, RED), DecoratedStr(new_name, GREEN))
                confirm_msg = DecoratedStr(confirm_msg, RED)
                if ask_confirm(confirm_msg):
                    new_abs_path = os.path.join(target.parent.abs_path, new_name)
                    if os.path.exists(new_abs_path):
                        notify(["node {} already exists".format(new_name)])
                        return
                    shutil.move(target.abs_path, new_abs_path)
                    target.name = new_name
                    target.refresh()
                    target.parent.refresh()
                    notify(["renamed to {}".format(new_name)])
                    self.cmd_ls('')
                    return
            if target is None or new_parent is None:
                raise ErrorCmdParams('unknown params: {}'.format(params))

        if not isinstance(target, ConceptNode) or not isinstance(new_parent, ConceptNode):
            notify(['Canceled.'])
            return

        if target.is_ancestor_of(new_parent):
            notify(["Failed: you can't move a node into anywhere under itself."])
            return

        if target.name in [node.name for node in new_parent.sub_nodes]:
            notify(
                ['Failed: {} already exist under {}'.format(DecoratedStr(target.name, RED), new_parent.decorated_path)])
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

    def cmd_path(self, params):
        if params == '-h':
            self.cmd_help('path')
            return
        if params != "":
            raise ErrorCmdParams('unknown params: {}'.format(params))
        path_nodes = [self.selected]
        while path_nodes[-1].parent is not None:
            path_nodes.append(path_nodes[-1].parent)
        path_nodes.reverse()
        self.list(path_nodes)

    def cmd_help(self, params):
        help_msg = []
        if not params or params == 'path':
            help_msg += ['─' * 4] if len(help_msg) > 0 else []
            help_msg += ['path                              show path info of current selected node']

        if not params or params == 'cd':
            help_msg += ['─' * 4] if len(help_msg) > 0 else []
            help_msg += ['cd                                navigate',
                         '  1. cd [listing.idx]             navigate to child node',
                         '  2. cd /                         navigate to root node',
                         '  3. cd [listing.name]            navigate to child node']

        if not params or params == 'mkdir':
            help_msg += ['─' * 4] if len(help_msg) > 0 else []
            if params == 'mkdir':
                help_msg += ['!!! It is recommended to use meaningful name of node, '
                             'just think they will fill your screen when seaching']
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
                         '  1.  move [node1] [node2]        move the node1 under node2',
                         '  2.  [node1], [node2] could be:  ',
                         '      a.  [listing.name]          the sub node show in listing',
                         '      b.  [listing.idx]           the sub node show in listing',
                         '      c.  ..                      the parent node of selected']

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
        cmd_map.update({name: self.cmd_path for name in ['path']})

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
                cmd = prompt('memory > ')
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
                        # select by name ?
                        for node in self.listing_nodes:
                            if node.name == cmd_name:
                                cmd_func = self.cmd_cd
                                cmd_params = cmd_name
                                break

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
