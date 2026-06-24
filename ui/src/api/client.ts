import type { Entity, GraphResponse, ExplainResponse } from './types';

const BASE = '/v1';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText}${body ? `: ${body}` : ''}`);
  }
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText}${text ? `: ${text}` : ''}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listEntities: (limit = 100) =>
    get<Entity[]>(`/entities/?limit=${limit}`),

  getEntityGraph: (id: string, minConfidence = 0, maxDepth = 3) =>
    get<GraphResponse>(
      `/entities/${id}/graph?min_confidence=${minConfidence}&max_depth=${maxDepth}`
    ),

  explainEntity: (id: string) =>
    get<ExplainResponse>(`/explain/${id}`),

  getDisputeQueue: () =>
    get<Entity[]>('/conflict/queue'),

  resolveConflict: (
    id: string,
    decision: 'ACCEPT' | 'REJECT',
    resolvedBy = 'user'
  ) =>
    post<Entity>(`/conflict/${id}/resolve`, {
      decision,
      resolved_by: resolvedBy,
      reason: `Resolved via Knowledge Explorer`,
    }),
};
