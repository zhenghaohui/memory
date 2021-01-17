import os
import typing


class Config:
    def __init__(self, workspace: str):
        self.workspace = workspace


class ConceptNode(object):
    def __init__(self, name: str, config: Config, parent: "ConceptNode" = None):
        self._config = config
        self.parent = parent
        self.sub_nodes = []  # type: typing.List[ConceptNode]

        self.name = name  # type: str
        self.content = []  # type: typing.List[str]

        self.path = ""
        self.refresh()

    @property
    def abs_path(self):
        return os.path.join(self._config.workspace, self.path)

    @property
    def content_path(self):
        return os.path.join(self.abs_path, "index.md")

    def _refresh_content(self):
        path = self.content_path
        if os.path.exists(path):
            with open(path, 'r') as fd:
                self.name = None
                for line in fd:
                    if line.strip() and self.name is None:
                        self.name = line.strip()
                    self.content.append(line)

    def _refresh_sub_nodes(self):

        # del
        self.sub_nodes = [node for node in self.sub_nodes if os.path.exists(node.abs_path())]

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

    def refresh(self):
        # TODO: 没必要的话不刷新
        self._refresh_path()
        self._refresh_content()
        self._refresh_sub_nodes()

    def searchable(self):
        return "".join(self.content) + self.path


def simple_test():
    root = ConceptNode("example_concept", Config(os.getcwd()))
    assert root.content == ['Test concept root it the root of concepts tree.']
    assert len(root.sub_nodes) == 1
    sub_node = root.sub_nodes[0]
    assert sub_node.content == ['subnode1 is ...']


if __name__ == '__main__':
    simple_test()
