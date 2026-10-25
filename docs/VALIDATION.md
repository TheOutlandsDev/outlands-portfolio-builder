# Validation and known limits

## Local checks

The current suite contains **42 cases**, including six desktop lifecycle/editor
cases. On Windows Python 3.12, 41 passed and one native symlink fixture skipped
because this review environment could not create it. Skips are not platform
passes. Tk was required; all six GUI cases passed.

The tests generate their own portfolios, evidence and temporary directories.
They cover schema/size/depth/type limits, duplicate JSON keys and IDs, evidence
references, reserved/path-like IDs, URL restrictions, escaped HTML/PDF text,
Windows-1252 support and unsupported-character refusal, optional evidence reads,
independent SHA-256 checks, no raw evidence/path inclusion, private input saving,
new-only output, one/ten-project inventories, exact archive verification,
tampering, CSV formula guards, cancellation and partial-write preservation.

Desktop cases cover empty startup, loading the fictional example, project-switch
editing, quote/pipe/newline round trips, actual worker-driven PDF/ZIP export,
controlled Stop behavior and plain-text entry. Tk polling callbacks are cancelled
when the app frame is destroyed, and tests reclaim Tk objects on the main thread.
The export worker communicates through a queue and touches no Tk widget.

The actual Windows desktop was visually checked from blank startup. The fictional
example was loaded with its real button; a fresh output was entered and Export
clicked. The window reported eleven exported files, and a separate CLI verifier
accepted that directory. No personal input or real evidence was used.

A separate fictional two-project bundle with the example receipt hashed produced
a three-page PDF. Every page was rendered with Poppler and visually inspected.
An independent pdfplumber character-boundary check found zero out-of-page text.
PDF text/metadata tests verify expected content, page count and an author derived
from the explicit profile, not the machine account. Native fonts/viewer rendering
can differ; text extraction alone is not the visual qualification.

## CI

The workflow installs the exact runtime/test pins and requires Tk on Windows and
Ubuntu with Python 3.12 and 3.13, using Xvfb on Ubuntu. It runs the source gate,
full suite, fictional CLI export and separate verification. Tests make no runtime
network call; package installation and the separate advisory-check step use PyPI.
See [Actions](https://github.com/TheOutlandsDev/outlands-portfolio-builder/actions)
for actual results, rather than treating workflow configuration as a passing run.

## Limits

- Outcomes are author-stated labels. Neither associated evidence IDs nor file
  hashes establish runtime, employment, authorship, acceptance or independent proof.
- There is no automatic redaction, network publication, receipt-content analysis,
  image embedding, DOCX export, résumé parsing or evidence-signature verification.
- PDFs are untagged standard-font documents. Broad Unicode, complex-script
  shaping and PDF accessibility conformance are not qualified in this release.
  Input outside printable Windows-1252 is rejected instead of silently replaced.
- Cancellation and file-change checks are cooperative/best-effort. Trusted local
  storage is required; hostile link races, unusual reparse types, network storage
  and atomic point-in-time captures are not established.
- Export verifies deterministic bytes on one runtime but does not promise the same
  compressed/PDF bytes across library or platform versions. PDF dates are fixed
  reproducibility metadata, not a project or receipt timestamp.
- A write error/cancel can leave incomplete new output. No existing destination
  is replaced and no automatic deletion is attempted. Back up editable input
  separately; an exported public snapshot is not an editable input file.
- Memory/time are bounded by input/page/output limits, not a forced process-level
  timeout. A blocked native filesystem call can outlast a Stop request.
- macOS, frozen executables, screen-reader accessibility and long-running/large
  production workflows have not been qualified. The GUI targets desktop widths.
