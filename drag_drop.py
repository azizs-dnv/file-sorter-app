"""
Drag & Drop функциональность для Windows
"""
import os
import ctypes
from ctypes import wintypes


class DragDropHelper:
    """Класс для реализации Drag & Drop функциональности на Windows"""
    
    def __init__(self, widget, callback):
        """
        Args:
            widget: tkinter виджет для приёма файлов
            callback: функция обратного вызова при проводке файла
        """
        self.widget = widget
        self.callback = callback
        self._setup()

    def _setup(self):
        """Регистрируем окно для приёма файлов и подменяем оконную процедуру"""
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.shell32 = ctypes.WinDLL("shell32", use_last_error=True)

        self.user32.GetParent.argtypes = [wintypes.HWND]
        self.user32.GetParent.restype = wintypes.HWND
        self.shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
        self.shell32.DragAcceptFiles.restype = None
        self.shell32.DragQueryFileW.argtypes = [
            wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT
        ]
        self.shell32.DragQueryFileW.restype = wintypes.UINT
        self.shell32.DragFinish.argtypes = [wintypes.HANDLE]

        if ctypes.sizeof(ctypes.c_void_p) == 8:
            get_window_long = self.user32.GetWindowLongPtrW
            set_window_long = self.user32.SetWindowLongPtrW
        else:
            get_window_long = self.user32.GetWindowLongW
            set_window_long = self.user32.SetWindowLongW

        get_window_long.argtypes = [wintypes.HWND, ctypes.c_int]
        get_window_long.restype = ctypes.c_void_p
        set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        set_window_long.restype = ctypes.c_void_p
        self.user32.CallWindowProcW.argtypes = [
            ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
            wintypes.WPARAM, wintypes.LPARAM
        ]
        self.user32.CallWindowProcW.restype = ctypes.c_ssize_t

        self.hwnd = self.user32.GetParent(self.widget.winfo_id())
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

        self.shell32.DragAcceptFiles(self.hwnd, True)

        self.old_wndproc = get_window_long(self.hwnd, -4)
        if not self.old_wndproc:
            raise ctypes.WinError(ctypes.get_last_error())

        prototype = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        self.new_wndproc = prototype(self._wndproc)
        ctypes.set_last_error(0)
        previous_wndproc = set_window_long(
            self.hwnd, -4, ctypes.cast(self.new_wndproc, ctypes.c_void_p)
        )
        if not previous_wndproc and ctypes.get_last_error():
            raise ctypes.WinError(ctypes.get_last_error())

    def _wndproc(self, hwnd, msg, wparam, lparam):
        """Обработчик оконных событий"""
        WM_DROPFILES = 0x0233
        if msg == WM_DROPFILES:
            hdrop = wparam
            # Получаем количество файлов
            file_count = self.shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
            for i in range(file_count):
                buf = ctypes.create_unicode_buffer(260)
                self.shell32.DragQueryFileW(hdrop, i, buf, 260)
                path = buf.value
                # Обрабатываем только папки
                if os.path.isdir(path):
                    self.widget.after(10, lambda p=path: self.callback(p))
                    break
            self.shell32.DragFinish(hdrop)
            return 0
        return self.user32.CallWindowProcW(self.old_wndproc, hwnd, msg, wparam, lparam)
