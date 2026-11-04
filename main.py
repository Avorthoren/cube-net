import sys


def main():
    """Entry point for the Cube Net application."""
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # TODO: Create and show main window
    # from src.gui.main_window import MainWindow
    # window = MainWindow()
    # window.show()
    
    print("Cube Net application started")
    print("PyQt6 is working!")
    
    # For now, just exit immediately to verify the environment works
    return 0


if __name__ == "__main__":
    sys.exit(main())
