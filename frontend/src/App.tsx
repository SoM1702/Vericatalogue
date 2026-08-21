import { type ChangeEvent, type FormEvent, useEffect, useMemo, useState } from 'react'
import {
  enrichProduct,
  exportUrl,
  fetchDemoFile,
  getAiStatus,
  getLatestReviewAgentPlan,
  processBatch,
  reviewAttribute,
  reviewQueueExportUrl,
  runReviewAgent,
} from './api'
import type { BatchResult, FieldStatus, ProductAttribute, ProductRecord, RecordOption, ReviewAgentPlan } from './types'
import type { AiStatus } from './api'
import './App.css'

type Screen = 'enrich' | 'workbench' | 'health'

const FIELD_LABELS: Record<string, string> = {
  manufacturer: 'Manufacturer',
  manufacturer_part_number: 'Manufacturer part number',
  product_title: 'Product title',
  product_type: 'Product type',
  material: 'Material',
  size: 'Size',
  end_connection: 'End connection',
  pressure_rating: 'Pressure rating',
  temperature_range: 'Temperature range',
  certifications: 'Certifications',
  description: 'Description',
}

const STATUS_COPY: Record<FieldStatus, string> = {
  verified: 'Verified', inferred: 'Inferred', missing: 'Missing', conflict: 'Conflict',
}

const valueOf = (attribute?: ProductAttribute) =>
  attribute?.reviewed_value || attribute?.normalized_value?.display || 'No source value'

const attributeOf = (product: ProductRecord, field: string) => product.attributes.find((attribute) => attribute.field === field)

function StatusPill({ status }: { status: FieldStatus }) {
  return <span className={`status-pill status-${status}`}>{STATUS_COPY[status]}</span>
}

function App() {
  const [screen, setScreen] = useState<Screen>('enrich')
  const [product, setProduct] = useState<ProductRecord | null>(null)
  const [selectedField, setSelectedField] = useState('pressure_rating')
  const [batch, setBatch] = useState<BatchResult | null>(null)
  const [notice, setNotice] = useState<{ tone: 'success' | 'error'; text: string } | null>(null)

  function openWorkbench(record: ProductRecord, field = 'pressure_rating') {
    setProduct(record)
    setSelectedField(attributeOf(record, field) ? field : record.attributes[0]?.field ?? 'pressure_rating')
    setScreen('workbench')
  }

  return <div className="app-shell">
    <aside className="sidebar" aria-label="Product navigation">
      <div className="brand"><div className="brand-mark" aria-hidden="true">V</div><div><div className="brand-name">VeriCatalog</div><div className="brand-subtitle">Proof workspace</div></div></div>
      <div className="sidebar-section-label">WORKSPACE</div>
      <nav className="nav-list">
        <button className={screen === 'enrich' ? 'nav-item active' : 'nav-item'} onClick={() => setScreen('enrich')}><span className="nav-glyph">⌁</span> Enrich product</button>
        <button className={screen === 'workbench' ? 'nav-item active' : 'nav-item'} onClick={() => setScreen('workbench')}><span className="nav-glyph">◫</span> Evidence &amp; review {product && <span className="nav-dot" aria-label="Product ready for review" />}</button>
        <button className={screen === 'health' ? 'nav-item active' : 'nav-item'} onClick={() => setScreen('health')}><span className="nav-glyph">◌</span> Catalog health</button>
      </nav>
      <div className="sidebar-bottom"><div className="local-badge"><span /> Local deterministic mode</div><p>Evidence stays on this machine. No model key or cloud account required.</p></div>
    </aside>
    <main className="workspace">
      <header className="topbar"><div className="crumb"><span>Industrial Commerce</span><b>/</b><strong>Industrial Valves &amp; Fittings</strong></div><div className="topbar-meta"><span className="synthetic-badge">SYNTHETIC DEMO READY</span><span className="secure-label">Local only</span></div></header>
      {notice && <div className={`toast toast-${notice.tone}`} role="status"><span>{notice.tone === 'success' ? '✓' : '!'}</span>{notice.text}<button onClick={() => setNotice(null)} aria-label="Dismiss message">×</button></div>}
      {screen === 'enrich' && <EnrichScreen product={product} onProduct={setProduct} onOpenWorkbench={openWorkbench} onNotice={setNotice} />}
      {screen === 'workbench' && product && <WorkbenchScreen key={product.id} product={product} selectedField={selectedField} onSelectField={setSelectedField} onProduct={setProduct} onNotice={setNotice} />}
      {screen === 'workbench' && !product && <WorkbenchEmpty onGoToEnrich={() => setScreen('enrich')} />}
      {screen === 'health' && <HealthScreen batch={batch} onBatch={setBatch} onOpenWorkbench={openWorkbench} onNotice={setNotice} />}
    </main>
  </div>
}

