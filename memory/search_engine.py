from memory.concept import ConceptNode
import typing


class SearchableNode(object):
    def __init__(self, node: ConceptNode, parent: "SearchableNode" = None):
        self.concept_node = node
        self.is_alive = True
        self.parent = parent  # type: SearchableNode
        self.alive_parent = self.parent
        self.sub_nodes = set()  # type: typing.Set[SearchableNode]
        self.sub_alive_nodes = set()
        if self.parent is not None:
            self.parent.sub_nodes.add(self)
            self.parent.sub_alive_nodes.add(self)
        self.depth = 0 if self.parent is None else self.parent.depth + 1
        self.alive_depth = self.depth
        self.searchable_content = self.concept_node.name
        for char in "".join(self.concept_node.content):
            if char in ['-', ' ', '_', '.']:
                continue
            self.searchable_content += char

        # for dfs
        self.is_last_alive_sub_node = False

class SearchEngine(object):
    def __init__(self, root: ConceptNode):
        self.root = SearchableNode(root)
        self.alive_root = self.root
        self.nodes = [self.root]  # type: typing.List[SearchableNode]
        idx = 0
        while idx < len(self.nodes):
            node = self.nodes[idx]
            idx += 1
            for sub_node in node.concept_node.sub_nodes:
                self.nodes.append(SearchableNode(sub_node, node))
        self.keywords = set()  # type: typing.Set[str]
        self.miss_keywords = set()  # type: typing.Set[str]

    def get_alive_nodes_in_dfs_order(self) -> typing.List[SearchableNode]:
        res = []

        def dfs(node: SearchableNode):
            res.append(node)
            subs = list(node.sub_alive_nodes)
            for sub_alive_node in subs:
                sub_alive_node.is_last_alive_sub_node = sub_alive_node is subs[-1]
                dfs(sub_alive_node)

        dfs(self.alive_root)
        return res

    #
    # def refresh_depths(self):
    #     def update(node: SearchableNode):
    #         if node is self.root:
    #             node.depth = 0
    #         else:
    #             node.depth = node.parent.depth + 1
    #         for sub_node in node.sub_nodes:
    #             update(sub_node)

    def __add_keyword(self, keyword: str):

        # is keyword legal ?
        def is_keyword_matched(node: SearchableNode):
            if node != self.alive_root and node.searchable_content.find(keyword) != -1:
                return True
            for sub_alive_node in node.sub_alive_nodes:
                if is_keyword_matched(sub_alive_node):
                    return True
            return False

        if not is_keyword_matched(self.alive_root):
            self.miss_keywords.add(keyword)
            return False
        else:
            self.keywords.add(keyword)

        # update live tree
        def update_is_alive_recursive(node: SearchableNode):
            assert node.is_alive

            if node.alive_parent is not None:
                if not node.alive_parent.is_alive:
                    node.alive_parent.sub_alive_nodes.remove(node)
                    node.alive_parent = node.alive_parent.alive_parent
                    if node.alive_parent is not None:
                        node.alive_parent.sub_alive_nodes.add(node)
            node.alive_depth = 0 if node.alive_parent is None else node.alive_parent.alive_depth + 1

            if node.searchable_content.find(keyword) == -1:
                if node.alive_parent is None:
                    node.is_alive = False

            for sub_node in node.sub_alive_nodes.copy():
                update_is_alive_recursive(sub_node)

        update_is_alive_recursive(self.alive_root)
        self.alive_root.is_alive = True
        for node in self.nodes:
            if node is not self.alive_root:
                if node.is_alive and node.alive_parent is None:
                    self.alive_root.sub_alive_nodes.add(node)
                    node.alive_parent = self.alive_root

        # update alive root
        while len(self.alive_root.sub_alive_nodes) == 1:
            self.alive_root.is_alive = False
            the_only_son = list(self.alive_root.sub_alive_nodes)[0]  # type: SearchableNode
            self.alive_root.sub_alive_nodes.clear()
            self.alive_root = the_only_son
            self.alive_root.alive_parent = None

    def add_keywords(self, raw_keywords: str):
        # keywords = ''.join([' ' if char in ['-', ' ', '_', '.'] else char for char in raw_keywords])
        keywords = raw_keywords.lower().split(' ')
        for keyword in keywords:
            self.__add_keyword(keyword)
