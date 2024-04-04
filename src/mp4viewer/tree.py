""" Defines the tree model used to represent the boxes """

from enum import Enum


class TreeType(Enum):
    """
    Types of trees.
    ATOM represents an iso 14996 atom.
    ATTR stands for a single attribute within an atom
    DICT represents a subobject within ATOM (a repeating object defined in a loop, for instance)
    """

    ATOM = 1
    ATTR = 2
    DICT = 3


class Tree:
    """Class representing a Tree"""

    def __init__(self, tree_type, name: str, value=None, display_value=None):
        self.type = tree_type
        self.name = name
        self.value = value
        self.display_value = display_value
        self.children = []

    def is_atom(self):
        """Return true if this node represents an ISO box"""
        return self.type == TreeType.ATOM

    def is_dict(self):
        """Return true if this node represents a sub object within an iso box"""
        return self.type == TreeType.DICT

    def is_attr(self):
        """Return true if this node represents a single value within an iso box"""
        return self.type == TreeType.ATTR

    def add_attr(self, *args):
        """
        Add an attribute to the root node of this tree
        Possible arguments are:
        - Either a single tree object of type ATTR, or
        - A key: str, value, and an optional display value, which will be used to construct
          a Tree(ATTR)
        """
        # First arg can be Attr or the name. If it is name, give value and optional converted value
        if len(args) == 0:
            raise TypeError("Add what?")
        if len(args) == 1 and not isinstance(args[0], Tree):
            raise TypeError(f"Sole argument should be a Tree, received {type(args[0])}")
        if len(args) > 1 and not isinstance(args[0], str):
            raise TypeError(f"First parameter shall be a string, received {args[0]}(type{args[0]})")

        if len(args) == 1:
            child = args[0]
        else:
            child = Tree(TreeType.ATTR, args[0], args[1], args[2] if len(args) > 2 else None)
        self.children.append(child)
        return child

    def add_sub_object(self, kv_object):
        """Add key value pairs from a dictionary object to the tree"""
        for key, value in kv_object.items():
            if isinstance(value, Tree):
                self.children.append(value)
            else:
                self.add_attr(key, value)

    def add_list_of_sub_objects(self, key: str, object_list: list):
        """Add a list of dict objects as a subtree"""
        for index, item in enumerate(object_list):
            kv_node = self.add_child(Tree(TreeType.DICT, key, str(index + 1)))
            kv_node.add_sub_object(item)

    def add_child(self, child: Tree):
        """Add a child node to this tree"""
        if not isinstance(child, Tree):
            raise TypeError(f"add_child received {type(child)}")
        self.children.append(child)
        return child

    def number_of_child_boxes(self):
        """Number of trees with type=ATOM"""
        return len([x for x in self.children if isinstance(x, Tree) and x.is_atom()])

    def __str__(self):
        return f"Tree<{self.name}>"
