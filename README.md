# Outlands Portfolio Builder

Create a portfolio PDF, an offline HTML index and project case studies from your
own structured information. A desktop editor and CLI produce a checked ZIP,
evidence-reference CSV, public JSON snapshot and SHA-256 manifests.

Original application code, tests, fictional examples and documentation are
[MIT licensed](LICENSE). The sample uses **Alex Example** and imaginary projects.
No personal résumé, business/employer content, real portfolio, private receipt,
font, runtime, dependency implementation or credential is bundled.

## Requirements and quick start

- **Python 3.12 or 3.13**. Desktop mode also needs Tk/Tcl, normally included in
  the python.org Windows installer. On Linux, install your distribution's Tk
  package (commonly `python3-tk`) if it is missing. CLI mode needs no display.
- Install the pinned PDF dependencies into a new virtual environment. No account,
  model download, subscription, external browser service or server is needed.
- PDF text currently supports **printable Windows-1252**, including common
  Western European accents. Emoji, CJK and other unsupported characters are
  rejected with a field error before output creation. There is no font selector
  or silent character replacement in this release.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements.txt
.\.venv\Scripts\python.exe portfolio.py
```

Linux:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
.venv/bin/python portfolio.py
```

Use Python 3.13 instead if that is your chosen supported installation. Commands
below use `python`; substitute your virtual environment's executable. The app
itself makes no network requests. pip needs network access to acquire dependencies.

## Desktop workflow

1. Start empty or click **Load fictional example**. Nothing is scanned, exported
   or uploaded automatically. New/Open/Example can replace the in-memory input;
   the editor warns when it has tracked unsaved edits. There is no autosave.
2. On **Profile**, enter your name, professional title, summary, skills and
   optional public contact text. Skills and contact items use one line per entry.
3. On **Projects**, add up to ten projects. Select a project to edit its stable
   ID, title, your role, summary, problem, approach, limitations and outcomes.
   Scroll the right-hand form to reach all fields. IDs use lowercase letters,
   digits and hyphens, start with a letter, and must be unique.
4. Write outcomes using pipe-separated CSV:

   ```text
   reported | The author reports a successful generated fixture run. | fixture-a
   planned | Add a search interface in a later version. |
   unverified | A real user acceptance session has not been completed. |
   ```

   Status must be `observed`, `reported`, `planned` or `unverified`. `observed`
   displays as **Observed (author-stated)**. Evidence IDs are optional,
   comma-separated references to the Evidence tab. Quote a statement containing
   a literal pipe; normal CSV double-quote escaping also supports quotes and
   multiline statements. The editor preserves those values when switching projects.
5. On **Evidence**, add a unique ID, public label, kind and optional public note.
   Choose `note`, `link` or `file`. For a file, use **Choose file** or enter a path.
   Click **Save evidence entry** to apply that form to the in-memory document.
   Removing an entry does not silently remove project references to its ID;
   fix those references before exporting. Original evidence files are not changed.
6. Use **Save input as new JSON** to preserve editable work. This creates a new
   file and never replaces an existing one. Private file references become
   absolute paths so a saved input remains usable from another folder on that
   machine. Keep this input JSON private when its content or paths are private.
7. Choose a **new** output folder with an existing parent. Select **Hash selected
   evidence files** only if you want their contents read for SHA-256. By default,
   file evidence is labelled **File not checked** and no evidence content is read.
8. Click **Export bundle**. It validates, renders and checks the archive before
   creating the destination, then verifies the written bundle. Review the result
   before sharing. Export uses a content snapshot captured when you click it;
   subsequent edits apply to a later export. **Stop** is cooperative and waits
   for the current operation. It is not a hard timeout on blocked filesystem I/O.

Input edits are not automatically saved by exporting. The public `portfolio.json`
inside an export is a normalized report, **not** the editable input format. Open
your separately saved input JSON to continue editing.

## CLI examples

Generate the fictional demo without reading its evidence-file contents:

```text
python portfolio.py --demo --output ../portfolio-demo-001
```

Generate it again with the bundled fictional receipt hashed:

```text
python portfolio.py --demo --check-evidence --output ../portfolio-demo-hashed-001
```

Use your own explicit input and verify the resulting folder:

```text
python portfolio.py my-private-input.json --output ../my-portfolio-001
python portfolio.py --verify ../my-portfolio-001
```

Use `--check-evidence` on your own input only when you want the selected files
read. File references are relative to the input JSON's parent; absolute local
paths are also supported. Links are descriptions and are **never fetched**.
`--help` and `--version` open no desktop window. Successful export/verification
returns exit code 0; a controlled input, dependency, I/O or verification failure
returns 2. Standard argparse usage errors also return 2.

## Input format

Start from [examples/workshop.json](examples/workshop.json), whose data is
entirely fictional. The schema accepts only the documented fields:

