import sys
import os
from os.path import abspath, commonpath
from PyQt6   import QtCore, QtGui, QtWidgets

import shutil
from   pathlib import Path

PRIMARY_BG    = "#F5F5F7"
PRIMARY_FG    = "#000000"
ACCENT_BLUE   = "#007AFF" # Alternatives: 007AFF, 0A84FF
BTN_BG        = "#777777"
WINDOW_RADIUS = 14

# Check if a path has a depth 3 from the root directory. This function does
# not take a shell variable path corruption technique into consideration.
def safe_path_depth(p : str) -> bool:
  cnt = 0

  for x, y in zip(p, p[1:]):
    if x == "/" and y != "/":
      cnt = cnt + 1

  cnt -= p.count("..")

  if cnt > 3:
    return True
  return False

# Remove certain Bash syntax rules so that Python's OS library can recognize
# the path.
def sanitize(s : str) -> str:
  return s.replace("\\ ", " ").replace("\\\n", " ").replace("\'", "") \
          .replace("\"", "").rstrip("/ \t\n")

def check_path(p : str) -> str:
  if not os.path.exists(p):
    return f"Error: '{p}' does not exist."
  elif not safe_path_depth(p):
    return f"Error: '{p}' is too near the root directory: /"
  return ""

# Copy src -> dst
def copy_path(src : str | Path, dst : str | Path) -> None:
  if not safe_path_depth(src):
    print(f"Error: '{src}' is too near the root directory: /")
    return None
  elif not safe_path_depth(dst):
    print(f"Error: '{dst}' is too near the root directory: /")
    return None

  src = Path(src)
  dst = Path(dst)

  if not dst.exists():
    print(f"Error: The following destination does not exist: {dst}")
    return None
  elif not dst.is_dir():
    print(f"Error: The following destination must be a directory: {dst}")
    return None
  elif commonpath([abspath(src), abspath(dst)]) == abspath(src):
    print("Error: The source is inside the destination which causes infinite recursion.")
    return None

  if src.is_file():
      dst_file = dst / src.name
      shutil.copy2(src, dst_file)
      print(f"Copied file: {src} -> {dst_file}")
  elif src.is_dir():
      dst_dir = dst / src.name
      shutil.copytree(src, dst_dir, dirs_exist_ok=True)
      print(f"Copied directory: {src} -> {dst_dir}")
  else:
      print(f"Error: '{src}' is not a valid file or directory")

class TitleBar(QtWidgets.QWidget):
  def __init__(self, parent=None):
    super().__init__(parent)
    self._parent    = parent
    self._mouse_pos = None

    self.setFixedHeight(36)
    self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)

    ### Layout ###
    layout = QtWidgets.QHBoxLayout(self)
    layout.setContentsMargins(10, 6, 10, 6)
    layout.setSpacing(8)

    ### Traffic light buttons ###
    self.min_btn   = self._create_circle_button("#febc2e", "-")
    self.max_btn   = self._create_circle_button("#28c840", "⛶")
    self.close_btn = self._create_circle_button("#ff5f57", "✕")

    layout.addStretch() # Push every subsequent widget to the right.
    layout.addWidget(self.min_btn)
    layout.addWidget(self.max_btn)
    layout.addWidget(self.close_btn)

    self.min_btn.clicked.connect(self._on_minimize)
    self.max_btn.clicked.connect(self._on_maximize)
    self.close_btn.clicked.connect(self._on_close)

  def _create_circle_button(self, color : str, symbol : str) -> QtWidgets.QPushButton:
    btn = QtWidgets.QPushButton(symbol)
    btn.setFixedSize(17, 17)
    btn.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
    btn.setFlat(True)
    btn.setStyleSheet(
      f"""
        QPushButton {{
          border-radius:    8px;
          background-color: {color};
          border:           0px;
          font-size:        14px;
          text-align:       center;
        }}
        QPushButton:hover {{
          background-color: #33495e; /* Lighter "brightness" effect */
        }}
        QPushButton:pressed {{
          background-color: #1e2b37;
        }}
      """
    )
    return btn

  def _on_close(self) -> None:
    if self._parent:
      self._parent.close()

  def _on_minimize(self) -> None:
    if self._parent:
      self._parent.showMinimized()

  def _on_maximize(self) -> None:
    if self._parent:
      if self._parent.isMaximized():
        self._parent.showNormal()
      else:
        self._parent.showMaximized()

  # Allow dragging the window by the title bar
  def mousePressEvent(self, event : QtGui.QMouseEvent) -> None:
    if event.button() == QtCore.Qt.MouseButton.LeftButton:
      self._mouse_pos = event.globalPosition().toPoint() - self._parent.frameGeometry().topLeft()
      event.accept()

  def mouseMoveEvent(self, event : QtGui.QMouseEvent) -> None:
    if self._mouse_pos is not None and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
      self._parent.move(event.globalPosition().toPoint() - self._mouse_pos)
      event.accept()

  def mouseReleaseEvent(self, event : QtGui.QMouseEvent) -> None:
    self._mouse_pos = None
    super().mouseReleaseEvent(event)

