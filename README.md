# Image Organiser

A simple web-based utility built with Flask to help organise image files by renaming and moving them.

## Features

*   Browse directories on the server where the application is running.
*   View thumbnails of images (.png, .jpg, .jpeg, .gif, .bmp, .webp).
*   Sort thumbnails by filename or modification time (newest first).
*   Select one or more images.
*   Rename selected images sequentially (e.g., `basename001.ext`, `basename002.ext`, ...).
*   Move selected images to a subdirectory or the parent directory.
*   Select all images with a similar base name (ignoring numbers/extension) with one click.
*   Double-click a thumbnail to open the image file using the system's default viewer.
*   Dark theme UI inspired by Google AI Studio.

## Prerequisites

*   Python 3 (tested with 3.8+)
*   `pip` (Python package installer)

## Setup Instructions

1.  **Clone the repository or download the files:**
    ```bash
    git clone <repository_url> # Or download and extract the ZIP
    cd image-organiser # Navigate to the project directory
    ```

2.  **Make the run script executable (Linux/macOS):**
    ```bash
    chmod +x run.sh
    ```

## Running the Application

1.  **Execute the `run.sh` script (Linux/macOS):**
    ```bash
    ./run.sh
    ```
    **On Windows:**
    You can run the steps from `run.sh` manually in your terminal (like Command Prompt or PowerShell):
    ```bash
    # 1. Create virtual environment (if it doesn't exist)
    python -m venv venv
    
    # 2. Activate virtual environment
    .\venv\Scripts\activate
    
    # 3. Install dependencies
    pip install -r requirements.txt
    
    # 4. Set Flask environment variables (optional, for development)
    set FLASK_APP=app.py
    set FLASK_ENV=development
    
    # 5. Run the Flask app on the specified port
    flask run --port 5010
    ```

2.  The script will:
    *   Create a Python virtual environment (`venv` directory) if it doesn't exist.
    *   Activate the virtual environment.
    *   Install the required Python packages (`Flask`, `Pillow`) listed in `requirements.txt`.
    *   Start the Flask development server.

3.  **Access the application:**
    Open your web browser and navigate to:
    [http://127.0.0.1:5010](http://127.0.0.1:5010)

## How to Use

1.  **Enter Directory Path:** Type the full path to the directory containing the images you want to organise into the "Directory Path" input field.
2.  **Load Images:** Press Enter or click the refresh icon (🔄) button.
3.  **Browse Folders:** Use the "Browse" dropdown (below the path input) to navigate to parent or subdirectories. Selecting a folder loads its images.
4.  **Sort:** Select the desired sorting order (Filename or Modification Time) from the "Sort by" dropdown.
5.  **Select Images:** Click on image thumbnails to select them. The border will change color.
6.  **Select Similar:** If you have exactly one image selected, click the magic wand icon (✨) to select all other visible images with the same base name.
7.  **Clear Selection:** Click the red 'X' icon (❌) to deselect all images.
8.  **Rename:** Select image(s), click the pencil icon (✏️), enter a new base name in the modal, and confirm.
9.  **Move:** Select image(s), click the folder icon (📁➡️), choose a destination (subfolder, parent, or enter manually) in the modal, and confirm.
10. **Open Image:** Double-click a thumbnail to open the original image file on your computer.

## Technologies Used

*   **Backend:** Python, Flask
*   **Image Processing:** Pillow (PIL Fork)
*   **Frontend:** HTML, CSS, JavaScript
*   **Icons:** Font Awesome 