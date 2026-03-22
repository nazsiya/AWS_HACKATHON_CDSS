"""
Drug interaction checker for CDSS (Req 9 – drug interaction → alert).

Checks a new medication against a patient's existing medications using a
rule-based approach. When an interaction is detected, calls the alert engine
to notify the prescriber/pharmacist.

Per CDSS.mdc: safety-critical — flag for senior review.
Per bedrock-agents.mdc: encode safety policies in tools, not only prompts.
Per project-conventions.mdc: doctor-in-the-loop; never auto-update EMR.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Known drug interaction pairs (lowercase). Expand with clinical protocols MCP.
KNOWN_INTERACTIONS: List[tuple[str, str, str]] = [
    ("warfarin", "aspirin", "Increased bleeding risk — monitor INR closely"),
    ("warfarin", "ibuprofen", "Increased bleeding risk — avoid combination if possible"),
    ("metformin", "contrast dye", "Risk of lactic acidosis — hold metformin 48h before/after"),
    ("lisinopril", "potassium", "Risk of hyperkalemia — monitor serum potassium"),
    ("simvastatin", "amiodarone", "Increased risk of myopathy/rhabdomyolysis — use lower statin dose"),
    ("ciprofloxacin", "theophylline", "Increased theophylline levels — monitor and adjust dose"),
    ("methotrexate", "trimethoprim", "Increased methotrexate toxicity — avoid combination"),
    ("digoxin", "amiodarone", "Increased digoxin levels — reduce digoxin dose by 50%"),
    ("clopidogrel", "omeprazole", "Reduced clopidogrel efficacy — use pantoprazole instead"),
    ("ssri", "tramadol", "Serotonin syndrome risk — use with extreme caution"),
    ("fluoxetine", "tramadol", "Serotonin syndrome risk — avoid combination"),
    ("lithium", "ibuprofen", "Increased lithium levels — monitor serum lithium"),
    ("lithium", "diclofenac", "Increased lithium levels — monitor serum lithium"),
]


def check_drug_interactions(
    patient_id: str,
    new_drug_name: str,
    existing_medications: List[str] | None = None,
) -> Dict[str, Any]:
    """
    Check a new medication against a patient's existing medications.

    Args:
        patient_id: Patient identifier
        new_drug_name: Name of the medication being prescribed
        existing_medications: List of current drug names; if None, fetched from DB

    Returns:
        dict with interactions found and alert_ids if any were emitted
    """
    new_drug = new_drug_name.lower().strip()
    if not new_drug:
        return {"interactions": [], "alert_ids": []}

    # Get existing medications if not provided
    if existing_medications is None:
        existing_medications = _fetch_patient_medications(patient_id)

    existing_lower = [m.lower().strip() for m in existing_medications]
    interactions = []

    for drug_a, drug_b, warning in KNOWN_INTERACTIONS:
        if new_drug in drug_a or drug_a in new_drug:
            for existing in existing_lower:
                if drug_b in existing or existing in drug_b:
                    interactions.append({
                        "new_drug": new_drug_name,
                        "existing_drug": existing,
                        "warning": warning,
                        "pair": f"{drug_a} + {drug_b}",
                    })
        elif new_drug in drug_b or drug_b in new_drug:
            for existing in existing_lower:
                if drug_a in existing or existing in drug_a:
                    interactions.append({
                        "new_drug": new_drug_name,
                        "existing_drug": existing,
                        "warning": warning,
                        "pair": f"{drug_a} + {drug_b}",
                    })

    alert_ids = []
    if interactions:
        try:
            from cdss.services.alerts import emit_alert

            for interaction in interactions:
                result = emit_alert(
                    severity="high",
                    alert_type="drug_interaction",
                    channel="pharmacist",
                    patient_id=patient_id,
                    message=f"Drug interaction detected: {interaction['warning']}",
                    context=interaction,
                )
                alert_ids.append(result.get("alert_id", ""))
        except Exception as e:
            logger.warning("Drug interaction alert emission failed: %s", e)

    return {
        "interactions": interactions,
        "alert_ids": alert_ids,
        "interaction_count": len(interactions),
    }


def _fetch_patient_medications(patient_id: str) -> List[str]:
    """Fetch current medication names for a patient from DB."""
    try:
        from cdss.db.session import get_session
        from cdss.db.models import Medication

        with get_session() as session:
            meds = (
                session.query(Medication.medication_name)
                .filter(Medication.patient_id == patient_id, Medication.status == "active")
                .all()
            )
            return [m[0] for m in meds if m[0]]
    except Exception as e:
        logger.warning("Cannot fetch medications for interaction check: %s", e)
        return []
