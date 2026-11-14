# First names in Latin and Devanagari (iteration 4, W1)

Used by `samajh/dialogue/_names.py` (`judge_name`, `known_first_name`, `keyterms_for`) for the right-party check, and by
`tests/dialogue/test_first_name_scripts.py`. Synthetic project; these files hold public first names only, no person.

## Source
Wikidata (CC0), queried on 2026-11-14 through the QLever endpoint `https://qlever.dev/api/wikidata`. The two queries are
in the docstring of `build_names.py`: humans with Indian citizenship (P27 = Q668) that have an English and a Hindi
label (18,966 rows), and given-name items (male, female, unisex) with both labels (846 rows). The labels were written
by Wikidata editors, so the Latin and Devanagari spellings are independent of this project's transliteration rules.
The raw CSVs are not kept in the repo; rerun the queries to rebuild.

    python3 data/names/build_names.py people.csv given.csv > data/names/first-names.tsv

## Files
- `first-names.tsv`: 1,945 (Latin, Devanagari) first-name pairs. People: first tokens of labels with the same number of
  tokens (two or more), no initials or dots, Latin letters only and Devanagari letters only; a pair kept when two or
  more people attest it (7,849 raw pairs, 1,836 kept). Given-name items: a one-word Hindi label, kept only when the
  Latin or Hindi label is also an Indian person's first token (363). Then the stoplist (1,955) and `exclusions.tsv`
  (1,945). No rule uses the matcher.
- `exclusions.tsv`: 10 pairs judged by hand to be Wikidata errors (a place name, a misaligned label, an initial, a
  misspelt Hindi label), each with its reason.
- `known-misses.tsv`: 54 real pairs the matcher does not judge `same`, each with its class (English orthography,
  Bengali or Odia, vowel quality, Punjabi, Manipuri, contracted spelling). The property test fails if a pair joins or
  leaves this list.
- `aliases.tsv`: per-name alias groups for conventions that a general fold would make unsafe (the Tamil -ian/-iam/-yam
  ending of Balasubramanian and Subramanian, the Arabic Ayesha/Aisha). Added after the independent check.
- `heldout-checker-openings.jsonl`: the independent checker's 256 opening cases (iteration 4). Seen by the builder
  after its first run, so any later score on it is a rerun of a seen set, not a held-out result.
- `known-first-tokens.txt`: 16,420 first tokens (either script, attested once or more, plus every pair spelling),
  minus the stoplist. It answers only "is this word some person's first name?" (the broad lexicon). It holds some
  common words that are also someone's first token (काम, राही), which is why a weak claim frame uses the strict lexicon.
- `stoplist.txt`: honorifics and name suffixes never counted as a first name (devi, kumar, kumari, lal, singh, bai, ben,
  bhai, ji, sahab, shri, smt, sir, sardar, swami, guru, pandit, mohammad/muhammad, syed, sheikh, mirza, begum, khan, dr,
  military and royal titles; both scripts).
- `dev-pairs.tsv`: the hand-written development list (119 same-name pairs, 92 different-name pairs, mostly near
  misses) that `SAME_MAX` was chosen on. Not a held-out set.
- `score_openings.py`: scores opening replies in played calls (false rejections, loan named to third parties, Wilson
  intervals); input format in its docstring.
