import sublime
import sublime_plugin

from pprint import pprint
import json

from .file_gather import find_project_files, calculate_fileset_deltas


### ---------------------------------------------------------------------------


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


### ---------------------------------------------------------------------------


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
