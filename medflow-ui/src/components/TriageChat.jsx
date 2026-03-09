import { useEffect, useMemo, useState } from "react";
import { answerTriage } from "../services/medflowApi";
import "../styles/triageChat.css";

function getPendingQuestions(triageState) {
  const raw = triageState?.rawOutput || {};
  const list = raw?.clarifying_questions || [];

  return list
    .map((item) => (typeof item === "string" ? item : item?.question || ""))
    .filter(Boolean);
}

function getDisplayHistory(chatHistory = [], pendingQuestions = [], questionIndex = 0) {
  const currentPending = pendingQuestions[questionIndex] || null;

  if (!currentPending) return chatHistory;

  // If the latest assistant message is already the current question,
  // don't render the live question separately again.
  const lastMsg = chatHistory[chatHistory.length - 1];
  const alreadyShown =
    lastMsg &&
    lastMsg.role === "assistant" &&
    String(lastMsg.text).trim() === String(currentPending).trim();

  return alreadyShown ? chatHistory : chatHistory;
}

export default function TriageChat({
  triageState,
  onTriageUpdated,
  onTriageCompleted,
  onClose,
}) {
  const [draftAnswer, setDraftAnswer] = useState("");
  const [localAnswers, setLocalAnswers] = useState([]);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const pendingQuestions = useMemo(
    () => getPendingQuestions(triageState),
    [triageState]
  );

  useEffect(() => {
    setDraftAnswer("");
    setLocalAnswers([]);
    setQuestionIndex(0);
    setError("");
  }, [triageState?.sessionId, triageState?.rawOutput]);

  if (!triageState?.visible) return null;

  const currentQuestion =
    pendingQuestions.length > 0 ? pendingQuestions[questionIndex] : null;

  const displayHistory = getDisplayHistory(
    triageState.chatHistory || [],
    pendingQuestions,
    questionIndex
  );

  const lastHistoryMsg = displayHistory[displayHistory.length - 1];
  const currentAlreadyInHistory =
    currentQuestion &&
    lastHistoryMsg &&
    lastHistoryMsg.role === "assistant" &&
    String(lastHistoryMsg.text).trim() === String(currentQuestion).trim();

  async function handleNext() {
    if (!draftAnswer.trim() || !currentQuestion) return;

    const nextLocal = [
      ...localAnswers,
      { question: currentQuestion, answer: draftAnswer.trim() },
    ];

    setDraftAnswer("");

    const isLast = questionIndex >= pendingQuestions.length - 1;

    if (!isLast) {
      setLocalAnswers(nextLocal);
      setQuestionIndex((x) => x + 1);
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const next = await answerTriage(triageState.sessionId, nextLocal);

      const updated = {
        ...triageState,
        visible: true,
        loading: false,
        status: next.status,
        currentQuestion: next.current_question,
        chatHistory: next.chat_history || [],
        summary: next.summary || "",
        urgency: next.urgency || "",
        suggestedTests: next.suggested_tests || [],
        missingInfo: next.missing_info || [],
        rawOutput: next.raw_output || null,
        error: "",
      };

      onTriageUpdated(updated);

      if (next.status === "completed") {
        onTriageCompleted(updated);
      }
    } catch (e) {
      setError(e.message || "Failed to submit triage answers");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mf-triage-overlay">
      <div className="mf-triage-modal">
        <div className="mf-triage-header">
          <div>
            <div className="mf-triage-title">AI Triage Assistant</div>
            <div className="mf-triage-subtitle">
              {triageState.urgency ? `Urgency: ${triageState.urgency}` : "Clinical follow-up"}
            </div>
          </div>

          <button className="mf-triage-close" onClick={onClose} type="button">
            ×
          </button>
        </div>

        <div className="mf-triage-body">
          {triageState.loading ? (
            <div className="mf-triage-thinking">
              <div className="mf-triage-bubble mf-triage-bubble-ai">Thinking...</div>
            </div>
          ) : (
            <>
              {triageState.summary ? (
                <div className="mf-triage-summary">{triageState.summary}</div>
              ) : null}

              <div className="mf-triage-messages">
                {displayHistory.map((msg, idx) => (
                  <div
                    key={`${msg.role}-${idx}`}
                    className={`mf-triage-row ${
                      msg.role === "assistant"
                        ? "mf-triage-row-ai"
                        : "mf-triage-row-user"
                    }`}
                  >
                    <div
                      className={`mf-triage-bubble ${
                        msg.role === "assistant"
                          ? "mf-triage-bubble-ai"
                          : "mf-triage-bubble-user"
                      }`}
                    >
                      {msg.text}
                    </div>
                  </div>
                ))}

                {localAnswers.map((item, idx) => (
                  <div key={`local-${idx}`}>
                    <div className="mf-triage-row mf-triage-row-ai">
                      <div className="mf-triage-bubble mf-triage-bubble-ai">
                        {item.question}
                      </div>
                    </div>
                    <div className="mf-triage-row mf-triage-row-user">
                      <div className="mf-triage-bubble mf-triage-bubble-user">
                        {item.answer}
                      </div>
                    </div>
                  </div>
                ))}

                {triageState.status === "awaiting_answer" &&
                currentQuestion &&
                !currentAlreadyInHistory ? (
                  <div className="mf-triage-row mf-triage-row-ai">
                    <div className="mf-triage-bubble mf-triage-bubble-ai">
                      {currentQuestion}
                    </div>
                  </div>
                ) : null}

                {triageState.status === "completed" ? (
                  <div className="mf-triage-complete">
                    <div className="mf-triage-complete-title">Suggested tests</div>
                    <div className="mf-triage-chip-row">
                      {(triageState.suggestedTests || []).map((t, idx) => (
                        <span key={`${t.name}-${idx}`} className="mf-triage-chip">
                          {t.name}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            </>
          )}
        </div>

        {triageState.status === "awaiting_answer" ? (
          <div className="mf-triage-inputbar">
            <textarea
              className="mf-triage-textarea"
              rows={3}
              value={draftAnswer}
              onChange={(e) => setDraftAnswer(e.target.value)}
              placeholder="Type your answer..."
              disabled={submitting}
            />
            <button
              className="mf-triage-send"
              onClick={handleNext}
              disabled={submitting || !draftAnswer.trim()}
              type="button"
            >
              {submitting
                ? "Submitting..."
                : questionIndex < pendingQuestions.length - 1
                ? "Next"
                : "Send"}
            </button>
          </div>
        ) : null}

        {triageState.status === "completed" ? (
          <div className="mf-triage-footer">
            <button
              className="mf-triage-primary"
              onClick={() => onTriageCompleted(triageState)}
              type="button"
            >
              Continue to Test Ordering
            </button>
          </div>
        ) : null}

        {error ? <div className="mf-triage-error">{error}</div> : null}
      </div>
    </div>
  );
}