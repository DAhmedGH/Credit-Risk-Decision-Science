"""Bounded independent inspection, NOT a replacement for canonical xlrd parsing.

Only the known UCI workbook layout is accepted. No data values are printed.
This diagnostic script is deliberately outside the production package.
"""

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from struct import pack, unpack_from
import json
import math

from credit_risk.data.schema import NORMALIZED_COLUMNS, SOURCE_COLUMNS


source = Path('data/raw/default of credit card clients.xls')
source_stat = source.stat()
raw = source.read_bytes()
source_hash = sha256(raw).hexdigest()
assert raw[:8] == bytes.fromhex('d0cf11e0a1b11ae1'), 'Not an OLE compound workbook'
assert unpack_from('<H', raw, 28)[0] == 0xfffe, 'Unsupported OLE byte order'
sector_size = 1 << unpack_from('<H', raw, 30)[0]
assert sector_size in (512, 4096), 'Unsupported OLE sector size'
assert unpack_from('<I', raw, 72)[0] == 0, 'Extended DIFAT not supported'
fat_sectors = [value for value in unpack_from('<109I', raw, 76) if value < 0xfffffffa]
assert len(fat_sectors) == unpack_from('<I', raw, 44)[0], 'FAT sector count differs'


def sector(index):
    begin = (index + 1) * sector_size
    result = raw[begin:begin + sector_size]
    assert len(result) == sector_size, 'Sector outside original file'
    return result


