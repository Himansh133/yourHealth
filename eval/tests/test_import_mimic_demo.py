import csv
import gzip
from datetime import date

import pymupdf

from eval.runners.import_mimic_demo import load_subject, lab_lines, render_pdf, shift_timestamp


def write_table(root, name, rows):
    path = root / 'hosp' / f'{name}.csv.gz'
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, 'wt', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_import_keeps_one_subject_and_does_not_invent_missing_allergies(tmp_path):
    write_table(tmp_path, 'patients', [{'subject_id': '1', 'gender': 'F'}, {'subject_id': '2', 'gender': 'M'}])
    write_table(tmp_path, 'd_labitems', [{'itemid': '10', 'label': 'Creatinine', 'fluid': 'Blood'}])
    write_table(tmp_path, 'labevents', [
        {'subject_id': '1', 'charttime': '2180-01-01 10:00:00', 'value': '1.25', 'itemid': '10'},
        {'subject_id': '2', 'charttime': '2180-01-01 10:00:00', 'value': '9.99', 'itemid': '10'},
    ])
    write_table(tmp_path, 'prescriptions', [{'subject_id': '1', 'drug': 'Metformin'}, {'subject_id': '2', 'drug': 'Other drug'}])
    write_table(tmp_path, 'admissions', [{'subject_id': '1', 'hadm_id': 'a'}, {'subject_id': '2', 'hadm_id': 'b'}])
    data = load_subject(tmp_path, '1')
    assert len(data['labs']) == 1 and data['labs'][0]['value'] == '1.25'
    assert [r['drug'] for r in data['prescriptions']] == ['Metformin']
    assert data['allergy_status'] == 'unknown'
    assert not data['allergies']


def test_specimen_and_source_measurements_are_preserved_without_serum_mapping_of_urine():
    from app.services.labs.row_parser import parse_line
    row = {'value': '1.25', 'valuenum': '1.25', 'valueuom': 'mg/dL', 'ref_range_lower': '0.7', 'ref_range_upper': '1.3', 'labevent_id': '42', 'itemid': '10'}
    blood = lab_lines(row, {'label': 'Creatinine', 'fluid': 'Blood'})
    assert any('Creatinine 1.25 mg/dL 0.7-1.3' in line for line in blood)
    urine = lab_lines(row, {'label': 'Creatinine', 'fluid': 'Urine'})
    assert any('Urine' in line and '1.25' in line for line in urine)
    assert not any(parse_line(line) for line in urine)
    missing_range = lab_lines({**row, 'ref_range_lower': '', 'ref_range_upper': ''}, {'label': 'Creatinine', 'fluid': 'Blood'})
    assert not any('0.7-1.3' in line for line in missing_range)


def test_dates_shift_consistently_and_export_has_provenance(tmp_path):
    shift = date(2026, 11, 17) - date(2180, 1, 1)
    assert shift_timestamp('2180-01-01 10:30:00', shift) == '2026-11-17 10:30:00'
    path = tmp_path / 'report.pdf'
    render_pdf(path, ['RECONSTRUCTED DE-IDENTIFIED DATA', 'Source: MIMIC-IV Demo 2.2', 'Source timestamp: 2180-01-01 10:30:00', 'Report Date: 2026-11-17', 'Creatinine 1.25 mg/dL 0.7-1.3'])
    with pymupdf.open(path) as doc:
        text = ''.join(p.get_text() for p in doc)
    assert 'RECONSTRUCTED' in text and '2180-01-01 10:30:00' in text and '1.25' in text
