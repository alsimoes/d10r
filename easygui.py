# -*- coding: utf-8 -*-
"""
@version: 0.93(2009-07-07)
EasyGui migrado para PySide6. Todas as funções Tkinter foram removidas.
Use gui_pyside.py para diálogos e caixas de mensagem.
"""
import sys, os, string, types, pickle, traceback
from utils import ICON
from gui_pyside import ChoiceBoxQt, TextEntryBoxQt, file_open_dialog, show_message

# Caixas de diálogo principais usando PySide6

def ynbox(msg="Shall I continue?", title=" ", choices=("Sim", "Não"), image=None):
    """
    Display a msgbox with choices of Yes and No.

    The default is "Yes".

    The returned value is calculated this way::
        if the first choice ("Yes") is chosen, or if the dialog is cancelled:
            return 1
        else:
            return 0

    If invoked without a msg argument, displays a generic request for a confirmation
    that the user wishes to continue.  So it can be used this way::
        if ynbox(): pass # continue
        else: sys.exit(0)  # exit the program

    @arg msg: the msg to be displayed.
    @arg title: the window title
    @arg choices: a list or tuple of the choices to be displayed
    """
    dlg = ChoiceBoxQt(title, msg, choices)
    if dlg.exec():
        return dlg.get() == choices[0]
    return False


#-----------------------------------------------------------------------
# ccbox
#-----------------------------------------------------------------------
def ccbox(msg="Shall I continue?"
    , title=" "
    , choices=("Continue", "Cancel")
    , image=None
    ):
    """
    Display a msgbox with choices of Continue and Cancel.

    The default is "Continue".

    The returned value is calculated this way::
        if the first choice ("Continue") is chosen, or if the dialog is cancelled:
            return 1
        else:
            return 0

    If invoked without a msg argument, displays a generic request for a confirmation
    that the user wishes to continue.  So it can be used this way::

        if ccbox():
            pass # continue
        else:
            sys.exit(0)  # exit the program

    @arg msg: the msg to be displayed.
    @arg title: the window title
    @arg choices: a list or tuple of the choices to be displayed
    """
    return ynbox(msg, title, choices, image)


#-----------------------------------------------------------------------
# boolbox
#-----------------------------------------------------------------------
def boolbox(msg="Shall I continue?"
    , title=" "
    , choices=("Yes","No")
    , image=None
    ):
    """
    Display a boolean msgbox.

    The default is the first choice.

    The returned value is calculated this way::
        if the first choice is chosen, or if the dialog is cancelled:
            returns 1
        else:
            returns 0
    """
    reply = buttonbox(msg=msg, choices=choices, title=title, image=image)
    if reply == choices[0]: return 1
    else: return 0


#-----------------------------------------------------------------------
# indexbox
#-----------------------------------------------------------------------
def indexbox(msg="Shall I continue?"
    , title=" "
    , choices=("Yes","No")
    , image=None
    ):
    """
    Display a buttonbox with the specified choices.
    Return the index of the choice selected.
    """
    reply = buttonbox(msg=msg, choices=choices, title=title, image=image)
    index = -1
    for choice in choices:
        index = index + 1
        if reply == choice: return index
    raise AssertionError(
        "There is a program logic error in the EasyGui code for indexbox.")


#-----------------------------------------------------------------------
# msgbox
#-----------------------------------------------------------------------
def msgbox(msg="(Your message goes here)", title="Mensagem", ok_button="OK", image=None, root=None):
    """
    Display a messagebox
    """
    show_message(title, msg)
    return ok_button


#-------------------------------------------------------------------
# buttonbox
#-------------------------------------------------------------------
def buttonbox(msg="", title=" "
    , choices=("Button1", "Button2", "Button3")
    , image=None
    , root=None
    ):
    """
    Display a msg, a title, and a set of buttons.
    The buttons are defined by the members of the choices list.
    Return the text of the button that the user selected.

    @arg msg: the msg to be displayed.
    @arg title: the window title
    @arg choices: a list or tuple of the choices to be displayed
    """
    dlg = ChoiceBoxQt(title, msg, choices)
    if dlg.exec():
        return dlg.get()
    return None


