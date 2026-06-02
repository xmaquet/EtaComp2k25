"""Issue #12 — export PDF sans TODO et tableau métrologique."""



import json

from datetime import datetime

from pathlib import Path



from pypdf import PdfReader



from src.etacomp.config.export_config import ExportConfig

from src.etacomp.core.calculation_engine import CalculatedResults

from src.etacomp.io.pdf_exporter import export_pdf, _metrology_table_rows

from src.etacomp.models.session import Session, MeasureSeries

from src.etacomp.rules.tolerance_engine import ToleranceRuleEngine

from src.etacomp.rules.verdict import VerdictStatus, evaluate_tolerances





def _pdf_text(path: Path) -> str:

    reader = PdfReader(str(path))

    return "\n".join(page.extract_text() or "" for page in reader.pages)





def _export_config() -> ExportConfig:

    return ExportConfig(

        entite="Test Entity",

        document_title="Rapport de verification",

        document_reference="REF-TEST",

        texte_normes="ISO 6789",

    )





def _runtime_session():

    return Session(

        operator="Operateur Test",

        date=datetime(2025, 6, 2, 10, 30, 0),

        temperature_c=20.0,

        humidity_pct=50.0,

        comparator_ref="TEST-PDF",

        series_count=2,

        measures_per_series=3,

        series=[MeasureSeries(target=0.0, readings=[0.01, -0.01, 0.02, -0.02])],

        observations="Observation test",

    )





def _results(**overrides) -> CalculatedResults:

    base = dict(

        total_error_mm=0.010,

        total_error_location={"target_mm": 0.0, "direction": "up", "error_mm": 0.01},

        local_error_mm=0.008,

        local_error_location={},

        hysteresis_max_mm=0.008,

        hysteresis_location={},

        fidelity_std_mm=0.002,

        fidelity_context=None,

        calibration_points=[

            {

                "target_mm": 0.0,

                "up_error_mm": 0.01,

                "down_error_mm": -0.01,

                "up_mean_mm": 0.01,

                "down_mean_mm": -0.01,

            }

        ],

    )

    base.update(overrides)

    return CalculatedResults(**base)





def _rules_path(tmp_path: Path) -> Path:

    data = {

        "normale": [

            {

                "graduation": 0.01,

                "course_min": 0.0,

                "course_max": 10.0,

                "Emt": 0.020,

                "Eml": 0.015,

                "Ef": 0.005,

                "Eh": 0.015,

            }

        ],

        "grande": [],

        "faible": [],

        "limitee": [],

    }

    p = tmp_path / "rules.json"

    p.write_text(json.dumps(data), encoding="utf-8")

    return p





def test_pdf_export_smoke(tmp_path: Path):

    rt = _runtime_session()

    results = _results()

    eng = ToleranceRuleEngine.load(_rules_path(tmp_path))

    verdict = evaluate_tolerances(

        {"range_type": "normale", "graduation": 0.01, "course": 2.0},

        results,

        eng,

    )

    assert verdict.status == VerdictStatus.CONFORME



    out = tmp_path / "rapport.pdf"

    path = export_pdf(rt, _export_config(), results, verdict, doc_no=1, output_path=out)



    text = _pdf_text(path)

    assert "TODO" not in text

    assert "Résultats métrologiques" in text or "Resultats metrologiques" in text

    assert "Critère" in text or "Critere" in text

    assert "Conforme" in text

    assert path.stat().st_size > 2000





def test_pdf_export_indeterminate_without_ef(tmp_path: Path):

    results = _results(fidelity_std_mm=None)

    eng = ToleranceRuleEngine.load(_rules_path(tmp_path))

    verdict = evaluate_tolerances(

        {"range_type": "normale", "graduation": 0.01, "course": 2.0},

        results,

        eng,

    )

    assert verdict.status == VerdictStatus.INDETERMINE

    assert "Ef" in verdict.limits

    assert "Ef" not in verdict.measured



    rows = _metrology_table_rows(results, verdict)

    ef_row = next(r for r in rows if "fidélité" in r[0] or "fidelite" in r[0].lower())

    assert ef_row[1] == "Indisponible"

    assert ef_row[4] == "Indisponible"



    path = export_pdf(

        _runtime_session(),

        _export_config(),

        results,

        verdict,

        doc_no=2,

        output_path=tmp_path / "indet.pdf",

    )

    text = _pdf_text(path)

    assert "TODO" not in text

    assert "Indisponible" in text





def test_pdf_export_non_conforme_shows_exceed(tmp_path: Path):

    results = _results(

        total_error_mm=0.050,

        local_error_mm=0.040,

        hysteresis_max_mm=0.030,

        fidelity_std_mm=0.020,

    )

    eng = ToleranceRuleEngine.load(_rules_path(tmp_path))

    verdict = evaluate_tolerances(

        {"range_type": "normale", "graduation": 0.01, "course": 2.0},

        results,

        eng,

    )

    assert verdict.status == VerdictStatus.NON_CONFORME

    assert verdict.exceed



    rows = _metrology_table_rows(results, verdict)

    assert any(r[4] == "Non conforme" and r[3] != "—" for r in rows)



    path = export_pdf(

        _runtime_session(),

        _export_config(),

        results,

        verdict,

        doc_no=3,

        output_path=tmp_path / "nc.pdf",

    )

    text = _pdf_text(path)

    assert "TODO" not in text

    assert "Non conforme" in text or "Non-conforme" in text

    assert "0.030000" in text





def test_pdf_export_no_verdict_still_has_table(tmp_path: Path):

    results = _results()

    rows = _metrology_table_rows(results, None)

    assert len(rows) == 4

    assert all(r[2] == "—" for r in rows)



    path = export_pdf(

        _runtime_session(),

        _export_config(),

        results,

        None,

        doc_no=4,

        output_path=tmp_path / "no_verdict.pdf",

    )

    text = _pdf_text(path)

    assert "TODO" not in text

    assert "Résultats métrologiques" in text or "Resultats metrologiques" in text

    assert "Erreur totale (Emt)" in text

    assert "Appareil : Indéterminé" in text or "Appareil : Indetermine" in text

