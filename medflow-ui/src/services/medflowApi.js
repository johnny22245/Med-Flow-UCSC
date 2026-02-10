const API_BASE = import.meta.env.VITE_MEDFLOW_API_BASE;

async function parseJsonOrThrow(res) {
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    // keep null
  }

  if (!res.ok) {
    const detail = data?.detail || `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return data;
}

// Create/update patient profile + intake payload
export async function createPatientProfile(payload) {
  const res = await fetch(`${API_BASE}/api/patients`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return parseJsonOrThrow(res);
}

// Optional helper (not used yet, but ready for next pages)
export async function getPatient(patientId) {
  const res = await fetch(`${API_BASE}/api/patients/${encodeURIComponent(patientId)}`);
  return parseJsonOrThrow(res);
}

// Optional helper (debug/demo)
export async function listPatients() {
  const res = await fetch(`${API_BASE}/api/patients`);
  return parseJsonOrThrow(res);
}

// investigation API code
export async function getInvestigationByPatientId(patientId) {
  const res = await fetch(`${API_BASE}/api/investigation/${patientId}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" }
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Investigation API failed (${res.status}): ${text}`);
  }
  return res.json();
}
