# Source

**Prime Minister Carney delivers remarks at the Forever Canadian Rally**, Calgary, Alberta, October 15, 2026, as prepared for delivery, published by the Prime Minister's Office at pm.gc.ca.

- `source_text.txt` is the full published text: one paragraph per line, from "Thank you, Mayor Farkas." to "Let us build it together."
- The episode reads the whole speech. Nothing is cut, added or reordered. The published text is the prepared one, so ad-libs from the night (for example the "election interference" aside) are not in it and not in the episode.
- `[cheer]` cues are synthesized crowd sound placed between sentences. They are not words and appear in no caption.
- Reproduced for non-commercial purposes with attribution. Not affiliated with or endorsed by the Government of Canada. The maple figure is invented and is not a likeness.

## Check

The `PM:` lines in `script.txt`, with cues removed and joined with single spaces, must equal the paragraphs of `source_text.txt` joined with single spaces:

```sh
python3 -c "import re; L=[re.sub(r'\s*\[\w+\]','',l.split(': ',1)[1]).strip() for l in open('script.txt') if l.startswith('PM:')]; print(' '.join(L)==' '.join(open('source_text.txt').read().split(chr(10))))"
```