#-------------------------------------------------------------------
# integerbox
#-------------------------------------------------------------------
def integerbox(msg=""
    , title=" "
    , default=""
    , argLowerBound=0
    , argUpperBound=99
    , image = None
    , root  = None
    ):
    """
    Show a box in which a user can enter an integer.

    In addition to arguments for msg and title, this function accepts
    integer arguments for default_value, lowerbound, and upperbound.

    The default_value argument may be None.

    When the user enters some text, the text is checked to verify
    that it can be converted to an integer between the lowerbound and upperbound.

    If it can be, the integer (not the text) is returned.

    If it cannot, then an error msg is displayed, and the integerbox is
    redisplayed.

    If the user cancels the operation, None is returned.
    """
    dlg = TextEntryBoxQt(title, msg, str(default))
    if dlg.exec():
        try:
            val = int(dlg.get())
            if argLowerBound <= val <= argUpperBound:
                return val
        except ValueError:
            pass
    return None


#-------------------------------------------------------------------
# enterbox
#-------------------------------------------------------------------
def enterbox(msg="Enter something."
    , title=" "
    , default=""
    , strip=True
    , image=None
    , root=None
    ):
    """
    Show a box in which a user can enter some text.

    You may optionally specify some default text, which will appear in the
    enterbox when it is displayed.

    Returns the text that the user entered, or None if he cancels the operation.

    By default, enterbox strips its result (i.e. removes leading and trailing
    whitespace).  (If you want it not to strip, use keyword argument: strip=False.)
    This makes it easier to test the results of the call::

        reply = enterbox(....)
        if reply:
            ...
        else:
            ...
    """
    dlg = TextEntryBoxQt(title, msg, default)
    if dlg.exec():
        result = dlg.get()
        return result.strip() if strip else result
    return None


def passwordbox(msg="Enter your password."
    , title=" "
    , default=""
    , image=None
    , root=None
    ):
    """
    Show a box in which a user can enter a password.
    The text is masked with asterisks, so the password is not displayed.
    Returns the text that the user entered, or None if he cancels the operation.
    """
    dlg = TextEntryBoxQt(title, msg, default)
    if dlg.exec():
        return dlg.get()
    return None


def choicebox(msg="Pick something."
    , title=" "
    , choices=()
    , buttons=()
    ):
    """
    Present the user with a list of choices.
    return the choice that he selects.
    return None if he cancels the selection selection.

    @arg msg: the msg to be displayed.
    @arg title: the window title
    @arg choices: a list or tuple of the choices to be displayed
    """
    dlg = ChoiceBoxQt(title, msg, choices)
    if dlg.exec():
        return dlg.get()
    return None


def fileopenbox(msg=None
    , title=None
    , default="*"
    , filetypes=None
    ):
    r"""
    A dialog to get a file name.

    About the "default" argument
    ============================
        The "default" argument specifies a filepath that (normally)
        contains one or more wildcards.
        fileopenbox will display only files that match the default filepath.
        If omitted, defaults to "*" (all files in the current directory).

        WINDOWS EXAMPLE::
            ...default="c:/myjunk/*.py"
        will open in directory c:\myjunk\ and show all Python files.

        WINDOWS EXAMPLE::
            ...default="c:/myjunk/test*.py"
        will open in directory c:\myjunk\ and show all Python files
        whose names begin with "test".


        Note that on Windows, fileopenbox automatically changes the path
        separator to the Windows path separator (backslash).

    About the "filetypes" argument
    ==============================
        If specified, it should contain a list of items,
        where each item is either::
            - a string containing a filemask          # e.g. "*.txt"
            - a list of strings, where all of the strings except the last one
                are filemasks (each beginning with "*.",
                such as "*.txt" for text files, "*.py" for Python files, etc.).
                and the last string contains a filetype description

        EXAMPLE::
            filetypes = ["*.css", ["*.htm", "*.html", "HTML files"]  ]

    NOTE THAT
    =========

        If the filetypes list does not contain ("All files","*"),
        it will be added.

        If the filetypes list does not contain a filemask that includes
        the extension of the "default" argument, it will be added.
        For example, if     default="*abc.py"
        and no filetypes argument was specified, then
        "*.py" will automatically be added to the filetypes argument.

    @rtype: string or None
    @return: the name of a file, or None if user chose to cancel

    @arg msg: the msg to be displayed.
    @arg title: the window title
    @arg default: filepath with wildcards
    @arg filetypes: filemasks that a user can choose, e.g. "*.txt"
    """
    return file_open_dialog(title or "Abrir arquivo", filetypes)