function EnrichScreen({ product, onProduct, onOpenWorkbench, onNotice }: {
  product: ProductRecord | null
  onProduct: (product: ProductRecord) => void
  onOpenWorkbench: (product: ProductRecord, field?: string) => void
  onNotice: (notice: { tone: 'success' | 'error'; text: string } | null) => void
}) {
  const [files, setFiles] = useState<File[]>([])
  const [title, setTitle] = useState('')
  const [mpn, setMpn] = useState('')
  const [recordOptions, setRecordOptions] = useState<RecordOption[]>([])
  const [recordIndex, setRecordIndex] = useState(0)
  const [aiCandidateCount, setAiCandidateCount] = useState(0)
  const [isProcessing, setIsProcessing] = useState(false)
  const [aiStatus, setAiStatus] = useState<AiStatus | null>(null)

  useEffect(() => {
    let active = true
    getAiStatus().then((status) => active && setAiStatus(status)).catch(() => active && setAiStatus(null))
    return () => { active = false }
  }, [])

  async function loadDemo(filename = 'synthetic_ball_valve_catalog.pdf') {
    try {
      setFiles([await fetchDemoFile(filename)])
      setTitle(''); setMpn(''); setRecordOptions([]); setRecordIndex(0); setAiCandidateCount(0)
      onNotice({ tone: 'success', text: filename.includes('multi_sku') ? 'Synthetic multi-SKU PDF loaded. Process it, then select the SKU to keep isolated.' : 'Synthetic PDF loaded. Process it to create an evidence-backed record.' })
    } catch (error) { onNotice({ tone: 'error', text: error instanceof Error ? error.message : 'Could not load the demo file.' }) }
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setIsProcessing(true); onNotice(null)
    try {
      const result = await enrichProduct(files, title, mpn, recordIndex)
      onProduct(result.product)
      setRecordOptions(result.record_options)
      setAiCandidateCount(result.ai_candidate_count)
      onNotice({ tone: 'success', text: result.message })
    } catch (error) { onNotice({ tone: 'error', text: error instanceof Error ? error.message : 'Could not process the source.' }) }
    finally { setIsProcessing(false) }
  }

  function chooseFiles(event: ChangeEvent<HTMLInputElement>) {
    setFiles(Array.from(event.target.files ?? []))
    setRecordOptions([])
    setRecordIndex(0)
    setAiCandidateCount(0)
  }

  return <section className="page-section">
    <div className="page-heading"><div><p className="eyebrow">SOURCE → PROOF → PIM</p><h1>Enrich a product, keep the proof.</h1><p className="page-lede">Turn limited valve and fitting information into a structured record where every field can be inspected before PIM export.</p></div><div className="demo-actions"><button className="button button-secondary" onClick={() => loadDemo()} type="button">Load synthetic PDF</button><button className="button button-secondary" onClick={() => loadDemo('synthetic_multi_sku_catalog.pdf')} type="button">Try multi-SKU PDF</button></div></div>
    <div className="trust-strip"><span className="trust-icon">✓</span><p><strong>Truth rule:</strong> only values with direct retained source evidence can be marked Verified. Normalizations always preserve the raw value.</p>{aiStatus && <span className={aiStatus.enabled ? 'ai-mode active' : 'ai-mode'}>{aiStatus.enabled ? `✦ AI candidate mapper · ${aiStatus.model}` : '⌁ Deterministic proof mode'}</span>}</div>
    <form className="enrich-layout" onSubmit={submit}>
      <div className="panel input-panel"><div className="panel-header"><div><span className="step-number">01</span><h2>Add a source</h2></div><span className="format-note">PDF · CSV · XLSX</span></div>
        <label className="upload-zone" htmlFor="source-upload"><span className="upload-icon">↥</span><strong>Drop supplier files here</strong><span>or browse from this device</span><small>PDFs, CSVs, and simple XLSX sheets up to 5 MB. Table-like PDFs create review-required candidates; scanned pages use local OCR when available.</small><input id="source-upload" type="file" accept=".pdf,.csv,.xlsx,application/pdf,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" multiple onChange={chooseFiles} /></label>
        {files.length > 0 && <div className="file-list" aria-live="polite">{files.map((file) => <div className="file-row" key={`${file.name}-${file.size}`}><span>▣</span><div><strong>{file.name}</strong><small>{Math.max(1, Math.ceil(file.size / 1024))} KB · {file.type.includes('pdf') ? 'PDF source' : 'tabular source'}</small></div></div>)}</div>}
        {recordOptions.length > 1 && <div className="record-selector"><div><strong>{recordOptions.length} separate catalog records detected</strong><p>Choose one SKU. Values from the other rows are kept separate.</p></div><label>Catalog record<select value={recordIndex} onChange={(event) => setRecordIndex(Number(event.target.value))}>{recordOptions.map((option) => <option key={option.index} value={option.index}>{option.label}{option.page ? ` · page ${option.page}` : ''}</option>)}</select><small>{recordOptions[recordIndex]?.detected_fields.length ?? 0} supported fields detected in this row</small></label></div>}
        <div className="divider"><span>OR ADD PARTIAL DETAILS</span></div>
        <div className="field-grid"><label>Product title<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. 1 in full port ball valve" /></label><label>Manufacturer part number<input value={mpn} onChange={(event) => setMpn(event.target.value)} placeholder="e.g. NFS-BV-1001" /></label></div>
        <label className="category-field">Category<select defaultValue="industrial_valves_fittings"><option value="industrial_valves_fittings">Industrial Valves &amp; Fittings</option></select></label>
        <button className="button button-primary processing-button" disabled={isProcessing || (!files.length && !title.trim() && !mpn.trim())} type="submit">{isProcessing ? <><span className="spinner" /> Processing source…</> : <>Create evidence-backed record <span>→</span></>}</button>
        <p className="form-footnote">Scanned pages use local Tesseract OCR when it is installed; otherwise the app returns a clear next step. Table-like or document-level evidence is kept as Inferred for human review. {aiStatus?.enabled ? 'When enabled, AI mapping sends source text only to the configured server-side provider.' : 'The default deterministic demo mode never sends a source to an external model.'}</p>
        <p className="ai-footnote">Optional AI mapping is configured server-side in <code>backend/.env</code>. It can suggest only source-quoted candidates, which remain Inferred for review.</p>
      </div>
      <div className="panel record-preview"><div className="panel-header"><div><span className="step-number">02</span><h2>Structured record</h2></div>{product ? <span className="record-state"><i /> Evidence retained</span> : <span className="record-state muted">Awaiting source</span>}</div>{product ? <><ProductPreview product={product} onInspect={onOpenWorkbench} />{aiCandidateCount > 0 && <p className="ai-result-note">✦ AI proposed {aiCandidateCount} source-quoted candidate{aiCandidateCount === 1 ? '' : 's'}; every one remains Inferred until review.</p>}</> : <PreviewEmpty onLoadDemo={loadDemo} />}</div>
    </form>
  </section>
}

