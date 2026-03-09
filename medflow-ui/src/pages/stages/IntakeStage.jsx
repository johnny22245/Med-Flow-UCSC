import { useMemo, useState } from "react";
import { createPatientProfile, startTriage } from "../../services/medflowApi";

const DEFAULT_VITALS = {
  tempC: "37.0",
  hr: "84",
  bpSys: "128",
  bpDia: "78",
  spo2: "98",
};

function makePatientId() {
  const n = Math.floor(1000 + Math.random() * 9000);
  return `P-${n}`;
}

export default function IntakeStage({
  activePatient,
  onPatientCreated,
  onRequestNext,
  onTriageStarted,
}) {
  // Patient profile fields
  const [name, setName] = useState(activePatient?.name ?? "");
  const [age, setAge] = useState(activePatient?.age ?? "");
  const [sex, setSex] = useState(activePatient?.sex ?? "M");

  // Intake fields
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [symptoms, setSymptoms] = useState("Chest discomfort\nShortness of breath on exertion");
  const [duration, setDuration] = useState("2 days");
  const [severity, setSeverity] = useState(6); // 0–10
  const [privacyConsent, setPrivacyConsent] = useState(true);

  // Vitals
  const [vitals, setVitals] = useState(DEFAULT_VITALS);

  const errors = useMemo(() => {
    const e = [];
    if (!name.trim()) e.push("Patient name is required.");
    if (!age || Number.isNaN(Number(age)) || Number(age) <= 0) e.push("Valid age is required.");
    if (!chiefComplaint.trim()) e.push("Chief complaint is required.");
    if (!privacyConsent) e.push("Consent is required for demo intake submission.");
    return e;
  }, [name, age, chiefComplaint, privacyConsent]);

  const canCreate = errors.length === 0;

  async function handleCreate() {
    if (!canCreate) return;

    const payload = {
      id: activePatient?.id ?? makePatientId(),
      name: name.trim(),
      age: Number(age),
      sex,
      intake: {
        chief_complaint: chiefComplaint.trim(),
        symptoms_text: symptoms.trim(),
        duration: duration.trim(),
        severity_0_10: Number(severity),
        vitals: {
          temp_c: Number(vitals.tempC),
          hr_bpm: Number(vitals.hr),
          bp_sys: Number(vitals.bpSys),
          bp_dia: Number(vitals.bpDia),
          spo2_pct: Number(vitals.spo2),
        },
        consent: true,
      },
    };

    const created = await createPatientProfile(payload);

    const patientForShell = {
      id: created.id,
      name: created.name,
      age: created.age,
      sex: created.sex,
      allergies: created.allergies ?? ["Aspirin"],
      meds: created.meds ?? ["Valproic Acid"],
      chiefComplaint: created.intake?.chief_complaint || payload.intake.chief_complaint,
      intake: created.intake || payload.intake,
    };

    onPatientCreated(patientForShell);

    if (typeof onTriageStarted === "function") {
      onTriageStarted({
        visible: true,
        loading: true,
        sessionId: null,
        status: "starting",
        currentQuestion: null,
        chatHistory: [],
        summary: "",
        urgency: "",
        suggestedTests: [],
        missingInfo: [],
        rawOutput: null,
      });

      try {
        const triage = await startTriage(created.id);

        onTriageStarted({
          visible: true,
          loading: false,
          sessionId: triage.session_id,
          status: triage.status,
          currentQuestion: triage.current_question,
          chatHistory: triage.chat_history || [],
          summary: triage.summary || "",
          urgency: triage.urgency || "",
          suggestedTests: triage.suggested_tests || [],
          missingInfo: triage.missing_info || [],
          rawOutput: triage.raw_output || null,
        });
      } catch (err) {
        onTriageStarted({
          visible: true,
          loading: false,
          sessionId: null,
          status: "error",
          currentQuestion: null,
          chatHistory: [],
          summary: "",
          urgency: "",
          suggestedTests: [],
          missingInfo: [],
          rawOutput: null,
          error: err.message || "Failed to start triage",
        });
      }
    }
  }

  return (
    <div className="mf-intake-grid">
      {/* Left: intake form */}
      <div className="mf-card mf-intake-card">
        <div className="mf-card-title">Patient Intake</div>
        <div className="mf-muted mf-mt8">
          Collect symptoms and vitals. This will later trigger “SOAP + suggested tests” generation.
        </div>

        <div className="mf-form">
          <div className="mf-form-row">
            <div className="mf-field">
              <label className="mf-label">Patient Name</label>
              <input className="mf-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g., John Doe" />
            </div>
            <div className="mf-field">
              <label className="mf-label">Age</label>
              <input className="mf-input" value={age} onChange={(e) => setAge(e.target.value)} placeholder="e.g., 55" />
            </div>
            <div className="mf-field">
              <label className="mf-label">Sex</label>
              <select className="mf-input" value={sex} onChange={(e) => setSex(e.target.value)}>
                <option value="M">M</option>
                <option value="F">F</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>

          <div className="mf-field">
            <label className="mf-label">Chief Complaint</label>
            <input
              className="mf-input"
              value={chiefComplaint}
              onChange={(e) => setChiefComplaint(e.target.value)}
              placeholder="e.g., Chest pain and shortness of breath"
            />
          </div>

          <div className="mf-field">
            <label className="mf-label">Symptoms (free text)</label>
            <textarea
              className="mf-textarea"
              rows={5}
              value={symptoms}
              onChange={(e) => setSymptoms(e.target.value)}
              placeholder="Enter symptoms, one per line…"
            />
          </div>

          <div className="mf-form-row">
            <div className="mf-field">
              <label className="mf-label">Duration</label>
              <input className="mf-input" value={duration} onChange={(e) => setDuration(e.target.value)} placeholder="e.g., 2 days" />
            </div>

            <div className="mf-field">
              <label className="mf-label">Severity (0–10)</label>
              <input
                className="mf-range"
                type="range"
                min="0"
                max="10"
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
              />
              <div className="mf-muted">Current: {severity}/10</div>
            </div>
          </div>

          <div className="mf-divider" />

          <div className="mf-card-subtitle">Vitals (demo)</div>
          <div className="mf-vitals-grid">
            <div className="mf-field">
              <label className="mf-label">Temp (°C)</label>
              <input className="mf-input" value={vitals.tempC} onChange={(e) => setVitals({ ...vitals, tempC: e.target.value })} />
            </div>
            <div className="mf-field">
              <label className="mf-label">HR (bpm)</label>
              <input className="mf-input" value={vitals.hr} onChange={(e) => setVitals({ ...vitals, hr: e.target.value })} />
            </div>
            <div className="mf-field">
              <label className="mf-label">BP Sys</label>
              <input className="mf-input" value={vitals.bpSys} onChange={(e) => setVitals({ ...vitals, bpSys: e.target.value })} />
            </div>
            <div className="mf-field">
              <label className="mf-label">BP Dia</label>
              <input className="mf-input" value={vitals.bpDia} onChange={(e) => setVitals({ ...vitals, bpDia: e.target.value })} />
            </div>
            <div className="mf-field">
              <label className="mf-label">SpO₂ (%)</label>
              <input className="mf-input" value={vitals.spo2} onChange={(e) => setVitals({ ...vitals, spo2: e.target.value })} />
            </div>
          </div>

          <div className="mf-consent">
            <input
              type="checkbox"
              checked={privacyConsent}
              onChange={(e) => setPrivacyConsent(e.target.checked)}
            />
            <span>
              Patient consent confirmed (demo). Data stays local / dummy.
            </span>
          </div>

          {errors.length > 0 && (
            <div className="mf-alert mf-alert-warn">
              <div className="mf-alert-title">Fix the following</div>
              <ul className="mf-alert-list">
                {errors.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="mf-actions">
            <button className="mf-btn-primary" onClick={handleCreate} disabled={!canCreate}>
              {activePatient ? "Update Patient" : "Create Patient"}
            </button>

            <button className="mf-btn-ghost" onClick={onRequestNext} disabled={!activePatient}>
              Continue to Test Ordering
            </button>
          </div>
        </div>
      </div>

      {/* Right: preview */}
      <div className="mf-card mf-intake-card">
        <div className="mf-card-title">Profile Preview</div>
        <div className="mf-muted mf-mt8">
          This mirrors what the shell sidebar will show once created.
        </div>

        <div className="mf-preview">
          <div className="mf-kv">
            <span className="mf-k">Name</span>
            <span className="mf-v">{name || "—"}</span>
          </div>
          <div className="mf-kv">
            <span className="mf-k">Age/Sex</span>
            <span className="mf-v">
              {age || "—"} / {sex}
            </span>
          </div>

          <div className="mf-divider" />

          <div className="mf-mini-section">
            <div className="mf-mini-label">Chief Complaint</div>
            <div className="mf-preview-box">{chiefComplaint || "—"}</div>
          </div>

          <div className="mf-mini-section">
            <div className="mf-mini-label">Symptoms</div>
            <div className="mf-preview-box mf-prewrap">{symptoms || "—"}</div>
          </div>

          <div className="mf-mini-section">
            <div className="mf-mini-label">Vitals</div>
            <div className="mf-preview-box">
              Temp {vitals.tempC}°C · HR {vitals.hr} · BP {vitals.bpSys}/{vitals.bpDia} · SpO₂ {vitals.spo2}%
            </div>
          </div>
        </div>

        <div className="mf-muted mf-mt12">
          Next topic will generate SOAP + suggested tests from this payload.
        </div>
      </div>
    </div>
  );
}
