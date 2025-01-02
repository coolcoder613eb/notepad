import lvgl as lv
import tulip
import os

def split(path):
    if path == "":
        return ("", "")
    r = path.rsplit("/", 1)
    if len(r) == 1:
        return ("", path)
    head = r[0]  # .rstrip("/")
    if not head:
        head = "/"
    return (head, r[1])


def dirname(path):
    return split(path)[0]

def basename(path):
    return split(path)[1]

def join(*args):
    return "/".join(args).replace('//','/')

def isdir(path):
    try:
        mode = os.stat(path)[0]
        return mode & 0o040000
    except OSError:
        return False


def isfile(path):
    try:
        return bool(os.stat(path)[0] & 0x8000)
    except OSError:
        return False

class SimpleBrowser:
    def __init__(self, screen, mode, callback):
        """
        Initialize file browser dialog

        Args:
            screen: Parent screen object
            mode: Either "open", "save" or "saveas"
            callback: Function to call with selected path
        """
        self.screen = screen
        self.mode = mode
        self.callback = callback
        self.current_path = os.getcwd()

        # Create modal window
        self.window = lv.obj(screen.group)
        (H_RES, V_RES) = tulip.screen_size()
        self.window.set_size(int(H_RES * 0.9), int(V_RES * 0.8))
        self.window.center()
        self.window.set_style_bg_color(tulip.pal_to_lv(146), 0)  # White background

        # Add title
        title = "Save File" if mode in ("save", "saveas") else "Open File"
        self.title = lv.label(self.window)
        self.title.set_text(title)
        self.title.align(lv.ALIGN.TOP_LEFT, 0, 2)

        # Current path display
        self.path_label = lv.label(self.window)
        self.path_label.set_text(self.current_path)
        self.path_label.align(lv.ALIGN.TOP_RIGHT, 0, 2)

        # File list
        self.list = lv.list(self.window)
        self.list.set_size(int(H_RES * 0.88)-30, int(V_RES * 0.77)-95)
        self.list.align(lv.ALIGN.CENTER, 0, -10)
        self.list.set_style_bg_color(tulip.pal_to_lv(255), 0)

        # Filename input field for save mode
        if mode in ("save", "saveas"):
            self.filename = lv.textarea(self.window)
            self.filename.set_size(int(H_RES * 0.45), 35)
            self.filename.align(lv.ALIGN.BOTTOM_MID, 0, -0)
            self.filename.set_one_line(True)
            self.filename.set_style_text_font(lv.font_montserrat_12, 0)
            self.filename.set_placeholder_text("Enter filename...")
            if hasattr(screen, 'editor'):
                self.filename.set_text(basename(screen.editor.current_file))

        # Buttons
        btn_width = 50
        btn_height = 35

        self.ok_btn = lv.button(self.window)
        self.ok_btn.set_size(btn_width, btn_height)
        self.ok_btn.align(lv.ALIGN.BOTTOM_LEFT, 0, -0)
        self.ok_label = lv.label(self.ok_btn)
        self.ok_label.set_text("OK")
        self.ok_label.center()
        self.ok_btn.add_event_cb(self.on_ok, lv.EVENT.CLICKED, None)

        self.cancel_btn = lv.button(self.window)
        self.cancel_btn.set_size(btn_width, btn_height)
        self.cancel_btn.align(lv.ALIGN.BOTTOM_RIGHT, 0, -0)
        self.cancel_label = lv.label(self.cancel_btn)
        self.cancel_label.set_text("Cancel")
        self.cancel_label.center()
        self.cancel_btn.add_event_cb(self.on_cancel, lv.EVENT.CLICKED, None)

        # Initial population
        self.refresh_file_list()

    def refresh_file_list(self):
        """Refresh the file list with current directory contents"""
        self.list.clean()
        self.path_label.set_text(self.current_path)

        try:
            entries = os.listdir(self.current_path)
            # Sort directories first, then files
            dirs = sorted([e for e in entries if isdir(join(self.current_path, e))])
            if self.current_path != '/':
                dirs.insert(0,'..')

            files = sorted([e for e in entries if isfile(join(self.current_path, e))])
            # Add directories with a "/" suffix
            for d in dirs:
                btn = self.list.add_button(None, f"{d}/")
                btn.add_event_cb(lambda e, d=d: self.on_dir_click(d), lv.EVENT.CLICKED, None)

            # Add files
            for f in files:
                btn = self.list.add_button(None, f"{f}")
                btn.add_event_cb(lambda e, f=f: self.on_file_click(f), lv.EVENT.CLICKED, None)

        except OSError as e:
            raise e
            # Handle case where directory can't be read
            self.list.add_button(None, "Error reading directory")

    def on_dir_click(self, dir):
        """Handle directory click by entering it"""
        if dir=='..':
            parent = dirname(self.current_path)
            if parent != self.current_path:  # Prevent going above root
                self.current_path = parent
                self.refresh_file_list()
        else:
            self.current_path = join(self.current_path, dir)
        self.current_path.replace('//','/')
        self.refresh_file_list()

    def on_file_click(self, filename):
        """Handle file click by selecting it"""
        if self.mode == "open":
            self.selected_file = filename
            self.path_label.set_text(join(self.current_path,filename))
        elif hasattr(self, 'filename'):
            self.filename.set_text(filename)

    def on_ok(self, event):
        """Handle OK button click"""
        if self.mode in ("save", "saveas"):
            if hasattr(self, 'filename'):
                filename = self.filename.get_text().strip()
                if filename:
                    full_path = join(self.current_path, filename)
                    self.cleanup()
                    self.callback(full_path)
        else:  # open mode
            if hasattr(self, 'selected_file'):
                full_path = join(self.current_path, self.selected_file)
                self.cleanup()
                self.callback(full_path)

    def on_cancel(self, event):
        """Handle cancel button click"""
        self.cleanup()
        self.callback(None)

    def cleanup(self):
        """Clean up the browser window"""
        self.window.delete()

