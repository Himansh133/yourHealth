"""Prepare/import one public, de-identified MIMIC-IV demo subject. Raw data stays local.

Run from the repository root with PYTHONPATH=backend. Downloads must already be
in --source (the five official hosp/*.csv.gz tables). --load creates a NEW
account, records credentials in ignored passwords.md, and runs real ingestion.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
import secrets
import textwrap
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "eval/data/internet-demo/mimic-iv-demo-2.2"
SOURCE_URL = "https://physionet.org/content/mimic-iv-demo/2.2/"
TABLES = ("patients", "admissions", "d_labitems", "labevents", "prescriptions")


def write_json(path: Path, data: dict) -> None:
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2))
    os.replace(temporary, path)


def load_subject(root: Path, subject: str) -> dict:
    data = {"subject_id": subject, "allergy_status": "unknown", "allergies": []}
    for table in TABLES:
        with gzip.open(root / "hosp" / f"{table}.csv.gz", "rt", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if table == "d_labitems":
            data["items"] = {r["itemid"]: r for r in rows}
        else:
            data[{"patients": "patient", "labevents": "labs"}.get(table, table)] = [r for r in rows if r["subject_id"] == subject]
    if len(data["patient"]) != 1 or not data["labs"]:
        raise ValueError("Subject must occur once in patients and have lab records in the public demo")
    return data


def shift_timestamp(value: str, offset: timedelta) -> str:
    return (datetime.fromisoformat(value) + offset).isoformat(sep=" ")


def clean(value: str) -> str:
    return " ".join(str(value or "").split())


def lab_lines(row: dict, item: dict) -> list[str]:
    from app.services.labs.dictionary import get_lab_dictionary
    label, fluid = clean(item["label"]), clean(item.get("fluid", "Unknown"))
    value, unit = clean(row.get("value", "")), clean(row.get("valueuom", ""))
    low, high = clean(row.get("ref_range_lower", "")), clean(row.get("ref_range_upper", ""))
    match = get_lab_dictionary().match(label)
    # Non-blood specimens must never become serum trend values through name matching.
    if fluid == "Blood" and match and match.score == 100 and row.get("valuenum"):
        reference = f"{low}-{high}" if low and high else f"> {low}" if low else f"< {high}" if high else ""
        lines = [" ".join(v for v in (match.test.canonical_name, value, unit, reference) if v)]
        lines.append(f"Source test: {label}; specimen: {fluid}; event id: {row.get('labevent_id', '')}.")
        return lines
    # End with prose so unsupported specimen/test rows remain searchable source facts, not guessed chart values.
    return [f"Recorded result: {value} {unit}; specimen: {fluid}; test: {label}; reference bounds: {low or 'not supplied'} to {high or 'not supplied'}; source event {row.get('labevent_id', '')}."]


def render_pdf(path: Path, lines: list[str]) -> None:
    wrapped = [part for line in lines for part in (textwrap.wrap(clean(line), width=100, break_long_words=False) or [""])]
    with pymupdf.open() as doc:
        for start in range(0, len(wrapped), 57):
            page = doc.new_page()
            page.insert_text((40, 40), "\n".join(wrapped[start:start + 57]), fontname="cour", fontsize=8, lineheight=1.55)
        doc.set_metadata({"title": "Reconstructed de-identified MIMIC-IV demo data", "subject": "Public ODbL dataset export; not an original hospital document"})
        doc.save(path, garbage=4, deflate=True, no_new_id=True)


def prepare(root: Path, subject: str, display_end: date) -> dict:
    data = load_subject(root, subject)
    timestamps = [r["charttime"] for r in data["labs"] if r.get("charttime")]
    timestamps += [r[k] for r in data["prescriptions"] for k in ("starttime", "stoptime") if r.get(k)]
    offset = display_end - max(datetime.fromisoformat(t).date() for t in timestamps)
    target = root / f"subject-{subject}"
    target.mkdir(exist_ok=True)
    old_manifest_path = target / 'manifest.json'
    if (target / 'import-state.json').exists() and old_manifest_path.exists():
        frozen = json.loads(old_manifest_path.read_text())
        if frozen['date_offset_days'] != offset.days:
            raise ValueError('Cannot change the date offset of an import that has already started')
        source_hashes = {table: hashlib.sha256((root / 'hosp' / f'{table}.csv.gz').read_bytes()).hexdigest() for table in TABLES}
        if frozen.get('source_tables_sha256', source_hashes) != source_hashes:
            raise ValueError('Source tables changed after import started')
    header = ["RECONSTRUCTED DE-IDENTIFIED DATA - NOT AN ORIGINAL HOSPITAL SCAN", "Source: MIMIC-IV Clinical Database Demo 2.2 (PhysioNet); ODbL 1.0.", f"Dataset: {SOURCE_URL}", f"Single source subject: {subject}. Dates rebased by {offset.days} days for this local demo.", "Source values, units and original de-identified timestamps are preserved."]
    packets = []
    groups = defaultdict(list)
    for row in data["labs"]:
        if row.get("charttime"):
            groups[row["charttime"]].append(row)
    for index, (timestamp, rows) in enumerate(sorted(groups.items()), 1):
        display = shift_timestamp(timestamp, offset)
        filename = f"lab-{index:04d}-{display[:10]}.pdf"
        lines = header + [f"Report Date: {display[:10]}", f"Source timestamp: {timestamp}", "LABORATORY DATA EXPORT - reference ranges only where present in source", ""]
        for row in rows:
            lines.extend(lab_lines(row, data["items"].get(row["itemid"], {"label": f"Unmapped item {row['itemid']}"})))
        render_pdf(target / filename, lines)
        packets.append({"file": filename, "kind": "lab", "source_timestamp": timestamp, "display_date": display[:10], "source_rows": len(rows)})
    prescriptions = data["prescriptions"]
    for start in range(0, len(prescriptions), 60):
        batch = prescriptions[start:start + 60]
        filename = f"prescription-history-{start // 60 + 1:03d}.pdf"
        lines = header + [f"Report Date: {display_end.isoformat()}", "HISTORICAL PRESCRIPTION ORDER DATA - NOT A CURRENT MEDICINE LIST", "Orders do not establish that a medicine was taken, is still used, or caused a result.", ""]
        for i, row in enumerate(batch, start + 1):
            lines += [f"Order {i}: {clean(row['drug'])}.", f"Recorded strength: {clean(row.get('prod_strength')) or 'not supplied'}; dose: {clean(row.get('dose_val_rx'))} {clean(row.get('dose_unit_rx'))}; route: {clean(row.get('route'))}.", f"Original source start: {row.get('starttime')}; stop: {row.get('stoptime')}.", f"Demo display start: {shift_timestamp(row['starttime'], offset) if row.get('starttime') else 'not supplied'}; stop: {shift_timestamp(row['stoptime'], offset) if row.get('stoptime') else 'not supplied'}.", ""]
        render_pdf(target / filename, lines)
        packets.append({"file": filename, "kind": "prescriptions", "display_date": display_end.isoformat(), "order_from": start, "order_to": start + len(batch)})
    filename = "source-history-summary.pdf"
    lines = header + [f"Report Date: {display_end.isoformat()}", "SOURCE HISTORY SUMMARY FOR REVIEW - NOT A TREATING DOCTOR NOTE", f"Available laboratory timestamps: {len(groups)}; source lab rows: {len(data['labs'])}.", f"Historical prescription orders: {len(prescriptions)}; admissions: {len(data['admissions'])}.", "Allergy information is not provided by this public dataset. Status remains unknown.", "Free-text clinician narratives are excluded from the public demo dataset.", "No allergy, medication adherence or current treatment is inferred by this import.", "The app's Doctor sheet is a computed summary of these released historical facts.", "", "Recorded admission history:"]
    lines += [f"Admission {r['hadm_id']}: source admitted {r.get('admittime')}; discharged {r.get('dischtime')}; type {r.get('admission_type')} ." for r in data['admissions']]
    render_pdf(target / filename, lines)
    packets.append({"file": filename, "kind": "summary", "display_date": display_end.isoformat()})
    manifest = {"source": SOURCE_URL, "citation": "Johnson et al. (2023), MIMIC-IV Clinical Database Demo 2.2, doi:10.13026/dp1f-ex47", "license": "Open Data Commons Open Database License 1.0", "subject_id": subject, "date_offset_days": offset.days, "display_end": display_end.isoformat(), "source_tables_sha256": {table: hashlib.sha256((root / "hosp" / f"{table}.csv.gz").read_bytes()).hexdigest() for table in TABLES}, "allergy_status": "unknown", "free_text_doctor_notes": "not available in public source", "documents": packets, "lab_rows": len(data['labs']), "prescription_orders": len(prescriptions)}
    for packet in packets:
        packet['sha256'] = hashlib.sha256((target / packet['file']).read_bytes()).hexdigest()
    write_json(target / "manifest.json", manifest)
    return manifest


def load_local(root: Path, manifest: dict) -> dict:
    from sqlalchemy import select
    from app.core.security import hash_password
    from app.db.models import Document, DrugIngredient, Profile, ProfileAllergyStatus, ProfileMedicine, ProfileMember, User
    from app.db.session import SessionLocal
    from app.services.medicines.store import set_ingredients
    from app.services.storage import get_storage
    from app.services.uploads import store_upload
    from app.workers.process_document import run
    from app.services.sheet import build_sheet

    target = root / f"subject-{manifest['subject_id']}"
    state_path = target / 'import-state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    storage = get_storage()
    offset = timedelta(days=manifest['date_offset_days'])
    data = load_subject(root, manifest['subject_id'])
    fingerprint = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    if state.get("manifest_sha256", fingerprint) != fingerprint:
        raise ValueError("Prepared manifest differs from the frozen import identity")
    with SessionLocal() as db:
        if not state:
            email = f"demo.mimic.{uuid.uuid4().hex[:10]}@example.com"
            password = secrets.token_urlsafe(24)
            user = User(email=email, password_hash=hash_password(password))
            db.add(user)
            db.flush()
            profile = Profile(display_name=f"Demo - MIMIC {manifest['subject_id']}", sex={'M': 'male', 'F': 'female'}.get(data['patient'][0].get('gender'), 'unknown'))
            db.add(profile)
            db.flush()
            db.add(ProfileMember(profile_id=profile.id, user_id=user.id, role='owner', relation_label='De-identified demo data'))
            db.add(ProfileAllergyStatus(profile_id=profile.id, status='unknown'))
            db.commit()
            state = {'email': email, 'user_id': str(user.id), 'profile_id': str(profile.id), 'subject_id': manifest['subject_id'], 'documents': {}, 'medicines_imported': False}
            credential_path = ROOT / 'passwords.md'
            fd = os.open(credential_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, 'a') as stream:
                stream.write(f"\n\n## De-identified MIMIC demo ({date.today().isoformat()})\n\n- Login email: `{email}`\n- Password: `{password}`\n- Profile ID: `{profile.id}`\n- Profile URL: `http://localhost:5173/profiles/{profile.id}`\n- Source subject: `{manifest['subject_id']}` (MIMIC-IV demo 2.2; public de-identified data)\n- Data manifest: `{target.relative_to(ROOT)}/manifest.json`\n- Allergy history and original doctor notes: not provided by the source.\n- PDFs are reconstructed data exports; source dates are consistently rebased for demonstration.\n")
            write_json(state_path, state)
        pid, uid = uuid.UUID(state['profile_id']), uuid.UUID(state['user_id'])
        member = db.get(ProfileMember, (pid, uid))
        profile = db.get(Profile, pid)
        if member is None or member.role != 'owner' or member.relation_label != 'De-identified demo data' or not profile or profile.display_name != f"Demo - MIMIC {manifest['subject_id']}" or db.get(User, uid).email != state['email']:
            raise ValueError('Existing import state does not belong to the expected dedicated account')

        packet_hashes = {p['file']: p['sha256'] for p in manifest['documents']}
        for filename, did in state['documents'].items():
            existing = db.get(Document, uuid.UUID(did))
            if not existing or existing.profile_id != pid or existing.sha256 != packet_hashes.get(filename):
                raise ValueError('Previously imported document no longer matches the source manifest')
        state['manifest_sha256'] = fingerprint
        state['date_offset_days'] = manifest['date_offset_days']
        write_json(state_path, state)

        class ImmediateQueue:
            def enqueue_document(self, did):
                run(db, storage, did)

        for i, packet in enumerate(manifest['documents'], 1):
            content = (target / packet['file']).read_bytes()
            if hashlib.sha256(content).hexdigest() != packet['sha256']:
                raise ValueError('Prepared file hash no longer matches manifest')
            document, created = store_upload(db, storage, ImmediateQueue(), pid, uid, content, packet['file'], 'web')
            if not created and document.status not in ('done', 'needs_review'):
                run(db, storage, document.id)
            if document.status not in ('done', 'needs_review'):
                raise RuntimeError(f"Import failed for {packet['file']}: {document.error_code or document.status}")
            state['documents'][packet['file']] = str(document.id)
            write_json(state_path, state)
            if i % 20 == 0 or i == len(manifest['documents']):
                print(f"Processed {i}/{len(manifest['documents'])} documents", flush=True)
        if not state['medicines_imported']:
            ingredients = {i.name.casefold(): i.id for i in db.scalars(select(DrugIngredient))}
            for index, row in enumerate(data['prescriptions']):
                packet = next(p for p in manifest['documents'] if p['kind'] == 'prescriptions' and p['order_from'] <= index < p['order_to'])
                mid = uuid.uuid5(pid, f"mimic:{manifest['subject_id']}:prescription:{index}")
                if db.get(ProfileMedicine, mid) is not None:
                    continue
                med = ProfileMedicine(id=mid, profile_id=pid, raw_text=clean(row['drug']), dose_text=clean(f"{row.get('dose_val_rx', '')} {row.get('dose_unit_rx', '')}; {row.get('route', '')}")[:50], started_on=date.fromisoformat(shift_timestamp(row['starttime'], offset)[:10]) if row.get('starttime') else None, stopped_on=date.fromisoformat(shift_timestamp(row['stoptime'], offset)[:10]) if row.get('stoptime') else None, source_document_id=uuid.UUID(state['documents'][packet['file']]), confirmed_by_user=False)
                db.add(med)
                db.flush()
                iid = ingredients.get(clean(row['drug']).casefold())
                if iid:
                    set_ingredients(db, med, [iid])
            db.commit()
            state['medicines_imported'] = True
            write_json(state_path, state)
        first = min(p['display_date'] for p in manifest['documents'])
        sheet = build_sheet(db, pid, date.fromisoformat(first), date.today(), True)
        (target / 'doctor-sheet.json').write_text(sheet.model_dump_json(indent=2))
        state['status'] = 'complete'
        write_json(state_path, state)
        print(json.dumps({'status': state['status'], 'profile_id': state['profile_id'], 'email': state['email'], 'documents': len(state['documents']), 'prescription_orders': len(data['prescriptions']), 'credentials_file': 'passwords.md'}), flush=True)
    return state


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--subject', default='10035631')
    parser.add_argument('--display-end', type=date.fromisoformat)
    parser.add_argument('--load', action='store_true', help='Create/resume a dedicated local demo account and import')
    args = parser.parse_args()
    display_end = args.display_end
    previous = args.source / f'subject-{args.subject}' / 'manifest.json'
    if display_end is None and previous.exists() and previous.with_name('import-state.json').exists():
        saved = json.loads(previous.read_text())
        display_end = date.fromisoformat(saved.get('display_end') or max(p['display_date'] for p in saved['documents']))
    manifest = prepare(args.source, args.subject, display_end or date.today() - timedelta(days=7))
    print(f"Prepared {len(manifest['documents'])} documents from one source subject", flush=True)
    if args.load:
        load_local(args.source, manifest)
