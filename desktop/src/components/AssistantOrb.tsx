import React, { useEffect, useMemo, useRef, useState } from 'react';
import './AssistantOrb.css';

export type OrbState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error' | 'disconnected';

interface AssistantOrbProps {
  state: OrbState;
  audioLevel?: number; // 0.0 to 1.0
  onClick?: () => void;
  size?: number;
  subtitle?: string;
}

const stateLabels: Record<OrbState, string> = {
  idle: 'Ready',
  listening: 'Listening',
  thinking: 'Processing',
  speaking: 'Speaking',
  error: 'Error',
  disconnected: 'Offline',
};

// Generate deterministic geodesic sphere points (Fibonacci sphere algorithm)
function generateSphereNodes(count: number, radius: number) {
  const points: { x: number; y: number; z: number }[] = [];
  const phi = Math.PI * (Math.sqrt(5) - 1); // Golden angle

  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2; // y from 1 to -1
    const radiusAtY = Math.sqrt(1 - y * y); // radius at y
    const theta = phi * i;

    const x = Math.cos(theta) * radiusAtY;
    const z = Math.sin(theta) * radiusAtY;

    points.push({
      x: x * radius,
      y: y * radius,
      z: z * radius,
    });
  }
  return points;
}

// Generate edges between proximate nodes
function generateSphereEdges(
  nodes: { x: number; y: number; z: number }[],
  maxDistance: number
): [number, number][] {
  const edges: [number, number][] = [];
  const maxDistSq = maxDistance * maxDistance;

  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dx = nodes[i].x - nodes[j].x;
      const dy = nodes[i].y - nodes[j].y;
      const dz = nodes[i].z - nodes[j].z;
      const distSq = dx * dx + dy * dy + dz * dz;

      if (distSq <= maxDistSq) {
        edges.push([i, j]);
      }
    }
  }
  return edges;
}

