from collections import deque
from operator import attrgetter


class StateNode:
    """
    Temporary representation for graph.Node with only relevant information for parsing
    """
    def __init__(self, index, node_id, swap_index=None, ref_node=None, text=None, label=None, is_root=False,
                 properties=None, anchors=None, expand=True):
        self.index = index  # Index in the configuration's node list
        self.id = str(node_id)  # ID of the reference node
        self.ref_node = ref_node or self  # Associated StateNode or graph.Node from the original Graph, during training
        self.text = text  # Text for terminals, None for non-terminals
        if label is None:
            self.label = None if self.text is None else self.text
            self.category = None
        else:  # Node label prediction is enabled
            self.label, _, self.category = label.partition("|")
            if not self.category:
                self.category = None
        self.outgoing = []  # StateEdge list
        self.incoming = []  # StateEdge list
        self.children = []  # StateNode list: the children of all edges in outgoing
        self.parents = []  # StateNode list: the parents of all edges in incoming
        self.outgoing_labs = set()  # String set
        self.incoming_labs = set()  # String set
        self.node = None  # Associated graph.Node, when creating final Graph
        self.swap_index = self.index if swap_index is None else swap_index  # To avoid swapping nodes more than once
        self.height = 0
        self._terminals = None
        self.is_root = is_root
        self.properties = properties
        self.anchors = self.expand_anchors(anchors) if expand else anchors

    def get(self, prop):
        return self.ref_node.properties.get(prop)

    def add_incoming(self, edge):
        self.incoming.append(edge)
        self.parents.append(edge.parent)
        self.incoming_labs.add(edge.lab)

    def add_outgoing(self, edge):
        self.outgoing.append(edge)
        self.children.append(edge.child)
        self.outgoing_labs.add(edge.lab)
        self.height = max(self.height, edge.child.height + 1)
        self._terminals = None  # Invalidate terminals because we might have added some

    @staticmethod
    def copy(node):
        return StateNode(index=node.index, node_id=node.node_id, ref_node=node, text=node.text, label=node.label,
                         is_root=node.is_root, properties=node.properties, anchors=node.anchors, expand=False)

    @property
    def descendants(self):
        """
        Find all children of this node recursively
        """
        result = [self]
        queue = deque(node for node in self.children if node is not self)
        while queue:
            node = queue.popleft()
            if node is not self and node not in result:
                queue.extend(node.children)
                result.append(node)
        return result

    @property
    def terminals(self):
        if self._terminals is None:
            q = [self]
            terminals = []
            while q:
                n = q.pop()
                q.extend(n.children)
                if n.text is not None:
                    terminals.append(n)
            self._terminals = sorted(terminals, key=attrgetter("index"))
        return self._terminals

    @classmethod
    def expand_anchors(cls, anchors):
        return set.union(*[set(range(x["from"], x["to"])) for x in anchors]) if anchors else set()

    def __repr__(self):
        return StateNode.__name__ + "(" + str(self.index) + \
               ((", " + self.text) if self.text else "") + \
               ((", " + self.id) if self.id else "") + ")" + \
               ((" (" + ",".join("%s=%s" % (k, v) for k, v in self.properties.items()) + ")")
                if self.properties else "")

    def __str__(self):
        s = "ROOT" if self.is_root else '"%s"' % self.text if self.text else str(self.id) or str(self.index)
        if self.label is not None:
            s += "/" + self.label
        if self.properties:
            s += "(" + ",".join("%s=%s" % (k, v) for k, v in self.properties.items()) + ")"
        return s

    def __eq__(self, other):
        return self.index == other.index and self.outgoing == other.outgoing

    def __hash__(self):
        return hash((self.index, tuple(self.outgoing)))

    def __iter__(self):
        return iter(self.outgoing)
