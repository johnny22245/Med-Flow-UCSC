import { useState } from "react";
import { getPatientById, uploadReport } from "../../services/medflowApi";

export default function PatientLookupStage({ onPatientSelected }) {

  const [query, setQuery] = useState("");
  const [patient, setPatient] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [showUpload, setShowUpload] = useState(false);
  const [file, setFile] = useState(null);
  const [reportType, setReportType] = useState("lab");
  const [testCode, setTestCode] = useState("");

  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");

  async function searchPatient() {
    if (!query.trim()) return;

    setLoading(true);
    setError("");
    setPatient(null);

    try {
      const data = await getPatientById(query.trim());
      setPatient(data);
    } catch (err) {
      setError("Patient not found");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload() {
    if (!file || !patient) return;

    setUploading(true);
    setUploadMsg("");

    try {
      await uploadReport(patient.id, file, reportType, testCode);

      setUploadMsg("Report uploaded successfully");
      setFile(null);
      setTestCode("");

    } catch (err) {
      setUploadMsg("Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mf-stage">

      <div className="mf-h2">Patient Lookup</div>

      <div className="mf-card mf-card-pad mf-mt12">

        {/* Search Row */}

        <div className="mf-row" style={{ gap: 10 }}>

          <input
            className="mf-input"
            placeholder="Enter Patient ID (e.g. P-0007)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") searchPatient();
            }}
            style={{ maxWidth: 300 }}
          />

          <button
            className="mf-btn mf-btn-primary"
            onClick={searchPatient}
          >
            Search
          </button>

        </div>

        {loading && (
          <div className="mf-muted mf-mt12">
            Searching patient...
          </div>
        )}

        {error && (
          <div className="mf-error-text mf-mt12">
            {error}
          </div>
        )}

        {/* Patient Card */}

        {patient && (

          <div className="mf-card mf-card-pad mf-mt16">

            <div className="mf-h3">{patient.name}</div>

            <div className="mf-subtext">
              MRN: {patient.id}
            </div>

            <div className="mf-subtext">
              Age: {patient.age} | Sex: {patient.sex}
            </div>

            <div className="mf-row mf-mt12" style={{ gap: 10 }}>

              <button
                className="mf-btn mf-btn-soft"
                onClick={() => setShowUpload(!showUpload)}
              >
                Upload Reports
              </button>

              <button
                className="mf-btn mf-btn-primary"
                onClick={() => onPatientSelected(patient)}
              >
                Continue Workflow
              </button>

            </div>

            {/* Upload Panel */}

            {showUpload && (

              <div className="mf-card mf-card-pad mf-mt16">

                <div className="mf-h3">Upload Diagnostic Report</div>

                <div className="mf-row mf-mt8" style={{ gap: 10 }}>

                  <select
                    className="mf-select"
                    value={reportType}
                    onChange={(e) => setReportType(e.target.value)}
                  >
                    <option value="lab">Lab Report</option>
                    <option value="imaging">Imaging Report</option>
                  </select>

                  <input
                    className="mf-input"
                    placeholder="Test Code (e.g. cbc, ct_head)"
                    value={testCode}
                    onChange={(e) => setTestCode(e.target.value)}
                  />

                </div>

                <div className="mf-row mf-mt8" style={{ gap: 10 }}>

                  <input
                    type="file"
                    onChange={(e) => setFile(e.target.files[0])}
                  />

                  <button
                    className="mf-btn mf-btn-primary"
                    onClick={handleUpload}
                    disabled={!file || uploading}
                  >
                    {uploading ? "Uploading..." : "Upload"}
                  </button>

                </div>

                {uploadMsg && (
                  <div className="mf-muted mf-mt8">
                    {uploadMsg}
                  </div>
                )}

              </div>

            )}

          </div>

        )}

      </div>

    </div>
  );
}