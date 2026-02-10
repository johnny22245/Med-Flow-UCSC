import { useEffect, useMemo, useState } from "react";
import "../../styles/investigationStage.css";
import { getInvestigationByPatientId } from "../../services/medflowApi";

function FlagPill({ flag }) {
  const cls =
    flag === "H" ? "mf-pill mf-pill-high" :
    flag === "L" ? "mf-pill mf-pill-low"  :
    "mf-pill mf-pill-normal";
  const label = flag === "H" ? "High" : flag === "L" ? "Low" : "Normal";
  return <span className={cls}>{label}</span>;
}

function formatDateTime(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export default function InvestigationStage({ activePatient, onApproveNext }) {
  // Patient id: prefer whatever intake saved; fallback to demo patient
  const patientId = useMemo(() => {
  return activePatient?.id || "P-007";
}, [activePatient]);

  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [data, setData] = useState(null);

  const [activeTab, setActiveTab] = useState("labs"); // labs | imaging
  const [selectedStudyId, setSelectedStudyId] = useState(null);

  const [doctorNote, setDoctorNote] = useState("");
  const [approved, setApproved] = useState(false);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setErr("");

    getInvestigationByPatientId(patientId)
      .then((res) => {
        if (!mounted) return;
        setData(res);
        const firstStudy = res?.imaging?.[0]?.study_id || null;
        setSelectedStudyId(firstStudy);
      })
      .catch((e) => {
        if (!mounted) return;
        setErr(e?.message || "Failed to load investigation data.");
      })
      .finally(() => mounted && setLoading(false));

    return () => { mounted = false; };
  }, [patientId]);

  const selectedStudy = useMemo(() => {
    if (!data?.imaging?.length) return null;
    return data.imaging.find(s => s.study_id === selectedStudyId) || data.imaging[0];
  }, [data, selectedStudyId]);

  const imageOrigin = useMemo(() => {
    // If image_url is relative (/static/...), make it absolute to backend
    const url = selectedStudy?.image_url;
    if (!url) return "";
    if (url.startsWith("http")) return url;
    const base = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    return `${base}${url}`;
  }, [selectedStudy]);

  const boxes = selectedStudy?.ai_findings?.boxes || [];

  const handleApprove = () => {
    setApproved(true);
    // For now: local gating only. AppShell can advance stage if you pass onApproveNext.
    if (typeof onApproveNext === "function") {
      onApproveNext({
        stage: "investigation",
        patient_id: patientId,
        approved_at: new Date().toISOString(),
        doctor_note: doctorNote,
      });
    }
  };

  return (
    <div className="mf-stage">
      <div className="mf-stage-header">
        <div>
          <div className="mf-h2">Investigation</div>
          <div className="mf-subtext">
            Review labs and imaging. Confirm findings before moving forward.
          </div>
        </div>

        <div className="mf-stage-meta">
          <div className="mf-meta-card">
            <div className="mf-meta-label">Patient ID</div>
            <div className="mf-meta-value">{patientId}</div>
          </div>
          <div className="mf-meta-card">
            <div className="mf-meta-label">Status</div>
            <div className="mf-meta-value">
              <span className={`mf-badge ${approved ? "mf-badge-ok" : "mf-badge-pending"}`}>
                {approved ? "Confirmed" : (data?.status || "pending_review")}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="mf-cockpit-grid">
        {/* LEFT: primary content */}
        <div className="mf-cockpit-left">
          <div className="mf-card mf-card-pad">
            <div className="mf-tabs">
              <button
                className={`mf-tab ${activeTab === "labs" ? "is-active" : ""}`}
                onClick={() => setActiveTab("labs")}
              >
                Labs
              </button>
              <button
                className={`mf-tab ${activeTab === "imaging" ? "is-active" : ""}`}
                onClick={() => setActiveTab("imaging")}
              >
                Imaging
              </button>
            </div>

            {loading && (
              <div className="mf-skeleton">
                <div className="mf-skeleton-line" />
                <div className="mf-skeleton-line" />
                <div className="mf-skeleton-line short" />
              </div>
            )}

            {!loading && err && (
              <div className="mf-alert mf-alert-error">
                <div className="mf-alert-title">Couldn’t load investigation data</div>
                <div className="mf-alert-body">{err}</div>
                <div className="mf-alert-body">
                  Tip: verify backend is running on <code>http://localhost:8000</code> and CORS allows your UI.
                </div>
              </div>
            )}

            {!loading && !err && data && activeTab === "labs" && (
              <div className="mf-labs">
                {data.labs?.map((panel, idx) => (
                  <div key={`${panel.panel}-${idx}`} className="mf-lab-panel">
                    <div className="mf-lab-panel-head">
                      <div>
                        <div className="mf-h3">{panel.panel}</div>
                        <div className="mf-subtext">Collected: {formatDateTime(panel.collected_at)}</div>
                      </div>
                    </div>

                    <div className="mf-table-wrap">
                      <table className="mf-table">
                        <thead>
                          <tr>
                            <th>Test</th>
                            <th>Value</th>
                            <th>Unit</th>
                            <th>Reference</th>
                            <th>Flag</th>
                          </tr>
                        </thead>
                        <tbody>
                          {panel.results?.map((r, rIdx) => (
                            <tr key={`${r.name}-${rIdx}`}>
                              <td className="mf-td-strong">{r.name}</td>
                              <td>{r.value}</td>
                              <td>{r.unit}</td>
                              <td className="mf-td-muted">{r.ref_range}</td>
                              <td><FlagPill flag={r.flag} /></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!loading && !err && data && activeTab === "imaging" && (
              <div className="mf-imaging">
                <div className="mf-imaging-grid">
                  {/* Study list */}
                  <div className="mf-imaging-list">
                    <div className="mf-imaging-list-title">Studies</div>
                    {data.imaging?.map((s) => (
                      <button
                        key={s.study_id}
                        className={`mf-study-item ${selectedStudyId === s.study_id ? "is-selected" : ""}`}
                        onClick={() => setSelectedStudyId(s.study_id)}
                      >
                        <div className="mf-study-top">
                          <span className="mf-badge mf-badge-soft">{s.modality}</span>
                          <span className="mf-subtext">{formatDateTime(s.acquired_at)}</span>
                        </div>
                        <div className="mf-study-main">{s.summary}</div>
                        <div className="mf-study-sub">{s.body_part}</div>
                      </button>
                    ))}
                  </div>

                  {/* Viewer */}
                  <div className="mf-imaging-viewer">
                    <div className="mf-viewer-head">
                      <div>
                        <div className="mf-h3">{selectedStudy?.summary || "Imaging Viewer"}</div>
                        <div className="mf-subtext">
                          {selectedStudy?.modality} · {selectedStudy?.body_part} · {formatDateTime(selectedStudy?.acquired_at)}
                        </div>
                      </div>
                    </div>

                    <div className="mf-image-frame">
                      {imageOrigin ? (
                        <>
                          <img
                            className="mf-image"
                            src={imageOrigin}
                            alt={selectedStudy?.summary || "Imaging"}
                          />
                          {/* Demo overlay boxes (normalized coords from backend) */}
                          {boxes.map((b, i) => (
                            <div
                              key={i}
                              className="mf-ai-box"
                              style={{
                                left: `${b.x * 100}%`,
                                top: `${b.y * 100}%`,
                                width: `${b.w * 100}%`,
                                height: `${b.h * 100}%`,
                              }}
                              title={`${b.label} (${Math.round((b.confidence || 0) * 100)}%)`}
                            />
                          ))}
                        </>
                      ) : (
                        <div className="mf-empty">
                          No image URL found for this study.
                        </div>
                      )}
                    </div>

                    <div className="mf-two-col">
                      <div className="mf-card mf-card-pad mf-mini">
                        <div className="mf-h4">Radiology impression</div>
                        <div className="mf-subtext">{selectedStudy?.radiology_impression || "-"}</div>
                      </div>

                      <div className="mf-card mf-card-pad mf-mini">
                        <div className="mf-h4">AI findings (demo)</div>
                        <div className="mf-subtext">{selectedStudy?.ai_findings?.summary || "-"}</div>
                        {boxes.length > 0 && (
                          <div className="mf-ai-chips">
                            {boxes.map((b, i) => (
                              <span key={i} className="mf-chip">
                                {b.label} · {Math.round((b.confidence || 0) * 100)}%
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT: approval + notes */}
        <div className="mf-cockpit-right">
          <div className="mf-card mf-card-pad">
            <div className="mf-h3">Clinician review</div>
            <div className="mf-subtext">
              Confirm the investigation results before advancing to diagnosis.
            </div>

            <div className="mf-form-row">
                <label className="mf-label">
                    Review note <span className="mf-muted">(optional)</span>
                </label>
                <textarea
                    className="mf-textarea"
                    placeholder="E.g., mild leukocytosis; MRI finding requires neuroradiology confirmation…"
                    rows={5}
                    value={doctorNote}
                    onChange={(e) => setDoctorNote(e.target.value)}
                />
            </div>


            <div className="mf-actions">
              <button
                className="mf-btn mf-btn-primary"
                onClick={handleApprove}
                disabled={loading || !!err || approved}
              >
                {approved ? "Confirmed" : "Confirm & Continue"}
              </button>

              <div className="mf-subtext">
                Next: Diagnosis suggestion + edit (Stage 3).
              </div>
            </div>
          </div>

          <div className="mf-card mf-card-pad mf-side-help">
            <div className="mf-h4">Demo safety note</div>
            <div className="mf-subtext">
              This page uses dummy fixtures and placeholder images served locally by the backend.
              No real PHI or external imaging links are used.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
