interface Env {
  DB: D1Database;
}

type ProposalRow = {
  id: number;
  external_id: string;
  reference_code: string | null;
  slug: string;
  official_title: string;
  display_title: string;
  summary: string | null;
  category: string;
  lifecycle_status: string;
  record_kind: 'demo' | 'official';
  submitted_at: string | null;
  official_url: string | null;
  updated_at: string;
};

const headers = {
  'content-type': 'application/json; charset=utf-8',
  'cache-control': 'no-store',
  'x-content-type-options': 'nosniff',
  'x-frame-options': 'DENY',
  'referrer-policy': 'no-referrer',
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers });
}

function paramInt(value: string | null, fallback: number, max: number): number {
  const num = Number(value);
  return value !== null && Number.isInteger(num) && num > 0 ? Math.min(num, max) : fallback;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;
    if (!path.startsWith('/api/')) return json({ error: 'Ismeretlen API útvonal.' }, 404);
    if (request.method !== 'GET') return json({ error: 'Csak GET engedélyezett ebben a szakaszban.' }, 405);
    try {
      if (path === '/api/health') {
        const row = await env.DB.prepare('SELECT 1 AS ok').first<{ ok: number }>();
        return json({ status: row?.ok === 1 ? 'ok' : 'degraded', database: 'd1', version: '0.1.0' });
      }
      if (path === '/api/proposals') {
        const page = paramInt(url.searchParams.get('page'), 1, 100000);
        const limit = paramInt(url.searchParams.get('limit'), 12, 50);
        const offset = (page - 1) * limit;
        const kind = url.searchParams.get('kind');
        const filter = kind === 'official' || kind === 'demo' ? kind : null;
        const where = filter ? ' WHERE record_kind = ?1' : '';
        const countStmt = env.DB.prepare(`SELECT COUNT(*) AS count FROM proposals${where}`);
        const listStmt = env.DB.prepare(`SELECT id, external_id, reference_code, slug, official_title, display_title, summary, category, lifecycle_status, record_kind, submitted_at, official_url, updated_at FROM proposals${where} ORDER BY updated_at DESC, id DESC LIMIT ?${filter ? '2' : '1'} OFFSET ?${filter ? '3' : '2'}`);
        const [total, results] = await Promise.all([
          filter ? countStmt.bind(filter).first<{ count: number }>() : countStmt.first<{ count: number }>(),
          filter ? listStmt.bind(filter, limit, offset).all<ProposalRow>() : listStmt.bind(limit, offset).all<ProposalRow>()
        ]);
        return json({ data: results.results ?? [], pagination: { page, limit, total: total?.count ?? 0 } });
      }
      const match = /^\/api\/proposals\/([a-z0-9][a-z0-9-]{0,99})$/.exec(path);
      if (match) {
        const proposal = await env.DB.prepare('SELECT id, external_id, reference_code, slug, official_title, display_title, summary, category, lifecycle_status, record_kind, submitted_at, official_url, updated_at FROM proposals WHERE slug = ?1')
          .bind(match[1]).first<ProposalRow>();
        if (!proposal) return json({ error: 'A javaslat nem található.' }, 404);
        const [versions, documents, explanations] = await Promise.all([
          env.DB.prepare('SELECT id, version_label, source_checksum, detected_at, document_url FROM proposal_versions WHERE proposal_id = ?1 ORDER BY detected_at DESC LIMIT 20').bind(proposal.id).all(),
          env.DB.prepare('SELECT id, title, source_url, section_label, retrieved_at FROM source_documents WHERE proposal_id = ?1 ORDER BY id DESC LIMIT 30').bind(proposal.id).all(),
          env.DB.prepare("SELECT id, version_number, short_text, detailed_text, model_provider, model_id, prompt_version, generated_at, review_status FROM explanations WHERE proposal_id = ?1 AND review_status = 'published' ORDER BY version_number DESC LIMIT 1").bind(proposal.id).all()
        ]);
        return json({ proposal, versions: versions.results ?? [], documents: documents.results ?? [], explanation: explanations.results?.[0] ?? null });
      }
      return json({ error: 'Ismeretlen API útvonal.' }, 404);
    } catch (error) {
      console.error('API request failed', path, error);
      return json({ error: 'Adatbázis- vagy szerverhiba. Futtasd a D1 migrációkat, majd próbáld újra.' }, 500);
    }
  }
} satisfies ExportedHandler<Env>;
