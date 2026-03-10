import { useEffect, useMemo, useState } from "react";
import {
  getInvestigationByPatientId,
  analyzeImagingReport,
  confirmImagingReview,
} from "../../services/medflowApi";
import "../../styles/investigationStage.css";

const API_BASE = import.meta.env.VITE_MEDFLOW_API_BASE || "http://localhost:24400/api";
const BACKEND_ORIGIN = API_BASE.replace(/\/api\/?$/, "");

function buildReportUrl(report, patientId) {
  if (!report) return null;

  if (report.url) {
    if (report.url.startsWith("http://") || report.url.startsWith("https://")) {
      return report.url;
    }
    return `${BACKEND_ORIGIN}${report.url}`;
  }

  if (report.filename && patientId) {
    return `${BACKEND_ORIGIN}/reports/${patientId}/${report.filename}`;
  }

  return null;
}

function fileTypeFromName(name = "") {
  const x = name.toLowerCase();
  if (x.endsWith(".pdf")) return "pdf";
  if (x.endsWith(".png") || x.endsWith(".jpg") || x.endsWith(".jpeg") || x.endsWith(".webp") || x.endsWith(".gif")) {
    return "image";
  }
  return "other";
}

function clampInt(v, fallback = 0) {
  const n = parseInt(v, 10);
  return Number.isFinite(n) ? n : fallback;
}

