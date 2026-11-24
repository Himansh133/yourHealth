"""Trusted one-patient import of original MIMIC CSV rows. Creates no PDFs or shifted dates."""
import argparse
import csv
import hashlib
import io
import json
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from app.services.labs.dictionary import LabDictionary, get_lab_dictionary
from app.services.labs.normalize import normalize_row
from app.services.labs.row_parser import RawRow

ROOT = Path(__file__).resolve().parents[2]
UNKNOWN_TESTS = LabDictionary([], {}, {})
TABLES = ('patients', 'admissions', 'd_labitems', 'labevents', 'prescriptions')


def record_groups(data: bytes, subject: str, key: str | None = None) -> dict[str, bytes]:
    text = data.decode('utf-8')
    lines = io.StringIO(text, newline='').readlines()
    reader = csv.DictReader(io.StringIO(text, newline=''))
    if not reader.fieldnames or 'subject_id' not in reader.fieldnames:
        raise ValueError('Source CSV requires subject_id')
    end = reader.line_num
    header = ''.join(lines[:end])
    groups = defaultdict(list)
    for row in reader:
        start, end = end, reader.line_num
        if row['subject_id'] == subject:
            groups[row[key] if key else ''].append(''.join(lines[start:end]))
    if not groups:
        raise ValueError('No source records for this subject')
    return {name: (header + ''.join(records)).encode('utf-8') for name, records in groups.items()}


def subset_csv_bytes(data: bytes, subject: str) -> bytes:
    return record_groups(data, subject)['']


def source_lab_row(row: dict, item: dict) -> dict:
    label, fluid = item['label'], item.get('fluid', 'Unknown')
    match = get_lab_dictionary().match(label)
    supported = fluid == 'Blood' and match and match.score == 100
    low, high = row.get('ref_range_lower', ''), row.get('ref_range_upper', '')
    reference = f'{low}-{high}' if low and high else f'> {low}' if low else f'< {high}' if high else None
    raw = RawRow(label if fluid == 'Blood' else f'{label} [{fluid}]', row.get('value', ''), row.get('valueuom') or None, reference, None)
    normalized = normalize_row(raw, get_lab_dictionary() if supported else UNKNOWN_TESTS)
    fields = {key: getattr(normalized, key) for key in ('value_num', 'qualifier', 'range_low', 'range_high', 'value_canonical', 'range_low_canonical', 'range_high_canonical', 'flag')}
    fields.update(raw_name=raw.raw_name, raw_value=raw.raw_value, raw_unit=raw.raw_unit, raw_range=raw.raw_range,
                  printed_flag=None, extraction_confidence=normalized.confidence)
    fields.update(canonical_loinc=normalized.test.loinc_code if normalized.test else None,
                  observed_on=datetime.fromisoformat(row['charttime']).date(), page_no=None,
                  extraction_method='source_csv', verified_by_user=False)
    return fields


def prepare(source: Path, target: Path, subject: str) -> dict:
    if not subject.isdecimal():
        raise ValueError('MIMIC subject_id must be numeric')
    target.mkdir(parents=True, exist_ok=True)
    manifest = {'subject_id': subject, 'source': 'https://www.kaggle.com/datasets/montassarba/mimic-iv-clinical-database-demo-2-2',
                'upstream': 'https://physionet.org/content/mimic-iv-demo/2.2/', 'license': 'ODbL 1.0 upstream terms',
                'date_policy': 'Unchanged provider-deidentified dates', 'files': [], 'source_hashes': {}}
    for table in TABLES:
        data = (source / f'{table}.csv').read_bytes()
        manifest['source_hashes'][table] = hashlib.sha256(data).hexdigest()
        groups = {'': data} if table == 'd_labitems' else record_groups(data, subject, 'charttime' if table == 'labevents' else None)
        for index, (timestamp, content) in enumerate(sorted(groups.items()), 1):
            filename = f'labevents-{index:04d}-source.csv' if table == 'labevents' else f'{table}-source.csv'
            path = target / filename
            if path.exists() and path.read_bytes() != content:
                raise ValueError('Refusing to overwrite different source records')
            path.write_bytes(content)
            rows = list(csv.DictReader(io.StringIO(content.decode(), newline='')))
            manifest['files'].append({'file': filename, 'source_table': table, 'source_timestamp': timestamp or None,
                                      'rows': len(rows), 'sha256': hashlib.sha256(content).hexdigest(),
                                      'selection': 'Unchanged dictionary file' if table == 'd_labitems' else 'Original record bytes selected for one subject; no cell values rewritten'})
    (target / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


def save_state(path: Path, state: dict) -> None:
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, indent=2))
    temporary.replace(path)