```json
{
  "schema_version": 1,
  "profile": {
    "name": "Alex Example",
    "title": "Developer",
    "summary": "A fictional portfolio.",
    "skills": ["Python", "Testing"],
    "contact": ["alex@example.invalid"]
  },
  "projects": [{
    "id": "small-tool",
    "title": "Small tool",
    "role": "Author",
    "summary": "An example project.",
    "problem": "Describe the need.",
    "approach": "Describe your contribution.",
    "limitations": "State what has not been established.",
    "outcomes": [{
      "status": "unverified",
      "statement": "Independent acceptance remains open.",
      "evidence": ["review-note"]
    }]
  }],
  "evidence": [{
    "id": "review-note",
    "label": "Author's review note",
    "kind": "note",
    "note": "This is not an independent acceptance result."
  }]
}
```

For `file` evidence, add `"source": "receipt.txt"`. For `link`, supply a public-style
HTTPS URL without credentials, query, fragment or nonstandard port. Local/private
literal addresses and common local hostnames are rejected. This is a conservative
URL-format guard, not a DNS lookup, privacy audit or destination safety verdict.
For `note`, omit `source`. IDs in every outcome must exist and must not repeat.

Limits include 256 KiB input, 12 JSON container levels, 1-10 projects, 1-20
outcomes per project, 20 evidence entries and 20 skills. Names/titles/roles have
120-180 character limits; profile/project prose fields allow up to 3,000
characters, outcome statements 1,200 and evidence notes 600. The total normalized
JSON is also bounded. Unknown fields, duplicate IDs/JSON keys, controls,
nonfinite/oversized numbers and unsupported PDF characters are rejected.

## Output and verification

For the two-project demo, the output directory has eleven files:

```text
portfolio.pdf
index.html
case-studies/workshop-inventory.html
case-studies/community-guide.html
portfolio.json
evidence.csv
README.txt
MANIFEST.json
SHA256SUMS
portfolio-bundle.zip
portfolio-bundle.zip.sha256
```

The ZIP contains the content files, manifest and checksum list. It does not
contain itself or its outer checksum file. `MANIFEST.json` records content-file
lengths and SHA-256 values; `SHA256SUMS` also covers that manifest. The verifier
checks exact directory/ZIP inventories, file bytes and archive checksum without
extracting the ZIP or opening the PDF in a viewer.

Open `index.html` directly in a browser: relative case-study links work offline.
There are no scripts, remote fonts, images or automatic network resources.
Explicit evidence hyperlinks can be clicked by a reader. User-supplied text is
escaped in both HTML and ReportLab markup; it is not treated as executable code.
Text fields in the CSV receive a formula prefix guard for spreadsheet use.

PDFs use standard built-in font metrics, Letter pages, flowing paragraphs and
page numbering. No local fonts or private images are embedded. Long content can
continue onto later pages; output is limited to 100 PDF pages, 8 MiB PDF,
32 MiB combined content and a 32 MiB archive. PDF metadata deliberately uses a fixed internal
creation date for repeatability; it does not date the user's project or evidence.
Identical inputs are tested for repeatability on the same dependency/runtime;
byte-for-byte identity across different platforms or future libraries is not promised.

Evidence hashing allows at most 16 MiB per file and 64 MiB total. Existing links
and junction ancestors are rejected on checked paths. Only explicitly referenced
regular files are read. Size, modification time and file identity checks detect
some concurrent changes; this is not an atomic snapshot or hostile-filesystem
containment mechanism. Use stable files on trusted local storage.

## Privacy, rights and failure handling

The builder does not certify the truth of a claim, ownership of evidence or
permission to disclose project information. A hash identifies bytes; it cannot
turn an author-stated or planned outcome into a passed test. Do not include
employer/client material, private personal information or third-party assets
unless you have the necessary permission.

Actual evidence contents and configured file paths are omitted from the bundle.
Your supplied profile text, contact details, labels, notes, URLs and optional
hashes remain visible. This is not redaction or anonymization; review the PDF,
HTML, CSV and public JSON before sharing. Saved editor inputs may contain private
paths. The app never publishes, uploads or contacts an evidence URL for you.

Destinations are new-only. Existing output folders and input JSON files are
never merged, replaced or deleted. An error or cancellation during writes can
leave a partial new folder. Preserve it for inspection or remove it yourself;
the app makes no automatic cleanup claim. Cancelled exports and failed
verification are not successful release packages.

## Tests and suggestions

```text
python -m pip install --only-binary=:all: -r requirements-dev.txt
python -B -m unittest discover -s tests -v
python -B source_check.py
```

Tests use generated input, receipts and owned temporary directories. Tk tests
need a display; use Xvfb on a headless Linux runner. Set `PORTFOLIO_REQUIRE_TK=1`
to require those GUI tests instead of allowing display-related skips. Native
symlink setup may skip where the platform does not allow it. See the detailed
[validation record](docs/VALIDATION.md), [provenance and dependencies](docs/PROVENANCE.md)
and [first-portfolio walkthrough](examples/WALKTHROUGH.md).

[Suggestions](https://github.com/TheOutlandsDev/outlands-portfolio-builder/issues/new?template=feature_request.yml),
[bug reports](https://github.com/TheOutlandsDev/outlands-portfolio-builder/issues/new?template=bug_report.yml)
and contributions are welcome. Explain the workflow you want improved; code is
not required to suggest a change. Use fictional reproductions and keep real
input, portfolios and evidence out of public issues. Read
[CONTRIBUTING](CONTRIBUTING.md) and [SECURITY](SECURITY.md).
