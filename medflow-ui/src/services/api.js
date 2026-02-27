const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function getDiagnosisSuggestion(patientId) {
  const res = await fetch(`${API_BASE}/api/diagnosis/suggest/${patientId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function confirmDiagnosis(payload) {
  const res = await fetch(`${API_BASE}/api/diagnosis/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// treatment

export async function getTreatmentPlan(patientId) {
  const res = await fetch(`${API_BASE}/api/treatment/plan/${patientId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function draftTreatmentOrder(payload) {
  const res = await fetch(`${API_BASE}/api/treatment/draft`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// safety

export async function runSafetyCheck(payload) {
  const res = await fetch(`${API_BASE}/api/safety/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function submitSafetyDecision(payload) {
  const res = await fetch(`${API_BASE}/api/safety/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// case summary
export async function finalizeCaseSummary(payload) {
  const res = await fetch(`${API_BASE}/api/case-summary/finalize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getCaseSummary(patientId) {
  const res = await fetch(`${API_BASE}/api/case-summary/${patientId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Prescription download settings
export function getPrescriptionPdfUrl(patientId) {
  if (!patientId) return "#";
  return `${API_BASE}/api/prescription/pdf/${patientId}`;
}