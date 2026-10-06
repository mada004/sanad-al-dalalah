import { useEffect, useRef, useState } from "react";
import { getImprovement, buildImprovedContent } from "./reviewContent";
import "./App.css";
import bathelLogo from "./assets/bathel.png";
import challengeLogo from "./assets/ai-challenge.png";

function Icon({ name, size = 18 }) {
  const paths = {
    book: <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    chevron: <path d="m9 18 6-6-6-6" />,
    copy: <><rect width="14" height="14" x="8" y="8" rx="2" /><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" /></>,
    file: <><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" /><polyline points="14 2 14 8 20 8" /><path d="M8 13h8M8 17h6" /></>,
    info: <><circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" /></>,
    link: <><path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7.07-7.07l-1.15 1.15" /><path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7.07 7.07l1.15-1.15" /></>,
    review: <><path d="M20 6 9 17l-5-5" /><path d="M16 19H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h8" /></>,
    search: <><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></>,
    sparkle: <><path d="m12 3-1.4 3.6L7 8l3.6 1.4L12 13l1.4-3.6L17 8l-3.6-1.4L12 3Z" /><path d="m5 14-.8 2.2L2 17l2.2.8L5 20l.8-2.2L8 17l-2.2-.8L5 14Z" /></>,
  };

  return (
    <svg
      aria-hidden="true"
      fill="none"
      height={size}
      viewBox="0 0 24 24"
      width={size}
    >
      <g stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8">
        {paths[name]}
      </g>
    </svg>
  );
}

function BrandMark({ size = 44 }) {
  return (
    <svg
      aria-hidden="true"
      className="brand-symbol"
      fill="none"
      height={size}
      viewBox="0 0 44 44"
      width={size}
    >
      <path d="M9 11h8.5c3 0 5.5 2.5 5.5 5.5v11c0 3 2.5 5.5 5.5 5.5H35" />
      <path d="M9 33h6.5c3 0 5.5-2.5 5.5-5.5v-11c0-3 2.5-5.5 5.5-5.5H35" />
      <circle cx="8" cy="11" r="3" />
      <circle cx="8" cy="33" r="3" />
      <rect height="6" rx="2" transform="rotate(45 36 8)" width="6" x="33" y="5" />
      <circle cx="36" cy="33" r="3" />
    </svg>
  );
}

const statusData = {
  supported: { label: "مدعوم", icon: "check" },
  partially_supported: { label: "مدعوم جزئيًا", icon: "link" },
  needs_context: { label: "يحتاج إلى سياق", icon: "info" },
  needs_review: { label: "يحتاج إلى مراجعة", icon: "review" },
};

function StatusBadge({ status }) {
  const item = statusData[status];
  return (
    <span className={`status status--${status}`}>
      <Icon name={item.icon} size={15} />
      {item.label}
    </span>
  );
}