export default function InvestigationStage({ activePatient, onApproveNext }) {
  const patientId = activePatient?.id;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [payload, setPayload] = useState(null);
  const [selectedReportIdx, setSelectedReportIdx] = useState(0);
  const [clinicianNote, setClinicianNote] = useState("");
  const [confirmed, setConfirmed] = useState(false);

  const [analyzing, setAnalyzing] = useState(false);
  const [savingReview, setSavingReview] = useState(false);
  const [aiResult, setAiResult] = useState(null);
  const [editableBox, setEditableBox] = useState({
    xmin: 0,
    ymin: 0,
    xmax: 0,
    ymax: 0,
  });

  useEffect(() => {
    async function loadInvestigation() {
      if (!patientId) {
        setLoading(false);
        setError("No active patient selected.");
        return;
      }

      setLoading(true);
      setError("");

      try {
        const data = await getInvestigationByPatientId(patientId);
        setPayload(data?.payload || null);
      } catch (err) {
        setError(err?.message || "Failed to load investigation data.");
      } finally {
        setLoading(false);
      }
    }

    loadInvestigation();
  }, [patientId]);

  const uploadedReports = useMemo(() => {
    return payload?.uploaded_reports || [];
  }, [payload]);

  const selectedReport = uploadedReports[selectedReportIdx] || null;
  const selectedReportKind = fileTypeFromName(selectedReport?.filename || "");
  const selectedReportUrl = buildReportUrl(selectedReport, patientId);

  useEffect(() => {
    setAiResult(null);
    setEditableBox({ xmin: 0, ymin: 0, xmax: 0, ymax: 0 });
    setClinicianNote("");
    setConfirmed(false);
  }, [selectedReportIdx]);

  function syncBox(box) {
    if (!box) {
      setEditableBox({ xmin: 0, ymin: 0, xmax: 0, ymax: 0 });
      return;
    }
    setEditableBox({
      xmin: clampInt(box.xmin),
      ymin: clampInt(box.ymin),
      xmax: clampInt(box.xmax),
      ymax: clampInt(box.ymax),
    });
  }

  async function runImagingAnalysis() {
    if (!selectedReport || selectedReportKind !== "image") return;

    setAnalyzing(true);
    setError("");

    try {
      const data = await analyzeImagingReport(patientId, selectedReport.filename);
      const result = data?.imaging_ai || null;
      setAiResult(result);
      syncBox(result?.clinician_box || result?.ai_box);

      if (result?.llava_summary) {
        setClinicianNote(result.llava_summary);
      }
    } catch (err) {
      setError(err?.message || "Imaging analysis failed.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function confirmAndContinue() {
    if (!selectedReport) return;

    try {
      setSavingReview(true);
      setError("");

      if (selectedReportKind === "image" && aiResult) {
        await confirmImagingReview(patientId, {
          filename: selectedReport.filename,
          clinician_note: clinicianNote,
          clinician_box: editableBox,
        });
      }

      setConfirmed(true);

      onApproveNext?.({
        stage: "investigation",
        patient_id: patientId,
        note: clinicianNote,
        reviewed_report: selectedReport?.filename || null,
        clinician_box: editableBox,
        ai_summary: aiResult?.llava_summary || null,
      });
    } catch (err) {
      setError(err?.message || "Failed to save review.");
    } finally {
      setSavingReview(false);
    }
  }

  const modelSize = aiResult?.image_size_model || { width: 256, height: 256 };
  const hasBox =
    aiResult?.clinician_box ||
    aiResult?.ai_box ||
    (editableBox.xmax > editableBox.xmin && editableBox.ymax > editableBox.ymin);

  const overlayStyle = {
    left: `${(editableBox.xmin / modelSize.width) * 100}%`,
    top: `${(editableBox.ymin / modelSize.height) * 100}%`,
    width: `${((editableBox.xmax - editableBox.xmin) / modelSize.width) * 100}%`,
    height: `${((editableBox.ymax - editableBox.ymin) / modelSize.height) * 100}%`,
  };

  return (
    <div className="mf-stage">
      <div className="mf-stage-header">
        <div>
          <div className="mf-h2">Investigation Workspace</div>
          <div className="mf-subtext">
            Review uploaded lab and imaging reports for the selected patient.
          </div>
        </div>

        <div className="mf-stage-meta">
          <div className="mf-meta-card">
            <div className="mf-meta-label">Patient</div>
            <div className="mf-meta-value">{activePatient?.name || "—"}</div>
          </div>
          <div className="mf-meta-card">
            <div className="mf-meta-label">MRN</div>
            <div className="mf-meta-value">{patientId || "—"}</div>
          </div>
          <div className="mf-meta-card">
            <div className="mf-meta-label">Reports</div>
            <div className="mf-meta-value">{uploadedReports.length}</div>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="mf-card mf-card-pad">
          <div className="mf-muted">Loading investigation data...</div>
        </div>
      ) : error ? (
        <div className="mf-card mf-card-pad">
          <div className="mf-error-text">{error}</div>
        </div>
      ) : (
        <div className="mf-cockpit-grid">
          <div className="mf-cockpit-left">
            <div className="mf-card mf-card-pad">
              <div className="mf-section-title">Uploaded Reports</div>

              {uploadedReports.length === 0 ? (
                <div className="mf-muted mf-mt8">
                  No uploaded reports found for this patient yet.
                </div>
              ) : (
                <div className="mf-list mf-mt12">
                  {uploadedReports.map((r, idx) => (
                    <button
                      key={`${r.filename}-${idx}`}
                      type="button"
                      className={`mf-order-row ${idx === selectedReportIdx ? "is-on" : ""}`}
                      onClick={() => setSelectedReportIdx(idx)}
                      style={{
                        width: "100%",
                        textAlign: "left",
                        border: "none",
                        background: "transparent",
                        cursor: "pointer",
                      }}
                    >
                      <div className="mf-order-main">
                        <div className="mf-order-title">
                          {r.filename}
                          <span className="mf-tag mf-tag-ai">{r.report_type || "report"}</span>
                        </div>

                        <div className="mf-subtext">Test code: {r.test_code || "—"}</div>
                        <div className="mf-subtext">
                          Uploaded: {r.uploaded_at ? new Date(r.uploaded_at).toLocaleString() : "—"}
                        </div>
                        <div className="mf-subtext">
                          Size: {r.size ? `${Math.round(r.size / 1024)} KB` : "—"}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="mf-cockpit-right">
            <div className="mf-card mf-card-pad">
              <div className="mf-h3">Report Preview</div>

              {!selectedReport ? (
                <div className="mf-muted mf-mt8">Select a report to preview.</div>
              ) : (
                <>
                  <div className="mf-subtext mf-mt8">
                    <b>{selectedReport.filename}</b>
                  </div>

                  <div className="mf-subtext">
                    Type: {selectedReport.report_type || "—"} | Test: {selectedReport.test_code || "—"}
                  </div>

                  <div className="mf-mt12">
                    {selectedReportKind === "pdf" ? (
                      <iframe
                        title={selectedReport.filename}
                        src={selectedReportUrl}
                        style={{
                          width: "100%",
                          height: "480px",
                          border: "1px solid #d7e0ea",
                          borderRadius: "12px",
                          background: "#fff",
                        }}
                      />
                    ) : selectedReportKind === "image" ? (
                      <div className="mf-image-frame">
                        <img
                          src={selectedReportUrl}
                          alt={selectedReport.filename}
                          className="mf-image"
                        />
                        {hasBox ? <div className="mf-ai-box" style={overlayStyle} /> : null}
                      </div>
                    ) : (
                      <div className="mf-muted">
                        Preview not available for this file type.
                      </div>
                    )}
                  </div>

                  <div className="mf-actions-inline mf-mt12">
                    <a
                      href={selectedReportUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="mf-btn mf-btn-soft"
                    >
                      Open Report
                    </a>

                    {selectedReportKind === "image" ? (
                      <button
                        className="mf-btn mf-btn-primary"
                        type="button"
                        onClick={runImagingAnalysis}
                        disabled={analyzing}
                      >
                        {analyzing ? "Analyzing..." : "Run AI Imaging Analysis"}
                      </button>
                    ) : null}
                  </div>

                  {selectedReportKind === "image" && aiResult ? (
                    <div className="mf-ai-panel mf-mt12">
                      <div className="mf-h4">AI Imaging Result</div>

                      <div className="mf-two-col mf-mt8">
                        <div className="mf-mini-box">
                          <div className="mf-label">Use case</div>
                          <div>{aiResult.use_case || "—"}</div>
                        </div>
                        <div className="mf-mini-box">
                          <div className="mf-label">Status</div>
                          <div>{aiResult.status || "—"}</div>
                        </div>
                      </div>

                      <div className="mf-mt12">
                        <div className="mf-label">AI Finding Summary</div>
                        <div className="mf-summary-box">{aiResult.llava_summary || "—"}</div>
                      </div>

                      <div className="mf-mt12">
                        <div className="mf-label">Editable Detection Box (model-space coordinates)</div>
                        <div className="mf-box-grid">
                          <label className="mf-form-row">
                            <span>X min</span>
                            <input
                              className="mf-input"
                              value={editableBox.xmin}
                              onChange={(e) =>
                                setEditableBox((p) => ({ ...p, xmin: clampInt(e.target.value, 0) }))
                              }
                            />
                          </label>
                          <label className="mf-form-row">
                            <span>Y min</span>
                            <input
                              className="mf-input"
                              value={editableBox.ymin}
                              onChange={(e) =>
                                setEditableBox((p) => ({ ...p, ymin: clampInt(e.target.value, 0) }))
                              }
                            />
                          </label>
                          <label className="mf-form-row">
                            <span>X max</span>
                            <input
                              className="mf-input"
                              value={editableBox.xmax}
                              onChange={(e) =>
                                setEditableBox((p) => ({ ...p, xmax: clampInt(e.target.value, 0) }))
                              }
                            />
                          </label>
                          <label className="mf-form-row">
                            <span>Y max</span>
                            <input
                              className="mf-input"
                              value={editableBox.ymax}
                              onChange={(e) =>
                                setEditableBox((p) => ({ ...p, ymax: clampInt(e.target.value, 0) }))
                              }
                            />
                          </label>
                        </div>
                      </div>
                    </div>
                  ) : null}
                </>
              )}
            </div>

            <div className="mf-card mf-card-pad mf-mt12">
              <div className="mf-h3">Clinician Review</div>
              <div className="mf-subtext">
                AI finding summary auto-populates here. Edit it before proceeding to diagnosis.
              </div>

              <textarea
                className="mf-input mf-mt12"
                rows={6}
                value={clinicianNote}
                onChange={(e) => setClinicianNote(e.target.value)}
                placeholder="AI review summary will appear here for imaging. You can edit before continue."
              />

              <div className="mf-actions mf-mt12">
                <button
                  className="mf-btn mf-btn-primary"
                  onClick={confirmAndContinue}
                  disabled={uploadedReports.length === 0 || savingReview}
                  type="button"
                >
                  {savingReview ? "Saving..." : confirmed ? "Reviewed" : "Confirm & Continue"}
                </button>
              </div>

              {uploadedReports.length === 0 ? (
                <div className="mf-muted mf-mt8">
                  Upload at least one report from Patient Lookup before continuing.
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}