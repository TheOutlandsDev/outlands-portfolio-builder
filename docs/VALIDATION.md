# Validation and known limits

## Local checks

The current suite contains **48 cases**, including eight desktop lifecycle/editor
cases. In the earlier 42-case Windows Python 3.12 run, 41 passed and one native
symlink fixture skipped because that review environment could not create it.
That historical run does not cover the new cases. Skips are not platform passes.
Tk was required there; all six GUI cases in that older version passed.

On local Linux with Python 3.12.14 and the pinned test dependencies, the earlier
45-case suite passed with `PORTFOLIO_REQUIRE_TK=1` and direct display access.
The first sandboxed full run had six Tk display-connection errors; rerunning
those six with direct display access passed, followed by the earlier 43-case
suite and then the 45-case suite. The 47-case suite added pre-export review
coverage and passed as a full local run in 10.928 seconds, with zero failures,
errors or skips. After the queued-review Stop fix, the current 48-case suite
passed locally in 12.694 seconds, with zero failures, errors or skips. The
48-case run is local acceptance; see Actions for the revision's hosted CI result.

The tests generate their own portfolios, evidence and temporary directories.
They cover schema/size/depth/type limits, duplicate JSON keys and IDs, evidence
references, reserved/path-like IDs, URL restrictions, escaped HTML/PDF text,
Windows-1252 support and unsupported-character refusal, optional evidence reads,
independent SHA-256 checks, no raw evidence/path inclusion, private input saving,
new-only output, one/ten-project inventories, exact archive verification,
tampering, CSV formula guards, cancellation and partial-write preservation.

The cross-format fictional-claim evaluation uses an explicit expected matrix of
four outcome statuses, three evidence types and two projects. It exports once
without reading the referenced file and once with a generated private receipt
hashed. For each export it checks exact outcome/status/evidence relationships in
public JSON, each HTML case-study section and extracted PDF case-study text; it
compares evidence IDs, labels, kinds and check states with the CSV. The evaluation
also checks the independently computed receipt hash and absence of its path,
filename and contents from text outputs and extracted PDF text. Both bundles must
pass the independent bundle verifier. Run only this case with:

```text
python -B -m unittest tests.test_portfolio.CoreTests.test_fictional_claims_match_across_export_formats -v
```

Two synthetic negative controls render a wrong PDF status or an incorrect HTML
evidence ID. Each deliberately inconsistent export still passes the bundle's
byte/ZIP verifier, then must fail the same cross-format claim check. They show
that checksum consistency alone does not establish semantic consistency.

This checks export consistency for the fictional fixture on the tested runtime.
It does not verify factual claims, evidence authenticity, private-data removal
from arbitrary user inputs, PDF accessibility or visual rendering.

Desktop cases cover empty startup, loading the fictional example, project-switch
editing, quote/pipe/newline round trips, actual worker-driven PDF/ZIP export,
controlled Stop behavior and plain-text entry. Tk polling callbacks are cancelled
when the app frame is destroyed, and tests reclaim Tk objects on the main thread.
The export worker communicates through a queue and touches no Tk widget.

The review path builds and checks the bundle in memory before showing a readable
public-field inventory and the exact public JSON. Tests confirm that no folder is
created before confirmation, cancellation does not write, a newly occupied
destination is preserved, and the confirmed output uses the same prepared JSON
bytes. The additional desktop case confirms that Stop after preparation but
before the queued review opens discards that review without writing output.
Evidence hashes, if selected, are captured during preparation. Review
does not inspect arbitrary private data for secrets or prove safe publication.

For the earlier 42-case build, a Windows desktop was visually checked from blank
startup. The fictional example was loaded with its real button; a fresh output
was entered and Export clicked. The window reported eleven exported files, and
a separate CLI verifier accepted that directory. No personal input or real
evidence was used. This older visual check does not cover the new review window.

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
For pull requests, the Windows 3.12 job also attempts to capture both tabs of
the fictional review window after checking the cancel/no-write and confirmed
export paths. It uploads short-lived screenshots for human visual inspection;
the artifact alone is not a visual PASS.
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
