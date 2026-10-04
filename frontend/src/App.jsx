import { useState } from 'react'
import mockData from './mockData'
import './App.css'

const statusLabels = {
  supported: 'مدعوم',
  partially_supported: 'مدعوم جزئيًا',
  needs_context: 'يحتاج إلى سياق',
  needs_review: 'يحتاج إلى مراجعة',
}

function ClaimReview({ claim, index, decision, onDecision }) {
  return (
    <article className="claim-review" aria-labelledby={`claim-${index}`}>
      <div className="claim-topline">
        <span className="claim-number">الادعاء {index + 1}</span>
        <span className={`status status-${claim.status}`}>
          <span className="status-dot" aria-hidden="true" />
          <span className="sr-only">التقييم الآلي: </span>{statusLabels[claim.status]}
        </span>
      </div>
      <h3 id={`claim-${index}`} className="claim-text">{claim.claim}</h3>

      <div className="evidence-section">
        <h4>الدليل</h4>
        <blockquote>{claim.evidence}</blockquote>
        <dl className="source-details">
          <div><dt>المصدر</dt><dd>{claim.source_name}</dd></div>
          <div><dt>موضع المصدر</dt><dd>{claim.source_location}</dd></div>
        </dl>
      </div>

      <div className="review-explanation">
        <div><h4>لماذا هذا التقييم؟</h4><p>{claim.reason}</p></div>
        <div><h4>الصياغة المقترحة</h4><p>{claim.suggestion}</p></div>
      </div>

      <div className="human-review">
        <div className="decision-copy">
          <h4>قرار المراجع</h4>
          <p role="status">{decision === 'approved' ? 'قرارك: اعتماد' : decision === 'review' ? 'قرارك: يحتاج مراجعة' : 'لم يُتخذ قرار بعد'}</p>
        </div>
        <div className="decision-actions" role="group" aria-label={`قرار المراجع للادعاء ${index + 1}`}>
          <button type="button" className="decision-button" aria-pressed={decision === 'approved'} onClick={() => onDecision('approved')}>اعتماد</button>
          <button type="button" className="decision-button" aria-pressed={decision === 'review'} onClick={() => onDecision('review')}>يحتاج مراجعة</button>
        </div>
      </div>
    </article>
  )
}

function App() {
  const [text, setText] = useState('')
  const [claims, setClaims] = useState([])
  const [decisions, setDecisions] = useState({})

  function handleAnalyze(event) {
    event.preventDefault()
    if (!text.trim()) return
    setClaims(mockData.claims)
    setDecisions({})
  }

  function handleTextChange(event) {
    setText(event.target.value)
    setClaims([])
    setDecisions({})
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="header-inner">
          <span className="brand"><span className="brand-mark" aria-hidden="true">س</span>سند الدلالة</span>
          <span className="demo-label">نسخة تجريبية</span>
        </div>
      </header>
      <main className="page">
        <section className="hero" aria-labelledby="page-title">
          <p className="eyebrow">مراجعة المحتوى قبل النشر</p>
          <h1 id="page-title">سند الدلالة</h1>
          <p className="hero-description">راجع ادعاءات المحتوى الدعوي والتعليمي الإسلامي في ضوء المصادر المعتمدة، وافهم الدليل وسبب التقييم قبل اتخاذ قرارك.</p>
          <p className="human-note"><span aria-hidden="true">◎</span> التقييم الآلي يساعدك في المراجعة، والقرار النهائي لك.</p>
        </section>

        <form className="analysis-panel" onSubmit={handleAnalyze}>
          <label htmlFor="content">المحتوى المراد مراجعته</label>
          <p id="content-help" className="input-help">الصق نصًا قصيرًا من منشور أو مادة تعليمية.</p>
          <textarea id="content" rows={7} value={text} onChange={handleTextChange} aria-describedby="content-help demo-note" placeholder="مثال: الرفق في الخطاب الدعوي يساعد على إيصال الرسالة بأسلوب حسن، واستخدام القصص قد يقرّب المعاني للمتعلمين…" />
          <div className="form-actions">
            <span className="character-count">{text.length.toLocaleString('ar-SA')} حرف</span>
            <button className="primary-button" type="submit" disabled={!text.trim()}>تحليل المحتوى <span aria-hidden="true">←</span></button>
          </div>
          <p id="demo-note" className="demo-note">للتجربة فقط: تظهر أربعة ادعاءات ثابتة بمصادر تجريبية، بغض النظر عن النص المدخل.</p>
        </form>

        <p className="results-announcement sr-only" role="status">{claims.length > 0 ? `تم تحديد ${claims.length} ادعاءات. النتائج جاهزة للمراجعة.` : ''}</p>
        {claims.length > 0 && (
          <section className="results" aria-labelledby="results-heading">
            <div className="results-header">
              <div><p className="eyebrow">من الدليل إلى القرار</p><h2 id="results-heading">نتيجة المراجعة</h2></div>
              <span className="claims-count">تم تحديد {claims.length} ادعاءات</span>
            </div>
            <p className="results-help">اقرأ الدليل وموضعه، ثم سجّل قرارك لكل ادعاء. القرارات محلية لهذه الجلسة ولا تُحفظ بعد تحديث الصفحة.</p>
            <div className="claims-list">
              {claims.map((claim, index) => (
                <ClaimReview key={index} claim={claim} index={index} decision={decisions[index]} onDecision={(decision) => setDecisions((current) => ({ ...current, [index]: decision }))} />
              ))}
            </div>
          </section>
        )}
        <footer className="page-footer">سند الدلالة · مراجعة تستند إلى الدليل، بقرار بشري.</footer>
      </main>
    </div>
  )
}

export default App
