# 008 · Special Order: The Full Hour

The 60-minute version of [007](../007-special-order): Rep. Clay Whitlow (fictional), a lame-duck congressman who lost his primary, uses a full special-order hour in the first week of the November 2026 lame duck.

- `script.txt` is assembled from `parts/` (in the order listed below); edit the parts, then rebuild the script.
- The full render (~280 MB) is too large to keep in git. Render it locally:

```bash
cat parts/01-opening.txt parts/02-calendar.txt parts/03-spending.txt parts/03b-prices.txt parts/03c-debt-limit.txt \
    parts/04-senate.txt parts/04b-lame-duck.txt parts/05-war.txt parts/06-surveillance-files.txt parts/07-process.txt \
    parts/08-two-parties.txt parts/08b-mail.txt parts/09-team.txt parts/10-closing.txt > script.txt
python ../../persona/render.py . --jobs 4      # ~1 hour on 2 cores
```

- `render.json` records the renderer version and commit used for the published cut.
- `clips/` holds a short highlight.

Facts referenced (as of Nov 2026): House schedule cuts and the Sept. 16 recess, the national fossil bill, the $40T debt and >$1T interest, the $41.1T debt limit, 30-year Treasury yields, the court-ordered tariff refunds, the Feb. 28 start of the Iran war and the March (212–219) and May (212–212) war-powers votes, the April FISA 702 vote (235–191), the 2018 farm bill, the 20th Amendment. Sources: AP, NPR, States Newsroom, ABC News, Washington Times.