export const AssistantOrb: React.FC<AssistantOrbProps> = ({
  state,
  audioLevel = 0,
  onClick,
  size = 280,
  subtitle,
}) => {
  const clampedLevel = Math.min(Math.max(audioLevel, 0), 1);
  const [rotationAngle, setRotationAngle] = useState(0);
  const animRef = useRef<number | null>(null);

  const sphereRadius = size * 0.30;
  const half = size / 2;

  // Rich 96-node polyhedral geodesic lattice for dense neural cluster
  const baseNodes = useMemo(() => generateSphereNodes(96, sphereRadius), [sphereRadius]);
  const edges = useMemo(() => generateSphereEdges(baseNodes, sphereRadius * 0.38), [baseNodes, sphereRadius]);

  // Subtle 3D tilt
  const tiltAngle = 0.22; // ~12 degrees tilt
  const cosTilt = Math.cos(tiltAngle);
  const sinTilt = Math.sin(tiltAngle);

  // Rotate sphere smoothly around Y-axis
  useEffect(() => {
    let lastTime = performance.now();

    const animate = (time: number) => {
      const delta = (time - lastTime) / 1000;
      lastTime = time;

      const speed =
        state === 'thinking'
          ? 1.2
          : state === 'speaking'
          ? 0.7 + clampedLevel * 1.5
          : state === 'listening'
          ? 0.5 + clampedLevel * 0.8
          : state === 'disconnected'
          ? 0.05
          : 0.22; // idle

      setRotationAngle((prev) => (prev + delta * speed) % (Math.PI * 2));
      animRef.current = requestAnimationFrame(animate);
    };

    animRef.current = requestAnimationFrame(animate);
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [state, clampedLevel]);

  // Dynamic scale with audio
  const audioScale = 1 + clampedLevel * 0.14;
  const cosRot = Math.cos(rotationAngle);
  const sinRot = Math.sin(rotationAngle);

  // Project 3D nodes into 2D screen coordinates with perspective and tilt
  const projectedNodes = baseNodes.map((pt) => {
    // 1. Rotate around Y
    const rotX = pt.x * cosRot - pt.z * sinRot;
    const tempZ = pt.x * sinRot + pt.z * cosRot;

    // 2. Tilt around X
    const rotY = pt.y * cosTilt - tempZ * sinTilt;
    const rotZ = pt.y * sinTilt + tempZ * cosTilt;

    const scaledX = rotX * audioScale;
    const scaledY = rotY * audioScale;
    const scaledZ = rotZ * audioScale;

    const depth = (scaledZ + sphereRadius) / (2 * sphereRadius); // 0 (back) to 1 (front)
    const screenX = half + scaledX;
    const screenY = half + scaledY;

    return {
      x: screenX,
      y: screenY,
      z: scaledZ,
      depth,
    };
  });

  return (
    <div
      className={`orb-wrapper state-${state}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-label={`JARVIS Core State: ${state}`}
      title={`JARVIS Core: ${stateLabels[state]}`}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.();
        }
      }}
    >
      <div className="orb-stage">
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          fill="none"
          className="orb-svg"
          aria-hidden="true"
        >
          <defs>
            {/* Radiant Neural Core Gradient */}
            <radialGradient id="neural-singularity" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#FFFFFF" stopOpacity="1" />
              <stop offset="18%" stopColor="#FF3038" stopOpacity="0.95" />
              <stop offset="48%" stopColor="#78151B" stopOpacity="0.65" />
              <stop offset="100%" stopColor="transparent" stopOpacity="0" />
            </radialGradient>

            {/* Ambient Red Atmospheric Glow */}
            <radialGradient id="neural-ambient-glow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#FF3038" stopOpacity={state === 'listening' ? 0.36 : 0.22} />
              <stop offset="50%" stopColor="#78151B" stopOpacity="0.08" />
              <stop offset="100%" stopColor="transparent" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* ── Outer Precision HUD Orbital Framework ────────────── */}
          {/* Cardinal crosshair ticks matching the reference image */}
          {/* 9 o'clock horizontal tick pointing inward */}
          <line x1={half - size * 0.44} y1={half} x2={half - size * 0.39} y2={half} className="hud-tick" />
          {/* 3 o'clock horizontal tick */}
          <line x1={half + size * 0.39} y1={half} x2={half + size * 0.44} y2={half} className="hud-tick" />
          {/* 12 o'clock vertical tick */}
          <line x1={half} y1={half - size * 0.44} x2={half} y2={half - size * 0.41} className="hud-tick" />
          {/* 6 o'clock vertical tick */}
          <line x1={half} y1={half + size * 0.41} x2={half} y2={half + size * 0.44} className="hud-tick" />

          {/* Right curved arc segment at 3 o'clock as in reference photo */}
          <path
            d={`M ${half + size * 0.405} ${half - 14} A ${size * 0.405} ${size * 0.405} 0 0 1 ${half + size * 0.405} ${half + 14}`}
            className="hud-arc-right"
          />
          <circle cx={half + size * 0.425} cy={half} r="1.8" className="hud-accent-dot" />

          {/* Concentric orbital rings */}
          <circle cx={half} cy={half} r={size * 0.41} className="hud-ring-outer" />
          <circle cx={half} cy={half} r={size * 0.36} className="hud-ring-mid" />

          {/* Audio reactive outer ring */}
          {clampedLevel > 0 && (
            <circle
              cx={half}
              cy={half}
              r={size * (0.36 + clampedLevel * 0.08)}
              className="orb-wave-outer"
              style={{
                opacity: 0.35 + clampedLevel * 0.55,
              }}
            />
          )}

          {/* ── Atmospheric Ambient Glow ─────────────────────────── */}
          <circle
            cx={half}
            cy={half}
            r={sphereRadius * (1.35 + clampedLevel * 0.2)}
            fill="url(#neural-ambient-glow)"
          />

          {/* ── Neural Geodesic Constellation (Back Edges) ───────── */}
          {edges.map(([i, j], idx) => {
            const p1 = projectedNodes[i];
            const p2 = projectedNodes[j];
            if (p1.z < 0 && p2.z < 0) {
              const avgDepth = (p1.depth + p2.depth) / 2;
              return (
                <line
                  key={`back-${idx}`}
                  x1={p1.x}
                  y1={p1.y}
                  x2={p2.x}
                  y2={p2.y}
                  className="neural-edge back"
                  style={{ opacity: 0.14 + avgDepth * 0.22 }}
                />
              );
            }
            return null;
          })}

          {/* ── Neural Geodesic Constellation (Front Edges) ──────── */}
          {edges.map(([i, j], idx) => {
            const p1 = projectedNodes[i];
            const p2 = projectedNodes[j];
            if (p1.z >= 0 || p2.z >= 0) {
              const avgDepth = (p1.depth + p2.depth) / 2;
              return (
                <line
                  key={`front-${idx}`}
                  x1={p1.x}
                  y1={p1.y}
                  x2={p2.x}
                  y2={p2.y}
                  className="neural-edge front"
                  style={{ opacity: 0.28 + avgDepth * 0.58 }}
                />
              );
            }
            return null;
          })}

          {/* ── Radiant Central Singularity Core ─────────────────── */}
          <circle
            cx={half}
            cy={half}
            r={size * (0.09 + clampedLevel * 0.03)}
            fill="url(#neural-singularity)"
            className="neural-core"
          />
          <circle
            cx={half}
            cy={half}
            r="2.8"
            fill="#FFFFFF"
            className="neural-singularity-center"
          />

          {/* ── Neural Synaptic Nodes (Vertices) ─────────────────── */}
          {projectedNodes.map((node, idx) => {
            const isFront = node.z >= 0;
            const r = (isFront ? 2.1 : 1.3) + clampedLevel * 0.5;
            const opacity = 0.3 + node.depth * 0.7;

            return (
              <circle
                key={`node-${idx}`}
                cx={node.x}
                cy={node.y}
                r={r}
                className={`neural-node ${isFront ? 'node-front' : 'node-back'}`}
                style={{ opacity }}
              />
            );
          })}
        </svg>
      </div>

      {/* Understated Typography below the Orb */}
      <div className="orb-typography">
        <h2 className="orb-wordmark">JARVIS</h2>
        <p className="orb-context-status">
          {subtitle ??
            (state === 'listening'
              ? 'LISTENING · AUDIO STREAM ACTIVE'
              : state === 'thinking'
              ? 'SYNTHESIZING NEURAL INFERENCE...'
              : state === 'speaking'
              ? 'TRANSMITTING VOCAL SYNTHESIS...'
              : state === 'error'
              ? 'SYSTEM DIAGNOSTIC REQUIRED'
              : state === 'disconnected'
              ? 'OFFLINE · TAP TO INITIALIZE'
              : 'HOW CAN I HELP YOU TODAY?')}
        </p>
      </div>
    </div>
  );
};

export default AssistantOrb;