def load_originals(source: Path, target: Path, subject: str, owner_email: str, *, switch_from: str | None = None) -> dict:
    from sqlalchemy import select, func
    from app.db.models import Chunk, Document, DocumentPage, DrugIngredient, LabResult, Profile, ProfileAllergyStatus, ProfileMedicine, ProfileMember, User
    from app.db.session import SessionLocal
    from app.services.chat.doc_search import index_document
    from app.services.labs.store import lab_test_ids
    from app.services.medicines.store import set_ingredients
    from app.services.storage import get_storage

    manifest = prepare(source, target, subject)
    fingerprint = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    state_path = target / 'import-state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else None
    if state and (state['manifest_sha256'] != fingerprint or state['owner_email'] != owner_email):
        raise ValueError('Import identity changed')
    storage = get_storage()
    items = {r['itemid']: r for r in csv.DictReader((source / 'd_labitems.csv').open())}
    with SessionLocal() as db:
        owner = db.scalar(select(User).where(User.email == owner_email))
        if not owner or owner.account_type != 'patient':
            raise ValueError('A known patient demo account is required')
        if switch_from:
            archived = db.get(Profile, uuid.UUID(switch_from))
            previous = db.get(ProfileMember, (uuid.UUID(switch_from), owner.id))
            already_switched = state and state.get('archived_profile_id') == switch_from and state.get('status') == 'complete'
            retained_seed = db.scalar(select(User.id).join(ProfileMember, ProfileMember.user_id == User.id).where(
                ProfileMember.profile_id == uuid.UUID(switch_from), ProfileMember.role == 'owner',
                ProfileMember.relation_label == 'De-identified demo data', User.id != owner.id,
                User.email.like('demo.mimic.%@example.com')))
            if owner_email != 'demo-check@example.com' or not retained_seed or not archived or archived.display_name != f'Demo - MIMIC {subject}' or (not previous and not already_switched) or (previous and (previous.role != 'owner' or previous.relation_label != 'De-identified demo data')):
                raise ValueError('Archive switch is limited to the known reconstructed demo')
        if state:
            pid = uuid.UUID(state['profile_id'])
            member = db.get(ProfileMember, (pid, owner.id))
            if not member or member.role != 'owner' or member.relation_label != 'Original source data':
                raise ValueError('Source profile ownership mismatch')
        else:
            profile = Profile(display_name=f'Original source - MIMIC {subject}')
            db.add(profile); db.flush(); pid = profile.id
            db.add(ProfileMember(profile_id=pid, user_id=owner.id, role='owner', relation_label='Original source data'))
            db.add(ProfileAllergyStatus(profile_id=pid, status='unknown'))
            db.commit()
            state = {'owner_email': owner_email, 'profile_id': str(pid), 'manifest_sha256': fingerprint, 'documents': {}}
            save_state(state_path, state)
        ids = lab_test_ids(db, get_lab_dictionary())
        ingredients = {i.name.casefold(): i.id for i in db.scalars(select(DrugIngredient))}
        for index, packet in enumerate(manifest['files'], 1):
            content = (target / packet['file']).read_bytes()
            rows = list(csv.DictReader(io.StringIO(content.decode(), newline='')))
            did = uuid.uuid5(pid, packet['file'])
            doc = db.get(Document, did)
            if doc:
                if doc.profile_id != pid or doc.sha256 != packet['sha256']:
                    raise ValueError('Stored source differs from manifest')
                state['documents'][packet['file']] = str(did)
                continue
            key = f'original-source/{pid}/{did}.csv'
            storage.put(key, content, 'text/csv')
            when = datetime.fromisoformat(packet['source_timestamp']).date() if packet['source_timestamp'] else None
            doc = Document(id=did, profile_id=pid, uploaded_by=owner.id, source_channel='web', original_filename=packet['file'],
                           storage_key=key, mime_type='text/csv', size_bytes=len(content), sha256=packet['sha256'],
                           doc_type='lab_report' if packet['source_table']=='labevents' else 'other', report_date=when, status='done')
            db.add(doc); db.flush()
            db.add(DocumentPage(document_id=did, page_no=1, method='source_csv', text=content.decode(), words_json=[], processor_version='original-csv-v1'))
            search = []
            if packet['source_table']=='labevents':
                for row in rows:
                    item = items[row['itemid']]
                    fields = source_lab_row(row, item)
                    code = fields.pop('canonical_loinc')
                    db.add(LabResult(profile_id=pid, document_id=did, lab_test_id=ids.get(code) if code else None, **fields))
                    search.append(f"Original source event {row['labevent_id']}: {item['label']}; specimen {item['fluid']}; value {row['value']} {row.get('valueuom','')}; source timestamp {row['charttime']}; source reference {row.get('ref_range_lower','')} to {row.get('ref_range_upper','')}.")
            elif packet['source_table']=='prescriptions':
                for order, row in enumerate(rows):
                    med = ProfileMedicine(id=uuid.uuid5(pid, f'prescription:{order}'), profile_id=pid, raw_text=row['drug'],
                                          dose_text=f"{row.get('dose_val_rx','')} {row.get('dose_unit_rx','')}; {row.get('route','')}",
                                          started_on=datetime.fromisoformat(row['starttime']).date() if row.get('starttime') else None,
                                          stopped_on=datetime.fromisoformat(row['stoptime']).date() if row.get('stoptime') else None,
                                          source_document_id=did, confirmed_by_user=False)
                    db.add(med); db.flush()
                    if row['drug'].casefold() in ingredients:
                        set_ingredients(db, med, [ingredients[row['drug'].casefold()]])
                    search.append(f"Historical prescription order {order+1}: {row['drug']}; original dose {row.get('dose_val_rx','')} {row.get('dose_unit_rx','')}; route {row.get('route','')}; source start {row.get('starttime','')}; source stop {row.get('stoptime','')}. This order does not establish current use or adherence.")
            else:
                search.append(content.decode())
            index_document(db, doc, [(1, '\n'.join(search))])
            db.commit()
            state['documents'][packet['file']] = str(did)
            save_state(state_path, state)
            if index % 40 == 0:
                print(f'Imported {index}/{len(manifest["files"])} original CSV sources', flush=True)
        count = db.scalar(select(func.count()).select_from(Document).where(Document.profile_id==pid))
        if count != len(manifest['files']):
            raise ValueError('Source file count mismatch; archive not switched')
        expected_labs = sum(p['rows'] for p in manifest['files'] if p['source_table'] == 'labevents')
        expected_meds = sum(p['rows'] for p in manifest['files'] if p['source_table'] == 'prescriptions')
        labs = db.scalar(select(func.count()).select_from(LabResult).where(LabResult.profile_id == pid))
        meds = db.scalar(select(func.count()).select_from(ProfileMedicine).where(ProfileMedicine.profile_id == pid))
        if (labs, meds) != (expected_labs, expected_meds):
            raise ValueError('Source row count mismatch; archive not switched')
        for packet in manifest['files']:
            doc = db.get(Document, uuid.uuid5(pid, packet['file']))
            if hashlib.sha256(storage.get(doc.storage_key)).hexdigest() != packet['sha256']:
                raise ValueError('Stored source bytes mismatch; archive not switched')
        state.update(status='complete', lab_rows=db.scalar(select(func.count()).select_from(LabResult).where(LabResult.profile_id==pid)),
                     prescriptions=db.scalar(select(func.count()).select_from(ProfileMedicine).where(ProfileMedicine.profile_id==pid)),
                     chunks=db.scalar(select(func.count()).select_from(Chunk).where(Chunk.profile_id==pid)))
        if switch_from:
            # Record intent before changing membership so a resumed import can finish safely.
            state['archived_profile_id'] = switch_from
            save_state(state_path, state)
            previous = db.get(ProfileMember, (uuid.UUID(switch_from), owner.id))
            if previous:
                db.delete(previous)
                db.commit()
        save_state(state_path, state)
        print(json.dumps(state | {'documents': len(state['documents'])}), flush=True)
        return state


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--target',type=Path,required=True)
    parser.add_argument('--subject',default='10035631')
    parser.add_argument('--owner-email',required=True)
    parser.add_argument('--switch-from')
    args=parser.parse_args()
    load_originals(args.source,args.target,args.subject,args.owner_email,switch_from=args.switch_from)