function AppHeader() {
  return (
    <header className="app-header">
      <div className="header-inner">
        <div className="brand" aria-label="سند الدلالة">
          <span className="brand-mark"><BrandMark size={31} /></span>
          <span>
            <strong>سند الدلالة</strong>
            <small>من المعلومة إلى الدليل</small>
          </span>
        </div>

        <div className="institutional-affiliation" aria-label="الجهات والشركاء">
          <div className="partner-logos">
            <span className="logo-frame logo-frame--challenge">
              <img src={challengeLogo} alt="تحدي الذكاء الاصطناعي في خدمة المحتوى الإسلامي" />
            </span>
            <span className="logo-divider" aria-hidden="true" />
            <span className="logo-frame logo-frame--bathel">
              <img src={bathelLogo} alt="باذل" />
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}

function InputSection({ onAnalyze, onEdit, analyzing, currentStep }) {
  const [value, setValue] = useState("");
  const updateValue = (nextValue) => {
    setValue(nextValue);
    onEdit();
  };

  const analyze = (event) => {
    event.preventDefault();
    if (!value.trim()) return;
    onAnalyze(value);
  };

  return (
    <section className="hero">
      <div className="hero-grid">
        <div className="hero-intro">
          <div className="eyebrow"><span className="eyebrow-node" /> مراجعة مدعومة بالدليل</div>
          <h1>راجع المحتوى التعريفي بالإسلام<br /><span>بدليل قابل للتتبع</span></h1>
          <p className="hero-copy">
            يساعد سند الدلالة المعرّفين بالإسلام على مراجعة المحتوى، وربط المعلومات الجوهرية بالمصادر المعتمدة، وبيان مدى دعم الأدلة لها، واقتراح التحسينات عند الحاجة.
          </p>
        </div>

        <div className="evidence-visual" aria-label="مسار بصري من النص إلى الدليل والمصدر">
          <div className="visual-grid" />
          <div className="visual-caption"><BrandMark size={19} /> مسار الدليل</div>
          <div className="document-sheet">
            <div className="document-head">
              <span><Icon name="file" size={14} /> النص</span>
              <small>محتوى قيد المراجعة</small>
            </div>
            <div className="text-fragment text-fragment--wide" />
            <div className="text-fragment text-fragment--medium" />
            <p><mark>الرفق في الخطاب الدعوي</mark> يساعد على إيصال الرسالة بأسلوب حسن.</p>
            <div className="text-fragment text-fragment--short" />
            <span className="document-index">٠١</span>
          </div>

          <svg className="evidence-path" viewBox="0 0 560 330" aria-hidden="true">
            <path d="M414 160 C355 160 368 84 302 84 S250 198 188 198 S146 262 88 262" />
            <path className="evidence-path-glow" d="M414 160 C355 160 368 84 302 84 S250 198 188 198 S146 262 88 262" />
          </svg>

          <div className="path-node path-node--one"><span /> معلومة جوهرية</div>
          <div className="path-node path-node--two"><span /> دليل مطابق</div>
          <div className="path-node path-node--three"><span /> مصدر معتمد</div>

          <div className="evidence-snippet">
            <span className="snippet-label"><Icon name="book" size={14} /> الدليل</span>
            <p>الرفق وحسن اختيار الألفاظ…</p>
            <small>دليل آداب الدعوة</small>
          </div>

          <div className="visual-verdict">
            <span className="verdict-check"><Icon name="check" size={17} /></span>
            <span><small>تقييم النظام</small><strong>مدعوم بدليل مباشر</strong></span>
          </div>
        </div>
      </div>

      <form className="editor-shell" onSubmit={analyze}>
        <div className="editor-label">
          <h2><span className="editor-node"><Icon name="file" size={16} /></span> راجع محتواك</h2>
          <div className="editor-actions">
            {value && (
              <button className="text-button text-button--muted" onClick={() => updateValue("")} type="button">
                مسح النص
              </button>
            )}
          </div>
        </div>
        <FlowSteps currentStep={currentStep} />
        <p id="editor-description" className="editor-description">أدخل المحتوى التعريفي بالإسلام لمراجعته وربط معلوماته بالمصادر المعتمدة.</p>
        <label className="content-label" htmlFor="content">المحتوى الأصلي</label>
        <textarea
          id="content"
          aria-describedby="editor-description"
          onChange={(event) => updateValue(event.target.value)}
          placeholder="ألصق المحتوى المراد مراجعته هنا..."
          value={value}
        />
        <div className="editor-footer">
          <div className="editor-help">
            <span>{value.length.toLocaleString("ar-SA")} حرف</span>
            <i />
            <span>لأفضل نتيجة، أدخل فقرة واضحة ومكتملة.</span>
          </div>
          <button className="primary-button" disabled={!value.trim() || analyzing} type="submit">
            <BrandMark size={23} />
            {analyzing ? "جارٍ تحليل المحتوى…" : "تحليل المحتوى"}
          </button>
        </div>
      </form>

    </section>
  );
}

const journeySteps = ["إدخال النص", "مراجعة المعلومات", "المراجعة البشرية", "النسخة النهائية"];

function FlowSteps({ currentStep }) {
  return <ol className="journey" aria-label="مراحل المراجعة">{journeySteps.map((title, index) => (
    <li key={title} data-state={index < currentStep ? "done" : index === currentStep ? "current" : "pending"} aria-current={index === currentStep ? "step" : undefined}>
      <span aria-hidden="true">{index < currentStep ? <Icon name="check" size={16} /> : (index + 1).toLocaleString("ar-SA")}</span><strong>{title}</strong>
    </li>
  ))}</ol>;
}

const analysisSteps = ["تحديد المعلومات الجوهرية", "ربط المعلومات بالأدلة والمصادر", "إعداد التقييم والتحسينات للمراجع"];

function AnalysisProgress({ text, stage, onCancel }) {
  const root = useRef(null);
  useEffect(() => { root.current?.focus(); }, []);
  return <section className="analysis-progress" ref={root} tabIndex={-1} aria-labelledby="analysis-heading">
    <div><span className="section-kicker">تحليل المحتوى</span><h2 id="analysis-heading">جارٍ إعداد المراجعة</h2>
      <p>لن يُعتمد أي تعديل دون قرارك.</p>
      <ol className="analysis-stage-list">{analysisSteps.map((title, index) => <li key={title} data-state={index < stage ? "done" : index === stage ? "current" : "pending"}><span aria-hidden="true">{index < stage ? <Icon name="check" size={16} /> : index + 1}</span>{title}</li>)}</ol>
      <p role="status" className="sr-only">{analysisSteps[stage]}</p>
      <button className="secondary-button" type="button" onClick={onCancel}>إلغاء التحليل</button>
    </div>
    <div className="analysis-preview"><span className="detail-label">المحتوى قيد المراجعة</span><p>{text}</p></div>
  </section>;
}

function ResultsWorkspace({ claims, originalContent, onFinalChange }) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [decisions, setDecisions] = useState({});
  const [finalContent, setFinalContent] = useState(null);
  const resultsHeading = useRef(null);
  const detail = useRef(null);
  useEffect(() => { resultsHeading.current?.focus(); }, []);
  const selectPoint = (index) => {
    setSelectedIndex(index);
    if (window.matchMedia("(max-width: 820px)").matches) detail.current?.scrollIntoView({ block: "start" });
  };
  const selected = claims[selectedIndex];
  const improvement = getImprovement(selected);
  const decision = decisions[selectedIndex];
  const setDecision = (value) => {
    setDecisions((current) => ({ ...current, [selectedIndex]: value }));
    setFinalContent(null);
    onFinalChange(false);
  };

  return (
    <section className="results-section" id="results">
      <div className="section-heading">
        <div>
          <span className="section-kicker">مساحة عمل المراجع</span>
          <h2 ref={resultsHeading} tabIndex={-1}>نتيجة المراجعة</h2>
          <p>تم تحديد المعلومات الجوهرية القابلة للتحقق ومراجعتها وربطها بالأدلة المتاحة.</p>
        </div>
        <div className="summary-badge"><Icon name="check" size={18} /> اكتمل التحليل</div>
      </div>

      <details className="original-context"><summary>عرض المحتوى الأصلي كاملًا</summary><p>{originalContent}</p></details>
      <div className="workspace">
        <aside className="claims-panel">
          <div className="panel-title">
            <div>
              <span>المعلومات التي تمت مراجعتها</span>
              <small>اختر معلومة لعرض دليلها ونتيجة المراجعة</small>
            </div>
            <b>{claims.length.toLocaleString("ar-SA")}</b>
          </div>
          <div className="claims-list">
            {claims.map((claim, index) => (
              <button
                className={`claim-card ${selectedIndex === index ? "is-selected" : ""}`}
                key={index}
                onClick={() => selectPoint(index)}
                aria-pressed={selectedIndex === index}
                aria-controls="claim-detail"
                type="button"
              >
                <span className="claim-number" aria-label={`المعلومة ${index + 1}`}>{(index + 1).toLocaleString("ar-SA")}</span>
                <span className="claim-content">
                  <StatusBadge status={claim.status} />
                  <strong>{claim.claim}</strong>
                  {decisions[index] && <small className="point-decision">{decisionLabels[decisions[index]]}</small>}
                </span>
                <Icon name="chevron" size={18} />
              </button>
            ))}
          </div>
          <div className="claims-legend">
            <Icon name="info" size={17} />
            <span>التقييم الآلي إرشادي. راجع الدليل وسجّل قرارك لكل معلومة.</span>
          </div>
        </aside>

        <article ref={detail} className="evidence-panel" id="claim-detail" aria-labelledby="claim-heading">
          <div className="evidence-header">
            <div>
              <h3 id="claim-heading">{selected.claim}</h3>
            </div>
            <div className="support-state">
              <small>تقييم النظام</small>
              <StatusBadge status={selected.status} />
            </div>
          </div>

          <div className="comparison-grid">
            <div className="comparison-card comparison-card--claim">
              <span className="comparison-title"><Icon name="file" size={18} /> النص الأصلي</span>
              <p>«{selected.claim}»</p>
            </div>
            <div className="comparison-link" aria-hidden="true">
              <span />
              <Icon name="chevron" size={16} />
              <span />
            </div>
            <div className="comparison-card comparison-card--source">
              <span className="comparison-title"><Icon name="book" size={18} /> الدليل من المصدر</span>
              <blockquote>{selected.evidence.replace(/^مقطع تجريبي:\s*/, "")}</blockquote>
            </div>
          </div>

          <div className="citation">
            <div className="citation-icon"><Icon name="book" size={22} /></div>
            <div className="citation-copy">
              <span>المصدر</span>
              <strong>{selected.source_name === "Dorar.net" ? "الدرر السنية" : selected.source_name.replace(/\s*\(مصدر تجريبي\)/g, "")}</strong>
              <small><b>موضع المصدر:</b> {selected.source_location}</small>
            </div>
          </div>

          <div className={`reason-box assessment-${selected.status}`}>
            <div className="assessment-heading"><span className="detail-label">تقييم النظام</span><StatusBadge status={selected.status} /></div>
            <span className="detail-label"><Icon name="search" size={17} /> سبب التقييم</span>
            <p>{selected.reason.replaceAll("الادعاء", "المعلومة")}</p>
          </div>

          <div className="suggestion-box">
            <div>
              <span className="detail-label"><Icon name="sparkle" size={17} /> التحسين المقترح</span>
              <p>{improvement || (selected.status === "supported"
                ? "لا يحتاج إلى تعديل"
                : selected.status === "needs_review"
                  ? "لم يُقترح تعديل تلقائي. راجع المعلومة والدليل قبل اتخاذ القرار."
                  : "لم يُقترح تعديل تلقائي لهذه المعلومة.")}</p>
            </div>
            {improvement && <button className="secondary-button" type="button" aria-pressed={decision === "improved"} onClick={() => setDecision("improved")}>{decision === "improved" ? "تم اعتماد التحسين" : "اعتماد التحسين"}</button>}
          </div>

          <div className="review-decision">
            <div className="review-copy">
              <span className="detail-label">قرار المراجع</span>
              <p>التقييم الآلي مساعد للمراجعة، والقرار النهائي لك.</p>
              <p role="status">{decision ? `قرارك: ${decisionLabels[decision]}` : "لم يُتخذ قرار بعد"}</p>
            </div>
            <div className="decision-actions" role="group" aria-label="قرار المراجع للمعلومة المحددة">
              {Object.entries(decisionLabels).map(([value, label]) => (
                <button key={value} className={`decision-button decision-button--${value === "specialist" ? "specialist" : "review"}`} type="button" disabled={value === "improved" && !improvement} aria-pressed={decision === value} onClick={() => setDecision(value)}>{label}</button>
              ))}
            </div>
            <div className="review-navigation">
              <button className="review-text-button" disabled={!decision} type="button" onClick={() => { setDecisions((current) => { const next = { ...current }; delete next[selectedIndex]; return next; }); setFinalContent(null); onFinalChange(false); }}>التراجع عن القرار</button>
              {selectedIndex < claims.length - 1 && <button className="review-text-button" type="button" onClick={() => selectPoint(selectedIndex + 1)}>المعلومة التالية ←</button>}
            </div>
          </div>
        </article>
      </div>
      <div className="final-step-actions">
        <p>يمكنك إكمال مراجعة المعلومات واتخاذ القرار المناسب لكل منها.</p>
        <button className="primary-button" type="button" onClick={() => { setFinalContent(buildImprovedContent(originalContent, claims, decisions)); onFinalChange(true); }}>إنشاء النسخة المحسّنة</button>
      </div>
      {finalContent && <FinalReview key={JSON.stringify(finalContent)} originalContent={originalContent} content={finalContent} onBack={() => { onFinalChange(false); setFinalContent(null); document.getElementById("results")?.scrollIntoView({ block: "start" }); }} />}
    </section>
  );
}

