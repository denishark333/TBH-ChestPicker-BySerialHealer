# TBH Reward Picker 2.5.6

An advanced, all-in-one automation and loot-tracking utility for **TaskbarHero**. This tool uses save-file monitoring and network interception to track your loot in real-time, alongside powerful mouse automation tasks to enable 100% safe AFK farming.

---

## 🚀 Key Features

### 📦 Loot Tracking & Target System
*   **Real-time Save Monitoring:** Watches your local game save to detect whenever a chest is opened or an item is acquired.
*   **Target Items Database:** Add specific item IDs to your "Targets" list. If a Target item drops, the utility immediately halts all automation and triggers an alarm to protect your loot.
*   **Network Interception (Mitmproxy):** Sniffs the game's incoming network packets to predict and log loot tables instantly.

### 🤖 Mouse Automation Suite
*   **Auto-Relogger:** Automatically restarts the game and logs back in if a crash is detected or if an automation task gets stuck. Includes an **Anti-Rollback Safety Delay** that waits before force-closing the game when a Target drops.
*   **Stage Switcher:** A customizable loop that periodically clicks 2 coordinates on your screen to automatically cycle between stages or re-enter portals. 
*   **Auto-Stash / Inventory Cleaner:** A customizable loop that periodically clicks up to 3 coordinates to automatically move your inventory items to the Stash (or Synthesize them). 
    *   *Smart Cooldown:* If a Target Item drops, the Auto-Stash automatically applies a 15-minute cooldown to ensure your target item is saved safely before stashing.

### 🔔 Discord Integrations
*   **Webhook Notifications:** Sends a ping to your Discord server whenever a Rare Chest is found, or when a Target Item is acquired.

---

## 🛠️ Installation & Setup

You don't need to manually install dependencies if you use the provided batch script.

1.  Clone or download this repository.
2.  Run the **`install_requirements.bat`** file. *(You only need to do this once, or whenever a new update requires a new library)*.
3.  Run the application by double-clicking **`run_peeker_gui.bat`**.

> **Note:** Python 3.10 or newer must be installed on your system and added to your `PATH`.

---

## 🛠️ Initial Configuration (Crucial for First-Time Setup)

When you open the application, you must configure two essential things for the utility to track your game:

### 1. Linking your Save File
To allow the utility to read your loot, you need to point it to your save file:
1. Go to the **Save File Section** in the UI.
2. Click on the **Gold Text** (the file path field).
3. Paste your game's save folder path into the field.
4. Click **Browse**.
5. Select the file named **`SaveFile_Live.es3`**.
6. Click **OK**.
*(This path will be saved, so you only need to do this once!)*

### 2. Starting the Proxy
The Network Interception (Mitmproxy) does not start automatically to prevent network conflicts. 
* **Every time you open the Panel**, you must explicitly click **"START PROXY"** in the Dashboard to begin tracking loot tables from the network.

---

## 🖱️ How to Calibrate Automation Tasks

Both the **Stage Switcher** and **Auto-Stash** use a simple Mouse Listener for calibration.

1.  Go to the **Settings** tab.
2.  Click the "Calibrate Click" button for the automation task you want to setup.
3.  Move your mouse over the desired button in the game window.
4.  **Left-Click** to register the coordinate.
    *   *(You can Right-Click at any time to cancel the calibration).*
5.  *Coordinates are automatically saved to your `config.json`. Note: If you move the game window, you must recalibrate!*

---

## ⚙️ AFK "Pro Tip" Setup

For the perfect AFK framing (allowing the utility to loop without getting stuck in menus), keep **3 panels open simultaneously** in-game:
1.  **Left Column:** Stash (Baú)
2.  **Center Column:** Inventory / Character Stats
3.  **Right Column:** Stage Portal / Map

*By doing this, the **Auto-Stash** will click on the left, and the **Stage Switcher** will click on the right, without ever overlapping or needing to open/close menus!*