class Editor:
    def __init__(self, screen):
        self.screen = screen
        self.current_file = "untitled.txt"
        self.undo_stack = []
        self.redo_stack = []
        self.last_text = ""
        self.filename_mode = False
        self.browser=None

    def create_file_browser(self, mode):
        def browser_callback(path):
            if path:
                self.current_file = path
                if mode == "open":
                    if self.load_text():
                        self.status.set_text(f"Opened {self.current_file}!")
                    else:
                        self.status.set_text("Failed to open file!")
                else:  # save or saveas
                    if self.save_text():
                        self.status.set_text(f"Saved to {self.current_file}!")
                    else:
                        self.status.set_text("Save failed!")
            lv.group_focus_obj(self.ta)

        self.browser = SimpleBrowser(self.screen, mode, browser_callback)


    def save_state(self):
        try:
            current = self.ta.get_text()
            if current != self.last_text:
                self.undo_stack.append(self.last_text)
                self.last_text = current
                self.redo_stack.clear()
        except:
            pass

    def undo(self):
        if self.undo_stack:
            current = self.ta.get_text()
            self.redo_stack.append(current)
            text = self.undo_stack.pop()
            self.ta.set_text(text)
            self.last_text = text

    def redo(self):
        if self.redo_stack:
            current = self.ta.get_text()
            self.undo_stack.append(current)
            text = self.redo_stack.pop()
            self.ta.set_text(text)
            self.last_text = text

    def save_text(self):
        try:
            with open(self.current_file, "wb") as f:
                f.write(self.ta.get_text().encode("utf-8", "ignore"))
            return True
        except:
            return False

    def load_text(self):
        try:
            with open(self.current_file, "rb") as f:
                text = f.read().decode("utf-8", "ignore")
                self.ta.set_text(text)
                self.last_text = text
                self.undo_stack.clear()
                self.redo_stack.clear()
            return True
        except:
            return False
