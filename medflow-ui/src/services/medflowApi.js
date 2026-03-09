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

export async function listPatients() {
  const res = await fetch(`${API_BASE}/api/patients`);
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
export async function getInvestigationByPatientId(patientId) {
  const res = await fetch(`${API_BASE}/api/investigation/${patientId}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  return parseJsonOrThrow(res);
}