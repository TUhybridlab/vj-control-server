#!/bin/sh

DEST_FOLDER="env-vj"

if [ ! -d "$DEST_FOLDER" ]; then
	virtualenv2 "$DEST_FOLDER"
else
	echo "Already there! Just activating"
fi
. "$DEST_FOLDER/bin/activate"
pip install -r requirements.txt

echo "Done"