function ProductPreview({ product, onInspect }: { product: ProductRecord; onInspect: (product: ProductRecord, field?: string) => void }) {
  const title = attributeOf(product, 'product_title')
  const mpn = attributeOf(product, 'manufacturer_part_number')
  const reviewCount = product.attributes.filter((attribute) => attribute.status !== 'verified').length
  return <div className="record-content"><div className="record-title-row"><div><p className="record-overline">{product.source_kind === 'synthetic_demo' ? 'SYNTHETIC PRODUCT RECORD' : 'NEW PRODUCT RECORD'}</p><h3>{valueOf(title)}</h3><p>{valueOf(mpn)}</p></div><div className="record-score"><strong>{product.attributes.filter((attribute) => attribute.status === 'verified').length}</strong><span>verified fields</span></div></div>
    <div className="attribute-grid">{product.attributes.map((attribute) => <button className="attribute-card" type="button" key={attribute.field} onClick={() => onInspect(product, attribute.field)}><div><span>{FIELD_LABELS[attribute.field]}</span><StatusPill status={attribute.status} /></div><strong>{valueOf(attribute)}</strong>{attribute.raw_value && attribute.raw_value !== attribute.normalized_value?.display && <small>Raw: {attribute.raw_value}</small>}</button>)}</div>
    <div className="record-actions"><button type="button" className="button button-secondary" onClick={() => onInspect(product, 'pressure_rating')}>Inspect evidence <span>→</span></button><a className="text-link" href={exportUrl(product.id, 'json')}>Export JSON</a><a className="text-link" href={exportUrl(product.id, 'csv')}>Export CSV</a>{reviewCount > 0 && <span className="review-callout">{reviewCount} field{reviewCount === 1 ? '' : 's'} require review</span>}</div>
  </div>
}

