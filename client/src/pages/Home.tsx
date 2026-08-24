import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  ChevronDown,
  CircleAlert,
  Crosshair,
  FileImage,
  ImagePlus,
  LoaderCircle,
  RotateCcw,
  ScanLine,
  ShieldCheck,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { getDisplayName, metadataEntries, type SearchResult } from "@/lib/retrievalDisplay";

type SearchResponse = {
  model: string;
  embedding_dimension: number;
  results: SearchResult[];
};

const ANALYSIS_STEPS = [
  "Image received",
  "Preparing image",
  "Analyzing visual features",
  "Searching engineering database",
  "Ranking similar parts",
];

const ACCEPTED_TYPES = ["image/png", "image/jpeg"];
const MAX_SIZE = 12 * 1024 * 1024;

function ResultMeta({ result, compact = false }: { result: SearchResult; compact?: boolean }) {
  const entries = metadataEntries(result).slice(0, compact ? 2 : 12);
  if (!entries.length) return <p className="meta-empty">No additional engineering metadata is available for this part.</p>;
  return (
    <dl className={compact ? "metadata-grid compact" : "metadata-grid"}>
      {entries.map(entry => (
        <div key={entry.key}>
          <dt>{entry.label}</dt>
          <dd>{entry.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [searching, setSearching] = useState(false);
  const [analysisStep, setAnalysisStep] = useState(0);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [selected, setSelected] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!searching) return;
    const interval = window.setInterval(() => setAnalysisStep(current => Math.min(current + 1, ANALYSIS_STEPS.length - 1)), 760);
    return () => window.clearInterval(interval);
  }, [searching]);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const bestMatch = result?.results[0] ?? null;
  const selectedPart = selected ?? bestMatch;
  const inputLabel = useMemo(() => file?.name || "Drop your component image here", [file]);

  function clearFile() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl(null);
    setResult(null);
    setSelected(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  function chooseFile(candidate: File | undefined) {
    if (!candidate) return;
    setError(null);
    setResult(null);
    setSelected(null);
    if (!ACCEPTED_TYPES.includes(candidate.type)) {
      setFile(null);
      setPreviewUrl(null);
      setError("Please choose a PNG or JPEG image.");
      return;
    }
    if (candidate.size > MAX_SIZE) {
      setFile(null);
      setPreviewUrl(null);
      setError("The selected image exceeds the 12 MB upload limit.");
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(candidate);
    setPreviewUrl(URL.createObjectURL(candidate));
  }

  async function findPart() {
    if (!file || searching) return;
    setSearching(true);
    setAnalysisStep(0);
    setError(null);
    setResult(null);
    setSelected(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const response = await fetch("/api/search", { method: "POST", body: form });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "The image could not be analyzed. Please try again.");
      if (!payload.results?.length) throw new Error("No matching part was returned by the engineering database.");
      setResult(payload as SearchResponse);
      setSelected(payload.results[0] as SearchResult);
      window.setTimeout(() => document.getElementById("results")?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "The retrieval request failed. Please try again.");
    } finally {
      setSearching(false);
    }
  }

  return (
    <main className="blueprint-shell">
      <div className="grid-overlay" aria-hidden="true" />
      <div className="corner-frame frame-a" aria-hidden="true" />
      <div className="corner-frame frame-b" aria-hidden="true" />

      <header className="site-header container">
        <a className="brand" href="#top" aria-label="Component Atlas home">
          <span className="brand-mark"><Crosshair size={18} /></span>
          <span>COMPONENT <b>ATLAS</b></span>
        </a>
        <div className="header-meta">
          <span className="status-dot" /> DINOv2 VISUAL RETRIEVAL <span className="header-separator" /> CAD GALLERY
        </div>
      </header>

      <section id="top" className="hero container">
        <div className="hero-copy">
          <div className="eyebrow"><span /> ENGINEERING IMAGE INTELLIGENCE</div>
          <h1>IDENTIFY ANY PART.<br /><em>FROM IMAGE TO CAD.</em></h1>
          <p>Upload a photograph of an industrial component and search the existing engineering gallery using the validated DINOv2 visual-retrieval workflow.</p>
          <div className="hero-specs" aria-label="System capabilities">
            <span>01 / PART-LEVEL RANKING</span>
            <span>02 / MULTI-VIEW CAD MATCHES</span>
            <span>03 / ENGINEERING METADATA</span>
          </div>
        </div>
        <div className="hero-drawing" aria-hidden="true">
          <img className="hero-reference-part" src="/manus-storage/40_t_shafts_adp416c_640x480_iso_d12a825c.png" alt="" />
          <div className="drawing-axis axis-x">+ X</div>
          <div className="drawing-axis axis-y">+ Y</div>
          <div className="drawing-ring ring-one" />
          <div className="drawing-ring ring-two" />
          <div className="drawing-line line-one" />
          <div className="drawing-line line-two" />
          <div className="drawing-label label-one">VISUAL / VECTOR</div>
          <div className="drawing-label label-two">Ø 384 DIM</div>
          <ScanLine className="drawing-scan" size={72} />
        </div>
      </section>

      <section className="upload-zone-section container" aria-labelledby="search-title">
        <div className="section-heading">
          <span className="section-number">01</span>
          <div><p>INPUT / SOURCE IMAGE</p><h2 id="search-title">SEARCH THE PART LIBRARY</h2></div>
          <div className="dimension-line" />
        </div>

        <div
          className={`upload-panel ${dragging ? "is-dragging" : ""} ${file ? "has-file" : ""}`}
          onDragEnter={event => { event.preventDefault(); setDragging(true); }}
          onDragOver={event => { event.preventDefault(); setDragging(true); }}
          onDragLeave={event => { event.preventDefault(); setDragging(false); }}
          onDrop={event => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files[0]); }}
        >
          <input
            ref={inputRef}
            className="sr-only"
            id="component-upload"
            type="file"
            accept="image/png,image/jpeg"
            capture="environment"
            onChange={event => chooseFile(event.target.files?.[0])}
          />
          {previewUrl ? (
            <div className="selected-file">
              <div className="upload-preview"><img src={previewUrl} alt="Selected component preview" /></div>
              <div className="selected-copy">
                <div className="file-verified"><Check size={16} /> IMAGE READY FOR ANALYSIS</div>
                <strong>{inputLabel}</strong>
                <span>PNG or JPEG / {file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : ""}</span>
                <div className="file-actions">
                  <Button variant="outline" className="blueprint-button ghost" onClick={() => inputRef.current?.click()}><RotateCcw size={15} /> Replace</Button>
                  <Button variant="ghost" className="remove-button" onClick={clearFile}><Trash2 size={15} /> Remove</Button>
                </div>
              </div>
            </div>
          ) : (
            <label htmlFor="component-upload" className="drop-content">
              <span className="upload-icon"><ImagePlus size={28} /></span>
              <strong>{inputLabel}</strong>
              <span>Drag and drop a component image, browse files, or use a supported device camera.</span>
              <span className="file-formats">SUPPORTED / PNG · JPEG · MAX 12 MB</span>
            </label>
          )}
          <div className="panel-coordinates" aria-hidden="true"><span>0.00</span><span>100.00</span></div>
        </div>

        {error && <div className="error-strip" role="alert"><CircleAlert size={18} /><span>{error}</span><button onClick={() => setError(null)} aria-label="Dismiss error"><X size={16} /></button></div>}

        <div className="action-row">
          <div className="security-note"><ShieldCheck size={16} /> Image processed for this search only. No result is generated until the real gallery query completes.</div>
          <Button className="find-button" disabled={!file || searching} onClick={findPart}>
            {searching ? <LoaderCircle className="animate-spin" size={18} /> : <Crosshair size={18} />} {searching ? "ANALYZING COMPONENT" : "FIND MY PART"}<ArrowRight size={17} />
          </Button>
        </div>
      </section>

      {searching && (
        <section className="analysis-section container" aria-live="polite">
          <div className="analysis-top"><div><p className="eyebrow"><span /> LIVE INFERENCE REQUEST</p><h2>ANALYZING COMPONENT</h2></div><LoaderCircle className="analysis-loader animate-spin" /></div>
          <ol className="analysis-steps">
            {ANALYSIS_STEPS.map((step, index) => <li className={index <= analysisStep ? "active" : ""} key={step}><span>{String(index + 1).padStart(2, "0")}</span><b>{step}</b><i>{index < analysisStep ? <Check size={15} /> : index === analysisStep ? <LoaderCircle size={15} className="animate-spin" /> : null}</i></li>)}
          </ol>
        </section>
      )}

      {bestMatch && (
        <section id="results" className="results-section container">
          <div className="section-heading">
            <span className="section-number">02</span>
            <div><p>OUTPUT / RANKED PARTS</p><h2>SIMILARITY REPORT</h2></div>
            <div className="result-model">{result?.model} / {result?.embedding_dimension}D</div>
          </div>

          <div className="best-match-grid">
            <div className="query-card technical-card">
              <div className="card-label">YOUR COMPONENT / QUERY</div>
              <div className="query-image">{previewUrl && <img src={previewUrl} alt="Uploaded component" />}</div>
              <span className="image-caption">SOURCE IMAGE / VALIDATED</span>
            </div>
            <article className="best-card technical-card">
              <div className="card-label"><span>BEST MATCH</span><span>RANK / 01</span></div>
              <div className="best-layout">
                <div className="match-image"><img src={bestMatch.preview_image} alt={`${bestMatch.part_id} ${bestMatch.best_view} view`} /></div>
                <div className="best-copy">
                  <p className="match-score">{bestMatch.similarity_percentage.toFixed(1)}<small>%</small></p>
                  <p className="match-caption">VISUAL MATCH / {bestMatch.best_view.toUpperCase()} VIEW</p>
                  <h3>{getDisplayName(bestMatch)}</h3>
                  <p className="part-code">PART ID / {bestMatch.part_id}</p>
                  <ResultMeta result={bestMatch} compact />
                  <Button className="detail-button" onClick={() => { setSelected(bestMatch); document.getElementById("part-detail")?.scrollIntoView({ behavior: "smooth", block: "start" }); }}>Inspect part <ArrowRight size={15} /></Button>
                </div>
              </div>
            </article>
          </div>

          <div className="subsection-title"><span>TOP FIVE / PHYSICAL PARTS</span><div /></div>
          <div className="comparison-grid">
            {result?.results.map(match => (
              <button className={`part-card technical-card ${selectedPart?.part_id === match.part_id ? "selected" : ""}`} key={match.part_id} onClick={() => setSelected(match)}>
                <span className="rank-badge">{String(match.rank).padStart(2, "0")}</span>
                <div className="part-preview"><img src={match.preview_image} alt={`${match.part_id} preview`} /></div>
                <div className="part-card-copy"><span>{match.similarity_percentage.toFixed(1)}% MATCH</span><strong>{getDisplayName(match)}</strong><small>{match.part_id}</small><small>BEST VIEW / {match.best_view.toUpperCase()}</small></div>
              </button>
            ))}
          </div>
        </section>
      )}

      {selectedPart && (
        <section id="part-detail" className="detail-section container">
          <div className="section-heading">
            <span className="section-number">03</span>
            <div><p>PART DETAIL / SELECTED MATCH</p><h2>{getDisplayName(selectedPart).toUpperCase()}</h2></div>
            <span className="result-model">{selectedPart.similarity_percentage.toFixed(1)}% VISUAL MATCH</span>
          </div>
          <div className="detail-layout technical-card">
            <div className="detail-info"><p className="part-code">PART ID / {selectedPart.part_id}</p><ResultMeta result={selectedPart} /></div>
            <div className="view-gallery">
              <div className="gallery-header"><span>AVAILABLE CAD VIEWS</span><span>{selectedPart.available_views.length} FILES</span></div>
              <div className="view-grid">{selectedPart.available_views.map(view => <figure key={view.view}><img src={view.image_url} alt={`${selectedPart.part_id} ${view.view} CAD rendered view`} /><figcaption>{view.view.toUpperCase()}</figcaption></figure>)}</div>
            </div>
          </div>
        </section>
      )}

      <footer className="site-footer container"><span>COMPONENT ATLAS / ENGINEERING VISUAL RETRIEVAL</span><span>VALIDATED DINOv2 + FAISS / PART-LEVEL MAX AGGREGATION</span></footer>
    </main>
  );
}
