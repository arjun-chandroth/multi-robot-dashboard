#!/bin/bash

# ROVER - Modular Car Controller Automation Script (with Ollama/Llama model setup)
# (c) 2024

banner="Multi-Robot Dashboard installer"

echo -e "\033[1;36m$banner\033[0m"

log() { echo -e "\033[1;32m[INFO] $1\033[0m"; }
warn() { echo -e "\033[1;33m[WARN] $1\033[0m"; }
err()  { echo -e "\033[1;31m[ERROR] $1\033[0m"; }
dbg()  { echo -e "\033[0;35m[DEBUG] $1\033[0m"; }

#-----------------------#
# 0. Install OLLAMA     #
#-----------------------#

if ! command -v ollama &>/dev/null; then
    log "Ollama not found. Attempting to install..."
    unameOut="$(uname -s)"
    case "${unameOut}" in
        Linux*)
            curl -fsSL https://ollama.com/install.sh | sh
            ;;
        Darwin*) 
            brew install ollama || curl -fsSL https://ollama.com/install.sh | sh
            ;;
        *)
            err "Ollama installation: Unsupported OS. Please install manually from https://ollama.com/download"
            exit 1
            ;;
    esac
    if ! command -v ollama &>/dev/null; then
        err "Ollama still not found after attempted install. Please install manually and re-run this script."
        exit 1
    fi
else
    dbg "Ollama already installed."
fi

#-----------------------#
# 1. Llama 3.2 Model Setup #
#-----------------------#

log "Pulling the Llama 3.2 base model with Ollama..."
ollama pull llama3:8b-instruct
if [ $? -ne 0 ]; then
    err "Failed to download llama3:8b-instruct. Please check your internet and Ollama setup."
    exit 1
fi
log "Llama 3.2 model pulled successfully."

#--------------------------#
# 2. Custom Modelfile Setup #
#--------------------------#

read -p "Enter GitHub Modelfile URL (raw .txt): " MODFILE_URL
MODFOLDER="ollama-custom"
mkdir -p "$MODFOLDER"
MODFILE_PATH="$MODFOLDER/Modelfile"
curl -fsSL "$MODFILE_URL" -o "$MODFILE_PATH"
if [ ! -s "$MODFILE_PATH" ]; then
    err "Failed to download Modelfile from $MODFILE_URL. Please verify the URL."
    exit 1
fi
log "Custom Modelfile downloaded to $MODFILE_PATH"

log "Building custom Ollama model for ROVER..."
ollama create rover -f "$MODFILE_PATH"
if [ $? -ne 0 ]; then
    err "Custom Ollama model build failed. Please check your Modelfile syntax."
    exit 1
fi
log "Custom Ollama model 'rover' created successfully."

#-----------------------#
#   Python/Git Checks   #
#-----------------------#

for cmd in python3 pip3 git; do
    if ! command -v $cmd &>/dev/null; then
        err "The required command '$cmd' is missing. Please install."
        exit 1
    fi
done

#-----------------------#
# 3. Get Project Source #
#-----------------------#

log "This script will set up the ROVER modular codebase."
read -p "Enter code Git repo URL [leave blank for local files]: " GIT_URL
if [ ! -z "$GIT_URL" ]; then
    REPO_NAME=$(basename -s .git "$GIT_URL")
    if [ -d "$REPO_NAME" ]; then
        warn "The folder '$REPO_NAME' already exists. Using it."
    else
        log "Cloning code from $GIT_URL..."
        git clone "$GIT_URL"
        if [ $? -ne 0 ]; then err "Git clone failed. Aborting."; exit 1; fi
    fi
    cd "$REPO_NAME"
else
    read -p "Enter local folder path for ROVER code [leave blank for current]: " LOCAL_SRC
    [ -z "$LOCAL_SRC" ] && LOCAL_SRC="."
    cd "$LOCAL_SRC"
    log "Using local directory: $(pwd)"
fi

#-----------------------#
# 4. Folder Structure   #
#-----------------------#

dbg "Ensuring required folders: recordings/, sensor_data/, static/, templates/..."
for folder in recordings sensor_data static templates; do
    [ ! -d $folder ] && mkdir -p $folder && log "Created: $folder"
done

if [ ! -f "static/placeholder.jpg" ]; then
    dbg "Downloading placeholder image..."
    wget -q -O static/placeholder.jpg "https://via.placeholder.com/640x480.jpg?text=ROVER"
    log "Added static/placeholder.jpg"
fi
if [ ! -f "templates/index.html" ]; then
    dbg "Creating templates/index.html."
    cat <<"EOF" > templates/index.html
<!DOCTYPE html>
<html>
<head><title>ROVER Modular Car Control</title></head>
<body style="font-family: sans-serif;">
    <h1 style="color: #008;">ROVER</h1>
    <p>Check your Flask-SocketIO web interface for live controls.</p>
</body>
</html>
EOF
    log "Added templates/index.html"
fi

if [ ! -f "yolov8n.pt" ]; then
    warn "YOLOv8n model file (yolov8n.pt) not present. Please download from Ultralytics."
fi

#-----------------------#
# 5. Python Virtual Env #
#-----------------------#

log "Setting up Python 3 virtual environment."
if ! python3 -m venv venv; then
    err "Python venv creation failed. Please ensure python3-venv is installed."
    exit 1
fi
source venv/bin/activate
log "Python venv activated."

#-----------------------#
# 6. Install Dependencies #
#-----------------------#

if [ ! -f requirements.txt ]; then
    err "requirements.txt not found. Please provide it."
    deactivate
    exit 1
fi
log "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    err "pip install failed. Try to fix and re-run."
    deactivate
    exit 1
fi
log "Dependencies installed successfully."

dbg "Checking main code files..."
for f in app.py config.py utils.py hardware_controller.py camera_processor.py ros_handler.py system_monitor.py ai_controller.py; do
    [ ! -f $f ] && warn "Missing file: $f"
done

log "ROVER setup complete!"
echo -e "\033[1;36m
To run the server:
    source venv/bin/activate
    python app.py
\033[0m
"

log "You may now use your Flask web app and custom Ollama LLM (invoke as 'rover')."

read -p "Would you like to start the Flask server now? [y/N]: " yn
if [[ $yn =~ ^[Yy]$ ]]; then
    python app.py
fi
