import { useEffect, useState } from 'react';
import { ArrowRight, ArrowUpRight, BookOpen, CheckCircle2, ChevronLeft, FileText, Filter, HeartHandshake, Landmark, Menu, Search, ShieldCheck, Sparkles, Vote, X } from 'lucide-react';
import type { DetailResponse, ListResponse, Proposal } from './types';

function safeOfficialUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const parsed = new URL(value);
    if (parsed.protocol === 'https:' && (parsed.hostname === 'parlament.hu' || parsed.hostname.endsWith('.parlament.hu'))) return parsed.toString();
  } catch { /* not a valid url */ }
  return null;
}

const categoryIcon: Record<string, string> = {
  Lakhatás: '⌂', Egészségügy: '+', Oktatás: '▤', Közlekedés: '↗', Energia: '◈'
};

export default function App() {
  const [items, setItems] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('Összes');
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<DetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  async function loadList() {
    setLoading(true); setError('');
    try {
      const response = await fetch('/api/proposals?limit=50');
      if (!response.ok) throw new Error('Nem érhető el a szerver.');
      const json = await response.json() as ListResponse;
      setItems(json.data);
    } catch (err) { setError(err instanceof Error ? err.message : 'Ismeretlen hiba.'); }
    finally { setLoading(false); }
  }
  useEffect(() => { void loadList(); }, []);
  useEffect(() => {
    if (!selected) { setDetail(null); return; }
    let active = true;
    setDetailLoading(true); setDetail(null);
    fetch(`/api/proposals/${encodeURIComponent(selected)}`)
      .then(async (res) => { if (!res.ok) throw new Error('Az adatlap nem tölthető be.'); return await res.json() as DetailResponse; })
      .then((value) => { if (active) setDetail(value); })
      .catch(() => { if (active) setDetail(null); })
      .finally(() => { if (active) setDetailLoading(false); });
    return () => { active = false; };
  }, [selected]);

  const categories = ['Összes', ...Array.from(new Set(items.map((p) => p.category)))];
  const filtered = items.filter((p) =>
    (category === 'Összes' || p.category === category) &&
    `${p.display_title} ${p.official_title} ${p.summary ?? ''}`.toLocaleLowerCase('hu-HU').includes(search.toLocaleLowerCase('hu-HU'))
  );
  const demoCount = items.filter((p) => p.record_kind === 'demo').length;
  const officialCount = items.length - demoCount;

  return <div className="app-shell">
    <header className="topbar">
      <div className="container header-inner">
        <a className="brand" href="/" onClick={(e) => { e.preventDefault(); setSelected(null); }} aria-label="Közös Döntés kezdőlap">
          <span className="brand-mark"><Vote size={23} strokeWidth={2.5}/></span>
          <span>Közös<span className="brand-strong">Döntés</span><span className="brand-dot">.</span></span>
        </a>
        <nav className={`nav ${menuOpen ? 'open' : ''}`} aria-label="Fő navigáció">
          <a href="#javaslatok" onClick={() => { setSelected(null); setMenuOpen(false); }}>Javaslatok</a>
          <a href="#hogyan-mukodik" onClick={() => { setSelected(null); setMenuOpen(false); }}>Hogyan működik?</a>
          <a href="#alapelvek" onClick={() => { setSelected(null); setMenuOpen(false); }}>Alapelveink</a>
        </nav>
        <span className="stage-label">Nyilvános demó · 1. fázis</span>
        <button className="menu-btn" aria-label="Menü" onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X/> : <Menu/>}</button>
      </div>
    </header>

    {selected ? <main className="container detail-main">
      <button className="back-btn" onClick={() => setSelected(null)}><ChevronLeft size={17}/> Vissza a javaslatokhoz</button>
      {detailLoading && <div className="panel">Adatlap betöltése…</div>}
      {!detailLoading && !detail && <div className="panel">Nem sikerült betölteni az adatlapot. <button onClick={() => setSelected(null)}>Vissza</button></div>}
      {detail && <>
        <div className="detail-heading">
          <div className="eyebrow"><span className="dot"/> {detail.proposal.record_kind === 'demo' ? 'KITALÁLT TESZTADAT' : 'HIVATALOS IROMÁNY'}</div>
          <h1>{detail.proposal.display_title}</h1>
          <p className="detail-subtitle">{detail.proposal.official_title}</p>
          <div className="chip-row"><span className="chip">{detail.proposal.category}</span><span className="chip subtle">{detail.proposal.reference_code ?? detail.proposal.external_id}</span></div>
        </div>
        {detail.proposal.record_kind === 'demo' && <div className="notice warning"><ShieldCheck size={19}/> Ez kizárólag kitalált fejlesztői példa. Nem valódi országgyűlési javaslat, nem lehetséges rá szavazni.</div>}
        <div className="detail-layout">
          <section className="panel reading-panel">
            <div className="section-label"><BookOpen size={19}/> Közérthető összefoglaló</div>
            <p className="reading-lead">{detail.explanation?.short_text ?? detail.proposal.summary ?? 'Ehhez az irományhoz még nincs jóváhagyott magyarázat.'}</p>
            {detail.explanation ? <>
              <h3>Részletes magyarázat</h3><p className="long-text">{detail.explanation.detailed_text}</p>
              <div className="model-meta"><Sparkles size={16}/> AI: {detail.explanation.model_provider} / {detail.explanation.model_id} · Magyarázat v{detail.explanation.version_number}</div>
            </> : <div className="pending"><Sparkles size={18}/><div><strong>Magyarázat előkészítés alatt</strong><p>Az AI-magyarázó a 3. fejlesztési szakaszban kerül bekötésre. Az oldal egyelőre nem állít elő jogi értelmezést.</p></div></div>}
          </section>
          <aside className="detail-aside">
            <div className="panel"><div className="section-label"><FileText size={18}/> Hivatalos adatok</div>
              <div className="kv"><span>Azonosító</span><strong>{detail.proposal.reference_code ?? detail.proposal.external_id}</strong></div>
              <div className="kv"><span>Állapot</span><strong>{detail.proposal.lifecycle_status}</strong></div>
              <div className="kv"><span>Forrásváltozatok</span><strong>{detail.versions.length}</strong></div>
              {safeOfficialUrl(detail.proposal.official_url) && <a className="official-link" target="_blank" rel="noopener noreferrer" href={safeOfficialUrl(detail.proposal.official_url)!}>Hivatalos forrás <ArrowUpRight size={16}/></a>}
            </div>
            <div className="panel"><div className="section-label"><ShieldCheck size={18}/> Források</div>
              {detail.documents.length === 0 ? <p className="small-muted">Még nincs hozzárendelt hivatalos forrásdokumentum.</p> : detail.documents.map((s) => <div key={s.id} className="source-entry">{s.source_url && safeOfficialUrl(s.source_url) ? <a href={safeOfficialUrl(s.source_url)!} target="_blank" rel="noopener noreferrer">{s.title} ↗</a> : <strong>{s.title}</strong>}<small>{s.section_label}</small></div>)}
            </div>
          </aside>
        </div>
      </>}
    </main> : <main>
      <section className="hero">
        <div className="container hero-content">
          <div className="hero-copy">
            <div className="hero-kicker"><span className="kicker-line"/> A döntések mögött az emberek</div>
            <h1>Értsd meg.<br/><em>Alakíts véleményt.</em><br/>Lásd a döntést.</h1>
            <p>Az Országgyűlés döntései közérthetően, egy helyen. Egy független közösségi platformot építünk, ahol minden szavazat mögött tájékozott döntés állhat.</p>
            <div className="hero-actions"><a className="button primary" href="#javaslatok">Javaslatok megtekintése <ArrowRight size={18}/></a><a className="button transparent" href="#hogyan-mukodik">Ismerd meg a tervet <ArrowUpRight size={17}/></a></div>
            <div className="hero-foot"><ShieldCheck size={16}/> Pártfüggetlen kezdeményezés <span/> Nyílt forráskód</div>
          </div>
          <div className="hero-art" aria-hidden="true"><div className="art-orbit orbit-one"/><div className="art-orbit orbit-two"/><div className="art-center"><Landmark size={91} strokeWidth={1.1}/></div><span className="art-dot d1"/><span className="art-dot d2"/><span className="art-dot d3"/><div className="art-mini mini-one">A közösség véleménye <CheckCircle2 size={17}/></div><div className="art-mini mini-two">Közérthető információ <BookOpen size={17}/></div></div>
        </div>
      </section>
      <section className="numbers-bar"><div className="container numbers-content"><div><strong>{items.length}</strong><span>betöltött téma</span></div><div><strong>{officialCount}</strong><span>hivatalos rekord</span></div><div><strong>{demoCount}</strong><span>demórekord</span></div><div className="numbers-message"><ShieldCheck size={21}/> Ezen a fejlesztői verzión a szavazás még nem elérhető.</div></div></section>
      <section id="javaslatok" className="container proposals-section">
        <div className="section-heading"><div><div className="eyebrow"><span className="dot"/> KÖVETHETŐ DÖNTÉSEK</div><h2>Parlamenti javaslatok</h2><p>Ismerd meg az előkészített témákat. Az éles adatimport után valós parlamenti irományok jelennek meg.</p></div><span className="feature-pill"><Filter size={15}/> Böngészhető adatbázis</span></div>
        <div className="filters"><div className="searchbox"><Search size={18}/><input aria-label="Keresés a javaslatok között" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Keress témák és javaslatok között..." /></div><div className="category-list">{categories.map((c) => <button key={c} className={category === c ? 'category active' : 'category'} onClick={() => setCategory(c)}>{c}</button>)}</div></div>
        {loading && <div className="empty-state">Törvényjavaslatok betöltése…</div>}
        {error && <div className="empty-state error"><p>{error}</p><p>Futtasd a D1 migrációt és a demóadatok betöltését a README alapján.</p><button className="button primary" onClick={() => void loadList()}>Újrapróbálás</button></div>}
        {!loading && !error && filtered.length === 0 && <div className="empty-state">Nincs megjeleníthető javaslat. {items.length === 0 ? 'A D1 adatbázis üres; töltsd be a helyi demóadatokat.' : 'Próbálj más keresést.'}</div>}
        <div className="cards-grid">{!loading && !error && filtered.map((p) => <article key={p.id} className="proposal-card">
          <div className="card-top"><span className="topic-symbol">{categoryIcon[p.category] ?? '§'}</span><span className={p.record_kind === 'demo' ? 'record-badge demo' : 'record-badge'}>{p.record_kind === 'demo' ? 'DEMÓ' : 'HIVATALOS'}</span></div>
          <span className="card-category">{p.category}</span><h3>{p.display_title}</h3><p>{p.summary ?? 'Az eredeti parlamenti leírás feldolgozása folyamatban.'}</p><div className="card-bottom"><span>{p.reference_code ?? p.external_id}</span><button onClick={() => { setSelected(p.slug); window.scrollTo({ top: 0, behavior: 'smooth' }); }} aria-label={`${p.display_title} részletei`}>Részletek <ArrowRight size={17}/></button></div>
        </article>)}</div>
      </section>
      <section className="how-section" id="hogyan-mukodik"><div className="container"><div className="eyebrow muted">AZ ÖTLETTŐL A DÖNTÉSIG</div><h2>Hogyan fog működni?</h2><div className="steps-grid"><div><span>01</span><FileText size={28}/><h3>Hivatalos forrás</h3><p>Az Országgyűlés dokumentumait és döntéseit követjük.</p></div><div><span>02</span><BookOpen size={28}/><h3>Érthető magyarázat</h3><p>Forrásolt, verziózott AI-magyarázatot készítünk.</p></div><div><span>03</span><Vote size={28}/><h3>Közösségi szavazás</h3><p>A megerősített fiókok később szavazhatnak.</p></div><div><span>04</span><Landmark size={28}/><h3>Összehasonlítás</h3><p>Megmutatjuk az online és a parlamenti döntést.</p></div></div></div></section>
      <section className="container principles" id="alapelvek"><div className="principles-icon"><HeartHandshake size={32}/></div><div><h2>Nem pártok mellett. A tájékozott döntésekért.</h2><p>A közösségi szavazás nem hivatalos népszavazás, és az önkéntes online minta nem reprezentálja automatikusan Magyarország lakosságát. A forrásokat és a működési szabályokat nyilvánosan dokumentáljuk.</p></div><a href="https://www.parlament.hu/w-api-tajekoztato" target="_blank" rel="noopener noreferrer">Parlamenti adatforrás <ArrowUpRight size={16}/></a></section>
    </main>}
    <footer className="footer"><div className="container footer-inner"><span>© {new Date().getFullYear()} KözösDöntés · Nyílt MVP</span><span>Független civil kísérleti projekt · A demóadatok kitaláltak.</span></div></footer>
  </div>;
}
