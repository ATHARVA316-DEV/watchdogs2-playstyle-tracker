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

* Dynamic Web Card (index.html) [Playstyle Card Screenshot] 
<img width="924" height="962" alt="Screenshot 2026-07-04 103309" src="https://github.com/user-attachments/assets/d9fd3078-a209-4852-96d6-7a7074a8dee2" />

* Placeholder for: Stat Engine Terminal Output [Stat Engine Screenshot]
<img width="992" height="500" alt="Screenshot 2026-07-04 110524" src="https://github.com/user-attachments/assets/7725af58-1f1b-495f-a621-629be932464e" />


* Placeholder for: Input Logger Terminal Output [Input Logger Screenshot]

<img width="755" height="293" alt="Screenshot 2026-07-04 110704" src="https://github.com/user-attachments/assets/0cafba18-2c5e-443e-bc5c-6530ad136abe" />

<img width="760" height="642" alt="Screenshot 2026-07-04 111350" src="https://github.com/user-attachments/assets/7155d541-8bcd-43aa-9c02-898dacc6f5a1" />

<img width="856" height="408" alt="Screenshot 2026-07-04 111403" src="https://github.com/user-attachments/assets/8870d316-d90e-4770-b740-1fc3761b94cb" />


* Placeholder for: OCR Capture Terminal Output [OCR Capture Screenshot]

<img width="894" height="511" alt="Screenshot 2026-07-04 110436" src="https://github.com/user-attachments/assets/98da35a4-9384-42e8-98d4-cdb6a77e9ff4" />

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
