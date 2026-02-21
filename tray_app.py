"""
LeetCode Helper - System Tray Application
A lightweight system tray app that runs the LeetCode Helper server.
"""
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

import pystray
from PIL import Image, ImageDraw


class LeetCodeTrayApp:
    def __init__(self):
        self.server_process = None
        self.icon = None
        self.base_dir = Path(__file__).parent

    def create_icon_image(self):
        """Create a simple icon for the system tray."""
        # Create a 64x64 image with a gradient background
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='white')
        dc = ImageDraw.Draw(image)
        
        # Draw a rounded rectangle with gradient-like effect
        dc.rounded_rectangle([4, 4, width-5, height-5], radius=12, fill='#0066cc')
        
        # Draw "LC" text
        dc.text((14, 18), "LC", fill='white', font=None)
        
        return image

    def start_server(self):
        """Start the LeetCode Helper server."""
        if self.server_process is not None:
            return
        
        server_script = self.base_dir / "server.py"
        
        def run_server():
            self.server_process = subprocess.Popen(
                [sys.executable, str(server_script)],
                cwd=str(self.base_dir),
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            self.server_process.wait()
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

    def stop_server(self):
        """Stop the LeetCode Helper server."""
        if self.server_process is not None:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None

    def open_browser(self):
        """Open the LeetCode Helper in browser."""
        webbrowser.open('http://localhost:8888')

    def quit_app(self, icon=None):
        """Quit the application."""
        self.stop_server()
        if self.icon:
            self.icon.stop()

    def create_menu(self):
        """Create the system tray menu."""
        return pystray.Menu(
            pystray.MenuItem("Open in Browser", self.open_browser, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start Server", lambda: self.start_server()),
            pystray.MenuItem("Stop Server", lambda: self.stop_server()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.quit_app),
        )

    def run(self):
        """Run the system tray application."""
        # Create icon
        image = self.create_icon_image()
        menu = self.create_menu()
        
        self.icon = pystray.Icon(
            "leetcode_helper",
            image,
            "LeetCode Helper",
            menu
        )
        
        # Start server automatically
        self.start_server()
        
        # Run the tray icon
        self.icon.run()


def main():
    app = LeetCodeTrayApp()
    app.run()


if __name__ == "__main__":
    main()