class Dialog(QtWidgets.QDialog):
  def __init__(self, parent):
    super().__init__(parent)
    self.setWindowTitle(parent.windowTitle())
    self.resize(350, 150)

    self.setWindowFlags(parent.windowFlags())
    self.setWindowIcon(parent.windowIcon())
    self.setStyleSheet(parent.styleSheet())
    self.setPalette(parent.palette())
    self.setFont(parent.font())

    self.setStyleSheet(
      f"""
        QDialog {{
          background-color: {PRIMARY_BG};
        }}
      """
    )

    layout = QtWidgets.QVBoxLayout(self)
    layout.setContentsMargins(20, 20, 20, 20)

    self.game_path = sanitize(parent.text_fieldLHS.text())
    self.mod_path  = sanitize(parent.text_fieldRHS.text())

    ### Message ###
    check_game_path = check_path(self.game_path)
    check_mod_path  = check_path(self.mod_path)
    if len(check_game_path) > 0:
      label = QtWidgets.QLabel(check_game_path)
    elif len(check_mod_path) > 0:
      label = QtWidgets.QLabel(check_mod_path)
    elif self.game_path == self.mod_path:
      label = QtWidgets.QLabel("Cannot install the game folder to the game folder.")
    elif not os.path.isdir(self.game_path):
      label = QtWidgets.QLabel("The game path must be a folder.")
    elif commonpath([abspath(self.mod_path), abspath(self.game_path)]) == abspath(self.mod_path):
      label = QtWidgets.QLabel("Cannot recursively install a parent folder inside its child folder.")
    else:
      self.resize(350, 250)
      label = QtWidgets.QLabel(f"Do you wish to install: {self.mod_path}\ninside:\n{self.game_path}?")
    label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
    label.adjustSize()
    label.setWordWrap(True)
    layout.addWidget(label)

    ### Buttons ###
    btn_layout        = QtWidgets.QHBoxLayout()
    self.ok_btn       = QtWidgets.QPushButton("Ok")
    self.continue_btn = QtWidgets.QPushButton("Continue")
    self.cancel_btn   = QtWidgets.QPushButton("Cancel")
    self.cancel_btn.setDefault(True)
    self.ok_btn.setDefault(True)

    ### Button stylesheets ###
    self.cancel_btn.setStyleSheet(
      f"""
        QPushButton {{
          background-color: {PRIMARY_BG};
        }}
        QPushButton:hover {{
          background-color: #d32f2f;
        }}
      """
    )

    self.continue_btn.setStyleSheet(
      f"""
        QPushButton {{
          background-color: {ACCENT_BLUE};
        }}
        QPushButton:hover {{
          background-color: #0b75e5;
        }}
      """
    )

    self.ok_btn.setStyleSheet(self.continue_btn.styleSheet())

    ### Button(s) to render ###
    if len(check_game_path) > 0 or len(check_mod_path) > 0 \
       or self.game_path == self.mod_path or not os.path.isdir(self.game_path) \
       or os.path.commonpath([abspath(self.mod_path), \
                              abspath(self.game_path)]) == abspath(self.mod_path):
      btn_layout.addWidget(self.ok_btn)
    else:
      btn_layout.addWidget(self.continue_btn)
      btn_layout.addWidget(self.cancel_btn)
    layout.addLayout(btn_layout)

    self.ok_btn.clicked.connect(self.reject)
    self.continue_btn.clicked.connect(self._on_accept)
    self.cancel_btn.clicked.connect(self.reject)

    # Make modal like QMessageBox.
    self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)

  # Execute inside the dialog box to block UI interaction and freeze buttons
  # during installation.
  def _on_accept(self) -> None:
    print("[*] Continue.")
    game_path = self.game_path
    mod_path  = self.mod_path
    print(f"Game path sanitized:\n{game_path}\nMod path sanitized:\n{mod_path}")
    if game_path == mod_path:
      print("Error: The game path must differ from the mod path.")
    else:
      print(f"Installing:\n{mod_path}\ninside:\n{game_path}")
      copy_path(mod_path, game_path) # Handles path safety.
    self.accept()

