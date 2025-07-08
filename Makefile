# Define the virtual environment directory
VENV_DIR := venv

# Define the Python interpreter
PYTHON := $(VENV_DIR)\Scripts\python.exe

# Create the virtual environment and install dependencies
install:
	$(PYTHON) -m pip install --progress-bar on -r requirements.txt

# Clean up the virtual environment
clean:
	rd /s /q $(VENV_DIR)

# Create the virtual environment
create:
	python -m venv $(VENV_DIR)
	$(VENV_DIR)\Scripts\activate.bat
	$(PYTHON) -m pip install --upgrade pip

# Run app.py using the virtual environment
run:
	$(PYTHON) ./src/pata_song_bot.py

freeze:
	$(PYTHON) -m pip freeze -l > requirements.txt 