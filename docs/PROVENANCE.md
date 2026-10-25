# Source and license scope

This is a fresh general-purpose implementation informed by the owner's existing
private portfolio/PDF/HTML packaging scripts. Those originals used hardcoded
personal prose, fixed output locations, document intermediates and Windows font
paths. No personal prose, architecture diagram, original output or receipt is
copied into this public application. Selected original-generator hashes were
recorded outside the public tree to verify that the originals remain unchanged.

The owner explicitly authorized cleanup, testing and public MIT release of this
generic application. The new core, Tk editor, tests, examples and documentation
are original, assistant-assisted work. No third-party application implementation
or required source notice was identified as incorporated. This records the
authorship basis; it does not independently prove exclusive ownership of all
historical source material.

The [MIT license](../LICENSE) covers this original source and fictional material.
It does not relicense a user's inputs, evidence, fonts, Python, Tk, dependencies
or external services. There is no automatic claim or licence grant for anything
a user later enters into the app.

## Runtime dependencies

| Package | Version | Upstream license |
| --- | --- | --- |
| ReportLab | 5.1.0 | BSD-style terms in its retained license text |
| Pillow | 13.0.0 | MIT-CMU and retained component notices |
| charset-normalizer | 3.5.2 | MIT |

Pillow and charset-normalizer are pinned transitive requirements of ReportLab.
They are installed separately; no wheel, implementation, native binary or
third-party font is included in the repository. ReportLab's standard font
metrics are used; Windows Arial and bundled Vera font files are not embedded.
Retained upstream notices are in [THIRD-PARTY-NOTICES.txt](../THIRD-PARTY-NOTICES.txt).
[DEPENDENCIES.json](DEPENDENCIES.json) records exact release versions, metadata,
release-file hashes and the dated PyPI advisory response for each runtime package.

PyPI reported no known advisories for these three exact versions on 2026-10-25.
This is a dated package-database result, not proof that the application or
dependencies have no vulnerabilities. Recheck before later releases. Pins alone
are not a complete supply-chain or cross-platform acceptance audit.

Development tests additionally use pypdf 6.10.0 (BSD-3-Clause); visual review used
separately installed pdfplumber and Poppler. None is required to run the desktop
or CLI app, and none is bundled as implementation code. Python/Tk and PDF viewers
keep their own licenses. Include the appropriate upstream notices if you later
redistribute a runtime, frozen executable or embedded dependencies.

Primary API references consulted:

- [ReportLab paragraphs and markup](https://docs.reportlab.com/reportlab/userguide/ch6_paragraphs/)
- [ReportLab Platypus flowables](https://docs.reportlab.com/reportlab/userguide/ch5_platypus/)
- [ReportLab open-source licensing](https://docs.reportlab.com/developerfaqs/)
- [Python Tkinter threading](https://docs.python.org/3/library/tkinter.html#threading-model)
- [Python zipfile](https://docs.python.org/3/library/zipfile.html)

Escaped text is passed to ReportLab rather than user-controlled markup or image
instructions. Evidence URLs are not fetched, raw evidence is not attached, and
archive verification compares bounded members without extraction.
