# Watch Dogs 2 Playstyle Card Maker

Welcome to the **Watch Dogs 2 Playstyle Card Maker**! This project is a local set of Python scripts designed to track your gameplay in Watch Dogs 2 and automatically generate a beautiful, dynamic "Playstyle Card" (similar to a player profile or stats card) that visualizes your in-game behavior and progression. 

## What does it do?
The tool uses a combination of techniques to gather data while you play:
* **Background Keylogging**: Tracks your WASD and mouse movements to calculate how much time you spend driving, in combat, etc.
* **OCR (Optical Character Recognition)**: Reads the mission-end screens to capture your raw stats (Kills, Headshots, Hacks, etc.) using Tesseract OCR.
* **Stat Engine**: Merges this data to classify your "Archetype" (e.g., Netrunner, Digital Anarchist, Balanced Operative) based on how you play.
* **Dynamic Web Card**: Generates a self-contained, interactive HTML web page with beautiful CSS/React components to visualize your stats and historical trends over time.

---

## Screenshots

<!-- ADD YOUR SCREENSHOTS BELOW THIS LINE -->
> **Tip:** You can drag and drop your screenshots directly into this area if you are editing this file on GitHub!

*Placeholder for: Dynamic Web Card (index.html)*
![Playstyle Card Screenshot](link-to-your-image-here)

*Placeholder for: Stat Engine Terminal Output*
![Stat Engine Screenshot](link-to-your-image-here)

*Placeholder for: Input Logger Terminal Output*
![Input Logger Screenshot](link-to-your-image-here)

*Placeholder for: OCR Capture Terminal Output*
![OCR Capture Screenshot](link-to-your-image-here)

---

## Documentation

For a detailed breakdown of what each file in this project does, please refer to the **[FILES_EXPLAINED.md](FILES_EXPLAINED.md)** file.

For instructions on how to install and run this project from scratch, please refer to the **[INSTALLATION.md](INSTALLATION.md)** file.

---

## Privacy & Data
This project runs entirely **locally** on your machine.
* **NO Private APIs**: There are no external API calls requiring private keys or subscriptions.
* **NO Data Sharing**: All your gameplay data, captured screenshots, and generated HTML cards are saved locally in this folder.
* **GitHub Safe**: A `.gitignore` file has been included so that if you fork or clone this repository, your personal `sessions` data, `card_data.json`, and OCR calibrations are kept private and are not pushed to the public repository.
