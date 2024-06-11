#!/usr/bin/env python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

#
# Script searches for following tag: <!-- insertstart include="" pre="" post="" -->
# and tag: <!-- insertend --> and inserts content of file pointed in "include" attribute.
# "pre" and "post" attributes can contain additional prefix and suffix of content of included file.
#
# For more advanced Markdown preprocessing see https://github.com/amyreese/markdown-pp
#

import os
import re

import argparse

import xmltodict


class MDPreprocessor:
    def __init__(self):
        self._base_dir = None
        self._input_content = None
        self._output_content = None
        self._items = None

    def process(self, md_path):
        self._base_dir = os.path.dirname(md_path)
        content = load_content(md_path)
        self._input_content = content

        self._find_tags()
        print("items:", self._items)
        replace_list = self._find_replace_list()
        print("replace list:", replace_list)

        if len(replace_list) > 0:
            replace_list = sorted(replace_list, key=lambda item: item[0].start())
            last_end = None
            for replace_pair in replace_list:
                if last_end is None:
                    last_end = replace_pair[1].end()
                    continue
                curr_start = replace_pair[1].start()
                if curr_start < last_end:
                    raise RuntimeError("unsupported case: nested placeholders")

        # we are sure that there is no nested placeholders
        self._output_content = content
        replace_list = sorted(replace_list, key=lambda item: item[0].start(), reverse=True)
        for replace_pair in replace_list:
            self._replace(*replace_pair)

        # print(f"new content:\n{self._output_content}")
        save_content(md_path, self._output_content)

    def _replace(self, start_item, end_item):
        print("handling pair:", start_item, end_item)
        # convert HTML comment to valid XML tag
        tag_text = start_item.group()
        tag_text = tag_text.replace("<!--", "")
        tag_text = tag_text.replace("-->", "")
        tag_text = tag_text.replace("insertstart", "")
        tag_text = f"<insertstart {tag_text}></insertstart>"
        attr_dict = xmltodict.parse(tag_text)
        attr_dict = attr_dict.get("insertstart", {})
        print("found attributes:", attr_dict)

        include_path = attr_dict.get("@include")
        pre_content = attr_dict.get("@pre", "")
        pre_content = pre_content.encode("utf-8").decode("unicode_escape")
        post_content = attr_dict.get("@post", "")
        post_content = post_content.encode("utf-8").decode("unicode_escape")

        include_content = ""
        if not os.path.isabs(include_path):
            include_path = os.path.join(self._base_dir, include_path)
        include_content = load_content(include_path)

        space_start_index = start_item.end()
        space_end_index = end_item.start()
        content_before = self._output_content[:space_start_index]
        content_after = self._output_content[space_end_index:]
        self._output_content = f"{content_before}{pre_content}{include_content}{post_content}{content_after}"

    def _find_replace_list(self):
        replace_list = []
        while True:
            replace_pair = self._find_replace_item(0)
            if not replace_pair:
                break
            replace_list.append(replace_pair)
        return replace_list

    def _find_replace_item(self, curr_index):
        if curr_index >= len(self._items):
            return ()
        curr_item = self._items[curr_index]
        if "insertstart" not in curr_item.group():
            # looking for insertstart
            return self._find_replace_item(curr_index + 1)
        next_index = curr_index + 1
        if next_index >= len(self._items):
            return ()
        next_item = self._items[next_index]
        if "insertend" not in next_item.group():
            # looking for insertend
            return self._find_replace_item(next_index + 1)
        # curr_item - insertstart
        # next_item - insertend
        del self._items[next_index]
        del self._items[curr_index]
        return (curr_item, next_item)

    def _find_tags(self):
        tag_list = []
        start_pattern = re.compile("<!--.*?(insertstart|insertend).*?-->", re.MULTILINE | re.DOTALL)
        for match_object in start_pattern.finditer(self._input_content):
            tag_list.append(match_object)
        self._items = sorted(tag_list, key=lambda item: item.start())


# ==============================================


def load_content(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def save_content(file_path, content):
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)


def main():
    parser = argparse.ArgumentParser(
        description="Markdown preprocessor", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("mdpath", action="store", help="Path to Markdowo file")

    args = parser.parse_args()

    md_path = args.mdpath
    md_path = os.path.abspath(md_path)

    processor = MDPreprocessor()
    processor.process(md_path)

    print("preprocessing completed")


## ========================================


if __name__ == "__main__":
    main()
