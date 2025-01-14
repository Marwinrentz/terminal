#!/bin/bash

# Ensure locale is set to C for predictable sorting
export LC_ALL=C
export LC_COLLATE=C

# Get the script's own path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Directory containing the JSON files to sort
DIR="$1"
found_missing_keys=false


##### Log Setup #####
# Log file path
LOGFILE="${SCRIPT_DIR}/lang_sort_log.txt"

# Redirect stdout and stderr to the logfile
exec > "${LOGFILE}" 2>&1
#####################


##### Exit Gates #####
# Check if jq is installed
if ! command -v jq &> /dev/null
then
    echo "jq could not be found, please install jq first."
    exit
fi

# Check for directory argument
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 /path/to/translations"
    exit
fi

# Check if en_EN.json exists in the directory
if [[ ! -f "${DIR}/en_EN.json" ]]; then
    echo "The file en_EN.json does not exist in ${DIR}.Ensure you have the right directory, Exiting."
    exit
fi
######################


# Sort keys of the en_EN.json file with 4-space indentation and overwrite it
jq -S --indent 4 '.' "${DIR}/en_EN.json" > "${DIR}/en_EN.json.tmp" && mv "${DIR}/en_EN.json.tmp" "${DIR}/en_EN.json"

# Function to recursively find all keys in a JSON object
function get_keys {
    jq -r 'paths(scalars) | join("/")' "$1"
}

# Get keys and subkeys from en_EN.json
ref_keys=$(mktemp)
get_keys "${DIR}/en_EN.json" | sort > "${ref_keys}"

# Iterate over each .json file in the directory
for file in "${DIR}"/*.json; do
    # Check if file is a regular file and not en_EN.json, humanized index and does not contain "_incomplete" in its name
    if [[ -f "${file}" && "${file}" != "${DIR}/en_EN.json" && "${file}" != "${DIR}/humanized_index.json" && ! "${file}" =~ _incomplete ]]; then

        # Get keys and subkeys from the current file
        current_keys=$(mktemp)
        get_keys "${file}" | sort > "${current_keys}"

        # Display keys present in en_EN.json but not in the current file
        missing_keys=$(comm -23 "${ref_keys}" "${current_keys}")
        if [[ -n "${missing_keys}" ]]; then
            found_missing_keys=true
            echo -e "\nKeys/subkeys present in en_EN.json but missing in $(basename "${file}"): "
            echo "${missing_keys}"
        fi

        # Sort keys of the JSON file and overwrite the original file
        jq -S --indent 4 '.' "${file}" > "${file}.tmp" && mv "${file}.tmp" "${file}"

        # Remove the temporary file
        rm -f "${current_keys}"
    fi
done

# Remove the temporary file
rm -f "${ref_keys}"

if ${found_missing_keys}; then
    echo -e "\n\nSorting complete!"
    echo "Comparison found missing keys, Please Review!"
    echo "-------------------------------------------------------------------"
    echo "If there are stale translations, you can exclude with '_incomplete'"
    echo "  e.g. lol_EN_incomplete.json"
    echo "-------------------------------------------------------------------"
    exit 1
else
    echo -e "\n\nComparison and Sorting complete!"
fi
