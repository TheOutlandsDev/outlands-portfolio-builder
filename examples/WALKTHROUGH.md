# Your first fictional portfolio

1. Install requirements in a virtual environment and launch `portfolio.py`.
2. Click **Load fictional example**. On Profile, check that the person is Alex
   Example and the contact uses `example.invalid`.
3. On Projects, select Workshop inventory helper. Change its title to
   **Workshop material checklist**. Switch to Community project guide, then back;
   the edit should remain. Keep its stable project ID unchanged.
4. Read the different outcome labels. The barcode idea is Planned; it must not
   become a successful test claim just because it appears in the portfolio.
5. On Evidence, select the generated receipt. Its source is the fictional
   `receipt.txt` in this example folder. It is not an actual acceptance receipt.
   Saving a file hash does not change that meaning.
6. Save input as a **new** private JSON if you want to keep edits. File source
   paths become absolute in that private copy. Keep it outside the public repo.
7. Choose a new output directory and leave the hash checkbox off. Click
   **Review and export...**. Inspect both **Readable review** and
   **Exact public JSON**; the output directory should not exist yet. Click
   **Back to editor** and confirm it still does not exist. Prepare the same
   fresh destination again, then click **Export reviewed bundle**. The file
   reference in the output should show File not checked.
8. Choose another fresh output directory and enable hashing. Click
   **Review and export...**, inspect both tabs, then click
   **Export reviewed bundle**. The file reference should show SHA-256 recorded.
9. Open the PDF and HTML index. Confirm the changed title, explicit limitations,
   claim labels and working relative links. There should be no raw receipt file
   or private source path in the public bundle.
10. Run `python portfolio.py --verify YOUR_BUNDLE_FOLDER`. For a disposable copy
   only, edit `index.html` and verify again: the check must fail.
11. Replace fictional input with your own authorized material before using it as
    your actual portfolio. Review all exported text, public URLs, labels and
    metadata before sharing. The program does not upload the bundle for you.

CLI equivalents:

```text
python portfolio.py --demo --output ../fictional-unchecked
python portfolio.py --demo --check-evidence --output ../fictional-hashed
python portfolio.py --verify ../fictional-hashed
```

All outputs must be new names. These commands do not replace your existing files.