class MainWindow(QtWidgets.QWidget):
  def __init__(self):
    super().__init__()
    self.setWindowTitle("Mod installer UI")
    self.setWindowFlags(
      QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Window
    )
    self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

    ### Outer layout to achieve rounded corners. ###
    outer_layout = QtWidgets.QVBoxLayout(self)
    outer_layout.setContentsMargins(0, 0, 0, 0)

    self.container = QtWidgets.QFrame()
    self.container.setObjectName("Container")
    self.container.setStyleSheet(
      f"""
        QFrame#Container {{
          background-color: {PRIMARY_BG};
          border-radius:    {WINDOW_RADIUS}px;
        }}
      """
    )

    container_layout = QtWidgets.QVBoxLayout(self.container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.setSpacing(0)

    ### Title bar ###
    self.title_bar = TitleBar(self)
    container_layout.addWidget(self.title_bar)

    content = QtWidgets.QWidget()

    content_layout = QtWidgets.QVBoxLayout(content)
    content_layout.setContentsMargins(24, 16, 24, 24)
    content_layout.setSpacing(16)

    title_label = QtWidgets.QLabel("Mod installer")
    title_label.setObjectName("TitleLabel")

    ### Toggle buttons ###
    #self.btn1 = QtWidgets.QPushButton("Option A")
    #self.btn2 = QtWidgets.QPushButton("Option B")
    #self.btn1.setCheckable(True)
    #self.btn2.setCheckable(True)
    #self.btn1.setObjectName("Toggle")
    #self.btn2.setObjectName("Toggle")

    # Group them so only one can be checked
    #group = QtWidgets.QButtonGroup(content)
    #group.setExclusive(True)
    #group.addButton(self.btn1)
    #group.addButton(self.btn2)

    #self.btn1.setChecked(True) # default

    subtitle_label = QtWidgets.QLabel("Install a mod into a compatible game:")
    subtitle_label.setWordWrap(True)
    subtitle_label.setObjectName("SubtitleLabel")

    sublabel2 = QtWidgets.QLabel("Game files and installed mods:")
    sublabel2.setWordWrap(True)
    sublabel2.setObjectName("SubtitleLabel")

    self.list_widget = QtWidgets.QListWidget()
    self.list_widget.setVerticalScrollMode(QtWidgets.QListWidget.ScrollMode.ScrollPerPixel)

    self._style_list()

    uninstall_label = QtWidgets.QLabel("We deliberately do not support "
      "uninstalling mods. You will have to manually delete them from the game's folder.")
    uninstall_label.setWordWrap(True)
    uninstall_label.setObjectName("SubtitleLabel")

    input_row = QtWidgets.QHBoxLayout()
    input_row.setSpacing(12)

    self.text_fieldLHS = QtWidgets.QLineEdit()
    self.text_fieldLHS.setPlaceholderText("Full path to the games folder.")
    self.text_fieldLHS.setObjectName("InputLine")

    self.text_fieldRHS = QtWidgets.QLineEdit()
    self.text_fieldRHS.setPlaceholderText("Full path to the mods folder.")
    self.text_fieldRHS.setObjectName("InputLine")

    ### Delay checking the content of the full path to the games folder. ###
    self.check_timer = QtCore.QTimer(self)
    self.check_timer.setSingleShot(True)
    self.check_timer.setInterval(1500) # 1.5 seconds.
    self.check_timer.timeout.connect(self.load_game_content)

    ### Restart the timer on every change. ###
    self.text_fieldLHS.textChanged.connect(self.on_text_changed)

    self.install_btn = QtWidgets.QPushButton("Install mod")
    self.install_btn.setObjectName("InstallButton")

    self.install_btn.clicked.connect(self.show_dialog)

    ### Render widgets ###
    input_row.addWidget(self.text_fieldLHS)
    input_row.addWidget(self.text_fieldRHS)
    input_row.addWidget(self.install_btn)

    content_layout.addWidget(title_label)
    #content_layout.addWidget(self.btn1)
    #content_layout.addWidget(self.btn2)
    content_layout.addWidget(subtitle_label)
    content_layout.addLayout(input_row)
    content_layout.addWidget(sublabel2)
    content_layout.addWidget(self.list_widget)
    content_layout.addWidget(uninstall_label)
    content_layout.addStretch()

    container_layout.addWidget(content)
    outer_layout.addWidget(self.container)

    self._apply_global_style()
    self.resize(900, 600)

  def show_dialog(self) -> None:
    dialog = Dialog(self)
    result = dialog.exec()
    if result == QtWidgets.QDialog.DialogCode.Accepted:
      self.on_continue()
    else:
      self.on_cancel()

  def _style_list(self) -> None:
    self.list_widget.setSelectionMode(self.list_widget.SelectionMode.SingleSelection)
    self.list_widget.setAlternatingRowColors(False)
    self.list_widget.setSpacing(3)

    self.list_widget.setStyleSheet("""
      QListWidget {
        background-color: #F5F5F7;
        border:           none;
        padding:          8px 0;
        font-size:        14px;
      }
      QListWidget::item {
        padding:       8px 16px;
        margin:        2px 12px;
        border-radius: 10px;
        color:         #1C1C1E;
      }
      QListWidget::item:selected {
        background-color: #D0E3FF;
        color:            #0A84FF;
      }
      QListWidget::item:hover:!selected {
        background-color: #E5E5EA;
      }
      QScrollBar:vertical {
        background:    transparent;
        width:         8px;
        margin:        4px 2px 4px 0;
        border-radius: 4px;
      }
      QScrollBar::handle:vertical {
        background:    rgba(0,0,0,0.25);
        border-radius: 4px;
        min-height:    24px;
      }
      QScrollBar::add-line:vertical,
      QScrollBar::sub-line:vertical {
        height: 0;
      }
      QScrollBar::add-page:vertical,
      QScrollBar::sub-page:vertical {
        background: none;
      }
    """)

  def _apply_global_style(self) -> None:
    self.setStyleSheet(
      f"""
        QWidget {{
          font-family:      -apple-system, system-ui, "SF Pro Text", "Segoe UI", sans-serif;
          color:            {PRIMARY_FG};
          background-color: transparent;
        }}

        QMenu {{
          background-color: {PRIMARY_BG};      /* menu background */
          color:            {PRIMARY_FG};      /* text color */
          border:           1px solid #222222;
        }}
        QMenu::item:selected {{
          background-color: {ACCENT_BLUE}; /* hover/selected item */
        }}

        /* Labels */

        QLabel#TitleLabel {{
          font-size:   20px;
          font-weight: 600;
        }}

        QLabel#SubtitleLabel {{
          font-size: 14px;
          color:     #3a3a3c;
        }}

        /* Input line */

        QLineEdit#InputLine {{
          background-color:           #ffffff;
          border-radius:              8px;
          border:                     1px solid #d2d2d7;
          padding:                    6px 10px;
          selection-background-color: {ACCENT_BLUE};
          selection-color:            #ffffff;
        }}

        QLineEdit#InputLine:focus {{
          border:  1px solid {ACCENT_BLUE};
          outline: none;
        }}

        /* Buttons */

        QPushButton#InstallButton {{
          background-color: {ACCENT_BLUE};
          border-radius:    8px;
          border:           none;
          color:            #ffffff;
          padding:          6px 18px;
          font-size:        13px;
          font-weight:      500;
        }}

        QPushButton#InstallButton:hover {{
          background-color: #0b75e5;
        }}

        QPushButton#InstallButton:pressed {{
          background-color: #0859b5;
        }}

        /* Toggles */

        QPushButton#Toggle {{
          border: 1px solid #d1d1d6;
          background-color: #f2f2f7;
          color:            #1c1c1e;
          border-radius:    16px;
          padding:          4px 12px;
        }}

        QPushButton#Toggle:checked {{
          background-color: {ACCENT_BLUE};
          color:            white;
        }}

        QPushButton#Toggle:pressed {{
          background-color: #0060c7;
        }}
        """
      )

  def on_text_changed(self) -> None:
    # Wait N seconds (setInterval()) after the last change.
    self.check_timer.start()

  def load_game_content(self) -> None:
    game_path_content = []
    game_path         = sanitize(self.text_fieldLHS.text())
    self.list_widget.clear()
    if os.path.exists(game_path) and os.path.isdir(game_path) \
       and safe_path_depth(game_path):
      game_path_content = os.listdir(game_path)
      game_path_content.sort(key=str.lower)
    self.list_widget.addItems(game_path_content)
    #self.list_widget.addItem(filenames)

  ### After dialog closure ###
  def on_continue(self) -> None:
    print("[*] Continue: done.")

  def on_cancel(self) -> None:
    print("[*] Cancel: done.")

  # Allow resizing with a small margin.
  def resizeEvent(self, event : QtGui.QResizeEvent) -> None:
    super().resizeEvent(event)

  def keyPressEvent(self, event : QtGui.QKeyEvent) -> None:
    if event.key() in (QtCore.Qt.Key.Key_Escape, ): # ESC
      self.close()
    elif event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier \
         and event.key() == QtCore.Qt.Key.Key_Q: # Ctrl+Q
      self.close()
    else:
      super().keyPressEvent(event)

def main():
  app    = QtWidgets.QApplication(sys.argv)
  window = MainWindow()
  window.show()
  sys.exit(app.exec())

if __name__ == "__main__":
  main()
