from pathlib import Path
import csv,io
import pytest

from eval.runners.import_original_source import subset_csv_bytes, source_lab_row


def test_subset_preserves_original_record_bytes_and_quoted_newlines():
    data=b'subject_id,value,comment\r\n1,2.10,"first\r\nsecond"\r\n2,9.9,other\r\n1,3.00,"quoted ""word"""\r\n'
    result=subset_csv_bytes(data,'1')
    assert result==b'subject_id,value,comment\r\n1,2.10,"first\r\nsecond"\r\n1,3.00,"quoted ""word"""\r\n'
    assert [r['subject_id'] for r in csv.DictReader(io.StringIO(result.decode()))]==['1','1']


def test_source_lab_values_units_and_original_dates_are_not_rewritten():
    row={'value':'2.10','valueuom':'mg/dL','ref_range_lower':'0.5','ref_range_upper':'1.2','charttime':'2159-08-03 10:30:00','labevent_id':'42'}
    fields=source_lab_row(row,{'label':'Creatinine','fluid':'Blood'})
    assert fields['raw_value']=='2.10' and fields['raw_unit']=='mg/dL'
    assert fields['observed_on'].isoformat()=='2159-08-03'
    assert fields['page_no'] is None
    assert fields['canonical_loinc']=='2160-0'
    urine=source_lab_row(row,{'label':'Creatinine','fluid':'Urine'})
    assert urine['canonical_loinc'] is None and urine['value_canonical'] is None


def test_subset_requires_a_patient_column_and_matching_records():
    with pytest.raises(ValueError):subset_csv_bytes(b'value\n1\n','1')
    with pytest.raises(ValueError):subset_csv_bytes(b'subject_id,value\n2,1\n','1')


def test_patient_filter_does_not_treat_field_control_characters_as_record_boundaries():
    data = b'subject_id,value\r\n2,"other\x0bpatient"\r\n1,target\r\n'
    assert subset_csv_bytes(data, '1') == b'subject_id,value\r\n1,target\r\n'
