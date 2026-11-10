#!/bin/sh
# Judge probe: replies at "may we go on?" that are not refusals. Run from the repo root.
# Usage: sh references/reviews/iter1/judge-probes/judge_goahead_probe.sh [--llm]
P=references/reviews/iter1/judge-probes
for reply in "ठीक है, जल्दी बोलिए थोड़ा बिज़ी हूँ" "ये फ्रॉड कॉल तो नहीं है? आप कहाँ से बोल रहे हो?" "मुझे हिंदी ठीक से नहीं आती, तमिल में बोलिए" "अभी गाड़ी चला रहा हूँ, शाम को कॉल करना" "हाँ बोलो, पर लोन का पैसा तो मैंने भर दिया है" "किस चीज़ का फ़ीडबैक? मैंने तो कोई शिकायत नहीं की"; do
  printf '%s\n%s\n' "हाँ" "$reply" | uv run python -m samajh.dialogue play --record $P/record_compliant.json --lang hi --lender "Namoona Bank" "$@" 2>&1 \
    | awk -v r="$reply" '/call ended/ {print r " => " $0; f=1} END {if (!f) print r " => call continues (bot re-asked or went on)"}'
done
