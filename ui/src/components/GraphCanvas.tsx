import { useCallback, useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { Entity, Relationship } from '../api/types';

const ENTITY_COLORS: Record<string, string> = {
  PERSON: '#6366f1',
  PROJECT: '#8b5cf6',
  GOAL: '#10b981',
  TASK: '#f59e0b',
  SKILL: '#3b82f6',
  DOCUMENT: '#64748b',
  ORGANIZATION: '#f97316',
  EVENT: '#ec4899',
  CONCEPT: '#14b8a6',
  ARTIFACT: '#84cc16',
  LOCATION: '#ef4444',
  PRODUCT: '#a855f7',
};

const STATE_BORDER: Record<string, string> = {
  VERIFIED: '#10b981',
  INFERRED: '#3b82f6',
  UNVERIFIED: '#3f3f46',
  DISPUTED: '#ef4444',
};

type EntityNodeData = { entity: Entity; isSelected: boolean };
type AppNode = Node<EntityNodeData, 'entity'>;
type LayoutMode = 'circle' | 'force';

function EntityNode({ data, selected }: NodeProps<AppNode>) {
  const { entity } = data;
  const typeColor = ENTITY_COLORS[entity.type] ?? '#6366f1';
  const borderColor = selected
    ? '#fff'
    : STATE_BORDER[entity.verification_state] ?? STATE_BORDER.UNVERIFIED;

  return (
    <>
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div
        style={{
          borderColor,
          borderWidth: selected ? 2 : 1,
          borderStyle: 'solid',
          background: '#18181b',
          borderRadius: 8,
          padding: '8px 12px',
          minWidth: 120,
          maxWidth: 180,
          boxShadow: selected ? `0 0 0 2px ${borderColor}33` : undefined,
        }}
      >
        <div style={{ fontSize: 9, color: typeColor, fontFamily: 'monospace', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 3 }}>
          {entity.type}
        </div>
        <div style={{ fontSize: 12, color: '#fafafa', fontWeight: 500, lineHeight: 1.3 }}>
          {entity.name.length > 24 ? entity.name.slice(0, 22) + '…' : entity.name}
        </div>
        <div style={{ fontSize: 10, color: '#71717a', marginTop: 3, fontFamily: 'monospace' }}>
          {(entity.confidence * 100).toFixed(0)}%
          {entity.verification_state === 'DISPUTED' && (
            <span style={{ color: '#ef4444', marginLeft: 4 }}>⚠</span>
          )}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </>
  );
}

const nodeTypes = { entity: EntityNode };

// ── Circle layout ─────────────────────────────────────────────────────────────

function circleLayout(entities: Entity[], cx = 450, cy = 300): AppNode[] {
  if (entities.length === 0) return [];
  if (entities.length === 1) {
    return [{ id: entities[0].id, type: 'entity', position: { x: cx, y: cy }, data: { entity: entities[0], isSelected: false } }];
  }
  const radius = Math.min(80 + entities.length * 28, 320);
  return entities.map((e, i) => {
    const angle = (2 * Math.PI * i) / entities.length - Math.PI / 2;
    return {
      id: e.id,
      type: 'entity' as const,
      position: { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) },
      data: { entity: e, isSelected: false },
    };
  });
}

// ── Force-directed layout (resolves DEC-0011) ─────────────────────────────────
// Naive spring-force simulation: repulsion between all pairs + edge attraction.

interface Vec2 { x: number; y: number }

