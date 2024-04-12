""" json renderer """

import os
import json


class JsonRenderer:
    """json renderer"""

    def __init__(self, mp4_path, output_path):
        self.mp4_path = mp4_path
        if output_path is not None:
            self.output_path = output_path
        else:
            mp4_base_name = os.path.basename(mp4_path)
            self.output_path = f"./{mp4_base_name}.mp4viewer.json"

    def _write(self, output_object):
        print(self.output_path)
        with open(self.output_path, "w+", encoding="utf-8") as fd:
            fd.write(json.dumps(output_object, indent=2))

    def render(self, data):
        """generate a json object from the mp4 metadata"""
        root = {"file": self.mp4_path}
        for child in data.children:
            self.add_node(child, root)
        self._write(root)

    def _add_dict_node(self, node, parent):
        dict_wrapper = {}
        for item in node.children:
            if item.is_dict():
                self._add_dict_node(item, dict_wrapper)
            else:
                dict_wrapper[item.name] = self._get_attr(item)

        if node.name not in parent:
            # first entry; may be the only one, so no need for a list
            parent[node.name] = dict_wrapper
        else:
            # has multiple entries by this name; change it to a list
            if isinstance(parent[node.name], dict):
                # second entry
                temp = parent[node.name]
                list_in_parent = [temp]
                parent[node.name] = list_in_parent
            else:
                # third and subsequent entries
                list_in_parent = parent[node.name]
            list_in_parent.append(dict_wrapper)

    def add_node(self, node, parent):
        """recursively serialise box data"""
        j_node = {}
        if node.is_atom():
            j_node["boxtype"] = {"fourcc": node.name, "description": node.value}
            key_within_parent = "children"
        else:
            key_within_parent = node.name
        if key_within_parent not in parent:
            parent[key_within_parent] = []
        parent[key_within_parent].append(j_node)
        for child in node.children:
            if child.is_atom():
                self.add_node(child, j_node)
            elif child.is_dict():
                self._add_dict_node(child, j_node)
            elif child.is_list():
                for item in child.children:
                    self.add_node(item, j_node)
            else:
                # attr
                j_node[child.name] = self._get_attr(child)
        return j_node

    def _get_attr(self, attr):
        if attr.display_value is not None:
            return {
                    "raw value": attr.value,
                    "decoded": attr.display_value
                    }
        return attr.value
