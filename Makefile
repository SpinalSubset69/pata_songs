# Define the virtual environment directory
VENV_DIR := venv

# Define the Python executable and commands based on the operating system
ifeq ($(OS), Windows_NT)
	PYTHON := $(VENV_DIR)\Scripts\python.exe
	CLEAN_CMD := rd /s /q $(VENV_DIR)
	ACTIVATE_CMD := $(VENV_DIR)\Scripts\activate.bat
else
	PYTHON := $(VENV_DIR)/bin/python
	CLEAN_CMD := rm -rdf $(VENV_DIR)
	ACTIVATE_CMD := bash -c "source $(VENV_DIR)/bin/activate"
endif

# Create the virtual environment and install dependencies
install:
	$(ACTIVATE_CMD)
	$(PYTHON) -m pip install --progress-bar on -r requirements.txt

# Clean up the virtual environment
clean:
	$(CLEAN_CMD)

# Create the virtual environment
create:
	python -m venv $(VENV_DIR)
	$(ACTIVATE_CMD)
	$(PYTHON) -m pip install --upgrade pip

# Run app.py using the virtual environment
run:
	$(ACTIVATE_CMD)
	$(PYTHON) ./src/pata_song_bot.py

freeze:
	$(ACTIVATE_CMD)
	$(PYTHON) -m pip freeze -l > requirements.txt

test:
ifeq ($(OS), Windows_NT)
	set PYTHONPATH=src && $(PYTHON) -m pytest -v
else
	PYTHONPATH=src $(PYTHON) -m pytest -v
endif