const decisionLabels = { original: "اعتماد كما هو", improved: "اعتماد التحسين", specialist: "إحالة للمختص" };

function FinalReview({ originalContent, content, onBack }) {
  const [copyMessage, setCopyMessage] = useState("");
  const [approved, setApproved] = useState(false);
  const finalHeading = useRef(null);
  useEffect(() => { finalHeading.current?.focus(); }, []);
  async function copyText() {
    try {
      if (!navigator.clipboard) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(content.text);
      setCopyMessage("تم نسخ النص");
    } catch {
      setCopyMessage("تعذّر النسخ التلقائي. يمكنك تحديد النص ونسخه يدويًا.");
    }
  }
  return (
    <section className="final-review" aria-labelledby="final-heading">
      <div className="section-heading"><div><span className="section-kicker">المراجعة النهائية</span><h2 ref={finalHeading} tabIndex={-1} id="final-heading">النسخة المحسّنة للمراجعة النهائية</h2><p>نسخة محدثة بناءً على التحسينات التي اعتمدتها، وجاهزة للمراجعة النهائية.</p></div></div>
      <div className="final-comparison">
        <div><h3>المحتوى الأصلي</h3><p className="full-content">{originalContent}</p></div>
        <div><h3>المحتوى المحسّن</h3><p className="full-content">{content.parts.map((part, index) => part.changed ? <mark key={index}>{part.text}</mark> : <span key={index}>{part.text}</span>)}</p></div>
      </div>
      <p className="final-help">{content.applied > 0 ? "الأجزاء المظللة هي التحسينات المعتمدة التي أُدرجت في النص." : "لم يُدرج تعديل في النص؛ احتُفظ بالمحتوى الأصلي."}</p>
      {content.unmatched > 0 && <p className="final-help">هناك {content.unmatched.toLocaleString("ar-SA")} تحسينات معتمدة لم يُعثر على نصها الأصلي المطابق. أدرجها يدويًا عند الحاجة.</p>}
      <div className="final-actions">
        <button className="secondary-button" type="button" onClick={copyText}><Icon name="copy" /> نسخ النص</button>
        <button className="secondary-button" type="button" onClick={onBack}>العودة للمراجعة</button>
        <button className="primary-button" type="button" aria-pressed={approved} onClick={() => setApproved(true)}>{approved ? "تم اعتماد المراجعة" : "اعتماد المراجعة"}</button>
      </div>
      <p role="status" className="final-help">{copyMessage}</p>
      {approved && <p role="status" className="final-help">اعتمدت المراجعة النهائية بقرارك. الاعتماد محفوظ لهذه الجلسة فقط.</p>}
    </section>
  );
}

