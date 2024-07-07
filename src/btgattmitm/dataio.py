##
##
##

import logging
import yaml


_LOGGER = logging.getLogger(__name__)


def bytearray_constructor(loader, node):
    node_values = node.value
    value = node_values[0].value
    encoding = node_values[1].value
    return bytearray(value, encoding)


# fix bytearray deserialization error
yaml.add_constructor('tag:yaml.org,2002:python/object/apply:builtins.bytearray', bytearray_constructor)


# ===================================================


def dump(data_object):
    return yaml.dump(data_object, sort_keys=True)


def dump_to(data_object, output_path):
    with open(output_path, "w", encoding="utf-8") as output_file:
        yaml.dump(data_object, output_file, sort_keys=True)


def load(json_content):
    return yaml.full_load(json_content)


def load_from(config_path):
    with open(config_path) as data_file:
        return yaml.full_load(data_file)
