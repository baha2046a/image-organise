import os
import shutil
from flask import Flask, render_template, request, jsonify, send_from_directory
from pathlib import Path
import base64
from PIL import Image
from io import BytesIO
import logging
import platform # For OS detection
import subprocess # To open files

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 # Limit uploads if needed

# Configure logging
logging.basicConfig(level=logging.INFO)

# In-memory cache for thumbnails (consider a more robust cache for large directories)
thumbnail_cache = {}
MAX_THUMBNAIL_SIZE = (150, 150)
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

def is_image_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def create_thumbnail(image_path):
    try:
        img = Image.open(image_path)
        img.thumbnail(MAX_THUMBNAIL_SIZE)
        buffered = BytesIO()
        # Handle transparency for PNG/GIF
        if img.mode in ("RGBA", "P"):
             img.save(buffered, format="PNG")
        else:
             img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return f"data:image/{'png' if img.mode in ('RGBA', 'P') else 'jpeg'};base64,{img_str}"
    except Exception as e:
        app.logger.error(f"Error creating thumbnail for {image_path}: {e}")
        return None # Return None or a placeholder image data URL

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/list_images', methods=['POST'])
def list_images():
    data = request.get_json()
    directory = data.get('directory')
    sort_by = data.get('sortBy', 'name') # Default to sorting by name

    if not directory or not os.path.isdir(directory):
        return jsonify({'error': 'Invalid or inaccessible directory specified.'}), 400

    images = []
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path) and is_image_file(filename):
                # Use absolute path for cache key and operations
                abs_file_path = os.path.abspath(file_path)
                thumbnail_data = thumbnail_cache.get(abs_file_path)
                if not thumbnail_data:
                    thumbnail_data = create_thumbnail(abs_file_path)
                    if thumbnail_data:
                         # Cache only if successfully created
                         thumbnail_cache[abs_file_path] = thumbnail_data

                if thumbnail_data: # Only add if thumbnail could be created
                    try:
                        mtime = os.path.getmtime(abs_file_path)
                    except OSError:
                        mtime = 0 # Assign a default time if error
                    images.append({
                        'filename': filename,
                        'path': abs_file_path, # Send absolute path to client
                        'thumbnail': thumbnail_data,
                        'mtime': mtime # Add modification time
                    })
    except OSError as e:
        app.logger.error(f"Error listing directory {directory}: {e}")
        return jsonify({'error': f'Error accessing directory: {e.strerror}'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error listing images in {directory}: {e}")
        return jsonify({'error': 'An unexpected error occurred.'}), 500

    # Sort the images list
    try:
        if sort_by == 'mtime':
            # Sort by modification time, newest first
            images.sort(key=lambda x: x.get('mtime', 0), reverse=True)
        else: # Default to sorting by filename (case-insensitive)
            images.sort(key=lambda x: x.get('filename', '').lower())
    except Exception as e:
         app.logger.error(f"Error sorting images: {e}")
         # Proceed with unsorted list or default sort if error occurs
         if sort_by != 'name': # Attempt filename sort if mtime sort failed
            try:
                images.sort(key=lambda x: x.get('filename', '').lower())
            except Exception as sort_err:
                 app.logger.error(f"Fallback filename sort failed: {sort_err}")

    return jsonify({'images': images})

@app.route('/rename_images', methods=['POST'])
def rename_images():
    data = request.get_json()
    files_to_rename = data.get('files', [])
    new_base_name = data.get('newName', '').strip()
    target_directory = data.get('directory') # The directory where renaming happens

    if not files_to_rename or not new_base_name or not target_directory or not os.path.isdir(target_directory):
        return jsonify({'error': 'Missing required data: files, newName, or valid directory.'}), 400

    # Ensure we only work with files originally listed from this directory
    # Validate paths received from the client
    valid_files = []
    for file_info in files_to_rename:
        file_path = file_info.get('path')
        if not file_path or not os.path.exists(file_path):
            app.logger.warning(f"Rename request for non-existent file: {file_path}")
            continue # Skip non-existent files

        # Security check: Ensure the file is actually within the target directory
        abs_file_path = os.path.abspath(file_path)
        abs_target_dir = os.path.abspath(target_directory)
        if not abs_file_path.startswith(abs_target_dir):
             app.logger.warning(f"Attempt to rename file outside target directory: {abs_file_path}")
             continue # Skip files outside the target directory
        valid_files.append(abs_file_path)

    if not valid_files:
        return jsonify({'error': 'No valid files found to rename.'}), 400


    renamed_files = {}
    errors = []
    processed_count = 0

    # Sort files to ensure consistent renaming order (optional but good practice)
    valid_files.sort()

    for i, old_path in enumerate(valid_files):
        try:
            # Find the next available number
            counter = 1
            while True:
                new_filename = f"{new_base_name}{counter:03d}{Path(old_path).suffix}"
                new_path = os.path.join(target_directory, new_filename)
                if not os.path.exists(new_path) and new_path not in renamed_files.values():
                    break
                counter += 1
                if counter > 9999: # Safety break
                     raise OverflowError("Could not find an available filename sequence number.")

            # Remove old path from thumbnail cache
            if old_path in thumbnail_cache:
                del thumbnail_cache[old_path]

            shutil.move(old_path, new_path)
            app.logger.info(f"Renamed '{old_path}' to '{new_path}'")
            renamed_files[old_path] = new_path # Track original -> new mapping
            processed_count += 1

            # Optional: Add new path to cache if needed immediately
            # thumbnail_data = create_thumbnail(new_path)
            # if thumbnail_data:
            #    thumbnail_cache[new_path] = thumbnail_data

        except OSError as e:
            error_msg = f"Error renaming {os.path.basename(old_path)}: {e.strerror}"
            app.logger.error(error_msg)
            errors.append(error_msg)
        except OverflowError as e:
            error_msg = f"Error renaming {os.path.basename(old_path)}: {e}"
            app.logger.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error renaming {os.path.basename(old_path)}: {e}"
            app.logger.error(error_msg)
            errors.append(error_msg)

    if errors:
        return jsonify({'message': f'{processed_count} files renamed, but some errors occurred.', 'errors': errors, 'renamed': renamed_files}), 500
    else:
        return jsonify({'message': f'Successfully renamed {processed_count} files.', 'renamed': renamed_files}), 200


@app.route('/move_images', methods=['POST'])
def move_images():
    data = request.get_json()
    files_to_move = data.get('files', [])
    destination_directory = data.get('destination')
    source_directory = data.get('sourceDirectory') # The directory the files are currently in

    if not files_to_move or not destination_directory or not source_directory:
        return jsonify({'error': 'Missing required data: files, destination, or sourceDirectory.'}), 400

    if not os.path.isdir(destination_directory):
        # Optionally create the destination directory if it doesn't exist
        try:
            os.makedirs(destination_directory)
            app.logger.info(f"Created destination directory: {destination_directory}")
        except OSError as e:
            app.logger.error(f"Error creating destination directory {destination_directory}: {e}")
            return jsonify({'error': f'Invalid or inaccessible destination directory: {e.strerror}'}), 400
    elif not os.path.isdir(source_directory):
         return jsonify({'error': 'Invalid source directory.'}), 400


    moved_files = {}
    errors = []
    processed_count = 0

    # Validate paths received from the client
    abs_source_dir = os.path.abspath(source_directory)
    abs_dest_dir = os.path.abspath(destination_directory)

    if abs_source_dir == abs_dest_dir:
        return jsonify({'error': 'Source and destination directories cannot be the same.'}), 400

    for file_info in files_to_move:
        original_path = file_info.get('path')
        if not original_path or not os.path.exists(original_path):
            app.logger.warning(f"Move request for non-existent file: {original_path}")
            continue # Skip non-existent files

        abs_original_path = os.path.abspath(original_path)

        # Security check: Ensure the file is actually within the source directory
        if not abs_original_path.startswith(abs_source_dir):
             app.logger.warning(f"Attempt to move file outside source directory: {abs_original_path}")
             continue # Skip files outside the source directory

        filename = os.path.basename(abs_original_path)
        destination_path = os.path.join(abs_dest_dir, filename)

        try:
             # Prevent overwriting existing files in the destination
            if os.path.exists(destination_path):
                 raise FileExistsError(f"File '{filename}' already exists in the destination directory.")

            # Remove old path from thumbnail cache
            if abs_original_path in thumbnail_cache:
                del thumbnail_cache[abs_original_path]

            shutil.move(abs_original_path, destination_path)
            app.logger.info(f"Moved '{abs_original_path}' to '{destination_path}'")
            moved_files[original_path] = destination_path # Track original -> new mapping
            processed_count += 1

            # Optional: Add new path to cache if needed immediately
            # thumbnail_data = create_thumbnail(destination_path)
            # if thumbnail_data:
            #    thumbnail_cache[destination_path] = destination_path

        except (OSError, FileExistsError) as e:
            error_msg = f"Error moving {filename}: {e}"
            app.logger.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error moving {filename}: {e}"
            app.logger.error(error_msg)
            errors.append(error_msg)

    if errors:
        return jsonify({'message': f'{processed_count} files moved, but some errors occurred.', 'errors': errors, 'moved': moved_files}), 500
    else:
        return jsonify({'message': f'Successfully moved {processed_count} files.', 'moved': moved_files}), 200

@app.route('/list_directories', methods=['POST'])
def list_directories():
    data = request.get_json()
    directory = data.get('directory')

    if not directory or not os.path.isdir(directory):
        return jsonify({'error': 'Invalid or inaccessible directory specified.'}), 400

    destinations = []
    abs_directory = os.path.abspath(directory)

    # 1. Add Parent Directory
    parent_dir = os.path.dirname(abs_directory)
    # Add parent only if it's different from current and not the root's parent
    if parent_dir != abs_directory and os.path.exists(parent_dir):
         # Check if we have read access to parent (optional but good practice)
         try:
            os.listdir(parent_dir) # Try listing parent content
            destinations.append({'name': f'../ (Parent Directory)', 'path': parent_dir})
         except OSError:
            app.logger.warning(f"Cannot access parent directory: {parent_dir}")

    # 2. Add Subdirectories
    try:
        for item in os.listdir(abs_directory):
            item_path = os.path.join(abs_directory, item)
            if os.path.isdir(item_path):
                 # Check if we have read access to subdirectory
                try:
                    os.listdir(item_path)
                    destinations.append({'name': f'{item}/', 'path': item_path})
                except OSError:
                    app.logger.warning(f"Cannot access subdirectory: {item_path}")

        # Sort destinations alphabetically by name for consistency
        destinations.sort(key=lambda x: x['name'].lower())

    except OSError as e:
        app.logger.error(f"Error listing subdirectories for {abs_directory}: {e}")
        # Don't fail completely, maybe parent was added
        # return jsonify({'error': f'Error accessing subdirectories: {e.strerror}'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error listing directories for {abs_directory}: {e}")
        # return jsonify({'error': 'An unexpected error occurred while listing directories.'}), 500

    return jsonify({'destinations': destinations})

@app.route('/open_image', methods=['POST'])
def open_image():
    data = request.get_json()
    file_path = data.get('path')

    if not file_path:
        return jsonify({'error': 'Missing file path.'}), 400

    # Security: Basic validation - check if path exists and is a file
    abs_file_path = os.path.abspath(file_path)
    if not os.path.exists(abs_file_path):
         app.logger.error(f"Open request for non-existent file: {abs_file_path}")
         return jsonify({'error': 'File does not exist.'}), 404
    if not os.path.isfile(abs_file_path):
        app.logger.error(f"Open request for path that is not a file: {abs_file_path}")
        return jsonify({'error': 'Path is not a file.'}), 400
    # Add more validation if needed, e.g., check if it's within an allowed base directory

    try:
        system = platform.system()
        if system == "Windows":
            # os.startfile(abs_file_path) # Alternative, might be better on Windows
            subprocess.run(['cmd', '/c', 'start', '', abs_file_path], check=True)
        elif system == "Darwin": # macOS
            subprocess.run(['open', abs_file_path], check=True)
        else: # Linux and other Unix-like
            subprocess.run(['xdg-open', abs_file_path], check=True)
        app.logger.info(f"Attempted to open file: {abs_file_path}")
        return jsonify({'message': 'Open command issued.'}), 200
    except FileNotFoundError as e:
         # Handle cases where 'open', 'xdg-open' or 'cmd' might not be found
         app.logger.error(f"Command not found to open file ({system}): {e}")
         return jsonify({'error': f'Could not find command to open file on this system ({system}).'}), 500
    except subprocess.CalledProcessError as e:
        app.logger.error(f"Error opening file {abs_file_path} with {system} command: {e}")
        return jsonify({'error': f'System command failed to open the file.'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error opening file {abs_file_path}: {e}")
        return jsonify({'error': 'An unexpected error occurred while trying to open the file.'}), 500

# Serve static files (CSS, JS)
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    # Make sure templates and static directories exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('static/css'):
        os.makedirs('static/css')
    if not os.path.exists('static/js'): # Create js dir if needed later
        os.makedirs('static/js')

    # app.run(debug=True) # debug=True enables auto-reloading and debugger
    app.run(port=5010, debug=True) # Run on port 5010 