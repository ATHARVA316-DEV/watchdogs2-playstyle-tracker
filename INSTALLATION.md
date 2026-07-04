# Installation & Usage Guide

## Prerequisites
1. **Python 3.x**: Ensure you have Python installed on your system.
2. **Tesseract OCR**: 
   * The `ocr_capture.py` script requires Tesseract to extract stats from the screen.
   * **Windows**: Download and install it from [UB-Mannheim/tesseract wiki](https://github.com/UB-Mannheim/tesseract/wiki).
   * Ensure it is installed in the default directory (`C:/Program Files/Tesseract-OCR/tesseract.exe`) or update the path in `ocr_capture.py`.

## 1. Installation
1. Clone or download this repository to your local machine.
2. Open a terminal / command prompt in the project folder.
3. Install the required Python packages using pip:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: This installs libraries like `keyboard`, `mouse`, `pytesseract`, `Pillow`, `rich`, etc.)*

## 2. Setting Up Data Capture
You have two methods to capture data: the Input Logger and the OCR Capture.

### A. Background Input Logger
This script sits in the background and guesses your playstyle based on your keyboard and mouse inputs (WASD, mouse clicks).
1. Run the script:
   ```bash
   python input_logger.py
   ```
2. Press **F9** to start a session when you begin playing.
3. Press **F10** to stop and save the session data when you are done.

### B. OCR Screen Capture
This script captures the actual game stats from the "Mission Complete" or "Stats" screen using optical character recognition.
1. **Calibrate (First Time Only)**:
   * Open the game to the stats screen (or open a screenshot in full screen).
   * Run: `python ocr_capture.py --calibrate`
   * Click and drag boxes over the stats (Kills, Hacks, etc.) so the script knows where to look. Press Enter to save.
2. **Capture**:
   * Run: `python ocr_capture.py`
   * The script will automatically detect the stats screen while you play and capture the data. You can also manually press **F8** to force a capture.

## 3. Generating the Playstyle Card
Once you have collected some session data (which is saved into the `sessions/` folder), you need to process it and build the HTML card.

1. **Process the data**:
   ```bash
   python stat_engine.py
   ```
   *This reads all your sessions, calculates your averages, classifies your Playstyle Archetype (e.g., Netrunner), and saves the final output to `card_data.json`.*

2. **Build the HTML Web Page**:
   ```bash
   python build_card_dynamic.py
   ```
   *This takes the data from `card_data.json` and injects it into a dynamic React/HTML template.*

3. **View the Card**:
   * Open the newly generated `index.html` file in any modern web browser (Chrome, Edge, Firefox, etc.) to view your interactive Playstyle Card!