def filesavebox(msg=None
    , title=None
    , default=""
    , filetypes=None
    ):
    """
    A file to get the name of a file to save.
    Returns the name of a file, or None if user chose to cancel.

    The "default" argument should contain a filename (i.e. the
    current name of the file to be saved).  It may also be empty,
    or contain a filemask that includes wildcards.

    The "filetypes" argument works like the "filetypes" argument to
    fileopenbox.
    """

    return file_open_dialog(title or "Salvar arquivo", filetypes)


def textbox(msg="", title=" ", text="", codebox=0):
    show_message(title, f"{msg}\n\n{text}")
    return "OK"


def exceptionbox(msg=None, title=None):
    exc = traceback.format_exc()
    show_message(title or "Exceção", f"{msg}\n\n{exc}")
    return "OK"


EASYGUI_ABOUT_INFORMATION = '''
========================================================================
0.93(2009-07-07)
========================================================================

ENHANCEMENTS
------------------------------------------------------

 * Added exceptionbox to display stack trace of exceptions
 * modified names of some font-related constants to make it
   easier to customize them


========================================================================
0.92(2009-06-22)
========================================================================

ENHANCEMENTS
------------------------------------------------------

 * Added EgStore class to to provide basic easy-to-use persistence.

BUG FIXES
------------------------------------------------------

 * Fixed a bug that was preventing Linux users from copying text out of
   a textbox and a codebox.  This was not a problem for Windows users.


========================================================================
version: 0.91(2009-04-25)
========================================================================

ENHANCEMENTS
------------------------------------------------------

 * exposed egdemo().  Now you can write a program like this:

        from easygui import *
        egdemo()   # run the easygui demo


BUG FIXES
------------------------------------------------------

 * Removed some fileopenbox test code that was accidentally left in,
   causing egdemo to crash.

 * Made EasyGui "version 2.5 aware" so that it will use the correct
   default filemask in fileopenbox and filesavebox under Python 2.5
   and earlier.

 * fixed bugs in filesavebox by converting it to use the same code as
   fileopenbox for handling the "default" and "filetypes" args.


========================================================================
version: 0.90(2009-04-20)
========================================================================

ENHANCEMENTS
------------------------------------------------------

 * Enhanced fileopenbox to allow it to accept multiple
   extensions for a single file type, e.g.:
         ... filetype = [[".htm",".html", "HTML filetypes"]]
   Previously it accepted only one.


BUG FIXES
------------------------------------------------------

 * Fixed a bug in fileopenbox (it was not displaying initialfile).

   Thanks to Matthias Meier in the lovely city of Schwerin, Germany
   (http://en.wikipedia.org/wiki/Schwerin) for reporting the problem
   and supplying the basic elements of the fix.

 * In fileopenbox, removed acceptance of a 1-tuple as a filetype.

   This was an unnecessary and confusing feature.  In theory,
   this change will break backward compatibility ... but
   there are probably no programs that used this feature.


NOTES
----------------------------------------------------------

   In some cases (e.g. ... default="junk.txt")
   there are minor differences in the display of fileopenbox
   between Python version 2.5 on the one hand,
   and Python version 2.6 and higher on the other.
   Python versions 2.6+ behave correctly.


========================================================================
version 0.89(2009-04-09)
========================================================================

BUG FIX
------------------------------------------------------
 * An enhancement in version 0.88 (which added an import of StringIO)
   broke compatibility with Python 3.

   "In Python 3, the StringIO and cStringIO modules are gone.
   Instead, import the io module and use io.StringIO or io.BytesIO
   for text and data respectively."

   Many thanks to Alan Gauld, author of the "Learn to Program" web site
   (http://www.alan-g.me.uk/l2p) for reporting this problem and
   supplying the fix.

========================================================================
version 0.88(2009-04-06)
========================================================================

ENHANCEMENTS
------------------------------------------------------
 * Support for display of images has been extended to
   the various flavors of enterbox.  An example of
   an enterbox with an image was added to the EasyGui demo.

MODIFICATIONS
------------------------------------------------------
 * In EasyGui demo, HELP output is now captured and displayed
   in a codebox rather than being written to stdout.

BUG FIX
------------------------------------------------------
 * Fixed a bug in fileopenbox.
   Thanks to Dennis A. Wolf for both the bug report and the fix.


========================================================================
version 0.87(2009-03-18)
========================================================================

ENHANCEMENTS
------------------------------------------------------
 * EasyGui will now run under Python version 3.*
   as well as version 2.*

BUG FIXES
------------------------------------------------------
 * added support for "root" argument to msgbox, buttonbox, and
   enterbox.  This feature is not yet documented or very well
   tested -- it should be considered experimental/beta.
'''

