import json
import os
import typing
from .config import Config
from .decorated_str import *

class ConceptNode(object):
    def __init__(self, name: str, config: Config, parent: "ConceptNode" = None):
        self._config = config
        self.parent = parent
        self.sub_nodes = []  # type: typing.List[ConceptNode]

        self.name = name  # type: str
        self.content = []  # type: typing.List[str]
        self.statistics = None

        # self.searchable  note: don't use this memeber

        self.path = ""
        self.refresh()

    @property
    def click_count(self) -> int:
        return int(self.statistics['click'])

    @property
    def decorated_name(self):
        return DecoratedStr(self.name, GREEN)

    @property
    def decorated_path(self):
        return DecoratedStr(self.path[:self.path.rfind('/')] + "/") + self.decorated_name

    @property
    def abs_path(self):
        return os.path.join(self._config.workspace, self.path)

    # @property
    # def summary(self):
    #     return "".join([line.strip('\n') for line in self.content])

    @property
    def all_nodes_below(self):
        res = [self]
        cur = 0
        while cur < len(res):
            res += res[cur].sub_nodes
            cur += 1
        return res

    @property
    def content_abs_path(self):
        return os.path.join(self.abs_path, "index.md")

    @property
    def statistics_abs_path(self):
        return os.path.join(self.abs_path, 'statistics.json')

    def _refresh_content(self):
        path = self.content_abs_path
        if os.path.exists(path):
            with open(path, 'r') as fd:
                self.content = [line for line in fd]
        summary_end_line = 0
        while summary_end_line < len(self.content):
            buf = self.content[summary_end_line].strip()
            if len(buf) >= 3 and not buf.strip('-'):
                break
            summary_end_line += 1
        self.summary = " ".join([line.strip('\n') for line in self.content[:summary_end_line]])

    def _refresh_sub_nodes(self):

        # del
        self.sub_nodes = [node for node in self.sub_nodes if os.path.exists(os.path.join(self.abs_path, node.name))]

        # add
        cur_nodes = set([node.name for node in self.sub_nodes])

        # check new
        abs_path = self.abs_path
        for name in os.listdir(abs_path):
            if name not in cur_nodes and os.path.isdir(os.path.join(abs_path, name)):
                self.sub_nodes.append(ConceptNode(name, self._config, self))
                cur_nodes.add(name)

    def _refresh_path(self):
        if not self.parent:
            self.path = self.name
        else:
            self.path = os.path.join(self.parent.path, self.name)
        for node in self.sub_nodes:
            node._refresh_path()

    def after_click(self):
        """this func will be called after this node be clicked"""
        self.statistics['click'] += 1
        with open(self.statistics_abs_path, 'w') as fd:
            print(json.dumps(self.statistics), file=fd)

    def refresh(self):
        # TODO: 没必要的话不刷新
        self._refresh_path()
        self._refresh_content()
        self._refresh_sub_nodes()

        # refresh statistics
        if not os.path.exists(self.statistics_abs_path):
            self.statistics = {
                'click': 0
            }
        else:
            with open(self.statistics_abs_path, 'r') as fd:
                self.statistics = json.loads(''.join([line for line in fd]))

    def is_ancestor_of(self, node: "ConceptNode"):
        while node is not None:
            if node == self:
                return True
            node = node.parent
        return False


def simple_test():
    root = ConceptNode("example_concept", Config(os.getcwd()))
    assert root.content == ['Test concept root it the root of concepts tree.']
    assert len(root.sub_nodes) == 1
    sub_node = root.sub_nodes[0]
    assert sub_node.content == ['subnode1 is ...']


if __name__ == '__main__':
    simple_test()
