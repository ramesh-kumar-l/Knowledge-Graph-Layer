import type { TrustScore } from '../api/types';

interface Props {
  trustScore: TrustScore | null;
}

function scoreColor(score: number): string {
  if (score >= 0.75) return '#10b981';
  if (score >= 0.5) return '#f59e0b';
  return '#ef4444';
}

function Bar({ label, value, negative = false }: { label: string; value: number; negative?: boolean }) {
  const pct = Math.abs(value) * 100;
  const color = negative ? '#ef4444' : '#6366f1';
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-zinc-400">{label}</span>
        <span style={{ color }} className="font-mono">
          {negative ? '-' : '+'}{pct.toFixed(1)}%
        </span>
      </div>
      <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${Math.min(pct, 100)}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export function TrustBreakdown({ trustScore }: Props) {
  if (!trustScore) {
    return (
      <p className="text-xs text-zinc-500 italic">No trust score computed yet.</p>
    );
  }

  const { score, components, computed_at } = trustScore;
  const color = scoreColor(score);

  return (
    <div>
      <div className="flex items-baseline gap-2 mb-3">
        <span className="text-3xl font-bold font-mono" style={{ color }}>
          {(score * 100).toFixed(1)}
        </span>
        <span className="text-xs text-zinc-500">/ 100</span>
        <span className="ml-auto text-xs text-zinc-600">
          {components.evidence_count} evidence
        </span>
      </div>

      <Bar label="Evidence Weight" value={components.evidence_weight * 0.50} />
      <Bar label="Freshness Decay" value={components.freshness_decay * 0.20} />
      <Bar label="Verification Bonus" value={components.verification_bonus * 0.20} />
      <Bar label="Conflict Penalty" value={components.conflict_penalty * 0.10} negative />

      <p className="text-xs text-zinc-600 mt-2">
        Computed {new Date(computed_at).toLocaleString()}
      </p>
      <p className="text-xs text-zinc-700 mt-0.5">{trustScore.algorithm}</p>
    </div>
  );
}