def abouteasygui():
    show_message("Sobre EasyGui", "EasyGui migrado para PySide6. Versão adaptada.")
    return "OK"



#-----------------------------------------------------------------------
#
#     class EgStore
#
#-----------------------------------------------------------------------
class EgStore:
    r"""
A class to support persistent storage.

You can use EgStore to support the storage and retrieval
of user settings for an EasyGui application.


# Example A
#-----------------------------------------------------------------------
# define a class named Settings as a subclass of EgStore
#-----------------------------------------------------------------------
class Settings(EgStore):

    def __init__(self, filename):  # filename is required
        #-------------------------------------------------
        # Specify default/initial values for variables that
        # this particular application wants to remember.
        #-------------------------------------------------
        self.userId = ""
        self.targetServer = ""

        #-------------------------------------------------
        # For subclasses of EgStore, these must be
        # the last two statements in  __init__
        #-------------------------------------------------
        self.filename = filename  # this is required
        self.restore()            # restore values from the storage file if possible



# Example B
#-----------------------------------------------------------------------
# create settings, a persistent Settings object
#-----------------------------------------------------------------------
settingsFile = "myApp_settings.txt"
settings = Settings(settingsFile)

user    = "obama_barak"
server  = "whitehouse1"
settings.userId = user
settings.targetServer = server
settings.store()    # persist the settings

# run code that gets a new value for userId, and persist the settings
user    = "biden_joe"
settings.userId = user
settings.store()


# Example C
#-----------------------------------------------------------------------
# recover the Settings instance, change an attribute, and store it again.
#-----------------------------------------------------------------------
settings = Settings(settingsFile)
settings.userId = "vanrossum_g"
settings.store()

"""
    def __init__(self, filename):  # obtaining filename is required
        raise NotImplementedError()

    def restore(self):
        """
        Set the values of whatever attributes are recoverable
        from the pickle file.

        Populate the attributes (the __dict__) of the EgStore object
        from     the attributes (the __dict__) of the pickled object.

        If the pickled object has attributes that have been initialized
        in the EgStore object, then those attributes of the EgStore object
        will be replaced by the values of the corresponding attributes
        in the pickled object.

        If the pickled object is missing some attributes that have
        been initialized in the EgStore object, then those attributes
        of the EgStore object will retain the values that they were
        initialized with.

        If the pickled object has some attributes that were not
        initialized in the EgStore object, then those attributes
        will be ignored.

        IN SUMMARY:

        After the recover() operation, the EgStore object will have all,
        and only, the attributes that it had when it was initialized.

        Where possible, those attributes will have values recovered
        from the pickled object.
        """
        if not os.path.exists(self.filename): return self
        if not os.path.isfile(self.filename): return self

        try:
            f = open(self.filename)
            unpickledObject = pickle.load(f)
            f.close()

            for key in list(self.__dict__.keys()):
                default = self.__dict__[key]
                self.__dict__[key] = unpickledObject.__dict__.get(key,default)
        except:
            pass

        return self

    def store(self):
        """
        Save the attributes of the EgStore object to a pickle file.
        Note that if the directory for the pickle file does not already exist,
        the store operation will fail.
        """
        f = open(self.filename, "w")
        pickle.dump(self, f)
        f.close()


    def kill(self):
        """
        Delete my persistent file (i.e. pickle file), if it exists.
        """
        if os.path.isfile(self.filename):
            os.remove(self.filename)
        return

    def __str__(self):
        """
        return my contents as a string in an easy-to-read format.
        """
        # find the length of the longest attribute name
        longest_key_length = 0
        keys = []
        for key in self.__dict__.keys():
            keys.append(key)
            longest_key_length = max(longest_key_length, len(key))

        keys.sort()  # sort the attribute names
        lines = []
        for key in keys:
            value = self.__dict__[key]
            key = key.ljust(longest_key_length)
            lines.append("%s : %s\n" % (key,repr(value))  )
        return "".join(lines)  # return a string showing the attributes




