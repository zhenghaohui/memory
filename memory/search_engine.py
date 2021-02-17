from memory.concept import ConceptNode
import typing


class SearchableNode(object):
    def __init__(self, node: ConceptNode, parent: "SearchableNode" = None):
        self.concept_node = node
        self.matched_keyword = set()
        self.is_alive = False
        self.parent = parent  # type: SearchableNode
        self.sub_nodes = []  # type: typing.List[SearchableNode]
        if self.parent is not None:
            self.parent.sub_nodes.append(self)
        self.depth = 0 if self.parent is None else self.parent.depth + 1
        self.searchable_content = self.concept_node.name + ''.join(self.concept_node.content)
        self.searchable_content = ''.join([char for char in self.searchable_content if
                                           char not in ['-', ' ', '_', '.']]).lower()

        self.__cached_alive_parent = None  # type: typing.Optional[SearchableNode]
        self.__cached_sub_alive_nodes = set(self.sub_nodes.copy())

        # for dfs
        self.alive_depth = 0
        self.is_last_alive_sub_node = False

    def set_alive_parent(self, node: "SearchableNode"):
        self.__cached_alive_parent = node
        if node is not None:
            node.__cached_sub_alive_nodes.add(self)

    def get_alive_parent(self) -> typing.Optional["SearchableNode"]:
        if self.__cached_alive_parent is None:
            return None
        if self.__cached_alive_parent.is_alive:
            return self.__cached_alive_parent
        latest_alive_parent = self.__cached_alive_parent.get_alive_parent()
        if latest_alive_parent != self.__cached_alive_parent:
            self.set_alive_parent(latest_alive_parent)
        return self.__cached_alive_parent

    def get_sub_alive_nodes(self) -> typing.Set["SearchableNode"]:
        self.__cached_sub_alive_nodes = set([node for node in self.__cached_sub_alive_nodes if node.is_alive])
        return self.__cached_sub_alive_nodes

    def get_path_under_alive_parent(self) -> str:
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
        self.alive_root.is_alive = True
        self.nodes = [self.root]  # type: typing.List[SearchableNode]
        idx = 0
        while idx < len(self.nodes):
            node = self.nodes[idx]
            idx += 1
            for sub_node in node.concept_node.sub_nodes:
                self.nodes.append(SearchableNode(sub_node, node))
        self.keywords = []  # type: typing.List[str]
        self.miss_keywords = []  # type: typing.List[str]

    def get_alive_leaves(self):
        def __get_alive_leaves(root: SearchableNode) -> typing.List[SearchableNode]:
            subs = root.get_sub_alive_nodes()
            if len(subs) == 0:
                return [root]
            res = []
            for node in subs:
                res += __get_alive_leaves(node)
            return res

        return __get_alive_leaves(self.alive_root)

    def get_alive_nodes_in_dfs_order(self) -> typing.List[SearchableNode]:
        res = []

        def dfs(node: SearchableNode):
            res.append(node)
            subs = list(node.get_sub_alive_nodes())
            for sub_alive_node in subs:
                sub_alive_node.is_last_alive_sub_node = sub_alive_node is subs[-1]
                sub_alive_node.alive_depth = node.alive_depth + 1
                dfs(sub_alive_node)

        self.alive_root.alive_depth = 0
        dfs(self.alive_root)
        return res

    @staticmethod
    def __exist_keyword_strictly_under(root: SearchableNode, keyword: str):
        for node in root.sub_nodes:
            if node.searchable_content.find(keyword) != -1:
                return True
            if SearchEngine.__exist_keyword_strictly_under(node, keyword):
                return True
        return False

    def __add_keyword(self, raw_keyword: str):
        keyword = ''.join([char for char in raw_keyword if char not in ['-', ' ', '_', '.']]).lower()

        keyword_matched_under_any_leaf = False
        alive_leaves = self.get_alive_leaves()
        for alive_leaf in alive_leaves:
            if SearchEngine.__exist_keyword_strictly_under(alive_leaf, keyword):
                keyword_matched_under_any_leaf = True
                break
        if not keyword_matched_under_any_leaf:
            self.miss_keywords.append(raw_keyword)
            return False
        else:
            self.keywords.append(raw_keyword)

        # update alive tree

        def get_alive_roots_strictly_under(root: SearchableNode) -> typing.List[SearchableNode]:
            alive_roots = []
            for _node in root.sub_nodes:
                if _node.searchable_content.find(keyword) != -1:
                    _node.is_alive = True
                    _node.matched_keyword.add(raw_keyword)
                    alive_roots.append(_node)
                    continue
                _sub_alive_roots = get_alive_roots_strictly_under(_node)
                if len(_sub_alive_roots) == 0:
                    continue
                elif len(_sub_alive_roots) == 1:
                    alive_roots.append(_sub_alive_roots[0])
                else:
                    _node.is_alive = True
                    for _sub_alive_root in _sub_alive_roots:  # type: SearchableNode
                        _sub_alive_root.set_alive_parent(_node)
                    alive_roots.append(_node)
            return alive_roots

        dropping_check_list = []  # type: typing.List[SearchableNode]
        new_leaves = []
        for alive_leaf in alive_leaves:
            sub_alive_roots = get_alive_roots_strictly_under(alive_leaf)
            if len(sub_alive_roots) == 0:
                alive_leaf.is_alive = False
                dropping_check_list.append(alive_leaf.get_alive_parent())
            elif len(sub_alive_roots) == 1:
                alive_leaf.is_alive = False
                sub_alive_roots[0].set_alive_parent(alive_leaf.get_alive_parent())
                new_leaves.append(sub_alive_roots[0])
            else:
                for sub_alive_root in sub_alive_roots:
                    sub_alive_root.set_alive_parent(alive_leaf)
                new_leaves.append(alive_leaf)

        # check dropping check list
        idx = 0
        while idx < len(dropping_check_list):
            node = dropping_check_list[idx]
            idx += 1
            if node is None or not node.is_alive:
                continue
            subs = node.get_sub_alive_nodes()
            assert len(subs) >= 1
            if len(subs) == 1:
                node.is_alive = False
                node.get_alive_parent()
                dropping_check_list.append(node.get_alive_parent())

        # update alive tree
        que = new_leaves.copy()
        que_set = set([node for node in que])
        idx = 0
        while idx < len(que):
            node = que[idx]
            idx += 1
            parent = node.get_alive_parent()
            if parent is not None and parent not in que_set:
                que_set.add(parent)
                que.append(parent)
        self.alive_root = que[-1]

    def add_keywords(self, raw_keywords: str):
        keywords = raw_keywords.split(' ')
        for keyword in keywords:
            self.__add_keyword(keyword)
