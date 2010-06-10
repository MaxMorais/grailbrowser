if __name__ == '__main__':
    # Testing
    import sys
    sys.path.insert(0, "../pythonlib")


from tktools import *


def make_super_text_box(parent, width=0, height=0, hbar=0, vbar=1,
                  fill=BOTH, expand=1, wrap=WORD, pack=1):

    """Create a text box with smooth scrolling."""

    hbar, vbar, frame = make_scrollbars(parent, hbar, vbar, pack)
    subframe = Frame(frame, borderwidth=2, relief=SUNKEN)
    subframe.pack(expand=expand, fill=fill)
    canvas = Canvas(subframe)
    frame.canvas = canvas
    canvas.pack(expand=expand, fill=fill, side=LEFT)
    text = Text(canvas, wrap=wrap, borderwidth=0)
    canvas.create_window(0, 0,
                         anchor=NW,
                         tags='theText',
                         window=text)
    if width:
        text.config(width=width)
        width = text.winfo_reqwidth()
        canvas.config(width=width)
        canvas.itemconfig('theText', width=width)
    if height:
        text.config(height=height)
        height = text.winfo_reqheight()
        canvas.config(height=height)
        canvas.itemconfig('theText', height=height)
    set_scroll_commands(text, hbar, None)
    text.vbar = vbar
    set_scroll_commands(canvas, None, vbar)
    canvas.text = text
    canvas.bind('<Configure>', resize_super_text_box)
    return text, frame


def resize_super_text_box(event=None, frame=None):
    canvas = frame and frame.canvas or event.widget
    canvas.update_idletasks()
    width = canvas.winfo_width()
    height = canvas.winfo_height()
##    print "canvas:", width, "x", height
    fakeheight = 1000000
    canvas.itemconfig('theText', width=width, height=fakeheight)
    text = canvas.text
    text.yview("1.0")
    canvas.update_idletasks()
    info = text.dlineinfo("end-1char")
##    print "info:", info
    if info:
        x, y, w, h, bl = info
        totheight = y + h
        canvas.config(scrollregion=(0, 0, width, totheight))
    else:
        canvas.config(scrollregion=(0, 0, 0, 0))


def test():
    data = "The quick brown fox jumps over the lazy dog.\n" * 25 + "END"
    root = Tk()
    super, frame = make_super_text_box(root, hbar=1, vbar=1,
                                       width=40, height=20, wrap=NONE)
    super.insert(END, data)
    resize_super_text_box(frame=frame)
    root.mainloop()


if __name__ == '__main__':
    test()