#-----------------------------------------------------------------------
#
# test/demo easygui
#
#-----------------------------------------------------------------------
def egdemo():
    """
    Run the EasyGui demo.
    """
    # clear the console
    writeln("\n" * 100)

    # ============================= define a code snippet =========================
    code_snippet = ("dafsdfa dasflkj pp[oadsij asdfp;ij asdfpjkop asdfpok asdfpok asdfpok"*3) +"\n"+\
"""# here is some dummy Python code
for someItem in myListOfStuff:
    do something(someItem)
    do something()
    do something()
    if somethingElse(someItem):
        doSomethingEvenMoreInteresting()

"""*16
    #======================== end of code snippet ==============================

    #================================= some text ===========================
    text_snippet = ((\
"""It was the best of times, and it was the worst of times.  The rich ate cake, and the poor had cake recommended to them, but wished only for enough cash to buy bread.  The time was ripe for revolution! """ \
*5)+"\n\n")*10

    #===========================end of text ================================

    intro_message = ("Pick the kind of box that you wish to demo.\n"
    + "\n * Python version " + sys.version
    + "\n * EasyGui version " + egversion
    + "\n * Tk version " + str(TkVersion)
    )

    #========================================== END DEMONSTRATION DATA


    while 1: # do forever
        choices = [
            "msgbox",
            "buttonbox",
            "buttonbox(image) -- a buttonbox that displays an image",
            "choicebox",
            "multchoicebox",
            "textbox",
            "ynbox",
            "ccbox",
            "enterbox",
            "enterbox(image) -- an enterbox that displays an image",
            "exceptionbox",
            "codebox",
            "integerbox",
            "boolbox",
            "indexbox",
            "filesavebox",
            "fileopenbox",
            "passwordbox",
            "multenterbox",
            "multpasswordbox",
            "diropenbox",
            "About EasyGui",
            " Help"
            ]
        choice = choicebox(msg=intro_message
            , title="EasyGui " + egversion
            , choices=choices)

        if not choice: return

        reply = choice.split()

        if   reply[0] == "msgbox":
            reply = msgbox("short msg", "This is a long title")
            writeln("Reply was: %s" % repr(reply))

        elif reply[0] == "About":
            reply = abouteasygui()

        elif reply[0] == "Help":
            _demo_help()

        elif reply[0] == "buttonbox":
            reply = buttonbox()
            writeln("Reply was: %s" % repr(reply))

            title = "Demo of Buttonbox with many, many buttons!"
            msg = "This buttonbox shows what happens when you specify too many buttons."
            reply = buttonbox(msg=msg, title=title, choices=choices)
            writeln("Reply was: %s" % repr(reply))

        elif reply[0] == "buttonbox(image)":
            _demo_buttonbox_with_image()

        elif reply[0] == "boolbox":
            reply = boolbox()
            writeln("Reply was: %s" % repr(reply))

        elif reply[0] == "enterbox":
            image = "python_and_check_logo.gif"
            message = "Enter the name of your best friend."\
                      "\n(Result will be stripped.)"
            reply = enterbox(message, "Love!", "     Suzy Smith     ")
            writeln("Reply was: %s" % repr(reply))

            message = "Enter the name of your best friend."\
                      "\n(Result will NOT be stripped.)"
            reply = enterbox(message, "Love!", "     Suzy Smith     ",strip=False)
            writeln("Reply was: %s" % repr(reply))

            reply = enterbox("Enter the name of your worst enemy:", "Hate!")
            writeln("Reply was: %s" % repr(reply))

        elif reply[0] == "enterbox(image)":
            image = "python_and_check_logo.gif"
            message = "What kind of snake is this?"
            reply = enterbox(message, "Quiz",image=image)
            writeln("Reply was: %s" % repr(reply))

        elif reply[0] == "exceptionbox":
            try:
                thisWillCauseADivideByZeroException = 1/0
            except:
                exceptionbox()

        elif reply[0] == "integerbox":
            reply = integerbox(
                "Enter a number between 3 and 333",
                "Demo: integerbox WITH a default value",
                222, 3, 333)
            writeln("Reply was: %s" % repr(reply))

            reply = integerbox(
                "Enter a number between 0 and 99",
                "Demo: integerbox WITHOUT a default value"
                )
            writeln("Reply was: %s" % repr(reply))

        elif reply[0] == "diropenbox" : _demo_diropenbox()
        elif reply[0] == "fileopenbox": _demo_fileopenbox()
        elif reply[0] == "filesavebox": _demo_filesavebox()

        elif reply[0] == "indexbox":
            title = reply[0]
            msg   =  "Demo of " + reply[0]
            choices = ["Choice1", "Choice2", "Choice3", "Choice4"]
            reply = indexbox(msg, title, choices)
            writeln("Reply was: %s" % repr(reply))

        elif reply[0] == "passwordbox":
            reply = passwordbox("Demo of password box WITHOUT default"
                + "\n\nEnter your secret password", "Member Logon")
            writeln("Reply was: %s" % str(reply))

            reply = passwordbox("Demo of password box WITH default"
                + "\n\nEnter your secret password", "Member Logon", "alfie")
            writeln("Reply was: %s" % str(reply))

        elif reply[0] == "multenterbox":
            msg = "Enter your personal information"
            title = "Credit Card Application"
            fieldNames = ["Name","Street Address","City","State","ZipCode"]
            fieldValues = []  # we start with blanks for the values
            fieldValues = multenterbox(msg,title, fieldNames)

            # make sure that none of the fields was left blank
            while 1:
                if fieldValues == None: break
                errmsg = ""
                for i in range(len(fieldNames)):
                    if fieldValues[i].strip() == "":
                        errmsg = errmsg + ('"%s" is a required field.\n\n' % fieldNames[i])
                if errmsg == "": break # no problems found
                fieldValues = multenterbox(errmsg, title, fieldNames, fieldValues)

            writeln("Reply was: %s" % str(fieldValues))

        elif reply[0] == "multpasswordbox":
            msg = "Enter logon information"
            title = "Demo of multpasswordbox"
            fieldNames = ["Server ID", "User ID", "Password"]
            fieldValues = []  # we start with blanks for the values
            fieldValues = multpasswordbox(msg,title, fieldNames)

            # make sure that none of the fields was left blank
            while 1:
                if fieldValues == None: break
                errmsg = ""
                for i in range(len(fieldNames)):
                    if fieldValues[i].strip() == "":
                        errmsg = errmsg + ('"%s" is a required field.\n\n' % fieldNames[i])
                if errmsg == "": break # no problems found
                fieldValues = multpasswordbox(errmsg, title, fieldNames, fieldValues)

            writeln("Reply was: %s" % str(fieldValues))

        elif reply[0] == "ynbox":
            title = "Demo of ynbox"
            msg = "Were you expecting the Spanish Inquisition?"
            reply = ynbox(msg, title)
            writeln("Reply was: %s" % repr(reply))
            if reply:
                msgbox("NOBODY expects the Spanish Inquisition!", "Wrong!")

        elif reply[0] == "ccbox":
            title = "Demo of ccbox"
            reply = ccbox(msg,title)
            writeln("Reply was: %s" % repr(reply))

        elif reply[0] == "choicebox":
            title = "Demo of choicebox"
            longchoice = "This is an example of a very long option which you may or may not wish to choose."*2
            listChoices = ["nnn", "ddd", "eee", "fff", "aaa", longchoice
                    , "aaa", "bbb", "ccc", "ggg", "hhh", "iii", "jjj", "kkk", "LLL", "mmm" , "nnn", "ooo", "ppp", "qqq", "rrr", "sss", "ttt", "uuu", "vvv"]

            msg = "Pick something. " + ("A wrapable sentence of text ?! "*30) + "\nA separate line of text."*6
            reply = choicebox(msg=msg, choices=listChoices)
            writeln("Reply was: %s" % repr(reply))

            msg = "Pick something. "
            reply = choicebox(msg=msg, title=title, choices=listChoices)
            writeln("Reply was: %s" % repr(reply))

            msg = "Pick something. "
            reply = choicebox(msg="The list of choices is empty!", choices=[])
            writeln("Reply was: %s" % repr(reply))

        elif reply[0] == "multchoicebox":
            listChoices = ["aaa", "bbb", "ccc", "ggg", "hhh", "iii", "jjj", "kkk"
                , "LLL", "mmm" , "nnn", "ooo", "ppp", "qqq"
                , "rrr", "sss", "ttt", "uuu", "vvv"]

            msg = "Pick as many choices as you wish."
            reply = multchoicebox(msg,"Demo of multchoicebox", listChoices)
            writeln("Reply was: %s" % repr(reply))

        elif reply[0] == "textbox":
            title = "Demo of textbox"
            msg = "Here is some sample text. " * 16
            reply = textbox(msg, "Text Sample", text_snippet)
            writeln("Reply was: %s" % repr(reply))

        elif reply[0] == "codebox":
            msg = "Here is some sample code. " * 16
            reply = codebox(msg, "Code Sample", code_snippet)
            writeln("Reply was: %s" % repr(reply))

        else:
            msgbox("Choice\n\n" + choice + "\n\nis not recognized", "Program Logic Error")
            return