function forceLayout(
  entities: Entity[],
  relationships: Relationship[],
  cx = 450,
  cy = 300,
  iterations = 120,
): AppNode[] {
  if (entities.length === 0) return [];
  if (entities.length === 1) {
    return [{ id: entities[0].id, type: 'entity', position: { x: cx, y: cy }, data: { entity: entities[0], isSelected: false } }];
  }

  // Start from circle positions to avoid degenerate initial state
  const initial = circleLayout(entities, cx, cy);
  const pos: Vec2[] = initial.map((n) => ({ x: n.position.x, y: n.position.y }));
  const vel: Vec2[] = entities.map(() => ({ x: 0, y: 0 }));
  const idxById = new Map(entities.map((e, i) => [e.id, i]));

  const K_REPEL = 18_000;  // repulsion constant
  const K_SPRING = 0.04;   // spring attraction constant
  const REST_LEN = 180;    // natural edge length
  const K_GRAVITY = 0.002; // center gravity
  const DAMPING = 0.85;

  for (let iter = 0; iter < iterations; iter++) {
    const force: Vec2[] = entities.map(() => ({ x: 0, y: 0 }));

    // Repulsion: O(n²) — fine for graph sizes ≤ 500 nodes
    for (let i = 0; i < entities.length; i++) {
      for (let j = i + 1; j < entities.length; j++) {
        const dx = pos[i].x - pos[j].x;
        const dy = pos[i].y - pos[j].y;
        const d2 = dx * dx + dy * dy + 0.01;
        const f = K_REPEL / d2;
        const norm = Math.sqrt(d2);
        force[i].x += (dx / norm) * f;
        force[i].y += (dy / norm) * f;
        force[j].x -= (dx / norm) * f;
        force[j].y -= (dy / norm) * f;
      }
    }

    // Edge attraction (spring)
    for (const rel of relationships) {
      const si = idxById.get(rel.from_entity_id);
      const ti = idxById.get(rel.to_entity_id);
      if (si === undefined || ti === undefined) continue;
      const dx = pos[ti].x - pos[si].x;
      const dy = pos[ti].y - pos[si].y;
      const d = Math.sqrt(dx * dx + dy * dy) + 0.01;
      const stretch = d - REST_LEN;
      const fx = (dx / d) * K_SPRING * stretch;
      const fy = (dy / d) * K_SPRING * stretch;
      force[si].x += fx;
      force[si].y += fy;
      force[ti].x -= fx;
      force[ti].y -= fy;
    }

    // Center gravity
    for (let i = 0; i < entities.length; i++) {
      force[i].x += (cx - pos[i].x) * K_GRAVITY;
      force[i].y += (cy - pos[i].y) * K_GRAVITY;
    }

    // Integrate
    for (let i = 0; i < entities.length; i++) {
      vel[i].x = (vel[i].x + force[i].x) * DAMPING;
      vel[i].y = (vel[i].y + force[i].y) * DAMPING;
      pos[i].x += vel[i].x;
      pos[i].y += vel[i].y;
    }
  }

  return entities.map((e, i) => ({
    id: e.id,
    type: 'entity' as const,
    position: { x: Math.round(pos[i].x), y: Math.round(pos[i].y) },
    data: { entity: e, isSelected: false },
  }));
}

// ── Edge builder ──────────────────────────────────────────────────────────────

function toEdges(relationships: Relationship[], minConfidence: number): Edge[] {
  return relationships
    .filter((r) => r.confidence >= minConfidence)
    .map((r) => ({
      id: r.id,
      source: r.from_entity_id,
      target: r.to_entity_id,
      label: r.type.replace(/_/g, ' '),
      animated: r.confidence < 0.5,
      style: {
        stroke: r.confidence >= 0.75 ? '#52525b' : '#3f3f46',
        strokeDasharray: r.confidence < 0.5 ? '4 2' : undefined,
      },
      labelStyle: { fill: '#52525b', fontSize: 9 },
      labelBgStyle: { fill: '#0a0a0b' },
    }));
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  nodes: Entity[];
  edges: Relationship[];
  selectedEntityId: string | null;
  minConfidence: number;
  onNodeSelect: (entity: Entity) => void;
}

export function GraphCanvas({ nodes: entities, edges: rels, selectedEntityId, minConfidence, onNodeSelect }: Props) {
  const [layout, setLayout] = useState<LayoutMode>('force');

  const rfNodes = useMemo(() => {
    const laid = layout === 'force'
      ? forceLayout(entities, rels)
      : circleLayout(entities);
    return laid.map((n) => ({ ...n, selected: n.id === selectedEntityId }));
  }, [entities, rels, selectedEntityId, layout]);

  const rfEdges = useMemo(() => toEdges(rels, minConfidence), [rels, minConfidence]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const entity = entities.find((e) => e.id === node.id);
      if (entity) onNodeSelect(entity);
    },
    [entities, onNodeSelect]
  );

  if (entities.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-600 text-sm flex-col gap-2">
        <span className="text-4xl">🕸️</span>
        <p>Select an entity from the sidebar to explore its graph</p>
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* Layout toggle */}
      <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 10, display: 'flex', gap: 4 }}>
        {(['force', 'circle'] as LayoutMode[]).map((m) => (
          <button
            key={m}
            onClick={() => setLayout(m)}
            style={{
              fontSize: 10,
              fontFamily: 'monospace',
              padding: '3px 8px',
              borderRadius: 4,
              border: `1px solid ${layout === m ? '#6366f1' : '#27272a'}`,
              background: layout === m ? '#1e1b4b' : '#141415',
              color: layout === m ? '#a5b4fc' : '#52525b',
              cursor: 'pointer',
            }}
          >
            {m}
          </button>
        ))}
      </div>

      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={3}
        style={{ background: '#0a0a0b' }}
      >
        <Background color="#27272a" gap={24} size={1} />
        <Controls style={{ background: '#141415', border: '1px solid #27272a' }} />
        <MiniMap
          nodeColor={(n) => {
            const e = entities.find((en) => en.id === n.id);
            return e ? (ENTITY_COLORS[e.type] ?? '#6366f1') : '#3f3f46';
          }}
          style={{ background: '#141415', border: '1px solid #27272a' }}
        />
      </ReactFlow>
    </div>
  );
}
