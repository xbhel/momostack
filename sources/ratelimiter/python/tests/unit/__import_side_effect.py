# -*- coding: utf-8 -*-
import inspect
import json
import logging
import os
import sys
from typing import Optional

__author__ = "xbhel"
__email__ = "xbhel@outlook.com"


logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", logging.DEBUG))


class Importer:
    __test_root_dir_aliases = ("tests", "Tests", "test")
    __src_root_dir_aliases = ("Source", "source", "src")

    def __init__(
        self,
        *,
        project_name: Optional[str] = None,
        source_root_dir_name: Optional[str] = None,
        test_root_dir_name: Optional[str] = None,
    ):
        test_root_aliases = (
            (test_root_dir_name,)
            if test_root_dir_name
            else self.__test_root_dir_aliases
        )
        source_root_aliases = (
            (source_root_dir_name,)
            if source_root_dir_name
            else self.__src_root_dir_aliases
        )
        root_path = self.__get_root_path(
            project_name, test_root_aliases, source_root_aliases
        )

        self.root_path = root_path
        self.project_name = os.path.split(root_path)[-1]
        self.source_root_path = self.__get_sub_path(root_path, source_root_aliases)
        self.test_root_path = self.__get_sub_path(root_path, test_root_aliases)

    def load_source_file(self, path: str, mode: str, encoding=None):
        full_file_path = os.path.join(self.source_root_path, path)
        return self.load_file(full_file_path, mode, encoding)

    def load_test_file(self, path: str, mode: str, encoding=None):
        full_file_path = os.path.join(self.test_root_path, path)
        return self.load_file(full_file_path, mode, encoding)

    def load_file(self, full_file_path: str, mode: str, encoding=None):
        match mode:
            case "json" | "j":
                return self.__load_json(full_file_path, encoding)
            case "txt" | "t":
                return self.__load_txt(full_file_path, encoding)
            case "binary" | "b":
                return self.__load_binary(full_file_path)
            case _:
                raise ValueError(f"Unsupported mode: {mode}.")

    def load_source_modules(self, module_paths: Optional[list[str]] = None):
        src_root_path = self.source_root_path

        if not module_paths:
            sys.path.append(src_root_path)
            logger.info(f"Adding module to system path: {src_root_path}")
            return

        for path in module_paths:
            if os.path.exists(fullpath := os.path.join(src_root_path, path)):
                logger.info(f"Adding module to system path: {fullpath}")
                sys.path.append(fullpath)
            else:
                raise ValueError(
                    f"Module not found: {path} in {src_root_path}. Please check the path."
                )

    @staticmethod
    def __load_json(path: str, encoding=None):
        if encoding is None:
            encoding = "utf-8"
        with open(path, "r", encoding=encoding) as f:
            json_file = json.load(f)
        return json_file

    @staticmethod
    def __load_txt(path: str, encoding=None):
        if encoding is None:
            encoding = "utf-8"
        with open(path, "r", encoding=encoding) as f:
            text = f.read().strip()
        return text

    @staticmethod
    def __load_binary(path: str):
        with open(path, "rb") as f:
            buffer = f.read()
        return buffer

    @staticmethod
    def __get_sub_path(root_path, subdir_aliases) -> str:
        for alias in subdir_aliases:
            subpath = os.path.join(root_path, alias)
            if os.path.exists(subpath):
                return str(subpath)
        raise ValueError(f"Cannot find the {subdir_aliases} in {root_path}")

    @staticmethod
    def __get_root_path(
        project_name, source_root_dir_aliases, test_root_dir_aliases
    ) -> str:
        current_location = inspect.stack()[0][1]
        possible_subdir_of_root = source_root_dir_aliases + test_root_dir_aliases

        if project_name:
            index = current_location.find(project_name)
            if index != -1:
                return current_location[: index + len(project_name)]
            else:
                logger.warning(f"Cannot find the {project_name} in {current_location}")

        current_dir = os.path.abspath(os.path.join(current_location, ".."))
        dir_num = len(current_dir.split(os.sep))

        root_dir = current_dir
        while dir_num:
            for subdir in possible_subdir_of_root:
                if os.path.exists(os.path.join(root_dir, subdir)):
                    return root_dir
            dir_num -= 1
            root_dir = os.path.abspath(os.path.join(root_dir, ".."))

        raise RuntimeError(
            "Cannot locate the root path. You may be need to set the project_name:{}, \
                source_root_dir_aliases:{} and test_root_dir_aliases:{} to assist us in locating the root path.".format(
                project_name, source_root_dir_aliases, test_root_dir_aliases
            )
        )
    

Importer().load_source_modules()