def _demo_buttonbox_with_image():
    image = "python_and_check_logo.gif"

    msg   = "Pretty nice, huh!"
    reply=msgbox(msg,image=image, ok_button="Wow!")
    writeln("Reply was: %s" % repr(reply))

    msg   = "Do you like this picture?"
    choices = ["Yes","No","No opinion"]

    reply=buttonbox(msg,image=image,choices=choices)
    writeln("Reply was: %s" % repr(reply))

    image = os.path.normpath("python_and_check_logo.png")
    reply=buttonbox(msg,image=image, choices=choices)
    writeln("Reply was: %s" % repr(reply))

    image = os.path.normpath("zzzzz.gif")
    reply=buttonbox(msg,image=image, choices=choices)
    writeln("Reply was: %s" % repr(reply))


def _demo_help():
    savedStdout = sys.stdout    # save the sys.stdout file object
    sys.stdout = capturedOutput = StringIO()
    help("easygui")
    sys.stdout = savedStdout   # restore the sys.stdout file object
    codebox("EasyGui Help",text=capturedOutput.getvalue())

def _demo_filesavebox():
    filename = "myNewFile.txt"
    title = "File SaveAs"
    msg ="Save file as:"

    f = filesavebox(msg,title,default=filename)
    writeln("You chose to save file: %s" % f)

