#!/bin/bash

# Script to set up virtual environment and run the Flask app

# Check if python3 is available
if ! command -v python3 &> /dev/null
then
    echo "Error: python3 command could not be found. Please install Python 3."
    exit 1
fi

# Check if pip3 is available
if ! command -v pip3 &> /dev/null
then
    # Try using python3 -m pip
     if ! python3 -m pip --version &> /dev/null
     then
        echo "Error: pip3 command not found, and 'python3 -m pip' failed. Please ensure pip is installed for Python 3."
        exit 1
    fi
    PIP_COMMAND="python3 -m pip"
else
    PIP_COMMAND="pip3"
fi


VENV_DIR="venv"

# Check if virtual environment directory exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in '$VENV_DIR'..."
    python3 -m venv $VENV_DIR
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment."
        exit 1
    fi
else
    echo "Virtual environment '$VENV_DIR' already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source $VENV_DIR/bin/activate
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate virtual environment."
    exit 1
fi


# Install dependencies
echo "Installing dependencies from requirements.txt..."
$PIP_COMMAND install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies."
    # Consider deactivating venv here if needed
    # deactivate
    exit 1
fi

# Check if app.py exists
if [ ! -f "app.py" ]; then
     echo "Error: app.py not found in the current directory."
     # deactivate
     exit 1
fi

# Run the Flask application
echo "Starting Flask development server..."
# echo "Access the application at http://127.0.0.1:5000"
echo "Access the application at http://127.0.0.1:5010"
# Use flask run which respects FLASK_APP and FLASK_ENV environment variables
# Set FLASK_APP environment variable for clarity
export FLASK_APP=app.py
# Optional: Set Flask environment to development (enables debugger, autoreload)
export FLASK_ENV=development

flask run --port 5010

# Deactivate virtual environment upon exit (optional, typically done manually)
# echo "Deactivating virtual environment..."
# deactivate 