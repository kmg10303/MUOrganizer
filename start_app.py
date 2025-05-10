import os, sys, webbrowser

# Ensure script works regardless of launch location
base_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(base_dir)

# Add project path to Python path
sys.path.insert(0, base_dir)

# Set Django settings module explicitly
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "audio_app.settings")

# Launch server
os.system("python manage.py runserver")
webbrowser.open("http://127.0.0.1:8000")
