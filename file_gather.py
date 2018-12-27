import sublime
import sublime_plugin

from pprint import pprint
import json

import hashlib
import fnmatch
import os
from os.path import dirname, basename


test_folder = {
  # This file does not appear locally
  "/home/tmartin/local/src/devember-2018/remote_build_server": {
    "BuildClient1.cs": {
      "last_modified": 1544504473.2212374,
      "name": "BuildClient.cs",
      "sha1": "201b43d4ddb4dc395c09b10e83305227b643db50"
    },
    # The hash on this is different on purpose
    "Extensions.cs": {
      "last_modified": 1544416126.3528106,
      "name": "Extensions.cs",
      "sha1": "3a137214ffd6dfdd52b8ff3bb46a9fdab96fab7c"
    },
    # The hash on this is different on purpose
    "Main.cs": {
      "last_modified": 1544502070.7733796,
      "name": "Main.cs",
      "sha1": "e596ffd55f6b253f14f09a7b68826e22fbb59f8e"
    },
    "messages/Error.cs": {
      "last_modified": 1544506203.8349078,
      "name": "messages/Error.cs",
      "sha1": "cfbdb4439a29e4cb679b17982c6f5b78c23e3642"
    },
    "messages/Introduction.cs": {
      "last_modified": 1544506197.8239672,
      "name": "messages/Introduction.cs",
      "sha1": "9f14770213767254dd30ee038299d97a712d872f"
    },
    "messages/Message.cs": {
      "last_modified": 1544506089.9700332,
      "name": "messages/Message.cs",
      "sha1": "8958b712e1a6baca2ae74f53aa8e808a0f9a15ce"
    },
    "messages/PartialMessage.cs": {
      "last_modified": 1544502110.762907,
      "name": "messages/PartialMessage.cs",
      "sha1": "78d85db5de04f841bf6a3832429add6727a64d24"
    },
    "messages/ProtocolMessageFactory.cs": {
      "last_modified": 1544504869.4056778,
      "name": "messages/ProtocolMessageFactory.cs",
      "sha1": "8b2b7f3fa05ef35857e7eee56cd9c1f7a9ccdbad"
    },
    "remote_build_server.csproj": {
      "last_modified": 1544225083.3561223,
      "name": "remote_build_server.csproj",
      "sha1": "e61459af3f70865b126f5d828adac52aef5a2968"
    }
  }
}

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


def _coalesce_folders(folder_dict):
    """
    Given a dictionary of top level build folders that has had its contents
    filled out, attempt to coalesce all of the child folders that appear into
    their parents.
    """
    get_folders = lambda d: sorted(d.keys(), key=lambda fn: (dirname(fn), basename(fn)))

    coalesced = {}
    for folder in get_folders(folder_dict):
        # Scan over all of the folders currently in the new output to see if
        # any of them are wholly used as our path prefix.
        common = None
        for fixed_folder in get_folders(coalesced):
            if folder.startswith(fixed_folder):
                common = fixed_folder
                break

        if common is None:
            coalesced[folder] = folder_dict[folder]

        else:
            suffix = folder[len(common):].lstrip(os.sep)
            # print("Coalescing '{0}' into {1}".format(suffix, common))

            # Alias the the dictionary we're going to copy items from and the
            # dictionary we're going to copy them to.
            src = folder_dict[folder]
            dst = coalesced[common]

            for name,info in src.items():
                new_entry = os.path.join(suffix, name)
                dst[new_entry] = info
                dst[new_entry]["name"] = new_entry

        # print(folder)

    return coalesced


def _get_file_details(root_path, filename, hash_file):
    """
    Get all of the underlying file details for the provided file in the given
    root path.
    """
    name = os.path.join(root_path, filename)

    try:
        mtime = os.path.getmtime(name)
        sha1 = None

        if hash_file:
            sha1 = hashlib.sha1()

            with open(name, "rb") as file:
                while True:
                    data = file.read(262144)
                    if not data:
                        break
                    sha1.update(data)

            sha1 = sha1.hexdigest()

        return {
            "name": filename,
            "last_modified": mtime,
            "sha1": sha1
        }

    except OSError:
        return None


def _files_for_folder(window, folder, project_path, hash_files):
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
                results[name] = _get_file_details(search_path, name, hash_files)

    return search_path, results


def find_project_files(window, folders=None, hash_files=True):
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
            files[base_folder] = _get_file_details(base_folder, filename, hash_files)

        return files

    for folder in folders:
        base_folder, folder_files = _files_for_folder(window, folder, path, hash_files)
        files[base_folder] = folder_files

    return _coalesce_folders(files)


def calculate_fileset_deltas(us, them):
    """
    Given two fileset dictionarys, one representing our files and one
    representing "their" files, this returns back a dictionary that indicates
    what files need to be added, removed or updated in order to make their
    files match ours.
    """
    file_deltas = {}

    # For all folders that we have, add entries to tell the other end how to
    # create or update their copies of these folders.
    for our_folder, our_files in us.items():
        file_deltas[our_folder] = {
            "add": {},
            "remove": {},
            "modify": {}
        }
        diffed = file_deltas[our_folder]

        # Get the set of files for them in this folder; if it doesn't exist,
        # then we need to add all of the files for this folder directly and
        # that's all we have to worry about.
        their_files = them.get(our_folder, None)
        if their_files is None:
            diffed["add"].update(us[our_folder])
            continue

        # print(our_files)
        # print(their_files)
        our_set = set(our_files.keys())
        their_set = set(their_files.keys())

        # print(our_set)
        # print(their_set)
        # print(our_set - their_set) # files we have they don't
        # print(their_set - our_set) # files they have we don't
        # print(our_set & their_set) # files we both have

        # Add files we have and they don't
        for file in our_set - their_set:
            diffed["add"][file] = our_files[file]

        # Remove files they have and we don't
        for file in their_set - our_set:
            diffed["remove"][file] = their_files[file]

        # Update any files we both have that have changed
        for file in our_set & their_set:
            if our_files[file]["sha1"] != their_files[file]["sha1"]:
                diffed["modify"][file] = our_files[file]


    # For all folders that the remote end has, if we don't have them, tell the
    # remote end to remove them now
    for their_folder, their_files in them.items():
        if their_folder not in us:
            file_deltas[their_folder] = {
                "add": {},
                "remove": their_files,
                "modify": {}
            }

    return file_deltas

# Any window with folders open always:
#   1) responds to window.folders() with a list of folders (absolute)
#   2) responds to window.project_data() with at least the "folders" key
#
# Additionally, anything with a project responds to:
#   1) window.project_file_name()
class FileGatherCommand(sublime_plugin.WindowCommand):
    def run(self):
        files = find_project_files(self.window, folders=[
                {
                    "path": "/home/tmartin/local/src/devember-2018/remote_build_server",
                    "folder_exclude_patterns":
                    [
                        "obj",
                        "bin",
                    ],
                },
            ])
        diffed = calculate_fileset_deltas(files, test_folder)
        print(json.dumps(diffed, indent=2, sort_keys=True))
