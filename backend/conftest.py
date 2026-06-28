"""Make the backend dir importable as the `app` package root during tests."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
