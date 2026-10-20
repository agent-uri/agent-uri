#!/bin/bash
# build-draft.sh - Build an Internet-Draft from its kramdown-rfc source
# Produces xml2rfc v3 XML (the file to submit) plus .txt, .html and .pdf

set -euo pipefail

# Colors for output
RED='\033[31m'
GREEN='\033[32m'
RESET='\033[0m'

# Configuration
KRAMDOWN_RFC=${KRAMDOWN_RFC:-kramdown-rfc}
XML2RFC=${XML2RFC:-xml2rfc}

usage() {
    echo "Usage: $0 <draft-name>"
    echo "Example: $0 draft-narvaneni-agent-uri-04"
    echo ""
    echo "Reads docs/rfc/<draft-name>.md and writes <draft-name>.{xml,txt,html,pdf}"
    echo "next to it. Override tool paths with KRAMDOWN_RFC and XML2RFC."
}

if [[ $# -ne 1 || "$1" == "-h" || "$1" == "--help" ]]; then
    usage
    exit 1
fi

name=${1%.md}
rfc_dir="$(cd "$(dirname "$0")/.." && pwd)/docs/rfc"

if [[ ! -f "$rfc_dir/$name.md" ]]; then
    echo -e "${RED}Not found: $rfc_dir/$name.md${RESET}" >&2
    exit 1
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# kramdown-rfc caches references in .refcache relative to the working directory
cd "$rfc_dir"

# kramdown-rfc still emits v2 vocabulary (<spanx>, <list>, <texttable>), which
# idnits3 flags as deprecated, so convert it with xml2rfc's own v2v3 converter.
"$KRAMDOWN_RFC" "$name.md" > "$tmp/raw.xml"
"$XML2RFC" --v2v3 "$tmp/raw.xml" -o "$tmp/v3.xml"

# Drop kramdown-rfc's <?line N?> source-mapping processing instructions, which
# idnits3 also flags; they only affect error-message line numbers.
sed -E '/^[[:space:]]*<\?line -?[0-9]+\?>[[:space:]]*$/d; s/<\?line -?[0-9]+\?>//g' \
    "$tmp/v3.xml" > "$name.xml"

"$XML2RFC" --text --html --pdf "$name.xml"

echo -e "${GREEN}Built $rfc_dir/$name.{xml,txt,html,pdf}${RESET}"
