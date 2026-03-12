import app.main
import os
import sys

print(f"Python Executable: {sys.executable}")
print(f"Current Directory: {os.getcwd()}")
print(f"App Main File: {app.main.__file__}")
print(f"App Main Title: {getattr(app.main.app, 'title', 'N/A')}")
print(f"App Main Version: {getattr(app.main.app, 'version', 'N/A')}")