def _demo_diropenbox():
    title = "Demo of diropenbox"
    msg = "Pick the directory that you wish to open."
    d = diropenbox(msg, title)
    writeln("You chose directory...: %s" % d)

    d = diropenbox(msg, title,default="./")
    writeln("You chose directory...: %s" % d)

    d = diropenbox(msg, title,default="c:/")
    writeln("You chose directory...: %s" % d)


def _demo_fileopenbox():
    msg  = "Python files"
    title = "Open files"
    default="*.py"
    f = fileopenbox(msg,title,default=default)
    writeln("You chose to open file: %s" % f)

    default="./*.gif"
    filetypes = ["*.jpg",["*.zip","*.tgs","*.gz", "Archive files"],["*.htm", "*.html","HTML files"]]
    f = fileopenbox(msg,title,default=default,filetypes=filetypes)
    writeln("You chose to open file: %s" % f)

    """#deadcode -- testing ----------------------------------------
    f = fileopenbox(None,None,default=default)
    writeln("You chose to open file: %s" % f)

    f = fileopenbox(None,title,default=default)
    writeln("You chose to open file: %s" % f)

    f = fileopenbox(msg,None,default=default)
    writeln("You chose to open file: %s" % f)

    f = fileopenbox(default=default)
    writeln("You chose to open file: %s" % f)

    f = fileopenbox(default=None)
    writeln("You chose to open file: %s" % f)
    #----------------------------------------------------deadcode """


def _dummy():
    pass
