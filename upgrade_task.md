# Task Directive: Upgrade `generate_video.py` for Local Batch Processing

## 1. Objective

Refactor the existing `generate_video.py` script to process local files in bulk. The script must scan a specified local directory containing multiple image files and a **single** text file. It will use the content of that one text file as the prompt for **every** image in the folder, generating a video for each image sequentially using the Volcengine Ark SDK (Seedance 1.5 Pro). Crucially, the script must now automatically download the generated videos directly to the local folder.

## 2. Detailed Requirements

### 2.1. Folder Scanning and File Discovery

- Implement command-line argument parsing (e.g., using `argparse`) so the user can pass a target directory path when running the script (e.g., `python generate_video.py ./assets`).

- Scan the target directory to find **all** image files (`.jpg`, `.jpeg`, `.png`).

- Find the **single** `.txt` file in that same directory. If there are no text files or multiple text files, the script should print a clear error message and exit to prevent generating videos with the wrong prompt.

### 2.2. Local File Handling & Payload Formatting

- **Text Input**: Read the content of the single `.txt` file once at the beginning of the script. Strip any extraneous whitespace or newlines. This text will serve as the prompt payload for every image.

- **Image Input**: For each image found in the folder, read the local file and encode it into a Base64 Data URI string.

  - Format: `data:image/[mime_type];base64,[base64_string]`

  - Inject this Base64 string into the `url` field of the payload where the HTTP link used to be.

### 2.3. Task Execution and Polling Loop

- Wrap the existing API call and polling logic inside a loop that iterates through all the found image files.

- Process the images sequentially: submit a task (using the current image and the common text prompt), poll until it reaches `succeeded` or `failed`, process the result, and then move on to the next image. This prevents hitting API concurrency limits.

- Add clear console `print` statements to indicate progress (e.g., `Processing 1/15: image_01.jpg...`).

### 2.4. Output Management, Automatic Download & Error Handling

- **Extract URL**: Extract the final video download URL for successful tasks.

- **Automatic Download**: Immediately download the `.mp4` file using the extracted URL (e.g., using `urllib.request` or `requests`). Save it in the same target directory, renaming it to match the original image file (e.g., if the input is `item_01.jpg`, save the downloaded video as `item_01.mp4`).

- **Backup Record**: Append the results (Original Image Filename, Video URL) to an output text file (e.g., `results.txt`) inside the target directory as a backup record in case the temporary URL needs to be accessed again.

- **Error Handling**: Implement robust error handling (`try/except` blocks) around the API call, polling, and the file downloading process. If a specific image fails to generate or download, log the exact error to the console and safely continue to the next image without crashing the entire script.

## 3. Context & Core Code

- Retain the existing `dotenv` environment variable loading and Ark client initialization from the original `generate_video.py`.

- Ensure the target model remains `doubao-seedance-1-5-pro-251215`.

