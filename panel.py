import sublime
import sublime_plugin


class RemoteBuildClearPanelCommand(sublime_plugin.TextCommand):
    """
    Provide a command to clear the remote build status window.
    """
    def run(self, edit):
        self.view.set_read_only(False)
        self.view.erase(edit, sublime.Region(0, len(self.view)))
        self.view.set_read_only(True)

    def is_enabled(self):
        return self.view.settings().get("_rb_net_window", False)

    def is_visible(self):
        return self.is_enabled()
