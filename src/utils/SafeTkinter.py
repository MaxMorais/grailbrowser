from types import *
# NB Don't import Tk!
from Tkinter import TkVersion, TclVersion, TclError

TEMPLATE = """
def %(name)s(*args, **kw):
    from Tkinter import %(name)s
    original = apply(%(name)s, args, kw)
    def filter(name):
        return name[0] != '_' or name in ('__getitem__',
                                          '__setitem__',
                                          '__str__',
                                          '_create',
                                          '_do')
    from Bastion import Bastion
    bastion = Bastion(original, filter=filter)
    if hasattr(original, '_w'):
        bastion._w = original._w        # XXX This defeats the purpose :-(
        bastion.tk = original.tk        # XXX This too :-(
        bastion.children = original.children # XXX And this :-(
        bastion.master = original.master # XXX And so on :-(
    return bastion
"""

for name in ('Event', 'StringVar', 'IntVar', 'DoubleVar',
     'BooleanVar', 'mainloop', 'getint', 'getdouble', 'getboolean',
     'Misc', 'Wm', 'Pack', 'Place', 'Toplevel', 'Button', 'Canvas',
     'Checkbutton', 'Entry', 'Frame', 'Label', 'Listbox', 'Menu',
     'Menubutton', 'Message', 'Radiobutton', 'Scale', 'Scrollbar',
     'Text', 'Image', 'PhotoImage', 'BitmapImage', 'OptionMenu',
     'image_names', 'image_types'):
     exec TEMPLATE % {'name': name}

del TEMPLATE, name
    
from Tkconstants import *

from Tkinter import _tkinter, _cnfmerge, _flatten
tkinter = _tkinter

class _DumbTkinter:
    """Helper class to provide interfaces to low-level handler functions"""
    READABLE = tkinter.READABLE
    WRITABLE = tkinter.WRITABLE
    try:
        createfilehandler = tkinter.createfilehandler
    except AttributeError:
        pass
    try:
        deletefilehandler = tkinter.deletefilehandler
    except AttributeError:
        pass
    try:
        createtimerhandler = tkinter.createtimerhandler
    except AttributeError:
        pass

tkinter = _DumbTkinter()

def _castrate(tk):
    """Remove all Tcl commands that can affect the file system.

    This way, if someone breaks through the bastion around Tk, all
    they can do is screw up Grail.  (Though if they are really clever,
    they may be able to catch some of the user's keyboard input, or do
    other subversive things.)

    """
    if not hasattr(tk, 'eval'): return # For Rivet
    def rm(name, tk=tk):
        try:
            tk.call('rename', name, '')
        except TclError:
            pass
    # Make sure the menu support commands are autoloaded, since we need them
    tk.eval("auto_load tkMenuInvoke")
    rm('exec')
    rm('cd')
    rm('open') # This is what breaks the menu support commands
    rm('send')
