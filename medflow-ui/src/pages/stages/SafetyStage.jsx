// src/pages/stages/SafetyStage.jsx
import { useEffect, useMemo, useState } from "react";
import "../../styles/safetyStage.css";
import { runSafetyCheck, submitSafetyDecision } from "../../services/api";

export default function SafetyStage({ activePatient, onBack, onComplete }) {
  const patientId = activePatient?.id;

  // Pull draft order from localStorage (TreatmentStage stores mf_rx_{patientId})
  const rxKey = useMemo(() => (patientId ? `mf_rx_${patientId}` : null), [patientId]);
  const overrideKey = useMemo(() => (patientId ? `mf_safety_${patientId}` : null), [patientId]);

  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const [checkResult, setCheckResult] = useState(null);

  // Modal / decision state
  const [showModal, setShowModal] = useState(false);
  const [overrideNote, setOverrideNote] = useState("");
  const [selectedSuggestion, setSelectedSuggestion] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const draftOrder = useMemo(() => {
    if (!rxKey) return null;
    const raw = localStorage.getItem(rxKey);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      // payload structure from TreatmentStage: { patientId, drafted, order:{meds, notes}}
      return parsed?.order || null;
    } catch {
      return null;
    }
  }, [rxKey]);

  useEffect(() => {
    if (!patientId) return;

    // If previous override decision exists locally, prefill
    const ov = overrideKey ? localStorage.getItem(overrideKey) : null;
    if (ov) {
      try {
        const parsed = JSON.parse(ov);
        setOverrideNote(parsed.overrideNote || "");
        setSelectedSuggestion(parsed.selectedSuggestion || "");
      } catch {
        // ignore
      }
    }

    if (!draftOrder) {
      setErr("No drafted order found. Go back to Treatment Planning and draft an order first.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setErr("");

    const payload = {
      patientId,
      patientAllergies: activePatient?.allergies || [],
      patientMeds: activePatient?.meds || [],
      order: draftOrder,
    };

    runSafetyCheck(payload)
      .then((data) => {
        setCheckResult(data);

        // If blocked -> show modal immediately
        if (data?.status === "blocked") setShowModal(true);
        else setShowModal(false);
      })
      .catch((e) => setErr(e?.message || "Safety check failed"))
      .finally(() => setLoading(false));
  }, [patientId, activePatient, draftOrder, overrideKey]);

  const rules = checkResult?.rules || { require_override_note: true };

  async function handleAbortEdit() {
    if (!patientId) return;
    setErr("");
    setSubmitting(true);

    try {
      await submitSafetyDecision({
        patientId,
        decision: "abort_edit",
        overrideNote: "",
        selectedSuggestion: "",
      });

      // Clear local override + go back to Treatment stage
      if (overrideKey) localStorage.removeItem(overrideKey);
      onBack?.();
    } catch (e) {
      setErr(e?.message || "Failed to submit decision");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleOverrideProceed() {
    if (!patientId) return;
    setErr("");

    if (rules?.require_override_note && !overrideNote.trim()) {
      setErr("Override note is required to proceed.");
      return;
    }

    setSubmitting(true);
    try {
      await submitSafetyDecision({
        patientId,
        decision: "override",
        overrideNote,
        selectedSuggestion,
      });

      // Persist local override decision for refresh convenience (demo)
      if (overrideKey) {
        localStorage.setItem(
          overrideKey,
          JSON.stringify({ decision: "override", overrideNote, selectedSuggestion })
        );
      }

      setShowModal(false);
      onComplete?.(); // continue / finish workflow
    } catch (e) {
      setErr(e?.message || "Failed to submit override");
    } finally {
      setSubmitting(false);
    }
  }

  if (!patientId) {
    return (
      <div className="mf-card">
        <h3>Safety Guardrail</h3>
        <p>No active patient. Complete earlier stages first.</p>
      </div>
    );
  }

  return (
    <div className="mf-safety-wrap">
      <div className="mf-card">
        <div className="mf-row mf-between">
          <h3>Safety Guardrail</h3>
          <span className={`mf-badge ${checkResult?.status === "blocked" ? "mf-badge-danger" : "mf-badge-ok"}`}>
            {checkResult?.status ? checkResult.status.toUpperCase() : "—"}
          </span>
        </div>

        <div className="mf-muted mf-mt8">
          This stage runs an automatic safety check against the drafted order (Phase 7) and the patient profile.
        </div>

        {loading && <p className="mf-muted mf-mt12">Running safety check…</p>}
        {err && <div className="mf-alert mf-alert-danger mf-mt12">{err}</div>}

        {!loading && checkResult && (
          <>
            <div className="mf-mt12">
              <div className="mf-card-title">Drafted Order</div>
              <div className="mf-order-box">
                {(draftOrder?.meds || []).length > 0 ? (
                  <ul className="mf-ul">
                    {draftOrder.meds.map((m, i) => (
                      <li key={i}>
                        <b>{m.drug}</b> — {m.dose} / {m.route} / {m.frequency} / {m.duration}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="mf-muted">—</div>
                )}
                {draftOrder?.notes ? (
                  <div className="mf-muted mf-mt8">
                    <b>Notes:</b> {draftOrder.notes}
                  </div>
                ) : null}
              </div>
            </div>

            <div className="mf-mt12">
              <div className="mf-card-title">Safety Findings</div>

              {checkResult.alerts?.length ? (
                <div className="mf-alert-list">
                  {checkResult.alerts.map((a, idx) => (
                    <div key={idx} className={`mf-alert-item mf-sev-${a.severity || "medium"}`}>
                      <div className="mf-row mf-between">
                        <div className="mf-alert-title">
                          {a.type} • {a.severity?.toUpperCase() || "MEDIUM"}
                        </div>
                        <div className="mf-muted">
                          {a.drugA} ↔ {a.drugB}
                        </div>
                      </div>
                      <div className="mf-mt8">{a.message}</div>

                      {(a.suggestions || []).length > 0 && (
                        <div className="mf-mt8">
                          <div className="mf-mini-label">Suggested edits</div>
                          <ul className="mf-ul">
                            {a.suggestions.map((s, j) => (
                              <li key={j}>{s}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mf-ok-box">
                  No conflicts detected. You can proceed.
                </div>
              )}
            </div>

            <div className="mf-row mf-between mf-mt12">
              <button className="mf-btn-ghost" onClick={onBack} type="button">
                Back to Treatment
              </button>

              {checkResult.status === "blocked" ? (
                <button className="mf-btn-danger" onClick={() => setShowModal(true)} type="button">
                  View Blocking Alert
                </button>
              ) : (
                <button className="mf-btn-primary" onClick={onComplete} type="button">
                  Complete Case
                </button>
              )}
            </div>
          </>
        )}
      </div>

      {/* RED ALERT MODAL */}
      {showModal && checkResult?.status === "blocked" && (
        <div className="mf-modal-overlay" role="dialog" aria-modal="true">
          <div className="mf-modal">
            <div className="mf-row mf-between">
              <div>
                <div className="mf-modal-title">⚠️ Safety Block</div>
                <div className="mf-muted mf-mt4">
                  A high-severity conflict was detected. Choose to edit the order or override with justification.
                </div>
              </div>
              <button className="mf-btn-ghost" onClick={() => setShowModal(false)} type="button">
                Close
              </button>
            </div>

            <div className="mf-modal-body mf-mt12">
              <div className="mf-mini-label">Top suggestions</div>
              <select
                className="mf-input"
                value={selectedSuggestion}
                onChange={(e) => setSelectedSuggestion(e.target.value)}
              >
                <option value="">(optional) select a suggested edit…</option>
                {checkResult.alerts.flatMap((a) => (a.suggestions || [])).map((s, i) => (
                  <option key={i} value={s}>{s}</option>
                ))}
              </select>

              <div className="mf-field mf-mt12">
                <div className="mf-label">
                  Override note {rules?.require_override_note ? <b>(required)</b> : "(optional)"}
                </div>
                <textarea
                  className="mf-textarea"
                  rows={5}
                  value={overrideNote}
                  onChange={(e) => setOverrideNote(e.target.value)}
                  placeholder="Explain why benefits outweigh risks; include monitoring/mitigation plan…"
                />
              </div>

              {err && <div className="mf-alert mf-alert-danger mf-mt12">{err}</div>}
            </div>

            <div className="mf-modal-actions mf-mt12">
              <button
                className="mf-btn-soft"
                onClick={handleAbortEdit}
                disabled={submitting}
                type="button"
                title="Return to Treatment stage to edit the order"
              >
                Abort/Edit (go back)
              </button>

              <button
                className="mf-btn-danger"
                onClick={handleOverrideProceed}
                disabled={submitting}
                type="button"
              >
                Override & Proceed
              </button>
            </div>

            <div className="mf-muted mf-small mf-mt8">
              Demo behavior: Abort/Edit returns to Treatment Planning. Override stores a justification note and completes the case.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}