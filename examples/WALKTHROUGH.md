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
7. Choose a new output directory. Export once without the hash checkbox; the
   file reference should show File not checked. Choose another fresh directory
   and export with hashing enabled; it should show SHA-256 recorded.
8. Open the PDF and HTML index. Confirm the changed title, explicit limitations,
   claim labels and working relative links. There should be no raw receipt file
   or private source path in the public bundle.
9. Run `python portfolio.py --verify YOUR_BUNDLE_FOLDER`. For a disposable copy
   only, edit `index.html` and verify again: the check must fail.
10. Replace fictional input with your own authorized material before using it as
    your actual portfolio. Review all exported text, public URLs, labels and
    metadata before sharing. The program does not upload the bundle for you.

CLI equivalents:

```text
python portfolio.py --demo --output ../fictional-unchecked
python portfolio.py --demo --check-evidence --output ../fictional-hashed
python portfolio.py --verify ../fictional-hashed
```

All outputs must be new names. These commands do not replace your existing files.
