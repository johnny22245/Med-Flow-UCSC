const API_BASE = import.meta.env.VITE_MEDFLOW_API_BASE;

async function parseJsonOrThrow(res) {
  const text = await res.text();
  let data = null;

  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }

  if (!res.ok) {
    const detail = data?.detail || `Request failed (${res.status})`;
    throw new Error(detail);
  }

  return data;
}

// --------------------
// Patient APIs
// --------------------
export async function createPatientProfile(payload) {
  const res = await fetch(`${API_BASE}/api/patients`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return parseJsonOrThrow(res);
}

export async function getPatient(patientId) {
  const res = await fetch(
    `${API_BASE}/api/patients/${encodeURIComponent(patientId)}`
  );
  return parseJsonOrThrow(res);
}

// --------------------
// Triage APIs
// --------------------
export async function startTriage(patientId) {
  const res = await fetch(`${API_BASE}/api/triage/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patient_id: patientId }),
  });

  return parseJsonOrThrow(res);
}

export async function answerTriage(sessionId, answers) {
  const res = await fetch(`${API_BASE}/api/triage/${sessionId}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers }),
  });

  return parseJsonOrThrow(res);
}

// --------------------
// Investigation APIs
// --------------------
// get reports
export async function getInvestigationByPatientId(patientId) {
  const res = await fetch(
    `${API_BASE}/api/investigation/${encodeURIComponent(patientId)}`
  );

  if (!res.ok) {
    throw new Error("Failed to load investigation data");
  }

  return res.json();
}

// COnfirm Test order APIs
export async function saveConfirmedInvestigationOrders(patientId, payload) {
  const res = await fetch(
    `${API_BASE}/api/investigation/${encodeURIComponent(patientId)}/orders`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Failed to save confirmed investigation orders");
  }

  return res.json();
}

// look up patient
export async function listPatients() {
  const res = await fetch(`${API_BASE}/api/patients`);
  if (!res.ok) {
    throw new Error("Failed to fetch patients");
  }
  return res.json();
}

export async function getPatientById(patientId) {

  const res = await fetch(
    `${API_BASE}/api/patients/${encodeURIComponent(patientId)}`
  );

  if (!res.ok) {
    throw new Error("Patient not found");
  }

  return res.json();
}

// report upload
export async function uploadReport(patientId, file, reportType, testCode) {

  const form = new FormData()

  form.append("file", file)
  form.append("report_type", reportType)
  form.append("test_code", testCode)

  const res = await fetch(
    `${API_BASE}/api/investigation/${patientId}/upload`,
    {
      method: "POST",
      body: form
    }
  )

  if (!res.ok) {
    throw new Error("Upload failed")
  }

  return res.json()
}

async function handleJson(res) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data?.detail || data?.message || "Request failed");
  }
  return data;
}

export async function analyzeImagingReport(patientId, filename) {
  const res = await fetch(`${API_BASE}/api/investigation/${patientId}/imaging/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename }),
  });
  return handleJson(res);
}

export async function confirmImagingReview(patientId, payload) {
  const res = await fetch(`${API_BASE}/api/investigation/${patientId}/imaging/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleJson(res);
}