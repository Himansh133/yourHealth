from app.refdata.labels import first_sentence, pick_label, section_text, verify_effect


def label(set_id, substances, product_type="HUMAN PRESCRIPTION DRUG", effective="20250101", **sections):
    return {
        "set_id": set_id,
        "effective_time": effective,
        "openfda": {"substance_name": substances, "product_type": [product_type], "rxcui": ["123"]},
        **{k: [v] for k, v in sections.items()},
    }


# --- choosing a label ----------------------------------------------------------

def test_prefers_single_ingredient_prescription_label():
    combo = label("combo", ["METFORMIN HYDROCHLORIDE", "SITAGLIPTIN"])
    otc = label("otc", ["METFORMIN HYDROCHLORIDE"], product_type="HUMAN OTC DRUG")
    single = label("single", ["METFORMIN HYDROCHLORIDE"])
    assert pick_label([combo, otc, single])["set_id"] == "single"


def test_newest_single_ingredient_label_wins():
    old = label("old", ["ALLOPURINOL"], effective="20190101")
    new = label("new", ["ALLOPURINOL"], effective="20240601")
    assert pick_label([old, new])["set_id"] == "new"


def test_falls_back_to_otc_single_ingredient_when_no_prescription_label():
    # e.g. acetaminophen, aspirin
    otc = label("otc", ["ACETAMINOPHEN"], product_type="HUMAN OTC DRUG")
    combo = label("combo", ["ACETAMINOPHEN", "CAFFEINE"])
    assert pick_label([combo, otc])["set_id"] == "otc"


def test_no_usable_label():
    assert pick_label([label("combo", ["A", "B"])]) is None
    assert pick_label([]) is None


# --- reading sections ----------------------------------------------------------

def test_section_text_joins_paragraphs_and_falls_back_from_warnings_and_cautions():
    lab = {"warnings": ["Liver: monitor ALT.", "Muscle: check CK."]}
    assert section_text(lab, "warnings_and_cautions") == "Liver: monitor ALT. Muscle: check CK."
    assert section_text(lab, "laboratory_tests") == ""


def test_first_sentence_strips_heading_numbers():
    text = "1 INDICATIONS AND USAGE Metformin is indicated as an adjunct to diet and exercise. Limitations of use: ..."
    assert first_sentence(text) == "Metformin is indicated as an adjunct to diet and exercise."


# --- verifying the curated medicine -> lab effects -----------------------------

def test_effect_verified_when_evidence_phrase_is_in_cited_section():
    lab = {"warnings_and_cautions": ["5.3 Vitamin B12 Deficiency: metformin may lower vitamin B 12 levels."]}
    assert verify_effect(lab, "warnings_and_cautions", "vitamin B12|vitamin B 12") is True


def test_effect_not_verified_when_phrase_only_in_another_section():
    lab = {"adverse_reactions": ["Vitamin B12 decreased"], "warnings_and_cautions": ["Lactic acidosis"]}
    assert verify_effect(lab, "warnings_and_cautions", "vitamin B12") is False


def test_evidence_match_is_case_and_space_insensitive():
    lab = {"warnings_and_cautions": ["Monitor   SERUM POTASSIUM periodically"]}
    assert verify_effect(lab, "warnings_and_cautions", "serum potassium") is True


def test_prefers_oral_label_over_injection():
    # pantoprazole: the newest Rx label was "for Injection", which lacks the long-term B12 warning
    iv = label("iv", ["PANTOPRAZOLE SODIUM"], effective="20260930")
    iv["openfda"]["route"] = ["INTRAVENOUS"]
    oral = label("oral", ["PANTOPRAZOLE SODIUM"], effective="20250101")
    oral["openfda"]["route"] = ["ORAL"]
    assert pick_label([iv, oral])["set_id"] == "oral"
