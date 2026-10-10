# Source data

Place the original UCI dataset 350 workbook in ignored `data/raw/` as
`default of credit card clients.xls`. The supplied workbook is preserved unchanged.
No original ZIP or acquisition record was supplied; the original archive checksum
and retrieval date remain unknown. See the unchanged
[source manifest](../artifacts/source_manifest.json) for historical provenance
and parsing choices.

The supplied workbook was subsequently verified byte-for-byte against the
official UCI archive retrieved at `2026-10-10T18:00:23.006402Z`. All three
workbook hashes (recorded accepted, existing local and official ZIP member)
match. The [new verification receipt](../reports/provenance/uci350-official-comparison-20261010T180023Z.json)
records the current archive checksum and HTTP metadata. This later comparison
does not reconstruct the original download chain or date.

Official source: [UCI Default of Credit Card Clients](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients).
Citation: Yeh, I. (2009). Default of Credit Card Clients [Dataset]. UCI Machine
Learning Repository. [DOI 10.24432/C55S3H](https://doi.org/10.24432/C55S3H).
License: CC BY 4.0. Generated customer-level exports, quarantine records, and raw
bytes remain ignored; synthetic software fixtures live separately in tests/fixtures.
