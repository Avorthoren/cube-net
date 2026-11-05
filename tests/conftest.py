import os

# Run Qt headless in tests (no window appears), unless explicitly overridden.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
