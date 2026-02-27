// src/pages/stages/TreatmentStage.jsx
import { useEffect, useMemo, useState } from "react";
import "../../styles/treatmentStage.css";
import { getTreatmentPlan, draftTreatmentOrder } from "../../services/api";

export default function TreatmentStage({ activePatient, onBack, onApproveNext }) {
  const patientId = activePatient?.id;

  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  // Suggested plan from backend
  const [suggestedPlan, setSuggestedPlan] = useState(null);

  // Editable draft order state (what clinician can change)
  const [meds, setMeds] = useState([]);
  const [orderNotes, setOrderNotes] = useState("");

  const rxKey = useMemo(() => (patientId ? `mf_rx_${patientId}` : null), [patientId]);

  useEffect(() => {
    if (!patientId) return;

    // Prefer localStorage (demo convenience / refresh-safe)
    const local = rxKey ? localStorage.getItem(rxKey) : null;
    if (local) {
      try {
        const parsed = JSON.parse(local);
        const savedMeds = parsed?.order?.meds || parsed?.meds || [];
        const savedNotes = parsed?.order?.notes || parsed?.notes || "";
        setMeds(savedMeds);
        setOrderNotes(savedNotes);
        setSuggestedPlan({ title: "Loaded saved draft (local)", meds: [], notes: [] });
        setLoading(false);
        return;
      } catch {
        // fall through to backend
      }
    }

    setLoading(true);
    setErr("");

    getTreatmentPlan(patientId)
      .then((data) => {
        if (data?.drafted && data?.order) {
          // Backend draft exists
          setMeds(data.order.meds || []);
          setOrderNotes(data.order.notes || "");
          setSuggestedPlan({ title: "Loaded saved draft (backend)", meds: [], notes: [] });
        } else {
          // Suggested plan exists
          const sp = data?.suggestedPlan || null;
          setSuggestedPlan(sp);

          // Start empty draft by default; clinician can copy from AI plan
          setMeds([]);
          setOrderNotes("");
        }
      })
      .catch((e) => setErr(e?.message || "Failed to load treatment plan"))
      .finally(() => setLoading(false));
  }, [patientId, rxKey]);

  function copySuggestedToDraft() {
    if (!suggestedPlan) return;
    setMeds((suggestedPlan.meds || []).map((m) => ({ ...m })));
    setOrderNotes((suggestedPlan.notes || []).join("\n"));
  }

  function addRow() {
    setMeds([
      ...meds,
      { drug: "", dose: "", route: "PO", frequency: "", duration: "" },
    ]);
  }

  function removeRow(idx) {
    setMeds(meds.filter((_, i) => i !== idx));
  }

  function updateRow(idx, key, value) {
    setMeds(
      meds.map((m, i) => (i === idx ? { ...m, [key]: value } : m))
    );
  }

  function validateDraft() {
    if (meds.length === 0) return "Add at least one medication before drafting the order.";
    for (let i = 0; i < meds.length; i++) {
      const m = meds[i];
      if (!m.drug?.trim()) return `Row ${i + 1}: Drug name is required.`;
      if (!m.dose?.trim()) return `Row ${i + 1}: Dose is required.`;
      if (!m.route?.trim()) return `Row ${i + 1}: Route is required.`;
      if (!m.frequency?.trim()) return `Row ${i + 1}: Frequency is required.`;
      if (!m.duration?.trim()) return `Row ${i + 1}: Duration is required.`;
    }
    return "";
  }

  async function onDraftOrder() {
    if (!patientId) return;
    setErr("");

    const validationError = validateDraft();
    if (validationError) {
      setErr(validationError);
      return;
    }

    const payload = {
      patientId,
      drafted: true,
      order: {
        meds,
        notes: orderNotes,
      },
    };

    try {
      await draftTreatmentOrder(payload);

      // Save locally too for refresh reliability (demo)
      localStorage.setItem(rxKey, JSON.stringify(payload));

      onApproveNext?.();
    } catch (e) {
      setErr(e?.message || "Failed to draft order");
    }
  }

  if (!patientId) {
    return (
      <div className="mf-card">
        <h3>Treatment Planning</h3>
        <p>No active patient. Complete Intake first.</p>
      </div>
    );
  }

  return (
    <div className="mf-tx-grid">
      {/* Left: suggested plan */}
      <div className="mf-card">
        <div className="mf-row mf-between">
          <h3>AI Suggested Plan</h3>
          <span className="mf-badge">PHASE 7</span>
        </div>

        {loading && <p className="mf-muted">Loading plan…</p>}
        {err && <div className="mf-alert mf-alert-warn">{err}</div>}

        {!loading && (
          <>
            {suggestedPlan ? (
              <>
                <div className="mf-plan-title">{suggestedPlan.title || "Suggested plan"}</div>

                <div className="mf-mini-section mf-mt12">
                  <div className="mf-mini-label">Suggested meds</div>
                  {(suggestedPlan.meds || []).length > 0 ? (
                    <ul className="mf-ul">
                      {suggestedPlan.meds.map((m, idx) => (
                        <li key={idx}>
                          <b>{m.drug}</b> — {m.dose} / {m.route} / {m.frequency} / {m.duration}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="mf-muted">No suggested meds loaded (draft already exists).</div>
                  )}
                </div>

                <div className="mf-mini-section mf-mt12">
                  <div className="mf-mini-label">Notes</div>
                  {(suggestedPlan.notes || []).length > 0 ? (
                    <ul className="mf-ul">
                      {suggestedPlan.notes.map((n, i) => (
                        <li key={i}>{n}</li>
                      ))}
                    </ul>
                  ) : (
                    <div className="mf-muted">—</div>
                  )}
                </div>

                <div className="mf-row mf-right mf-mt12">
                  <button className="mf-btn" onClick={copySuggestedToDraft} disabled={(suggestedPlan.meds || []).length === 0}>
                    Copy plan to draft →
                  </button>
                </div>
              </>
            ) : (
              <div className="mf-muted">No plan found. Add fixture for this patient.</div>
            )}
          </>
        )}
      </div>

      {/* Right: editable prescription builder */}
      <div className="mf-card">
        <div className="mf-row mf-between">
          <h3>Prescription Builder</h3>
          <span className="mf-badge mf-badge-ok">CLINICIAN EDIT</span>
        </div>

        <div className="mf-muted mf-mt8">
          Add/edit meds below. Drafting the order is the Phase 7 STOP node.
        </div>

        <div className="mf-table-wrap mf-mt12">
          <table className="mf-table">
            <thead>
              <tr>
                <th>Drug</th>
                <th>Dose</th>
                <th>Route</th>
                <th>Frequency</th>
                <th>Duration</th>
                <th></th>
              </tr>
            </thead>

            <tbody>
              {meds.length === 0 ? (
                <tr>
                  <td colSpan={6} className="mf-muted mf-td-center">
                    No medications in draft. Click “Add medication” or “Copy plan to draft”.
                  </td>
                </tr>
              ) : (
                meds.map((m, idx) => (
                  <tr key={idx}>
                    <td>
                      <input
                        className="mf-input"
                        value={m.drug}
                        onChange={(e) => updateRow(idx, "drug", e.target.value)}
                        placeholder="e.g., Temozolomide"
                      />
                    </td>
                    <td>
                      <input
                        className="mf-input"
                        value={m.dose}
                        onChange={(e) => updateRow(idx, "dose", e.target.value)}
                        placeholder="e.g., 65 mg"
                      />
                    </td>
                    <td>
                      <select
                        className="mf-input"
                        value={m.route}
                        onChange={(e) => updateRow(idx, "route", e.target.value)}
                      >
                        <option value="PO">PO</option>
                        <option value="IV">IV</option>
                        <option value="IM">IM</option>
                        <option value="SC">SC</option>
                        <option value="Topical">Topical</option>
                      </select>
                    </td>
                    <td>
                      <input
                        className="mf-input"
                        value={m.frequency}
                        onChange={(e) => updateRow(idx, "frequency", e.target.value)}
                        placeholder="e.g., Daily / BID / q8h PRN"
                      />
                    </td>
                    <td>
                      <input
                        className="mf-input"
                        value={m.duration}
                        onChange={(e) => updateRow(idx, "duration", e.target.value)}
                        placeholder="e.g., 42 days"
                      />
                    </td>
                    <td className="mf-td-actions">
                      <button className="mf-btn-ghost mf-btn-x" onClick={() => removeRow(idx)} type="button">
                        ×
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="mf-row mf-between mf-mt12">
          <button className="mf-btn-soft" onClick={addRow} type="button">
            + Add medication
          </button>

          <div className="mf-row mf-gap">
            <button className="mf-btn-ghost" onClick={onBack} type="button">
              Back
            </button>
            <button className="mf-btn-primary" onClick={onDraftOrder} type="button">
              Draft Order
            </button>
          </div>
        </div>

        <label className="mf-field mf-mt12">
          <div className="mf-label">Order notes</div>
          <textarea
            className="mf-textarea"
            rows={4}
            value={orderNotes}
            onChange={(e) => setOrderNotes(e.target.value)}
            placeholder="Optional notes: monitoring, dose adjustments, patient factors…"
          />
        </label>

        <div className="mf-muted mf-small mf-mt8">
          Tip: For the demo, include one med that will trigger a Safety conflict in Phase 8.
        </div>
      </div>
    </div>
  );
}