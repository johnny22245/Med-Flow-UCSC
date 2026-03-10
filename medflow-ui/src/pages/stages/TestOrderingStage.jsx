import { useEffect, useMemo, useState } from "react";
import { saveConfirmedInvestigationOrders } from "../../services/medflowApi";
import "../../styles/testOrderingStage.css";

const DUMMY_AI_SUGGESTIONS = {
  headache: {
    labs: [
      { code: "cbc", name: "CBC", why: "Rule out infection/inflammation" },
      { code: "bmp", name: "BMP", why: "Electrolytes + renal baseline" },
      { code: "crp", name: "CRP", why: "Inflammation marker" },
    ],
    imaging: [
      { code: "ct_head", name: "CT Head (non-contrast)", why: "Rule out bleed" },
      { code: "mri_brain", name: "MRI Brain w/ contrast", why: "Evaluate focal lesion" },
    ],
  },
  chest_pain: {
    labs: [
      { code: "troponin", name: "Troponin", why: "Myocardial injury" },
      { code: "bmp", name: "BMP", why: "Baseline metabolic status" },
      { code: "cbc", name: "CBC", why: "Anemia/infection" },
    ],
    imaging: [
      { code: "cxr", name: "Chest X-ray", why: "Pulmonary/cardiac screen" },
      { code: "cta_chest", name: "CT Angiography Chest", why: "If PE/dissection suspected" },
    ],
  },
};

function makeOrderItem(test, source, group) {
  return {
    code: test.code,
    name: test.name,
    group,
    source,
    priority: "routine",
    reason: test.why || "",
    selected: true,
  };
}

function inferGroupFromName(name = "") {
  const x = name.toLowerCase();

  if (
    x.includes("x-ray") ||
    x.includes("ct") ||
    x.includes("mri") ||
    x.includes("ultrasound") ||
    x.includes("angiography") ||
    x.includes("scan")
  ) {
    return "imaging";
  }

  return "labs";
}

function normalizeTriageTests(tests = []) {
  return tests.map((t, idx) => {
    const name = t?.name || `Suggested Test ${idx + 1}`;
    return {
      code: `triage_${idx}_${name.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`,
      name,
      group: inferGroupFromName(name),
      source: "ai",
      priority: "routine",
      reason: t?.reason || "",
      selected: t?.selected ?? true,
    };
  });
}