SAVE="Save ^S"
SAVEAS="Save As"
OPEN="Open ^O"
NEW="New ^N"
EXIT="Exit ^Q"
UNDO="Undo ^Z"
REDO="Redo ^Y"
KEYBOARD="Keyboard ^K"

def run(screen):
    def menu_cb(e):
        dropdown = e.get_target_obj()
        option = b" "*64 # should be large enough to store the option
        #option=dropdown.__dereference__(1024)
        dropdown.get_selected_str(option, len(option))
        action(str(option.strip().rstrip(b'\0'),'utf-8'))

    editor = Editor(screen)
    screen.bg_color = 146  # White background
    screen.handle_keyboard = True
    screen.quit_callback = quit

    (H_RES, V_RES) = tulip.screen_size()

    file_menu = lv.dropdown(screen.group)
    file_menu.align(lv.ALIGN.TOP_LEFT, 2, 2)
    file_menu.set_options(
        "\n".join([SAVE, SAVEAS, OPEN, NEW, EXIT])
    )
    file_menu.set_text("File")
    file_menu.add_event_cb(menu_cb, lv.EVENT.VALUE_CHANGED, None)

    edit_menu = lv.dropdown(screen.group)
    edit_menu.align(lv.ALIGN.TOP_LEFT, 138, 2)
    edit_menu.set_options("\n".join([UNDO, REDO, KEYBOARD]))
    edit_menu.set_text("Edit")
    edit_menu.add_event_cb(menu_cb, lv.EVENT.VALUE_CHANGED, None)

    # Create status bar
    status = lv.label(screen.group)
    status.set_pos(5, V_RES - 25)
    status.set_style_text_color(tulip.pal_to_lv(0), 0)
    status.set_text("Ready")
    editor.status = status

    # Create main text area
    ta = lv.textarea(screen.group)
    ta.set_pos(0, 30)
    ta.set_size(H_RES, V_RES - 65)  # Leave room for status bar
    ta.set_style_text_font(lv.font_montserrat_12, 0)
    ta.set_style_bg_color(tulip.pal_to_lv(255), lv.PART.MAIN)
    ta.set_style_text_color(tulip.pal_to_lv(0), 0)
    ta.set_style_border_color(tulip.pal_to_lv(0), lv.PART.CURSOR | lv.STATE.FOCUSED)
    ta.set_placeholder_text("Type away...")
    editor.ta = ta



    def action(name):
        if name == SAVE:
            if editor.current_file == "untitled.txt":
                editor.create_file_browser("save")
            else:
                if editor.save_text():
                    editor.status.set_text(f"Saved to {editor.current_file}!")
                else:
                    editor.status.set_text("Save failed!")
        elif name == SAVEAS:
            editor.create_file_browser("saveas")
        elif name == OPEN:
            editor.create_file_browser("open")
        elif name == NEW:
            editor.ta.set_text("")
            editor.current_file = "untitled.txt"
            editor.save_state()
            editor.status.set_text("New file created")
        elif name == UNDO:
            editor.undo()
        elif name == REDO:
            editor.redo()
        elif name == KEYBOARD:
            tulip.keyboard()
        elif name == EXIT:
            screen.quit()

    def key_handler(key):
        keys = tulip.keys()

        if key == 19:  # Ctrl+S
            action(SAVE)
        elif key == 15:  # Ctrl+O
            action(OPEN)
        elif key == 26:  # Ctrl+Z
            action(UNDO)
        elif key == 25:  # Ctrl+Y
            action(REDO)
        elif key == 11:  # Ctrl+K
            action(KEYBOARD)
        elif key == 14:  # Ctrl+N
            action(NEW)
        else:
            editor.save_state()  # Save state for undo/redo

    # Register keyboard callback
    tulip.keyboard_callback(key_handler)

    # Set initial focus
    lv.group_focus_obj(ta)

    # Try to load previous text
    editor.load_text()

    screen.present()

    # Store references for cleanup
    screen.editor = editor


def quit(screen):
    tulip.keyboard_callback()