fat = []
for index in fat_sectors:
    fat.extend(unpack_from('<' + 'I' * (sector_size // 4), sector(index)))


def stream(first, size=None):
    result = []
    visited = set()
    index = first
    while index < 0xfffffffa:
        assert index not in visited, 'OLE stream cycle'
        assert index < len(fat), 'OLE stream outside FAT'
        visited.add(index)
        result.append(sector(index))
        index = fat[index]
    assert index == 0xfffffffe, 'OLE stream did not end normally'
    content = b''.join(result)
    if size is not None:
        assert len(content) >= size, 'OLE stream shorter than declared size'
        content = content[:size]
    return content


directory = stream(unpack_from('<I', raw, 48)[0])
workbook_candidates = []
for offset in range(0, len(directory), 128):
    entry = directory[offset:offset + 128]
    name_length = unpack_from('<H', entry, 64)[0]
    name = entry[:max(name_length - 2, 0)].decode('utf-16le')
    if name in ('Workbook', 'Book'):
        assert entry[66] == 2, 'Workbook directory entry is not a stream'
        size = unpack_from('<Q', entry, 120)[0]
        assert size >= 4096, 'Mini-stream workbook is unsupported'
        workbook_candidates.append(stream(unpack_from('<I', entry, 116)[0], size))
assert len(workbook_candidates) == 1, 'Expected exactly one workbook stream'
workbook = workbook_candidates[0]


def records(offset):
    while offset + 4 <= len(workbook):
        code, length = unpack_from('<HH', workbook, offset)
        payload = workbook[offset + 4:offset + 4 + length]
        assert len(payload) == length, 'Truncated BIFF record'
        yield code, payload
        offset += 4 + length
        if code == 0x000a:
            return
    raise AssertionError('Missing BIFF EOF')


sheets = []
strings = []
for code, payload in records(0):
    if code == 0x0809:
        assert unpack_from('<HH', payload, 0) == (0x0600, 0x0005), 'Not BIFF8 globals'
    if code == 0x0085:
        sheet_offset = unpack_from('<I', payload, 0)[0]
        length, wide = payload[6], payload[7] & 1
        name = payload[8:8 + length * (2 if wide else 1)].decode(
            'utf-16le' if wide else 'latin1'
        )
        assert payload[5] == 0, 'Unsupported non-worksheet sheet'
        sheets.append((name, sheet_offset))
    if code == 0x00fc:
        unique = unpack_from('<I', payload, 4)[0]
        position = 8
        for _ in range(unique):
            length = unpack_from('<H', payload, position)[0]
            flags = payload[position + 2]
            position += 3
            assert flags & ~0x0d == 0, 'Unsupported string flags'
            runs = unpack_from('<H', payload, position)[0] if flags & 8 else 0
            position += 2 if flags & 8 else 0
            extension = unpack_from('<I', payload, position)[0] if flags & 4 else 0
            position += 4 if flags & 4 else 0
            size = length * (2 if flags & 1 else 1)
            assert position + size + 4 * runs + extension <= len(payload), (
                'SST continuation requires canonical xlrd'
            )
            strings.append(payload[position:position + size].decode(
                'utf-16le' if flags & 1 else 'latin1'
            ))
            position += size + 4 * runs + extension
        assert position == len(payload), 'Unexpected SST suffix'
assert len(sheets) == 1 and sheets[0][0] == 'Data', 'Unexpected sheet layout'

cells = [[None] * 25 for _ in range(30_000)]
headers = {0: {}, 1: {}}
dimensions = None
numeric_record_counts = Counter()
sheet_record_counts = Counter()
numeric_cell_count = 0
first_outcome_decoding_utc = None


def put(row, column, value):
    global numeric_cell_count, first_outcome_decoding_utc
    assert row >= 2 and row < 30_002 and column >= 0 and column < 25, (
        'Numeric cell outside expected data rectangle'
    )
    assert cells[row - 2][column] is None, 'Duplicate numeric cell'
    assert math.isfinite(value), 'Non-finite numeric cell'
    if column == 24 and first_outcome_decoding_utc is None:
        first_outcome_decoding_utc = datetime.now(timezone.utc).isoformat()
    cells[row - 2][column] = int(value) if value.is_integer() else value
    numeric_cell_count += 1


def rk(value):
    if value & 2:
        signed = value if value < 0x80000000 else value - 0x100000000
        number = float(signed >> 2)
    else:
        number = unpack_from('<d', pack('<II', 0, value & 0xfffffffc), 0)[0]
    return number / 100 if value & 1 else number


# Explicit metadata-record allowlist for this diagnostic's BIFF8 worksheet.
metadata_codes = {
    0x0809, 0x000a, 0x020b, 0x000d, 0x000c, 0x000f, 0x0011, 0x0010,
    0x005f, 0x002a, 0x002b, 0x0082, 0x0080, 0x0225, 0x0081, 0x0014,
    0x0015, 0x0083, 0x0084, 0x0026, 0x0027, 0x0028, 0x0029, 0x00a1,
    0x0055, 0x007d, 0x0208, 0x00d7, 0x023e, 0x001d, 0x0041, 0x00e5,
    0x00dd, 0x0012, 0x0013, 0x01af, 0x01bc, 0x0867, 0x0868,
    # MS-XLS HeaderFooter: printed page header/footer metadata, not cells.
    # https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-xls/5d3587f3-baef-46ab-b2cf-1c57e8b3dccf
    0x089c,
    # MS-XLS PLV (page layout view) and PhoneticInfo (sheet phonetic settings).
    0x088b, 0x00ef,
}
for code, payload in records(sheets[0][1]):
    sheet_record_counts[f'0x{code:04x}'] += 1
    if code == 0x0200:
        assert dimensions is None, 'Duplicate worksheet dimensions'
        dimensions = unpack_from('<IIHH', payload, 0)
        assert dimensions == (0, 30_002, 0, 25), 'Unexpected data dimensions'
    elif code == 0x00fd:
        assert len(payload) == 10, 'Unsupported LABELSST size'
        row, column = unpack_from('<HH', payload, 0)
        assert row in headers and column < 25, 'Text encountered in numeric data rectangle'
        assert column not in headers[row], 'Duplicate header cell'
        headers[row][column] = strings[unpack_from('<I', payload, 6)[0]]
    elif code == 0x0203:
        assert len(payload) == 14, 'Unsupported NUMBER size'
        row, column = unpack_from('<HH', payload, 0)
        put(row, column, unpack_from('<d', payload, 6)[0])
        numeric_record_counts['NUMBER'] += 1
    elif code == 0x027e:
        assert len(payload) == 10, 'Unsupported RK size'
        row, column = unpack_from('<HH', payload, 0)
        put(row, column, rk(unpack_from('<I', payload, 6)[0]))
        numeric_record_counts['RK'] += 1
    elif code == 0x00bd:
        row, first_column = unpack_from('<HH', payload, 0)
        last_column = unpack_from('<H', payload, len(payload) - 2)[0]
        assert len(payload) == 6 + (last_column - first_column + 1) * 6, 'Invalid MULRK size'
        for index, column in enumerate(range(first_column, last_column + 1)):
            put(row, column, rk(unpack_from('<I', payload, 6 + index * 6)[0]))
        numeric_record_counts['MULRK'] += 1
    elif code in (0x0201, 0x00be):
        row = unpack_from('<H', payload, 0)[0]
        assert row < 2, 'Blank encountered in numeric data rectangle'
    else:
        assert code in metadata_codes, f'Unsupported worksheet BIFF record 0x{code:04x}'

assert dimensions is not None
assert tuple(headers[1].get(column) for column in range(25)) == SOURCE_COLUMNS
assert tuple(headers[0].get(column) for column in range(1, 25)) == (
    *(f'X{column}' for column in range(1, 24)), 'Y'
)
assert numeric_cell_count == 30_000 * 25, 'Incorrect numeric cell count'
assert all(all(value is not None for value in row) for row in cells), 'Missing data cell'
assert sha256(source.read_bytes()).hexdigest() == source_hash, 'Source bytes changed during inspection'
assert source.stat().st_mtime_ns == source_stat.st_mtime_ns, 'Source modification time changed'

output_directory = Path('data/processed')
output_directory.mkdir(parents=True, exist_ok=True)
output = output_directory / 'inspection_records.jsonl'
output_digest = sha256()
with output.open('w', encoding='utf-8', newline='\n') as handle:
    for row in cells:
        record = dict(zip(NORMALIZED_COLUMNS, row, strict=True))
        line = json.dumps(record, separators=(',', ':'), allow_nan=False) + '\n'
        output_digest.update(line.encode())
        handle.write(line)

metadata = {
    'purpose': 'Independent bounded numeric BIFF8 diagnostic; canonical xlrd parity pending',
    'source_path': str(source),
    'source_sha256': source_hash,
    'source_bytes': len(raw),
    'workbook_stream_bytes': len(workbook),
    'source_bytes_and_mtime_preserved': True,
    'inspection_utc': datetime.now(timezone.utc).isoformat(),
    'first_outcome_decoding_utc': first_outcome_decoding_utc,
    'script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
    'ole_sector_bytes': sector_size,
    'sheet_names': [name for name, _ in sheets],
    'sheet_dimensions': {'first_row': 0, 'exclusive_last_row': 30_002, 'first_column': 0, 'exclusive_last_column': 25},
    'header_row_index': 1,
    'headers': list(SOURCE_COLUMNS),
    'data_rows': 30_000,
    'data_columns': 25,
    'numeric_cells': numeric_cell_count,
    'numeric_record_counts': dict(numeric_record_counts),
    'worksheet_record_counts': dict(sorted(sheet_record_counts.items())),
    'strict_no_missing_duplicate_formula_text_or_error_data_cells': True,
    'records_path': str(output),
    'records_sha256': output_digest.hexdigest(),
    'outcome_distributions_computed': False,
    'canonical_xlrd_crosscheck': 'pending dependency availability',
}
(output_directory / 'inspection_metadata.json').write_text(
    json.dumps(metadata, indent=2) + '\n', encoding='utf-8'
)
print(json.dumps({
    'rows': metadata['data_rows'], 'numeric_cells': numeric_cell_count,
    'first_outcome_decoding_utc': first_outcome_decoding_utc,
    'source_sha256': source_hash, 'records_sha256': output_digest.hexdigest(),
    'strict_cells_validated': True, 'canonical_xlrd_crosscheck': metadata['canonical_xlrd_crosscheck'],
}))
