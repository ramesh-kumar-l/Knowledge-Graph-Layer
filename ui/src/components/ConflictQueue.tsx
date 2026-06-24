import type { Entity } from '../api/types';

interface Props {
  entities: Entity[];
  loading: boolean;
  onResolve: (id: string, decision: 'ACCEPT' | 'REJECT') => void;
}

function EntityTypeBadge({ type }: { type: string }) {
  return (
    <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 font-mono">
      {type}
    </span>
  );
}

export function ConflictQueue({ entities, loading, onResolve }: Props) {
  if (loading) {
    return <p className="text-xs text-zinc-500 p-4">Loading disputes…</p>;
  }

  if (entities.length === 0) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm text-zinc-500">No disputed entities</p>
        <p className="text-xs text-zinc-700 mt-1">All conflicts resolved ✓</p>
      </div>
    );
  }

  return (
    <div className="overflow-y-auto flex-1">
      {entities.map((entity) => (
        <div
          key={entity.id}
          className="px-3 py-2.5 border-b border-zinc-800 hover:bg-zinc-900 transition-colors"
        >
          <div className="flex items-center gap-2 mb-1.5">
            <span className="w-2 h-2 rounded-full bg-red-500 shrink-0" />
            <span className="text-sm text-zinc-100 font-medium truncate">{entity.name}</span>
            <EntityTypeBadge type={entity.type} />
          </div>

          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-xs text-zinc-500">
              Confidence: {(entity.confidence * 100).toFixed(0)}%
            </span>
            <span className="text-xs text-zinc-700">·</span>
            <span className="text-xs text-zinc-500">v{entity.version}</span>
          </div>

          <div className="flex gap-2 mt-2">
            <button
              onClick={() => onResolve(entity.id, 'ACCEPT')}
              className="flex-1 text-xs py-1 px-2 rounded bg-emerald-900/50 text-emerald-400 border border-emerald-800 hover:bg-emerald-900 transition-colors"
            >
              Accept → Verified
            </button>
            <button
              onClick={() => onResolve(entity.id, 'REJECT')}
              className="flex-1 text-xs py-1 px-2 rounded bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 transition-colors"
            >
              Reject → Unverified
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
