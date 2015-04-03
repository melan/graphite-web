#!/bin/bash

if [[ -z "$1" || -z "$2" ]]; then
  echo "Usage: $0 <WHISPER_DIR> <INDEX_FILE>"
  exit 1
fi

WHISPER_DIR="$1"
INDEX_FILE="$2"

if [ ! -d "$WHISPER_DIR" ]
then
  echo "Fatal Error: $WHISPER_DIR does not exist."
  exit 1
fi

TMP_INDEX="${INDEX_FILE}.tmp"

rm -f $TMP_INDEX
cd $WHISPER_DIR
touch $INDEX_FILE
echo "[`date`]  building index..."
find -L . -name '*.wsp'    | perl -pe 's!^[^/]+/(.+)\.wsp$!$1!; s!/!.!g' > $TMP_INDEX
find -L . -name '*.wsp.gz' | perl -pe 's!^[^/]+/(.+)\.wsp$!$1!; s!/!.!g' >> $TMP_INDEX
echo "[`date`]  complete, switching to new index file"
mv -f $TMP_INDEX $INDEX_FILE
