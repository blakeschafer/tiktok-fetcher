#!/bin/bash

python3 -m venv venv
source venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo "Note: The Whisper model (~140MB for 'base') will be downloaded on first transcription."
echo "Run with: ./run.sh"
