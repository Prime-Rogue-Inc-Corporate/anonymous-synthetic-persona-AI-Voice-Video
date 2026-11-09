# Source

**Remarks to the United Nations General Assembly in New York City**, President Donald J. Trump, September 23, 2025, 10:08 a.m., United Nations Headquarters.

- Official record: Daily Compilation of Presidential Documents, DCPD-202500944 (Office of the Federal Register): https://www.govinfo.gov/app/details/DCPD-202500944/
- A work of the US government by an official in his official capacity, so public domain under 17 U.S.C. 105.

## The excerpt

`excerpt.txt` runs from "In May, I traveled to the Middle East" (07:25 into the address) to "much, much bigger." (just before 14:04). It is one contiguous stretch, with nothing cut, added or reordered.

The wording follows an as-delivered, time-stamped transcript of the address audio (the `narrativeflow` repository on GitHub, `transscripts/trump_1.txt`), because the delivered words include ad-libs (the escalator, the teleprompter "working now") that the prepared text does not. Where an as-delivered transcript and the official record differ, the differences are punctuation and small function words (e.g. "it's working now, just went on" vs "it's working now. It just went on.").

## Check

The `PRESIDENT:` lines in `script.txt`, joined with single spaces, must equal `excerpt.txt` byte for byte:

```sh
python3 -c "L=[l.split(': ',1)[1] for l in open('script.txt') if l.startswith('PRESIDENT')]; print(' '.join(x.strip() for x in L)==open('excerpt.txt').read())"
```

Respellings in `episode.json` (`pronounce`) change only what the synthesizer says (e.g. "$500 million" is spoken as "five hundred million dollars"), never the captions.
