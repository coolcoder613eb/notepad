import lvgl as lv
import tulip
import os

class Editor:
    def __init__(self, screen):
        self.screen = screen
        self.current_file = 'untitled.txt'
        self.undo_stack = []
        self.redo_stack = []
        self.last_text = ""
        self.filename_mode = False
        
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
            with open(self.current_file, 'wb') as f:
                f.write(self.ta.get_text().encode('utf-8','ignore'))
            return True
        except:
            return False

    def load_text(self):
        try:
            with open(self.current_file, 'rb') as f:
                text = f.read().decode('utf-8','ignore')
                self.ta.set_text(text)
                self.last_text = text
                self.undo_stack.clear()
                self.redo_stack.clear()
            return True
        except:
            return False

def run(screen):
    editor = Editor(screen)
    screen.bg_color = 255  # White background
    screen.handle_keyboard = True
    screen.quit_callback = quit
    
    (H_RES, V_RES) = tulip.screen_size()
    
    # Create top panel for filename and keys
    top_panel = lv.obj(screen.group)
    top_panel.set_pos(0, 0)
    top_panel.set_size(H_RES, 50)
    top_panel.set_style_bg_color(tulip.pal_to_lv(191), lv.PART.MAIN)
    top_panel.set_style_pad_all(0, 0)
    
    # Create filename input
    filename = lv.textarea(top_panel)
    filename.set_pos(5, 5)
    filename.set_size(200, 25)
    filename.set_one_line(True)
    filename.set_text(editor.current_file)
    filename.set_style_text_font(lv.font_montserrat_12, 0)
    filename.set_style_bg_color(tulip.pal_to_lv(223), lv.PART.MAIN)
    filename.set_style_text_color(tulip.pal_to_lv(0), 0)
    editor.filename = filename
    
    # Create keybindings display
    keys_label = lv.label(top_panel)
    keys_label.set_pos(210, 10)
    keys_label.set_style_text_color(tulip.pal_to_lv(0), 0)
    keys_label.set_style_text_font(lv.font_montserrat_12, 0)
    keys_label.set_text("^S : Save | ^O : Open | ^Z : Undo | ^Y : Redo | ^K : Kbd")
    
    # Create status bar
    status = lv.label(screen.group)
    status.set_pos(5, V_RES - 25)
    status.set_style_text_color(tulip.pal_to_lv(0), 0)
    status.set_text("Ready")
    editor.status = status
    
    # Create main text area
    ta = lv.textarea(screen.group)
    ta.set_pos(0, 40)
    ta.set_size(H_RES, V_RES - 65)  # Leave room for status bar
    ta.set_style_text_font(lv.font_montserrat_12, 0)
    ta.set_style_bg_color(tulip.pal_to_lv(255), lv.PART.MAIN)
    ta.set_style_text_color(tulip.pal_to_lv(0), 0)
    ta.set_style_border_color(tulip.pal_to_lv(0), lv.PART.CURSOR | lv.STATE.FOCUSED)
    ta.set_placeholder_text("Type away...")
    editor.ta = ta
    
    def key_handler(key):
        keys = tulip.keys()
        
        if key == 19:  # Ctrl+S
            editor.current_file = filename.get_text()
            if editor.save_text():
                status.set_text(f"Saved to {editor.current_file}!")
            else:
                status.set_text("Save failed!")
            lv.group_focus_obj(ta)
        elif key == 15:  # Ctrl+O
            editor.current_file = filename.get_text()
            if editor.load_text():
                status.set_text(f"Opened {editor.current_file}!")
            else:
                status.set_text("File not found!")
            lv.group_focus_obj(ta)
        elif key == 26:  # Ctrl+Z
            editor.undo()
        elif key == 25:  # Ctrl+Y
            editor.redo()
        elif key == 11:  # Ctrl+K
            tulip.keyboard()
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
