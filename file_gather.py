import sublime
import sublime_plugin

from pprint import pprint
import json

import hashlib
import fnmatch
import os

# From a build system
spec1 = [{
    "path": "/home/tmartin/local/src/devember-2018/",

    "folder_include_patterns": [],
    "file_include_patterns": [],

    "folder_exclude_patterns": [],
    "file_exclude_patterns": [],
}]

# From a build system
spec2 = [{
    "folder_exclude_patterns":
    [
        "obj",
        "bin",
        "__pycache__"
    ],
    "path": "/home/tmartin/local/src/devember-2018/"
}]

spec3 = [{
}]

spec4 = []

# TODO: this requires some case sensitive path checks
def _keep(filename, includes, excludes):
    """
    Given a file name, return a boolean to indicate if this file should be
    considered part of the build based on the given list of include and exclude
    patterns.

    The filters are applied in the order: "include, exclude" such that if there
    are no includes, we assume that everything is included by default.
    """
    def list_match(filename, patterns, default_if_empty):
        if not patterns:
            return default_if_empty

        for pattern in patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True

        return False

    return (list_match(filename, includes, True) and
                not list_match(filename, excludes, False))


# TODO: this requires some case sensitive path checks
def _prune_folders(folders, includes, excludes):
    """
    Given a list of folders, return a copy of it that includes just the folders
    that should be considered part of the build based on the given list of
    include and exclude patterns.

    The filters are applied in the order: "include, exclude" such that if there
    are no includes, we assume that everything is included by default.
    """
    result = []
    for folder in folders:
        if not includes or folder in includes:
            if folder not in excludes:
                result.append(folder)

    return result


def _get_file_details(root_path, filename):
    """
    Get all of the underlying file details for the provided file in the given
    root path.
    """
    name = os.path.join(root_path, filename)

    try:
        mtime = os.path.getmtime(name)
        sha1 = hashlib.sha1()

        with open(name, "rb") as file:
            while True:
                data = file.read(262144)
                if not data:
                    break
                sha1.update(data)

        return {
            "name": filename,
            "last_modified": mtime,
            "sha1": sha1.hexdigest()
        }

    except OSError:
        return None


def _files_for_folder(window, folder, project_path):
    """
    Given a particular folder dict in a window with the provided project path,
    return a list of all files in that folder that should apply to the build.
    """
    search_path = folder.get("path", None)
    file_includes = folder.get("file_include_patterns", [])
    file_excludes = folder.get("file_exclude_patterns", [])
    path_includes = folder.get("folder_include_patterns", [])
    path_excludes = folder.get("folder_exclude_patterns", [])

    settings = sublime.load_settings("Preferences.sublime-settings")
    file_excludes.extend(settings.get("file_exclude_patterns", []))
    path_excludes.extend(settings.get("folder_exclude_patterns", []))

    if search_path is None:
        raise ValueError("folder entry does not contain a path")

    if not os.path.isabs(search_path):
        if project_path is None:
            raise ValueError("paths in non-project folder entries cannot be relative")

        search_path = os.path.abspath(os.path.join(project_path, search_path))

    # print("---------------------------------------")
    # print("folder:       '%s'" % search_path)
    # print("file include: %s" % file_includes)
    # print("file exclude: %s" % file_excludes)
    # print("path include: %s" % path_includes)
    # print("path exclude: %s" % path_excludes)

    results = {}
    for (path, dirs, files) in os.walk(search_path):
        dirs[:] = _prune_folders(dirs, path_includes, path_excludes)

        rPath = os.path.relpath(path, search_path) if path != search_path else ""
        for name in files:
            name = os.path.join(rPath, name)
            if _keep(name, file_includes, file_excludes):
                results[name] = _get_file_details(search_path, name)

    return search_path, results


def _find_project_files(window, folders=None):
    """
    Given a list of folder entries and a potential project path, return a list
    of all files that exist at that particular path.
    """
    path = None
    if folders is None:
        data = window.project_data()
        folders = data.get("folders", None) if data else None
        path = window.project_file_name()
        if path:
            path = os.path.split(path)[0]

    files = {}
    if not folders:
        view = window.active_view()
        if view and view.file_name() is not None:
            base_folder, filename = os.path.split(view.file_name())
            files[base_folder] = _get_file_details(base_folder, filename)

        return files

    for folder in folders:
        base_folder, folder_files = _files_for_folder(window, folder, path)
        files[base_folder] = folder_files

    return files


# Any window with folders open always:
#   1) responds to window.folders() with a list of folders (absolute)
#   2) responds to window.project_data() with at least the "folders" key
#
# Additionally, anything with a project responds to:
#   1) window.project_file_name()
class FileGatherCommand(sublime_plugin.WindowCommand):
    def run(self):
        files = _find_project_files(self.window, folders=[])
            #     {
            #         "path": "/home/tmartin/local/src/devember-2018/",
            #         "folder_exclude_patterns":
            #         [
            #             "obj",
            #             "bin",
            #             "__pycache__"
            #         ],
            #     },
            #     {
            #         "path": "/home/tmartin/local/src/devember-2017/",
            #     }
            # ])
        # pprint(files)
        print(json.dumps(files, indent=2, sort_keys=True))

        # dirs = ['.git', 'remote_build_server', 'net_test', 'enum']
        # dirs[:] = _prune_folders(dirs, [], [".git", ".svn"])
        # pprint(dirs)

        # filename = "sample.txt"
        # print(filename, _keep(filename, ["*.txt"], []))

