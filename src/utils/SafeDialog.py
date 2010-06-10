# A simple Dialog modeled after Tk's dialog script
# 
# XXX Bugs:
# - Resizing behavior is ugly

#from SafeTkinter import *
from Tkinter import *
import tktools

class Dialog:

    def __init__(self, master=None,
                 title='', text='', bitmap='', default=-1, strings=[]):
        self.root = tktools.make_toplevel(master, title=title)
        self.message = Message(self.root, text=text, aspect=400)
        self.message.pack()
        self.frame = Frame(self.root)
        self.frame.pack()
        num = 0
        self.num = default
        if 0 <= default < len(strings):
            self.root.bind('<Return>', self.default_done)
        for s in strings:
            b = Button(self.frame, text=s,
                       command=(lambda self=self, num=num: self.done(num)))
            if num == default:
                b.config(relief='ridge', border=4)
            b.pack(side='left', fill='both', expand=1)
            num = num+1
        tktools.set_transient(self.root, master)
        try:
            self.root.grab_set()
        except TclError:
            print "*** Grab failed ***"
        try:
            self.root.mainloop()
        except SystemExit:
            pass
        self.root.destroy()

    def default_done(self, event):
        raise SystemExit

    def done(self, num):
        self.num = num
        raise SystemExit

def _test():
        d = Dialog(root,  title='File Modified',
                          text=
                          'File "Python.h" has been modified'
                          ' since the last time it was saved.'
                          ' Do you want to save it before'
                          ' exiting the application?',
                          bitmap='questhead',
                          default=0,
                          strings=('Save File', 
                                      'Discard Changes', 
                                      'Return to Editor'))
        print d.num

if __name__ == '__main__':
    from Tkinter import Tk
    root = Tk()
    t = Button(root, text='Test', command=_test)
    t.pack()
    q = Button(root, text='Quit', command=t.quit)
    q.pack()
    t.mainloop()
