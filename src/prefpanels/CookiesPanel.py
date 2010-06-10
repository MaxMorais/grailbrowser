"""Grail configuration panel for cookie handling."""

__version__ = '$Revision: 1.1 $'


import PrefsPanels
import string
import Tkinter


GROUP = "cookies"
LABEL_WIDTH = 16

_get_tr = string.maketrans(" ", "-")
_set_tr = string.maketrans("-", " ")


def conv_display(s):
    return string.capitalize(string.translate(s, _set_tr))


class CapitalizedStringVar(Tkinter.StringVar):
    def get(self):
        value = Tkinter.StringVar.get(self)
        return string.lower(string.translate(value, _get_tr))

    def set(self, value):
        Tkinter.StringVar.set(self, conv_display(value))


class CookiesPanel(PrefsPanels.Framework):

    # Class var for help button - relative to grail-home-page.
    HELP_URL = "help/prefs/cookies.html"

    def CreateLayout(self, name, frame):
        self.add_option_menu(frame, "On receipt:", "receive-action",
                             "always-accept ask reject")
        self.add_option_menu(frame, "On request:", "send-action",
                             "always-send ask never-send")

    def add_option_menu(self, frame, label, option, items):
        items = map(conv_display, string.split(items))
        var = CapitalizedStringVar(frame)
        self.PrefsOptionMenu(frame, label,
                             GROUP, option, items,
                             label_width=LABEL_WIDTH,
                             variable=var)
