import React, { useEffect, useMemo, useState } from "react";
import { getDiagnosisSuggestion, confirmDiagnosis } from "../../services/api";
import "../../styles/diagnosisStage.css";

export default function DiagnosisStage({ activePatient, onStageComplete }) {
  const patientId = activePatient?.id;

  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [suggestion, setSuggestion] = useState(null);

  // Editable clinician form state
  const [primary, setPrimary] = useState("");
  const [confidence, setConfidence] = useState("medium");
  const [differential, setDifferential] = useState([]);
  const [rationale, setRationale] = useState([]);
  const [clinicianNote, setClinicianNote] = useState("");

  const lockedKey = useMemo(() => (patientId ? `mf_dx_${patientId}` : null), [patientId]);

  useEffect(() => {
    if (!patientId) return;

    // If already confirmed (local), load & lock
    const local = lockedKey ? localStorage.getItem(lockedKey) : null;
    if (local) {
      const dx = JSON.parse(local);
      setPrimary(dx.primary || "");
      setConfidence(dx.confidence || "medium");
      setDifferential(dx.differential || []);
      setRationale(dx.rationale || []);
      setClinicianNote(dx.clinicianNote || "");
      setSuggestion({ confirmed: true });
      setLoading(false);
      return;
    }

    setLoading(true);
    setErr("");
    getDiagnosisSuggestion(patientId)
      .then((data) => {
        if (data?.confirmed && data?.diagnosis) {
          // backend confirmed
          const d = data.diagnosis;
          setPrimary(d.primary || "");
          setConfidence(d.confidence || "medium");
          setDifferential(d.differential || []);
          setRationale(d.rationale || []);
          setClinicianNote(d.clinicianNote || "");
          setSuggestion({ confirmed: true });
        } else {
          const s = data?.suggestion;
          setSuggestion(s);
          setPrimary(s?.primary || "");
          setConfidence(s?.confidence || "medium");
          setDifferential(s?.differential || []);
          setRationale(s?.rationale || []);
        }
      })
      .catch((e) => setErr(e.message || "Failed to load diagnosis suggestion"))
      .finally(() => setLoading(false));
  }, [patientId, lockedKey]);

  const isConfirmed = !!suggestion?.confirmed;

  function addDiff(item) {
    const clean = item.trim();
    if (!clean) return;
    if (differential.includes(clean)) return;
    setDifferential([...differential, clean]);
  }

  function removeDiff(i) {
    setDifferential(differential.filter((_, idx) => idx !== i));
  }

  function addRationale(item) {
    const clean = item.trim();
    if (!clean) return;
    setRationale([...rationale, clean]);
  }

  function removeRationale(i) {
    setRationale(rationale.filter((_, idx) => idx !== i));
  }

  async function onConfirm() {
    if (!patientId) return;
    setErr("");

    const payload = {
      patientId,
      primary,
      differential,
      confidence,
      rationale,
      clinicianNote,
      confirmed: true,
    };

    try {
      await confirmDiagnosis(payload);
      localStorage.setItem(lockedKey, JSON.stringify(payload));
      setSuggestion({ confirmed: true });
      onStageComplete?.(); // AppShell moves to Phase 7 later
    } catch (e) {
      setErr(e.message || "Confirm failed");
    }
  }

  if (!patientId) {
    return (
      <div className="mf-card">
        <h3>Diagnosis</h3>
        <p>No active patient. Please complete Intake first.</p>
      </div>
    );
  }

  return (
    <div className="mf-dx-grid">
      <div className="mf-card">
        <h3>Evidence Summary</h3>
        <p className="mf-muted">
          This panel will later pull structured highlights from Investigation results.
          For now, it acts as a clinician review anchor.
        </p>

        <div className="mf-evidence">
          <div className="mf-evidence-item">
            <div className="mf-label">Chief complaint</div>
            <div>{activePatient?.intake?.chiefComplaint || "—"}</div>
          </div>

          <div className="mf-evidence-item">
            <div className="mf-label">Symptoms</div>
            <div>{activePatient?.intake?.symptoms || "—"}</div>
          </div>

          <div className="mf-evidence-item">
            <div className="mf-label">Investigation</div>
            <div className="mf-muted">
              (Demo) Use Phase 5 Investigation viewer + AI findings; we’ll wire it here later.
            </div>
          </div>
        </div>
      </div>

      <div className="mf-card">
        <div className="mf-row mf-between">
          <h3>Diagnosis Card</h3>
          {isConfirmed ? <span className="mf-badge mf-badge-ok">CONFIRMED</span> : <span className="mf-badge">DRAFT</span>}
        </div>

        {loading && <p className="mf-muted">Loading suggestion…</p>}
        {err && <div className="mf-alert mf-alert-warn">{err}</div>}

        {!loading && (
          <>
            <label className="mf-field">
              <div className="mf-label">Primary diagnosis</div>
              <input
                className="mf-input"
                value={primary}
                onChange={(e) => setPrimary(e.target.value)}
                disabled={isConfirmed}
                placeholder="e.g., Suspected glioma"
              />
            </label>

            <label className="mf-field">
              <div className="mf-label">Confidence</div>
              <select
                className="mf-input"
                value={confidence}
                onChange={(e) => setConfidence(e.target.value)}
                disabled={isConfirmed}
              >
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
              </select>
            </label>

            <div className="mf-field">
              <div className="mf-label">Differential diagnosis</div>
              <DiffEditor
                items={differential}
                onAdd={addDiff}
                onRemove={removeDiff}
                disabled={isConfirmed}
              />
            </div>

            <div className="mf-field">
              <div className="mf-label">Rationale bullets</div>
              <DiffEditor
                items={rationale}
                onAdd={addRationale}
                onRemove={removeRationale}
                disabled={isConfirmed}
                placeholder="Add a rationale bullet"
              />
            </div>

            <label className="mf-field">
              <div className="mf-label">Clinician note</div>
              <textarea
                className="mf-textarea"
                rows={3}
                value={clinicianNote}
                onChange={(e) => setClinicianNote(e.target.value)}
                disabled={isConfirmed}
                placeholder="Optional note for medical record…"
              />
            </label>

            <div className="mf-row mf-right">
              <button className="mf-btn mf-btn-primary" onClick={onConfirm} disabled={isConfirmed || !primary.trim()}>
                Confirm Diagnosis
              </button>
            </div>

            <p className="mf-muted mf-small">
              Confirm locks edits and acts as the Phase 6 STOP node.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

function DiffEditor({ items, onAdd, onRemove, disabled, placeholder = "Add item" }) {
  const [val, setVal] = useState("");

  return (
    <div>
      <div className="mf-chip-row">
        {items.map((x, i) => (
          <span key={`${x}-${i}`} className="mf-chip">
            {x}
            {!disabled && (
              <button className="mf-chip-x" onClick={() => onRemove(i)} type="button">
                ×
              </button>
            )}
          </span>
        ))}
        {items.length === 0 && <span className="mf-muted">—</span>}
      </div>

      {!disabled && (
        <div className="mf-row mf-gap">
          <input
            className="mf-input"
            value={val}
            onChange={(e) => setVal(e.target.value)}
            placeholder={placeholder}
          />
          <button
            className="mf-btn"
            type="button"
            onClick={() => {
              onAdd(val);
              setVal("");
            }}
          >
            Add
          </button>
        </div>
      )}
    </div>
  );
}