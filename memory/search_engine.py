from memory.concept import ConceptNode
import typing


class SearchableNode(object):
    def __init__(self, node: ConceptNode, parent: "SearchableNode" = None):
        self.concept_node = node
        self.is_alive = True
        self.is_candidate = True
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
        self.searchable_content = self.searchable_content.lower()

        # for dfs
        self.is_last_alive_sub_node = False

    @property
    def path_under_alive_parent(self) -> str:
        path_nodes = []
        tmp = self.parent
        while tmp is not None and not tmp.is_alive:
            path_nodes.append(tmp)
            tmp = tmp.parent
        path_nodes.reverse()
        res = ""
        for node in path_nodes:
            assert isinstance(node, SearchableNode)
            res += node.concept_node.name + "/"
        return res + self.concept_node.name


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
                sub_alive_node.alive_depth = node.alive_depth + 1
                dfs(sub_alive_node)

        self.alive_root.alive_depth = 0
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
        lower_keyword = keyword.lower()

        # is keyword legal ?
        def is_keyword_matched(node: SearchableNode):
            if node != self.alive_root and node.searchable_content.find(lower_keyword) != -1:
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

        # update candidate tree
        def update_is_candidate_recursive(node: SearchableNode):
            assert node.is_alive
            if node.is_candidate:
                if node.alive_parent is None or not node.alive_parent.is_candidate:
                    if node.searchable_content.find(lower_keyword) == -1:
                        node.is_candidate = False
            for sub_node in node.sub_alive_nodes:
                update_is_candidate_recursive(sub_node)

        update_is_candidate_recursive(self.alive_root)

        # update live tree
        def get_alive_root_recursive(node: SearchableNode) -> typing.Optional[SearchableNode]:
            assert node.is_alive
            sub_roots = [get_alive_root_recursive(sub_node) for sub_node in node.sub_alive_nodes]
            sub_roots = [root for root in sub_roots if root is not None]
            # is candidate or keep alive as middle path node
            node.is_alive = node.is_candidate or len(sub_roots) > 1
            if node.is_alive:
                node.sub_alive_nodes = sub_roots
                for sub in node.sub_alive_nodes:
                    sub.alive_parent = node
                return node
            if len(sub_roots) == 0:
                return None
            assert len(sub_roots) == 1
            return sub_roots[0]

        self.alive_root = get_alive_root_recursive(self.alive_root)

        # # update alive root
        # while len(self.alive_root.sub_alive_nodes) == 1:
        #     self.alive_root.is_alive = False
        #     the_only_son = list(self.alive_root.sub_alive_nodes)[0]  # type: SearchableNode
        #     self.alive_root.sub_alive_nodes.clear()
        #     self.alive_root = the_only_son
        #     self.alive_root.alive_parent = None

    def add_keywords(self, raw_keywords: str):
        keywords = ''.join([' ' if char in ['-', ' ', '_', '.'] else char for char in raw_keywords])
        keywords = keywords.split(' ')
        for keyword in keywords:
            self.__add_keyword(keyword)
