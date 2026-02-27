import { useEffect, useMemo, useState } from "react";
import "../../styles/caseSummaryStage.css";
import { finalizeCaseSummary, getCaseSummary, getPrescriptionPdfUrl } from "../../services/api";

export default function CaseSummaryStage({ activePatient, onBack, onStartNewCase }) {
  const patientId = activePatient?.id;

  const dxKey = useMemo(() => (patientId ? `mf_dx_${patientId}` : null), [patientId]);
  const rxKey = useMemo(() => (patientId ? `mf_rx_${patientId}` : null), [patientId]);
  const safetyKey = useMemo(() => (patientId ? `mf_safety_${patientId}` : null), [patientId]);

  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  const [diagnosis, setDiagnosis] = useState(null);
  const [order, setOrder] = useState(null);
  const [safety, setSafety] = useState({ decision: "none", overrideNote: "", selectedSuggestion: "" });

  const [finalClinicianNote, setFinalClinicianNote] = useState("");
  const [savedRecord, setSavedRecord] = useState(null);
  const [saving, setSaving] = useState(false);

  const pdfUrl = useMemo(() => getPrescriptionPdfUrl(patientId), [patientId]);

  // Load from localStorage first (demo)
  useEffect(() => {
    if (!patientId) return;

    setLoading(true);
    setErr("");

    try {
      // Diagnosis
      const dxRaw = dxKey ? localStorage.getItem(dxKey) : null;
      const dx = dxRaw ? JSON.parse(dxRaw) : null;

      // Order
      const rxRaw = rxKey ? localStorage.getItem(rxKey) : null;
      const rxParsed = rxRaw ? JSON.parse(rxRaw) : null;
      const ord = rxParsed?.order || null;

      // Safety
      const sRaw = safetyKey ? localStorage.getItem(safetyKey) : null;
      const sParsed = sRaw ? JSON.parse(sRaw) : null;

      setDiagnosis(dx);
      setOrder(ord);
      if (sParsed?.decision) setSafety(sParsed);

      // Also try to pull an already-saved case summary from backend (optional)
      getCaseSummary(patientId)
        .then((data) => setSavedRecord(data))
        .catch(() => {}) // ignore if not found
        .finally(() => setLoading(false));
    } catch (e) {
      setErr("Failed to load local case artifacts (diagnosis/order/safety).");
      setLoading(false);
    }
  }, [patientId, dxKey, rxKey, safetyKey]);

  function validate() {
    if (!patientId) return "No active patient.";
    if (!diagnosis?.primary) return "Missing diagnosis. Go back and confirm Diagnosis.";
    if (!order?.meds?.length) return "Missing drafted order. Go back and Draft Order in Treatment stage.";
    // If safety decision was override, encourage note (already enforced earlier), but still:
    if (safety?.decision === "override" && !safety?.overrideNote?.trim()) {
      return "Safety decision was override but note is missing.";
    }
    return "";
  }

  async function onFinalize() {
    setErr("");
    const v = validate();
    if (v) {
      setErr(v);
      return;
    }

    const payload = {
      patient: {
        id: activePatient.id,
        name: activePatient.name,
        age: activePatient.age,
        sex: activePatient.sex,
        allergies: activePatient.allergies || [],
        meds: activePatient.meds || [],
      },
      diagnosis: {
        primary: diagnosis.primary,
        differential: diagnosis.differential || [],
        confidence: diagnosis.confidence || "medium",
        rationale: diagnosis.rationale || [],
        clinicianNote: diagnosis.clinicianNote || "",
        confirmed: true,
      },
      order: {
        meds: order.meds || [],
        notes: order.notes || "",
      },
      safety: {
        decision: safety.decision || "none",
        overrideNote: safety.overrideNote || "",
        selectedSuggestion: safety.selectedSuggestion || "",
      },
      finalClinicianNote,
    };

    setSaving(true);
    try {
      const res = await finalizeCaseSummary(payload);
      setSavedRecord(res.record);
      // Store a local copy too (demo)
      localStorage.setItem(`mf_case_${patientId}`, JSON.stringify(res.record));
    } catch (e) {
      setErr(e?.message || "Failed to finalize case.");
    } finally {
      setSaving(false);
    }
  }

  function onClearLocalCase() {
    if (!patientId) return;
    localStorage.removeItem(dxKey);
    localStorage.removeItem(rxKey);
    localStorage.removeItem(safetyKey);
    localStorage.removeItem(`mf_case_${patientId}`);
    setSavedRecord(null);
    setFinalClinicianNote("");
  }

  if (!patientId) {
    return (
      <div className="mf-card">
        <h3>Case Summary</h3>
        <p>No active patient.</p>
      </div>
    );
  }

  return (
    <div className="mf-case-grid">
      <div className="mf-card">
        <div className="mf-row mf-between">
          <h3>Case Summary</h3>
          <span className={`mf-badge ${savedRecord ? "mf-badge-ok" : ""}`}>
            {savedRecord ? "FINALIZED" : "DRAFT SUMMARY"}
          </span>
        </div>

        <div className="mf-muted mf-mt8">
          This is the final output of the staged workflow: Diagnosis → Order → Safety disposition.
          Click “Finalize & Save” to persist to backend JSON.
        </div>

        <div className="mf-row mf-right mf-mt12">
          <a
            className={`mf-btn ${savedRecord ? "mf-btn-primary" : "mf-btn-disabled"}`}
            href={savedRecord ? pdfUrl : undefined}
            onClick={(e) => {
              if (!savedRecord) {
                e.preventDefault();
                setErr("Finalize & Save first — PDF is generated from backend case summary JSON.");
              }
            }}
          >
            Download Prescription PDF
          </a>
        </div>

        {loading && <div className="mf-muted mf-mt12">Loading case artifacts…</div>}
        {err && <div className="mf-alert mf-alert-warn mf-mt12">{err}</div>}

        {!loading && (
          <>
            <div className="mf-summary-block mf-mt12">
              <div className="mf-card-title">Patient</div>
              <div className="mf-kv"><span className="mf-k">Name</span><span className="mf-v">{activePatient.name}</span></div>
              <div className="mf-kv"><span className="mf-k">MRN</span><span className="mf-v">{activePatient.id}</span></div>
              <div className="mf-kv"><span className="mf-k">Age/Sex</span><span className="mf-v">{activePatient.age} / {activePatient.sex}</span></div>
              <div className="mf-kv"><span className="mf-k">Allergies</span><span className="mf-v">{(activePatient.allergies || []).join(", ") || "—"}</span></div>
              <div className="mf-kv"><span className="mf-k">Current Meds</span><span className="mf-v">{(activePatient.meds || []).join(", ") || "—"}</span></div>
            </div>

            <div className="mf-summary-block mf-mt12">
              <div className="mf-card-title">Diagnosis</div>
              <div className="mf-big">{diagnosis?.primary || "—"}</div>
              <div className="mf-row mf-gap mf-mt8">
                <span className="mf-pill mf-pill-muted">confidence: {diagnosis?.confidence || "—"}</span>
                <span className="mf-pill mf-pill-muted">differential: {(diagnosis?.differential || []).length}</span>
              </div>
              {(diagnosis?.rationale || []).length ? (
                <ul className="mf-ul mf-mt8">
                  {diagnosis.rationale.map((x, i) => <li key={i}>{x}</li>)}
                </ul>
              ) : <div className="mf-muted mf-mt8">—</div>}
              {diagnosis?.clinicianNote ? (
                <div className="mf-muted mf-mt8"><b>Clinician note:</b> {diagnosis.clinicianNote}</div>
              ) : null}
            </div>

            <div className="mf-summary-block mf-mt12">
              <div className="mf-card-title">Final Prescription (Drafted Order)</div>
              {(order?.meds || []).length ? (
                <table className="mf-mini-table">
                  <thead>
                    <tr>
                      <th>Drug</th><th>Dose</th><th>Route</th><th>Frequency</th><th>Duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {order.meds.map((m, i) => (
                      <tr key={i}>
                        <td><b>{m.drug}</b></td>
                        <td>{m.dose}</td>
                        <td>{m.route}</td>
                        <td>{m.frequency}</td>
                        <td>{m.duration}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : <div className="mf-muted">—</div>}
              {order?.notes ? (
                <div className="mf-muted mf-mt8"><b>Order notes:</b> {order.notes}</div>
              ) : null}
            </div>

            <div className="mf-summary-block mf-mt12">
              <div className="mf-card-title">Safety Disposition</div>
              <div className="mf-row mf-between mf-mt8">
                <span className={`mf-pill ${safety?.decision === "override" ? "mf-pill-warn" : "mf-pill-muted"}`}>
                  decision: {safety?.decision || "none"}
                </span>
                {safety?.selectedSuggestion ? (
                  <span className="mf-muted">selected: {safety.selectedSuggestion}</span>
                ) : <span className="mf-muted">selected: —</span>}
              </div>
              {safety?.overrideNote ? (
                <div className="mf-muted mf-mt8"><b>Override note:</b> {safety.overrideNote}</div>
              ) : (
                <div className="mf-muted mf-mt8">No override note.</div>
              )}
            </div>

            <label className="mf-field mf-mt12">
              <div className="mf-label">Final clinician wrap-up note (optional)</div>
              <textarea
                className="mf-textarea"
                rows={4}
                value={finalClinicianNote}
                onChange={(e) => setFinalClinicianNote(e.target.value)}
                placeholder="One final note for the case summary…"
              />
            </label>

            <div className="mf-row mf-between mf-mt12">
              <button className="mf-btn-ghost" onClick={onBack} type="button">
                Back
              </button>

              <div className="mf-row mf-gap">
                <button className="mf-btn-soft" onClick={onClearLocalCase} type="button" title="Demo helper: clears local stage artifacts">
                  Clear Local Artifacts
                </button>
                <button className="mf-btn-primary" onClick={onFinalize} disabled={saving} type="button">
                  {saving ? "Saving…" : "Finalize & Save"}
                </button>
              </div>
            </div>

            {savedRecord && (
              <div className="mf-alert mf-alert-ok mf-mt12">
                Saved case summary for <b>{savedRecord.patientId}</b> at <b>{savedRecord.createdAt}</b>.
              </div>
            )}

            <div className="mf-row mf-right mf-mt12">
              <button className="mf-btn" onClick={onStartNewCase} type="button">
                Start New Case →
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}