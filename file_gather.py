import sublime
import sublime_plugin

from pprint import pprint
import os

# From a project
spec = {
    "path": ".",

    "folder_include_patterns": [],
    "file_include_patterns": [],

    "folder_exclude_patterns": [], # Include the global in this
    "file_exclude_patterns": [],   # Include the global in this
}

# From a project
spec2 = {
    "folder_exclude_patterns":
    [
        "obj",
        "bin",
        "__pycache__"
    ],
    "path": "."
}

spec3 = {

}

def _keep(subpath, file_inc, file_exc, path_inc, path_exc):
    return True

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

    if not os.path.isabs(search_path):
        search_path = os.path.abspath(os.path.relpath(project_path, search_path))

    print("---------------------------------------")
    # print("folder:       '%s'" % search_path)
    # print("file include: %s" % file_includes)
    # print("file exclude: %s" % file_excludes)
    # print("path include: %s" % path_includes)
    # print("path exclude: %s" % path_excludes)

    results = []
    for (path, dirs, files) in os.walk(search_path, followlinks=False):
        rPath = os.path.relpath(path, search_path) if path != search_path else ""
        for name in files:
            name = os.path.join(rPath, name)
            if _keep(name, file_includes, file_excludes, path_includes, path_excludes):
                results.append(name)

    return results


def _find_project_files(window):
    """
    Given a list of folder entries and a potential project path, return a list
    of all files that exist at that particular path.
    """
    data = window.project_data()
    folders = data.get("folders", None) if data else None
    path = window.project_file_name()
    if path:
        path = os.path.split(path)[0]

    files = []
    if not folders:
        view = window.active_view()
        if view and view.file_name() is not None:
            files.append(view.file_name())

        return files

    for folder in folders:
        files.extend(_files_for_folder(window, folder, path))

    return files



# Any window with folders open always:
#   1) responds to window.folders() with a list of folders (absolute)
#   2) responds to window.project_data() with at least the "folders" key
#
# Additionally, anything with a project responds to:
#   1) window.project_file_name()
class FileGatherCommand(sublime_plugin.WindowCommand):
    def run(self):
        files = _find_project_files(self.window)
        pprint(files)

