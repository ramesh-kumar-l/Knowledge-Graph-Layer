import type { Entity, ExplainResponse } from '../api/types';
import { TrustBreakdown } from './TrustBreakdown';

interface Props {
  entity: Entity | null;
  explain: ExplainResponse | null;
  loading: boolean;
  onResolve?: (decision: 'ACCEPT' | 'REJECT') => void;
}

const STATE_STYLES: Record<string, string> = {
  VERIFIED: 'bg-emerald-900/50 text-emerald-400 border-emerald-800',
  INFERRED: 'bg-blue-900/50 text-blue-400 border-blue-800',
  UNVERIFIED: 'bg-zinc-800 text-zinc-400 border-zinc-700',
  DISPUTED: 'bg-red-900/50 text-red-400 border-red-800',
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-zinc-800 pt-3 mt-3">
      <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">{title}</h3>
      {children}
    </div>
  );
}

export function EntityInspector({ entity, explain, loading, onResolve }: Props) {
  if (!entity) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-600 text-sm p-6 text-center">
        Select a node to inspect
      </div>
    );
  }

  const stateStyle = STATE_STYLES[entity.verification_state] ?? STATE_STYLES.UNVERIFIED;

  return (
    <div className="overflow-y-auto h-full p-4">
      {/* Entity header */}
      <div className="mb-3">
        <h2 className="text-base font-semibold text-zinc-100 break-words">{entity.name}</h2>
        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-900/50 text-indigo-400 border border-indigo-800 font-mono">
            {entity.type}
          </span>
          <span className={`text-xs px-1.5 py-0.5 rounded border ${stateStyle}`}>
            {entity.verification_state}
          </span>
          <span className="text-xs text-zinc-500 ml-auto">v{entity.version}</span>
        </div>
        <p className="text-xs text-zinc-500 mt-1.5">
          Confidence: <span className="text-zinc-300 font-mono">{(entity.confidence * 100).toFixed(1)}%</span>
        </p>
      </div>

      {/* Conflict resolution for disputed entities */}
      {entity.verification_state === 'DISPUTED' && onResolve && (
        <div className="rounded border border-red-900 bg-red-950/30 p-3 mb-3">
          <p className="text-xs text-red-400 mb-2">This entity has a conflict.</p>
          <div className="flex gap-2">
            <button
              onClick={() => onResolve('ACCEPT')}
              className="flex-1 text-xs py-1.5 rounded bg-emerald-900/50 text-emerald-400 border border-emerald-800 hover:bg-emerald-900 transition-colors"
            >
              Accept → Verified
            </button>
            <button
              onClick={() => onResolve('REJECT')}
              className="flex-1 text-xs py-1.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 transition-colors"
            >
              Reject → Unverified
            </button>
          </div>
        </div>
      )}

      {loading && (
        <p className="text-xs text-zinc-500 italic">Loading trust data…</p>
      )}

      {explain && (
        <>
          <Section title="Trust Score">
            <TrustBreakdown trustScore={explain.trust_score} />
          </Section>

          <Section title={`Evidence (${explain.evidence.length})`}>
            <div className="space-y-1.5 max-h-40 overflow-y-auto">
              {explain.evidence.length === 0 && (
                <p className="text-xs text-zinc-600 italic">No evidence records.</p>
              )}
              {explain.evidence.map((ev) => (
                <div key={ev.id} className="rounded bg-zinc-800/50 p-2">
                  <div className="flex justify-between text-xs mb-0.5">
                    <span className="text-zinc-400">{ev.source_type}</span>
                    <span className="text-zinc-500 font-mono">{(ev.confidence * 100).toFixed(0)}%</span>
                  </div>
                  {ev.content_preview && (
                    <p className="text-xs text-zinc-500 truncate">{ev.content_preview}</p>
                  )}
                </div>
              ))}
            </div>
          </Section>

          {explain.provenance && (
            <Section title="Provenance">
              <div className="text-xs space-y-1 text-zinc-400">
                <p><span className="text-zinc-600">Origin:</span> {explain.provenance.origin}</p>
                <p><span className="text-zinc-600">Method:</span> {explain.provenance.extraction_method}</p>
                <p><span className="text-zinc-600">Agent:</span> {explain.provenance.agent_id}</p>
              </div>
            </Section>
          )}

          {explain.conflict_history.length > 0 && (
            <Section title={`Conflict History (${explain.conflict_history.length})`}>
              <div className="space-y-1.5 max-h-32 overflow-y-auto">
                {explain.conflict_history.map((ev) => (
                  <div key={ev.version} className="rounded bg-red-950/30 border border-red-900/50 p-2">
                    <p className="text-xs text-red-400">v{ev.version}: {ev.change_reason}</p>
                    <p className="text-xs text-zinc-600">{ev.changed_by} · {new Date(ev.changed_at).toLocaleDateString()}</p>
                  </div>
                ))}
              </div>
            </Section>
          )}
        </>
      )}
    </div>
  );
}