export default function App() {
  const [claims, setClaims] = useState([]);
  const [originalContent, setOriginalContent] = useState("");
  const [analysisVersion, setAnalysisVersion] = useState(0);
  const [pendingText, setPendingText] = useState(null);
  const [analysisStage, setAnalysisStage] = useState(0);
  const [showFinal, setShowFinal] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  useEffect(() => {
    if (pendingText === null) return;
    const controller = new AbortController();
    let active = true;

    async function analyze() {
      try {
        setAnalysisStage(1);
        const response = await fetch("http://127.0.0.1:8002/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: pendingText }),
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(`Analysis failed: HTTP ${response.status}`);
        setAnalysisStage(2);
        const data = await response.json();
        if (!Array.isArray(data?.claims)) throw new Error("Invalid analysis response");
        const adaptedClaims = data.claims.map((claim) => {
          if (!claim || typeof claim.claim !== "string") {
            throw new Error("Invalid claim in analysis response");
          }
          const evidence = Array.isArray(claim.evidence) ? claim.evidence : [];
          const evidenceText = (field) => evidence
            .map((entry) => typeof entry?.[field] === "string" ? entry[field] : "")
            .join("\n\n");
          return {
            ...claim,
            status: Object.hasOwn(statusData, claim.status) ? claim.status : "needs_review",
            evidence: evidenceText("evidence"),
            source_name: evidenceText("source_name"),
            source_location: evidenceText("source_location"),
            reason: typeof claim.reason === "string" ? claim.reason : "",
            suggestion: typeof claim.suggestion === "string" ? claim.suggestion : "",
          };
        });
        if (!active) return;
        setOriginalContent(pendingText);
        setClaims(adaptedClaims);
        setAnalysisVersion((version) => version + 1);
      } catch (error) {
        if (active && error.name !== "AbortError") {
          setAnalysisError("تعذّر تحليل المحتوى. يرجى المحاولة مرة أخرى.");
        }
      } finally {
        if (active) setPendingText(null);
      }
    }

    analyze();
    return () => {
      active = false;
      controller.abort();
    };
  }, [pendingText]);

  return (
    <div className="app" dir="rtl">
      <AppHeader />
      <div className="page-glow page-glow--one" />
      <div className="page-glow page-glow--two" />
      <main className="container" id="main-content">
        <InputSection analyzing={pendingText !== null} currentStep={showFinal ? 3 : claims.length ? 2 : pendingText !== null ? 1 : 0} onEdit={() => { setAnalysisError(""); setClaims([]); setPendingText(null); setShowFinal(false); }} onAnalyze={(value) => {
          setAnalysisError("");
          setClaims([]);
          setShowFinal(false);
          setAnalysisStage(0);
          setPendingText(value);
        }} />
        {analysisError && <p className="final-help" role="alert">{analysisError}</p>}
        {pendingText !== null && <AnalysisProgress text={pendingText} stage={analysisStage} onCancel={() => setPendingText(null)} />}
        <p className="sr-only" role="status">{claims.length > 0 ? `تمت مراجعة المعلومات. النتائج جاهزة للمراجعة.` : ""}</p>
        {claims.length > 0 && <ResultsWorkspace key={analysisVersion} claims={claims} originalContent={originalContent} onFinalChange={setShowFinal} />}
      </main>
      <footer id="about">
        <span className="footer-brand"><BrandMark size={22} /> سند الدلالة</span>
        <span>أداة مساندة لمراجعة المحتوى التعريفي بالإسلام</span>
        <span>المصادر المعتمدة فقط</span>
      </footer>
    </div>
  );
}

