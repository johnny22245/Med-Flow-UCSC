import React from "react";
import { useNavigate } from "react-router-dom";
import "../styles/landing.css";

export default function LandingPage() {
  const navigate = useNavigate();
  return (
    <div className="mf">
      <header className="mf-header">
        <div className="mf-container mf-header-inner">
          <div className="mf-brand">
            <div className="mf-logo" aria-hidden="true">MF</div>
            <div>
              <div className="mf-brand-name">Med-Flow</div>
              <div className="mf-brand-tagline">Local AI • Human-verified • Clinical workflow</div>
            </div>
          </div>

          <nav className="mf-nav">
            <a href="#how">How it works</a>
            <a href="#features">Features</a>
            <a href="#security">Security</a>
            <a className="mf-btn mf-btn-ghost" href="#demo">View demo</a>
          </nav>
        </div>
      </header>

      <main>
        <section className="mf-hero">
          <div className="mf-container mf-hero-grid">
            <div className="mf-hero-copy">
              <span className="mf-badge">Staged clinical decision support</span>
              <h1>Move from symptoms → tests → diagnosis → safe prescription, faster.</h1>
              <p>
                Med-Flow guides clinicians through a structured workflow with human approvals at
                every critical step. Designed for local deployment and privacy-preserving operation.
              </p>

              <div className="mf-hero-cta" id="demo">
                <button
                  className="mf-btn mf-btn-primary"
                  onClick={() => navigate("/app")}
                >
                  Start diagnosis
                </button>
                <button
                  className="mf-btn mf-btn-soft"
                  onClick={() => window.location.hash = "#how"}
                >
                  See how it works
                </button>
              </div>

              <div className="mf-metrics">
                <div className="mf-metric">
                  <div className="mf-metric-value">4</div>
                  <div className="mf-metric-label">Workflow stages</div>
                </div>
                <div className="mf-metric">
                  <div className="mf-metric-value">100%</div>
                  <div className="mf-metric-label">Human verified</div>
                </div>
                <div className="mf-metric">
                  <div className="mf-metric-value">Local</div>
                  <div className="mf-metric-label">Privacy-preserving</div>
                </div>
              </div>
            </div>

            <div className="mf-hero-art" aria-label="Product preview mock">
              <div className="mf-art-card mf-art-card-top">
                <div className="mf-art-title">Clinician Cockpit</div>
                <div className="mf-art-row">
                  <div className="mf-chip">Intake</div>
                  <div className="mf-chip mf-chip-active">Investigation</div>
                  <div className="mf-chip">Treatment</div>
                  <div className="mf-chip">Safety</div>
                </div>
                <div className="mf-art-skeleton">
                  <div className="mf-skel skel-wide" />
                  <div className="mf-skel skel-mid" />
                  <div className="mf-skel skel-wide" />
                  <div className="mf-skel skel-mid" />
                </div>
              </div>

              <div className="mf-art-card mf-art-card-bottom">
                <div className="mf-art-title">Safety Guardrail</div>
                <div className="mf-alert">
                  <div className="mf-alert-dot" />
                  <div>
                    <div className="mf-alert-title">Potential interaction detected</div>
                    <div className="mf-alert-sub">Review • Edit • Override with note</div>
                  </div>
                </div>
                <div className="mf-art-actions">
                  <button className="mf-btn mf-btn-danger" type="button">Abort/Edit</button>
                  <button className="mf-btn mf-btn-ghost" type="button">Override</button>
                </div>
              </div>

              <div className="mf-glow" aria-hidden="true" />
            </div>
          </div>
        </section>

        <section className="mf-section" id="how">
          <div className="mf-container">
            <h2>How it works (staged workflow)</h2>
            <div className="mf-steps">
              <div className="mf-step">
                <div className="mf-step-num">1</div>
                <div>
                  <div className="mf-step-title">Intake & Triage</div>
                  <div className="mf-step-text">
                    Capture symptoms + history, generate a structured summary, and propose tests.
                    Doctor confirms or edits before ordering.
                  </div>
                </div>
              </div>
              <div className="mf-step">
                <div className="mf-step-num">2</div>
                <div>
                  <div className="mf-step-title">Investigation</div>
                  <div className="mf-step-text">
                    View labs and imaging placeholders. Findings are suggested; doctor approves/adjusts.
                  </div>
                </div>
              </div>
              <div className="mf-step">
                <div className="mf-step-num">3</div>
                <div>
                  <div className="mf-step-title">Treatment Planning</div>
                  <div className="mf-step-text">
                    Suggest diagnosis and plan; doctor edits and finalizes prior to prescribing.
                  </div>
                </div>
              </div>
              <div className="mf-step">
                <div className="mf-step-num">4</div>
                <div>
                  <div className="mf-step-title">Safety Guardrail</div>
                  <div className="mf-step-text">
                    Check interactions/contraindications using patient history. Alert requires explicit doctor action.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mf-section" id="features">
          <div className="mf-container">
            <h2>Built for clinicians</h2>
            <div className="mf-cards">
              <div className="mf-card">
                <h3>Human-in-the-loop by design</h3>
                <p>Every critical decision is a STOP node with confirm/edit/override actions.</p>
              </div>
              <div className="mf-card">
                <h3>Explainable outputs</h3>
                <p>Recommendations appear as checklists and cards with traceable “why” sections.</p>
              </div>
              <div className="mf-card">
                <h3>Fast demo workflow</h3>
                <p>Dummy patients, labs, and imaging previews let you showcase the end-to-end flow.</p>
              </div>
            </div>
          </div>
        </section>

        <section className="mf-section" id="security">
          <div className="mf-container mf-security">
            <div>
              <h2>Privacy-first deployment</h2>
              <p>
                The demo mimics a local hospital deployment model: no internet required, and patient data
                remains within the system boundary.
              </p>
            </div>
            <div className="mf-security-box">
              <div className="mf-security-row">
                <span className="mf-check" aria-hidden="true">✓</span>
                <span>Local-first architecture (demo)</span>
              </div>
              <div className="mf-security-row">
                <span className="mf-check" aria-hidden="true">✓</span>
                <span>Clear approval gates for safety</span>
              </div>
              <div className="mf-security-row">
                <span className="mf-check" aria-hidden="true">✓</span>
                <span>Audit-friendly overrides</span>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="mf-footer">
        <div className="mf-container mf-footer-inner">
          <div>© {new Date().getFullYear()} Med-Flow (demo)</div>
          <div className="mf-footer-links">
            <a href="#how">Workflow</a>
            <a href="#features">Features</a>
            <a href="#security">Security</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