function PreviewEmpty({ onLoadDemo }: { onLoadDemo: () => void }) {
  return <div className="preview-empty"><div className="empty-orbit"><span>◌</span></div><h3>Evidence starts with a source.</h3><p>Upload a supplier file or add partial product details. Every extracted field will keep its raw value, source snippet, and validation result.</p><button type="button" className="text-button" onClick={onLoadDemo}>Try the synthetic ball valve source →</button><div className="empty-rules"><span>Source traceability</span><span>Deterministic validation</span><span>Human review</span></div></div>
}

function WorkbenchEmpty({ onGoToEnrich }: { onGoToEnrich: () => void }) {
  return <section className="empty-workbench"><p className="eyebrow">EVIDENCE &amp; REVIEW</p><h1>No product is open for review.</h1><p>Create a record first, then each extracted field will expose raw value, normalization, rules, and source evidence here.</p><button className="button button-primary" onClick={onGoToEnrich}>Enrich a product</button></section>
}

function WorkbenchScreen({ product, selectedField, onSelectField, onProduct, onNotice }: {
  product: ProductRecord; selectedField: string; onSelectField: (field: string) => void; onProduct: (product: ProductRecord) => void; onNotice: (notice: { tone: 'success' | 'error'; text: string } | null) => void
}) {
  const selected = attributeOf(product, selectedField) ?? product.attributes[0]
  const [editOpen, setEditOpen] = useState(false)
  const [editValue, setEditValue] = useState(selected?.normalized_value?.display ?? '')
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [agentPlan, setAgentPlan] = useState<ReviewAgentPlan | null>(null)
  const [agentLoading, setAgentLoading] = useState(false)

  useEffect(() => {
    let active = true
    getLatestReviewAgentPlan(product.id).then((plan) => active && setAgentPlan(plan)).catch(() => active && setAgentPlan(null))
    return () => { active = false }
  }, [product.id])

  async function runAgent() {
    setAgentLoading(true)
    try {
      const plan = await runReviewAgent(product.id)
      setAgentPlan(plan)
      const firstTask = plan.tasks[0]
      if (firstTask) {
        onSelectField(firstTask.field)
        setEditOpen(false)
        setEditValue(attributeOf(product, firstTask.field)?.normalized_value?.display ?? '')
        setNote('')
      }
      onNotice({ tone: 'success', text: `Evidence Review Agent completed ${plan.tool_trace.length} local checks. No product values were changed.` })
    } catch (error) { onNotice({ tone: 'error', text: error instanceof Error ? error.message : 'Could not run the Evidence Review Agent.' }) }
    finally { setAgentLoading(false) }
  }

  async function saveReview(action: 'approve' | 'reject' | 'edit') {
    if (!selected) return
    setSaving(true)
    try {
      const updated = await reviewAttribute(product.id, selected.field, action, note, action === 'edit' ? editValue : undefined)
      onProduct(updated); setEditOpen(false); setNote('')
      setAgentPlan(null)
      onNotice({ tone: 'success', text: `Review action saved. Original source evidence remains attached to ${FIELD_LABELS[selected.field]}.` })
    } catch (error) { onNotice({ tone: 'error', text: error instanceof Error ? error.message : 'Could not save the review.' }) }
    finally { setSaving(false) }
  }

  return <section className="workbench-page"><div className="page-heading compact-heading"><div><p className="eyebrow">FIELD-LEVEL PROVENANCE</p><h1>Evidence &amp; review workbench</h1><p className="page-lede">{valueOf(attributeOf(product, 'product_title'))} <span>·</span> {valueOf(attributeOf(product, 'manufacturer_part_number'))}</p></div><div className="workbench-actions"><a className="button button-secondary" href={exportUrl(product.id, 'json')}>Export JSON</a><a className="button button-primary soft" href={exportUrl(product.id, 'csv')}>Export CSV</a></div></div>
    <ReviewAgentPanel plan={agentPlan} loading={agentLoading} onRun={runAgent} onOpenField={(field) => { onSelectField(field); setEditOpen(false); setEditValue(attributeOf(product, field)?.normalized_value?.display ?? ''); setNote('') }} />
    <div className="workbench-layout"><aside className="field-rail"><div className="rail-heading"><span>PRODUCT FIELDS</span><strong>{product.attributes.filter((attribute) => attribute.status !== 'verified').length} to review</strong></div>{product.attributes.map((attribute) => <button key={attribute.field} className={selected?.field === attribute.field ? 'field-item selected' : 'field-item'} onClick={() => { onSelectField(attribute.field); setEditOpen(false); setEditValue(attribute.normalized_value?.display ?? ''); setNote('') }}><span>{FIELD_LABELS[attribute.field]}</span><div><StatusPill status={attribute.status} /><small>{attribute.review_status}</small></div></button>)}</aside>
      {selected && <article className="detail-panel"><div className="detail-topline"><div><p className="eyebrow">ATTRIBUTE REVIEW</p><h2>{FIELD_LABELS[selected.field]}</h2></div><StatusPill status={selected.status} /></div>
        <div className="value-compare"><div><span>EXTRACTED RAW VALUE</span><strong>{selected.raw_value || 'No direct source value'}</strong></div><div className="compare-arrow">→</div><div className="canonical-value"><span>PIM CANONICAL VALUE</span><strong>{valueOf(selected)}</strong>{selected.normalization_explanation && <small>{selected.normalization_explanation}</small>}</div></div>
        <div className="review-signals"><div><span>Confidence</span><strong>{Math.round(selected.confidence * 100)}<small>/100</small></strong><p>Review heuristic</p></div><div><span>Validation</span><strong>{selected.validation_results.every((result) => result.status === 'pass') ? 'Pass' : 'Review'}</strong><p>{selected.validation_results.filter((result) => result.status !== 'pass').length || 'All'} flagged rules</p></div><div><span>Review state</span><strong className={`review-state-${selected.review_status}`}>{selected.review_status}</strong><p>{selected.review_note || 'No reviewer note yet'}</p></div></div>
        {selected.agent_decision && (
          <section className="agent-analysis-section" style={{
            margin: '1rem 0',
            padding: '1rem',
            borderRadius: '6px',
            border: '1px solid var(--border-color)',
            backgroundColor: 'rgba(0, 0, 0, 0.02)',
          }}>
            <p className="eyebrow" style={{ margin: 0, fontSize: '0.75rem', letterSpacing: '0.05em' }}>AGENT ANALYSIS &amp; AUDIT</p>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
              <h4 style={{ margin: 0, fontSize: '0.95rem' }}>Final Recommendation</h4>
              <span className={`decision-badge decision-${selected.agent_decision}`} style={{
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                fontWeight: 'bold',
                fontSize: '0.8rem',
                backgroundColor: selected.agent_decision === 'AUTO_VERIFY' ? '#4caf50' : '#ff9800',
                color: '#fff',
              }}>{selected.agent_decision.replaceAll('_', ' ')}</span>
            </div>
            {selected.agent_reason && (
              <p style={{ margin: '0.5rem 0 0', fontSize: '0.85rem', color: 'var(--muted-color)', fontStyle: 'italic' }}>
                “{selected.agent_reason}”
              </p>
            )}
          </section>
        )}
        <section className="evidence-section"><div className="section-title"><div><p className="eyebrow">RETAINED EVIDENCE</p><h3>{selected.evidence.length} source reference{selected.evidence.length === 1 ? '' : 's'}</h3></div><span className="proof-lock">◈ Evidence-first</span></div>{selected.evidence.length ? selected.evidence.map((evidence, index) => <div className="evidence-card" key={`${evidence.source_file}-${index}`}><div className="evidence-meta"><span className="source-file">▣ {evidence.source_file}</span><span>{evidence.page ? `Page ${evidence.page}` : evidence.row ? `Row ${evidence.row}` : 'Manual input'}</span><span>{evidence.method.replaceAll('_', ' ')}</span></div><blockquote>“{evidence.snippet}”</blockquote></div>) : <div className="no-evidence">No direct source evidence. The field cannot be marked Verified.</div>}</section>
        <section className="validation-section"><p className="eyebrow">DETERMINISTIC VALIDATION</p>{selected.validation_results.map((result) => <div className={`validation-row validation-${result.status}`} key={result.rule}><span>{result.status === 'pass' ? '✓' : result.status === 'warning' ? '!' : '×'}</span><div><strong>{result.rule.replaceAll('_', ' ')}</strong><p>{result.message}</p></div><b>{result.status}</b></div>)}</section>
        <section className="review-section"><div><p className="eyebrow">HUMAN DECISION</p><h3>Record your review</h3><p className="review-helper">Approving or editing does not remove a conflict or change the original source evidence.</p></div><div className="review-buttons"><button className="button button-secondary approve" disabled={saving} onClick={() => saveReview('approve')}>Approve evidence</button><button className="button button-secondary reject" disabled={saving} onClick={() => saveReview('reject')}>Reject field</button><button className="button button-primary soft" disabled={saving} onClick={() => setEditOpen(!editOpen)}>Edit value</button></div>{editOpen && <div className="edit-form"><label>Reviewed value<input value={editValue} onChange={(event) => setEditValue(event.target.value)} /></label><label>Review note (recommended)<textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Why is this reviewed value appropriate?" /></label><button className="button button-primary" disabled={saving || !editValue.trim()} onClick={() => saveReview('edit')}>{saving ? 'Saving…' : 'Save reviewed value'}</button></div>}</section>
      </article>}</div>
  </section>
}

function ReviewAgentPanel({ plan, loading, onRun, onOpenField }: { plan: ReviewAgentPlan | null; loading: boolean; onRun: () => void; onOpenField: (field: string) => void }) {
  const actionCopy: Record<ReviewAgentPlan['tasks'][number]['recommended_action'], string> = {
    resolve_conflict: 'Compare evidence',
    find_source_value: 'Find source value',
    verify_candidate: 'Verify candidate',
  }
  
  const workflowStages = [
    { name: 'Evidence Agent', key: 'evidence_extraction' },
    { name: 'Normalization Agent', key: 'normalization_check' },
    { name: 'Validation Agent', key: 'validation_check' },
    { name: 'Conflict Agent', key: 'conflict_resolution' },
    { name: 'Decision Agent', key: 'decision_agent' },
    { name: 'Policy Engine', key: 'policy_engine' },
  ]

  return <section className="review-agent-panel" aria-label="Evidence Review Agent">
    <div className="agent-heading"><div><p className="eyebrow">BOUNDED AGENTIC WORKFLOW</p><h2>Evidence Review Agent</h2><p>Runs local inspection tools, ranks the human review queue, and leaves every product value unchanged.</p></div><button className="button button-primary agent-run" onClick={onRun} disabled={loading}>{loading ? 'Running local checks…' : plan ? 'Run again' : 'Run review agent'}</button></div>
    {plan && (
      <div className="agent-workflow-stages" style={{
        display: 'flex',
        gap: '0.5rem',
        flexWrap: 'wrap',
        margin: '0.75rem 0',
        padding: '0.5rem',
        borderRadius: '6px',
        backgroundColor: 'rgba(0,0,0,0.02)',
        border: '1px solid var(--border-color)'
      }}>
        {workflowStages.map((stage) => {
          const executed = plan.tool_trace.some((t) => t.tool === stage.key)
          return (
            <span key={stage.key} className={`workflow-stage-pill ${executed ? 'active' : ''}`} style={{
              padding: '0.2rem 0.6rem',
              borderRadius: '1rem',
              fontSize: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.2rem',
              border: '1px solid var(--border-color)',
              backgroundColor: executed ? 'rgba(76, 175, 80, 0.1)' : 'transparent',
              color: executed ? '#4caf50' : 'var(--muted-color)',
            }}>
              {executed ? '✓' : '○'} {stage.name}
            </span>
          )
        })}
      </div>
    )}
    {plan ? <div className="agent-result"><div className="agent-summary"><span className="agent-seal">◈</span><p><strong>{plan.summary}</strong><small>{plan.guardrail}</small></p><span className="agent-mode">{plan.tool_trace.length} local tools · human approval required</span></div>{plan.tasks.length ? <div className="agent-task-list">{plan.tasks.map((task) => <button key={task.field} className="agent-task" onClick={() => onOpenField(task.field)}><div><span className="agent-task-priority">{task.priority}</span><strong>{FIELD_LABELS[task.field]}</strong><StatusPill status={task.status} /></div><p>{task.reason}</p><small>{actionCopy[task.recommended_action]} · {task.evidence_count} evidence reference{task.evidence_count === 1 ? '' : 's'} →</small></button>)}</div> : <div className="agent-clear">No exceptions were found. The agent made no changes and left verified evidence available for spot review.</div>}<details className="agent-trace"><summary>{plan.tool_trace.length} tool calls recorded in the local audit trail</summary><ol>{plan.tool_trace.map((trace) => <li key={trace.tool}><strong>{trace.tool.replaceAll('_', ' ')}</strong><span>{trace.outcome}</span></li>)}</ol></details></div> : <div className="agent-empty"><span>01</span><p>Run the agent after enrichment. It will inspect exceptions, provenance, and validation results before suggesting the next human action.</p><span>02</span><p>It cannot approve, edit, export, or create product facts.</p></div>}
  </section>
}

function HealthScreen({ batch, onBatch, onOpenWorkbench, onNotice }: {
  batch: BatchResult | null; onBatch: (batch: BatchResult) => void; onOpenWorkbench: (product: ProductRecord, field?: string) => void; onNotice: (notice: { tone: 'success' | 'error'; text: string } | null) => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [processing, setProcessing] = useState(false)
  const [filter, setFilter] = useState<'all' | FieldStatus>('all')
  const filtered = useMemo(() => batch?.metrics.priority_products.filter((item) => filter === 'all' || item.statuses.includes(filter)) ?? [], [batch, filter])

  async function loadDemoBatch() {
    try { setFile(await fetchDemoFile('synthetic_valve_batch.csv')); onNotice({ tone: 'success', text: 'Synthetic 60-product batch loaded. Process it to calculate catalog health.' }) }
    catch (error) { onNotice({ tone: 'error', text: error instanceof Error ? error.message : 'Could not load the demo batch.' }) }
  }
  async function submit() {
    if (!file) return
    setProcessing(true)
    try { const result = await processBatch(file); onBatch(result); onNotice({ tone: 'success', text: result.message }) }
    catch (error) { onNotice({ tone: 'error', text: error instanceof Error ? error.message : 'Could not process this batch.' }) }
    finally { setProcessing(false) }
  }

  return <section className="page-section health-page"><div className="page-heading"><div><p className="eyebrow">BATCH DATA QUALITY</p><h1>See where human attention matters.</h1><p className="page-lede">Process a compatible valve/fitting batch, quantify exceptions, and export a focused review queue.</p></div><a className="button button-secondary" href={reviewQueueExportUrl()}>Export review queue</a></div>
    <div className="batch-upload"><div><span className="step-number">01</span><strong>Batch source</strong><p>{file ? `${file.name} · ${Math.ceil(file.size / 1024)} KB` : 'CSV or simple XLSX with product headers'}</p></div><div className="batch-actions"><label className="button button-secondary">Choose file<input type="file" accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label><button className="text-button" onClick={loadDemoBatch}>Load synthetic batch</button><button className="button button-primary" disabled={!file || processing} onClick={submit}>{processing ? 'Processing…' : 'Process batch →'}</button></div></div>
    {batch ? <><div className="metric-grid"><MetricCard label="Products processed" value={batch.metrics.product_count.toString()} note="This batch only" /><MetricCard label="Completeness" value={`${batch.metrics.completeness_score}%`} note="Verified required fields" emphasis /><MetricCard label="Fields needing review" value={batch.metrics.fields_requiring_review.toString()} note="Inferred, missing, or conflict" warning /><MetricCard label="Conflicts" value={batch.metrics.conflict_count.toString()} note="Sources or rules disagree" danger /><MetricCard label="Missing mandatory" value={batch.metrics.missing_mandatory_fields.toString()} note="Required PIM fields" /><MetricCard label="Duplicate candidates" value={batch.metrics.duplicate_candidate_count.toString()} note="Normalized identifier keys" /></div><p className="metric-method">ⓘ {batch.metrics.metric_note}</p>
      <div className="health-grid"><section className="panel priority-panel"><div className="panel-header"><div><p className="eyebrow">REVIEW QUEUE</p><h2>Highest-priority products</h2></div><label className="filter-control">Status<select value={filter} onChange={(event) => setFilter(event.target.value as 'all' | FieldStatus)}><option value="all">All exceptions</option><option value="conflict">Conflict</option><option value="missing">Missing</option><option value="inferred">Inferred</option></select></label></div><div className="table-wrap"><table><thead><tr><th>Product</th><th>Reasons</th><th>Priority</th><th /></tr></thead><tbody>{filtered.map((item) => <tr key={item.product_id}><td><strong>{item.product_title}</strong><span>{item.manufacturer_part_number}</span><div className="row-statuses">{item.statuses.map((status) => <StatusPill key={status} status={status} />)}</div></td><td>{item.reasons.map((reason) => <span className="reason" key={reason}>{reason}</span>)}</td><td><b className="priority-number">{item.priority}</b></td><td><button className="row-action" onClick={() => { const record = batch.products.find((product) => product.id === item.product_id); if (record) onOpenWorkbench(record, record.attributes.find((attribute) => attribute.status !== 'verified')?.field) }}>Review →</button></td></tr>)}</tbody></table>{filtered.length === 0 && <div className="table-empty">No records match this review filter.</div>}</div></section>
        <aside className="panel health-notes"><p className="eyebrow">HOW TO READ THIS</p><h2>Metrics with a method.</h2><p>Completeness counts only required fields marked <strong>Verified</strong>. A conflict is never silently treated as complete.</p><div className="rule-list"><div><span>01</span><p>Every batch row keeps CSV/XLSX row evidence.</p></div><div><span>02</span><p>Duplicate candidates use normalized part number first.</p></div><div><span>03</span><p>Priority favors conflicts, then missing required fields.</p></div></div><span className="method-link">See the documented method in the repository</span></aside></div>
    </> : <HealthEmpty onLoadDemo={loadDemoBatch} />}
  </section>
}

function MetricCard({ label, value, note, warning, danger, emphasis }: { label: string; value: string; note: string; warning?: boolean; danger?: boolean; emphasis?: boolean }) {
  return <div className={`metric-card ${warning ? 'metric-warning' : ''} ${danger ? 'metric-danger' : ''} ${emphasis ? 'metric-emphasis' : ''}`}><span>{label}</span><strong>{value}</strong><small>{note}</small></div>
}

function HealthEmpty({ onLoadDemo }: { onLoadDemo: () => void }) {
  return <div className="health-empty"><div><p className="eyebrow">CATALOG HEALTH</p><h2>Start with a batch source.</h2><p>Use the 60-product synthetic CSV to demonstrate completeness, conflicts, missing required fields, and duplicate candidates.</p><button className="button button-primary" onClick={onLoadDemo}>Load synthetic 60-product batch</button></div><div className="health-illustration"><span>60</span><i /><i /><i /><i /><i /><i /></div></div>
}

export default App
