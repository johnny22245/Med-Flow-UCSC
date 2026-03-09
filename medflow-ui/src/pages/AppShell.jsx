import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

// Reuse your existing design tokens + primitives.
import "../styles/landing.css";
import "../styles/appShell.css";

import IntakeStage from "./stages/IntakeStage";
import "../styles/intakeStage.css";

import TestOrderingStage from "./stages/TestOrderingStage";
import "../styles/testOrderingStage.css";

import InvestigationStage from "./stages/InvestigationStage";
import "../styles/investigationStage.css";

import DiagnosisStage from "./stages/DiagnosisStage";
import "../styles/diagnosisStage.css";

import TreatmentStage from "./stages/TreatmentStage";
import "../styles/treatmentStage.css";

import SafetyStage from "./stages/SafetyStage";
import "../styles/safetyStage.css";

import CaseSummaryStage from "./stages/CaseSummaryStage";
import "../styles/caseSummaryStage.css";

import TriageChat from "../components/TriageChat";

const STAGES = [
  { key: "intake", label: "Intake & Triage", hint: "Symptoms → SOAP + suggested tests → doctor approves" },
  { key: "tests", label: "Test Ordering", hint: "AI suggests labs/imaging → doctor overrides → confirms" },
  { key: "investigation", label: "Investigation", hint: "Labs + imaging → findings → doctor approves" },
  { key: "diagnosis", label: "Diagnosis", hint: "AI suggests Dx → clinician edits → confirms" },
  { key: "treatment", label: "Treatment Planning", hint: "Dx + plan → doctor edits" },
  { key: "safety", label: "Safety Guardrail", hint: "Interactions + contraindications → alert → override note" },
  { key: "case_summary", label: "Case Summary", hint: "Final Rx + safety disposition → export" },
];

export default function AppShell() {
  const navigate = useNavigate();

  const [activePatient, setActivePatient] = useState({
    id: "P-0007",
    name: "John Doe",
    age: 55,
    sex: "M",
    allergies: ["Aspirin"],
    meds: ["Valproic Acid"],
  });

  const [stageKey, setStageKey] = useState("intake");

  const [triageState, setTriageState] = useState({
    visible: false,
    loading: false,
    sessionId: null,
    status: "idle",
    currentQuestion: null,
    chatHistory: [],
    summary: "",
    urgency: "",
    suggestedTests: [],
    missingInfo: [],
    rawOutput: null,
    error: "",
  });

  const stageIdx = useMemo(
    () => Math.max(0, STAGES.findIndex((s) => s.key === stageKey)),
    [stageKey]
  );

  const canAdvance = !!activePatient;

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
    setStageKey("intake");
    setTriageState({
      visible: false,
      loading: false,
      sessionId: null,
      status: "idle",
      currentQuestion: null,
      chatHistory: [],
      summary: "",
      urgency: "",
      suggestedTests: [],
      missingInfo: [],
      rawOutput: null,
      error: "",
    });
  }

  return (
    <div className="mf-shell">
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
                  {(activePatient.allergies || []).map((a) => (
                    <span key={a} className="mf-chip mf-chip-warn">{a}</span>
                  ))}
                </div>
              </div>

              <div className="mf-mini-section">
                <div className="mf-mini-label">Current Meds</div>
                <div className="mf-chip-row">
                  {(activePatient.meds || []).map((m) => (
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
        </div>

        <div className="mf-sidebar-footer">
          <div className="mf-muted">Privacy mode: local demo</div>
        </div>
      </aside>

      <main className="mf-main">
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
            <span className="mf-pill mf-pill-ok">Backend: Connected</span>
          </div>
        </header>

        <section className="mf-stepper mf-card">
          <div className="mf-stepper-row">
            {STAGES.map((s, i) => {
              const status = i < stageIdx ? "done" : i === stageIdx ? "active" : "todo";
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
            <button
              className="mf-btn-primary"
              onClick={goNext}
              disabled={!canAdvance || stageIdx === STAGES.length - 1}
            >
              Next
            </button>
          </div>
        </section>

        <section className="mf-workspace">
          <div className="mf-card mf-workspace-card">
            <div className="mf-card-title">Stage Workspace</div>
            <div className="mf-muted mf-mt8">
              This area will render the stage page: <b>{STAGES[stageIdx].label}</b>
            </div>

            <div className="mf-mt12">
              {stageKey === "intake" ? (
                <>
                  <IntakeStage
                    activePatient={activePatient}
                    onPatientCreated={(p) => setActivePatient(p)}
                    onRequestNext={() => setStageKey("tests")}
                    onTriageStarted={(triage) => setTriageState(triage)}
                  />

                  <TriageChat
                    triageState={triageState}
                    onTriageUpdated={(next) => setTriageState(next)}
                    onTriageCompleted={(next) => {
                      setTriageState(next);
                      setStageKey("tests");
                    }}
                    onClose={() =>
                      setTriageState((prev) => ({ ...prev, visible: false }))
                    }
                  />
                </>
              ) : stageKey === "tests" ? (
                <TestOrderingStage
                  activePatient={activePatient}
                  intakeContext={{
                    chiefComplaint: activePatient?.chiefComplaint || "",
                  }}
                  triageContext={triageState}
                  onBack={() => setStageKey("intake")}
                  onApproveNext={() => setStageKey("investigation")}
                />
              ) : stageKey === "investigation" ? (
                <InvestigationStage
                  activePatient={activePatient}
                  onApproveNext={() => setStageKey("diagnosis")}
                />
              ) : stageKey === "diagnosis" ? (
                <DiagnosisStage
                  activePatient={activePatient}
                  onApproveNext={() => setStageKey("treatment")}
                />
              ) : stageKey === "treatment" ? (
                <TreatmentStage
                  activePatient={activePatient}
                  onApproveNext={() => setStageKey("safety")}
                  onBack={() => setStageKey("diagnosis")}
                />
              ) : stageKey === "safety" ? (
                <SafetyStage
                  activePatient={activePatient}
                  onBack={() => setStageKey("treatment")}
                  onComplete={() => setStageKey("case_summary")}
                />
              ) : stageKey === "case_summary" ? (
                <CaseSummaryStage
                  activePatient={activePatient}
                  onBack={() => setStageKey("safety")}
                  onStartNewCase={() => setStageKey("intake")}
                />
              ) : null}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}