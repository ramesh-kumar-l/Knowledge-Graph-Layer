import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Entity, Relationship, ExplainResponse } from '../api/types';
import { GraphCanvas } from '../components/GraphCanvas';
import { EntityInspector } from '../components/EntityInspector';
import { ConflictQueue } from '../components/ConflictQueue';

type Tab = 'entities' | 'conflicts';

export function KnowledgeExplorer() {
  const [allEntities, setAllEntities] = useState<Entity[]>([]);
  const [graphNodes, setGraphNodes] = useState<Entity[]>([]);
  const [graphEdges, setGraphEdges] = useState<Relationship[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [explain, setExplain] = useState<ExplainResponse | null>(null);
  const [disputed, setDisputed] = useState<Entity[]>([]);
  const [minConfidence, setMinConfidence] = useState(0);
  const [tab, setTab] = useState<Tab>('entities');
  const [searchQ, setSearchQ] = useState('');
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [loadingExplain, setLoadingExplain] = useState(false);

  useEffect(() => {
    api.listEntities(200).then(setAllEntities).catch(console.error);
    api.getDisputeQueue().then(setDisputed).catch(console.error);
  }, []);

  const selectEntity = useCallback(async (entity: Entity) => {
    setSelectedEntity(entity);
    setExplain(null);

    setLoadingGraph(true);
    api.getEntityGraph(entity.id, minConfidence)
      .then((g) => { setGraphNodes(g.nodes); setGraphEdges(g.edges); })
      .catch(console.error)
      .finally(() => setLoadingGraph(false));

    setLoadingExplain(true);
    api.explainEntity(entity.id)
      .then(setExplain)
      .catch(console.error)
      .finally(() => setLoadingExplain(false));
  }, [minConfidence]);

  const handleResolve = useCallback(async (id: string, decision: 'ACCEPT' | 'REJECT') => {
    await api.resolveConflict(id, decision);
    const updated = await api.listEntities(200);
    setAllEntities(updated);
    const newDisputed = await api.getDisputeQueue();
    setDisputed(newDisputed);
    if (selectedEntity?.id === id) {
      const refreshed = updated.find((e) => e.id === id);
      if (refreshed) selectEntity(refreshed);
    }
  }, [selectedEntity, selectEntity]);

  const filtered = allEntities.filter(
    (e) => e.name.toLowerCase().includes(searchQ.toLowerCase())
       && e.confidence >= minConfidence
  );

  return (
    <div className="h-screen flex flex-col bg-canvas text-zinc-100 font-sans">
      {/* Header */}
      <header className="h-12 bg-surface border-b border-border flex items-center px-4 gap-4 shrink-0">
        <span className="text-sm font-semibold text-zinc-100">SCP Knowledge Explorer</span>
        <span className="text-xs text-zinc-600">v0.5.0</span>
        <div className="ml-auto flex items-center gap-3">
          <label className="text-xs text-zinc-500">Min confidence</label>
          <input
            type="range" min={0} max={1} step={0.05}
            value={minConfidence}
            onChange={(e) => setMinConfidence(Number(e.target.value))}
            className="w-28 accent-indigo-500"
          />
          <span className="text-xs font-mono text-zinc-400 w-8">{(minConfidence * 100).toFixed(0)}%</span>
        </div>
      </header>

      {/* Main */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-72 bg-surface border-r border-border flex flex-col shrink-0">
          <div className="flex border-b border-border">
            {(['entities', 'conflicts'] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`flex-1 py-2 text-xs font-medium capitalize transition-colors ${
                  tab === t ? 'text-zinc-100 border-b-2 border-indigo-500' : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                {t}
                {t === 'conflicts' && disputed.length > 0 && (
                  <span className="ml-1.5 bg-red-500 text-white rounded-full px-1.5 py-0.5 text-[10px]">
                    {disputed.length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {tab === 'entities' && (
            <>
              <input
                type="text" placeholder="Search entities…"
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                className="m-2 px-2.5 py-1.5 bg-zinc-800 border border-border rounded text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-indigo-600"
              />
              <div className="overflow-y-auto flex-1">
                {loadingGraph && <p className="text-xs text-zinc-600 px-3 py-1">Loading graph…</p>}
                {filtered.map((e) => (
                  <button
                    key={e.id}
                    onClick={() => selectEntity(e)}
                    className={`w-full text-left px-3 py-2 border-b border-zinc-800 hover:bg-zinc-800 transition-colors ${
                      selectedEntity?.id === e.id ? 'bg-zinc-800' : ''
                    }`}
                  >
                    <p className="text-xs font-medium text-zinc-100 truncate">{e.name}</p>
                    <p className="text-xs text-zinc-500 font-mono">{e.type} · {(e.confidence * 100).toFixed(0)}%</p>
                  </button>
                ))}
                {filtered.length === 0 && (
                  <p className="text-xs text-zinc-600 px-3 py-4 text-center">No entities found</p>
                )}
              </div>
            </>
          )}

          {tab === 'conflicts' && (
            <ConflictQueue
              entities={disputed}
              loading={false}
              onResolve={(id, decision) => handleResolve(id, decision)}
            />
          )}
        </aside>

        {/* Graph */}
        <main className="flex-1 relative">
          <GraphCanvas
            nodes={graphNodes.length > 0 ? graphNodes : []}
            edges={graphEdges}
            selectedEntityId={selectedEntity?.id ?? null}
            minConfidence={minConfidence}
            onNodeSelect={selectEntity}
          />
        </main>

        {/* Inspector */}
        <aside className="w-80 bg-surface border-l border-border flex flex-col shrink-0">
          <div className="px-4 py-2.5 border-b border-border">
            <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Inspector</h2>
          </div>
          <EntityInspector
            entity={selectedEntity}
            explain={explain}
            loading={loadingExplain}
            onResolve={selectedEntity ? (d) => handleResolve(selectedEntity.id, d) : undefined}
          />
        </aside>
      </div>
    </div>
  );
}