export default function TestOrderingStage({
  activePatient,
  intakeContext,
  triageContext,
  onApproveNext,
  onBack,
}) {
  const patientId = activePatient?.id || "007";

  const conditionKey = useMemo(() => {
    const cc = (intakeContext?.chiefComplaint || "").toLowerCase();
    if (cc.includes("chest")) return "chest_pain";
    if (cc.includes("head") || cc.includes("migraine")) return "headache";
    return "headache";
  }, [intakeContext]);

  const suggested = useMemo(() => {
    return DUMMY_AI_SUGGESTIONS[conditionKey] || DUMMY_AI_SUGGESTIONS.headache;
  }, [conditionKey]);

  const storageKey = useMemo(() => `mf_orders_${patientId}`, [patientId]);

  const backendSuggestedOrders = useMemo(() => {
    return normalizeTriageTests(triageContext?.suggestedTests || []);
  }, [triageContext]);

  const [orders, setOrders] = useState([]);
  const [customName, setCustomName] = useState("");
  const [customGroup, setCustomGroup] = useState("labs");
  const [customReason, setCustomReason] = useState("");
  const [confirmed, setConfirmed] = useState(false);

  // new state for backend save
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  useEffect(() => {
    // Always prefer fresh backend triage suggestions
    if (backendSuggestedOrders.length > 0) {
      setOrders(backendSuggestedOrders);
      setConfirmed(false);
      localStorage.setItem(
        storageKey,
        JSON.stringify({ orders: backendSuggestedOrders, confirmed: false })
      );
      return;
    }

    const raw = localStorage.getItem(storageKey);
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        setOrders(parsed.orders || []);
        setConfirmed(!!parsed.confirmed);
        return;
      } catch {
        // ignore and rebuild below
      }
    }

    const initial = [
      ...suggested.labs.map((t) => makeOrderItem(t, "ai", "labs")),
      ...suggested.imaging.map((t) => makeOrderItem(t, "ai", "imaging")),
    ];
    setOrders(initial);
    setConfirmed(false);
  }, [storageKey, suggested, backendSuggestedOrders]);

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify({ orders, confirmed }));
  }, [orders, confirmed, storageKey]);

  function toggle(code) {
    if (confirmed) return;
    setOrders((prev) =>
      prev.map((o) => (o.code === code ? { ...o, selected: !o.selected } : o))
    );
  }

  function setPriority(code, priority) {
    if (confirmed) return;
    setOrders((prev) =>
      prev.map((o) => (o.code === code ? { ...o, priority } : o))
    );
  }

  function setReason(code, reason) {
    if (confirmed) return;
    setOrders((prev) =>
      prev.map((o) => (o.code === code ? { ...o, reason } : o))
    );
  }

  function addCustom() {
    if (confirmed) return;
    const name = customName.trim();
    if (!name) return;

    const code = `custom_${Date.now()}`;
    setOrders((prev) => [
      {
        code,
        name,
        group: customGroup,
        source: "manual",
        priority: "routine",
        reason: customReason.trim(),
        selected: true,
      },
      ...prev,
    ]);

    setCustomName("");
    setCustomReason("");
  }

  const selectedCount = useMemo(
    () => orders.filter((o) => o.selected).length,
    [orders]
  );

  async function confirmOrders() {
    if (confirmed || selectedCount === 0) return;

    setSaving(true);
    setSaveError("");

    const selectedOrders = orders.filter((o) => o.selected);

    try {
      const payload = {
        patient_id: patientId,
        suggested_tests: orders,
        ordered_tests: selectedOrders,
        notes: null,
        confirmed: true,
        confirmed_at: new Date().toISOString(),
      };

      await saveConfirmedInvestigationOrders(patientId, payload);

      setConfirmed(true);

      localStorage.setItem(
        storageKey,
        JSON.stringify({
          orders,
          confirmed: true,
        })
      );

      if (typeof onApproveNext === "function") {
        onApproveNext({
          stage: "tests",
          patient_id: patientId,
          confirmed_at: payload.confirmed_at,
          orders: selectedOrders,
        });
      }
    } catch (err) {
      setSaveError(err?.message || "Failed to save confirmed orders.");
      setConfirmed(false);
    } finally {
      setSaving(false);
    }
  }

  const labs = orders.filter((o) => o.group === "labs");
  const imaging = orders.filter((o) => o.group === "imaging");

  return (
    <div className="mf-stage">
      <div className="mf-stage-header">
        <div>
          <div className="mf-h2">Test Ordering</div>
          <div className="mf-subtext">
            {backendSuggestedOrders.length > 0 ? (
              <>AI triage suggested tests from backend. Doctor can override before ordering.</>
            ) : (
              <>
                AI suggested tests for <b>{conditionKey.replace("_", " ")}</b>. Doctor can override before ordering.
              </>
            )}
          </div>
        </div>

        <div className="mf-stage-meta">
          <div className="mf-meta-card">
            <div className="mf-meta-label">Patient</div>
            <div className="mf-meta-value">{activePatient?.name || "—"}</div>
          </div>
          <div className="mf-meta-card">
            <div className="mf-meta-label">Selected</div>
            <div className="mf-meta-value">{selectedCount}</div>
          </div>
          <div className="mf-meta-card">
            <div className="mf-meta-label">Status</div>
            <div className="mf-meta-value">
              <span className={`mf-badge ${confirmed ? "mf-badge-ok" : "mf-badge-pending"}`}>
                {confirmed ? "Ordered" : "Draft"}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="mf-cockpit-grid">
        <div className="mf-cockpit-left">
          <div className="mf-card mf-card-pad">
            <div className="mf-section-title">Suggested tests</div>

            <div className="mf-split">
              <div className="mf-list">
                <div className="mf-list-head">Labs</div>
                {labs.map((o) => (
                  <div key={o.code} className={`mf-order-row ${o.selected ? "is-on" : ""}`}>
                    <button
                      className="mf-check"
                      onClick={() => toggle(o.code)}
                      type="button"
                      aria-label="toggle"
                    >
                      <span className={`mf-check-dot ${o.selected ? "on" : ""}`} />
                    </button>

                    <div className="mf-order-main">
                      <div className="mf-order-title">
                        {o.name}
                        <span className={`mf-tag ${o.source === "ai" ? "mf-tag-ai" : "mf-tag-manual"}`}>
                          {o.source === "ai" ? "AI" : "Manual"}
                        </span>
                      </div>

                      <div className="mf-order-sub">
                        <input
                          className="mf-inline"
                          value={o.reason}
                          onChange={(e) => setReason(o.code, e.target.value)}
                          placeholder="Reason / clinical context"
                          disabled={confirmed}
                        />
                      </div>

                      <div className="mf-row-actions">
                        <button
                          className={`mf-btn-pill ${o.priority === "routine" ? "is-active" : ""}`}
                          onClick={() => setPriority(o.code, "routine")}
                          disabled={confirmed}
                          type="button"
                        >
                          Routine
                        </button>
                        <button
                          className={`mf-btn-pill ${o.priority === "urgent" ? "is-active" : ""}`}
                          onClick={() => setPriority(o.code, "urgent")}
                          disabled={confirmed}
                          type="button"
                        >
                          Urgent
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mf-list">
                <div className="mf-list-head">Imaging</div>
                {imaging.map((o) => (
                  <div key={o.code} className={`mf-order-row ${o.selected ? "is-on" : ""}`}>
                    <button
                      className="mf-check"
                      onClick={() => toggle(o.code)}
                      type="button"
                      aria-label="toggle"
                    >
                      <span className={`mf-check-dot ${o.selected ? "on" : ""}`} />
                    </button>

                    <div className="mf-order-main">
                      <div className="mf-order-title">
                        {o.name}
                        <span className={`mf-tag ${o.source === "ai" ? "mf-tag-ai" : "mf-tag-manual"}`}>
                          {o.source === "ai" ? "AI" : "Manual"}
                        </span>
                      </div>

                      <div className="mf-order-sub">
                        <input
                          className="mf-inline"
                          value={o.reason}
                          onChange={(e) => setReason(o.code, e.target.value)}
                          placeholder="Reason / clinical context"
                          disabled={confirmed}
                        />
                      </div>

                      <div className="mf-row-actions">
                        <button
                          className={`mf-btn-pill ${o.priority === "routine" ? "is-active" : ""}`}
                          onClick={() => setPriority(o.code, "routine")}
                          disabled={confirmed}
                          type="button"
                        >
                          Routine
                        </button>
                        <button
                          className={`mf-btn-pill ${o.priority === "urgent" ? "is-active" : ""}`}
                          onClick={() => setPriority(o.code, "urgent")}
                          disabled={confirmed}
                          type="button"
                        >
                          Urgent
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="mf-divider mf-mt12" />

            <div className="mf-section-title">Add custom test</div>
            <div className="mf-custom-grid">
              <select
                className="mf-select"
                value={customGroup}
                onChange={(e) => setCustomGroup(e.target.value)}
                disabled={confirmed}
              >
                <option value="labs">Lab</option>
                <option value="imaging">Imaging</option>
              </select>

              <input
                className="mf-input"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                placeholder="e.g., D-dimer / PT-INR / CTA head-neck"
                disabled={confirmed}
              />

              <input
                className="mf-input"
                value={customReason}
                onChange={(e) => setCustomReason(e.target.value)}
                placeholder="Reason (optional)"
                disabled={confirmed}
              />

              <button className="mf-btn mf-btn-soft" onClick={addCustom} disabled={confirmed}>
                Add
              </button>
            </div>
          </div>
        </div>

        <div className="mf-cockpit-right">
          <div className="mf-card mf-card-pad">
            <div className="mf-h3">Order summary</div>
            <div className="mf-subtext">Review selected tests and confirm.</div>

            <div className="mf-summary">
              {orders.filter((o) => o.selected).map((o) => (
                <div key={o.code} className="mf-summary-row">
                  <div className="mf-summary-left">
                    <div className="mf-summary-title">{o.name}</div>
                    {o.reason ? <div className="mf-subtext">{o.reason}</div> : null}
                  </div>
                  <span className={`mf-badge mf-badge-soft ${o.priority === "urgent" ? "mf-badge-urgent" : ""}`}>
                    {o.priority}
                  </span>
                </div>
              ))}
              {selectedCount === 0 && <div className="mf-muted">No tests selected.</div>}
            </div>

            <div className="mf-actions">
              <button
                className="mf-btn mf-btn-primary"
                onClick={confirmOrders}
                disabled={confirmed || selectedCount === 0 || saving}
                type="button"
              >
                {saving ? "Saving..." : confirmed ? "Orders Confirmed" : "Confirm Orders"}
              </button>

              {saveError && (
                <div className="mf-error-text">
                  {saveError}
                </div>
              )}

              <div className="mf-row">
                <button className="mf-btn-ghost" onClick={onBack} type="button">
                  Back
                </button>
                <button
                  className="mf-btn-ghost"
                  onClick={() => onApproveNext?.({ stage: "tests_skip", patient_id: patientId })}
                  disabled={!confirmed}
                  type="button"
                  title="Proceed after confirming orders"
                >
                  Proceed to Investigation →
                </button>
              </div>

              <div className="mf-muted mf-mt8">
                {backendSuggestedOrders.length > 0
                  ? "Backend triage suggestions loaded."
                  : "Dummy AI only. Later: backend agent generates these suggestions based on intake + risk context."}
              </div>
            </div>
          </div>

          <div className="mf-card mf-card-pad mf-side-help">
            <div className="mf-h4">Demo logic</div>
            <div className="mf-subtext">
              We store draft/confirmed orders in localStorage per patient. Next stage will read these to decide what
              labs/imaging to show (later: backend orchestration).
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}