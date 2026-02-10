import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

// Reuse your existing design tokens + primitives.
// If these are only defined in landing.css, importing here makes them available to /app too.
import "../styles/landing.css";
import "../styles/appShell.css";

// Adding 3. Patient intake + Profile creation
import IntakeStage from "../pages/stages/IntakeStage";
import "../styles/intakeStage.css";

// Ordering Tests
import TestOrderingStage from "./stages/TestOrderingStage";
import "../styles/testOrderingStage.css";

// Adding 5. Investigation stage
import InvestigationStage from "./stages/InvestigationStage";
import "../styles/investigationStage.css";

const STAGES = [
  { key: "intake", label: "Intake & Triage", hint: "Symptoms → SOAP + suggested tests → doctor approves" },
  { key: "tests", label: "Test Ordering", hint: "AI suggests labs/imaging → doctor overrides → confirms" },
  { key: "investigation", label: "Investigation", hint: "Labs + imaging → findings → doctor approves" },
  { key: "treatment", label: "Treatment Planning", hint: "Dx + plan → doctor edits" },
  { key: "safety", label: "Safety Guardrail", hint: "Interactions + contraindications → alert → override note" },
];

export default function AppShell() {
  const navigate = useNavigate();

  // For now: a local “demo patient” state. Later you’ll swap to backend-backed patient context.
  const [activePatient, setActivePatient] = useState({
    id: "P-0007",
    name: "John Doe",
    age: 55,
    sex: "M",
    allergies: ["Aspirin"],
    meds: ["Valproic Acid"],
  });

  // State machine stage (future: backend controls + approval events)
  const [stageKey, setStageKey] = useState("intake");

  const stageIdx = useMemo(
    () => Math.max(0, STAGES.findIndex((s) => s.key === stageKey)),
    [stageKey]
  );

  const canAdvance = !!activePatient; // later: require approvals per stage

  function goPrev() {
    const next = Math.max(0, stageIdx - 1);
    setStageKey(STAGES[next].key);
  }

  function goNext() {
    if (!canAdvance) return;
    const next = Math.min(STAGES.length - 1, stageIdx + 1);
    setStageKey(STAGES[next].key);
  }

  function resetCase() {
    // demo reset: keep patient but return to intake
    setStageKey("intake");
  }

  return (
    <div className="mf-shell">
      {/* Sidebar */}
      <aside className="mf-sidebar">
        <div className="mf-sidebar-header">
          <div className="mf-brand">
            <div className="mf-brand-dot" aria-hidden="true" />
            <div>
              <div className="mf-brand-title">Med-Flow</div>
              <div className="mf-brand-subtitle">Clinician Cockpit</div>
            </div>
          </div>

          <button className="mf-btn-ghost" onClick={() => navigate("/")}>
            Exit Demo
          </button>
        </div>

        <div className="mf-card mf-sidebar-card">
          <div className="mf-card-title">Active Patient</div>
          {activePatient ? (
            <>
              <div className="mf-kv">
                <span className="mf-k">Name</span>
                <span className="mf-v">{activePatient.name}</span>
              </div>
              <div className="mf-kv">
                <span className="mf-k">MRN</span>
                <span className="mf-v">{activePatient.id}</span>
              </div>
              <div className="mf-kv">
                <span className="mf-k">Age/Sex</span>
                <span className="mf-v">
                  {activePatient.age} / {activePatient.sex}
                </span>
              </div>

              <div className="mf-divider" />

              <div className="mf-mini-section">
                <div className="mf-mini-label">Allergies</div>
                <div className="mf-chip-row">
                  {activePatient.allergies.map((a) => (
                    <span key={a} className="mf-chip mf-chip-warn">{a}</span>
                  ))}
                </div>
              </div>

              <div className="mf-mini-section">
                <div className="mf-mini-label">Current Meds</div>
                <div className="mf-chip-row">
                  {activePatient.meds.map((m) => (
                    <span key={m} className="mf-chip">{m}</span>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="mf-muted">
              No active patient. Create/select one to start.
            </div>
          )}
        </div>

        <div className="mf-card mf-sidebar-card">
          <div className="mf-card-title">Quick Actions</div>
          <div className="mf-sidebar-actions">
            <button className="mf-btn-soft" onClick={resetCase}>
              Reset to Intake
            </button>
            <button
              className="mf-btn-danger"
              onClick={() => setActivePatient(null)}
              title="Demo-only: clears local state"
            >
              Clear Patient
            </button>
          </div>
          <div className="mf-muted mf-mt8">
            Later: this section calls backend events (approve/override) per stage.
          </div>
        </div>

        <div className="mf-sidebar-footer">
          <div className="mf-muted">
            Privacy mode: local demo (dummy data)
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="mf-main">
        {/* Topbar */}
        <header className="mf-topbar">
          <div className="mf-topbar-left">
            <div className="mf-topbar-title">Case Workflow</div>
            <div className="mf-topbar-subtitle">
              Stage-controlled flow with human approvals at critical nodes
            </div>
          </div>

          <div className="mf-topbar-right">
            <span className={`mf-pill ${activePatient ? "mf-pill-ok" : "mf-pill-muted"}`}>
              {activePatient ? "Patient Loaded" : "No Patient"}
            </span>
            <span className="mf-pill mf-pill-muted">
              Backend: not connected
            </span>
          </div>
        </header>

        {/* Stepper */}
        <section className="mf-stepper mf-card">
          <div className="mf-stepper-row">
            {STAGES.map((s, i) => {
              const status =
                i < stageIdx ? "done" : i === stageIdx ? "active" : "todo";
              return (
                <button
                  key={s.key}
                  className={`mf-stepper-item mf-stepper-${status}`}
                  onClick={() => setStageKey(s.key)}
                  type="button"
                >
                  <div className="mf-stepper-badge">{i + 1}</div>
                  <div className="mf-stepper-text">
                    <div className="mf-stepper-label">{s.label}</div>
                    <div className="mf-stepper-hint">{s.hint}</div>
                  </div>
                </button>
              );
            })}
          </div>

          <div className="mf-stepper-controls">
            <button className="mf-btn-ghost" onClick={goPrev} disabled={stageIdx === 0}>
              Back
            </button>
            <button className="mf-btn-primary" onClick={goNext} disabled={!canAdvance || stageIdx === STAGES.length - 1}>
              Next
            </button>
          </div>
        </section>

        <section className="mf-workspace">
        <div className="mf-card mf-workspace-card">
            <div className="mf-card-title">Stage Workspace</div>
            <div className="mf-muted mf-mt8">
            This area will render the stage page: <b> {STAGES[stageIdx].label}</b>
            </div>

            <div className="mf-mt12">
              {stageKey === "intake" ? (
                <IntakeStage
                  activePatient={activePatient}
                  onPatientCreated={(p) => setActivePatient(p)}
                  onRequestNext={() => setStageKey("tests")}
                />
              ) : stageKey === "tests" ? (
                <TestOrderingStage
                  activePatient={activePatient}
                  intakeContext={{
                    chiefComplaint: activePatient?.chiefComplaint || "",
                  }}
                  onBack={() => setStageKey("intake")}
                  onApproveNext={() => setStageKey("investigation")}
                />
              ) : stageKey === "investigation" ? (
                <InvestigationStage
                  activePatient={activePatient}
                  onApproveNext={() => setStageKey("treatment")}
                />
              ) : (
                <div className="mf-placeholder">
                  <div className="mf-placeholder-title">Coming next</div>
                  <div className="mf-placeholder-text">
                    We’ll implement <b>{STAGES[stageIdx].label}</b> as the next topic page.
                  </div>
                </div>
              )}
            </div>

        </div>
        </section>

      </main>
    </div>
  );
}
