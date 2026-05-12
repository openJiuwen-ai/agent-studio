/**
 * Derives known / unknown / candidate entities from ActionInfoResponse.
 *
 * API shape:
 *   previous_state.state  →  array of entity items
 *   result.new_states     →  array of *state objects*, each with a .state array of entity items
 *
 * Each entity item: { id, type, question_clues[], discovered_clues[], candidate: string|null, candidate_strength: number|null }
 *
 * Rules:
 *   - candidate !== null in previous_state  →  Known
 *   - candidate !== null in new state only  →  Known + Hypothesis tag
 *   - candidate !== null in both            →  Known (use new value)
 *   - candidate === null in both            →  Unknown
 */
import type { Entity, CandidateEntity } from "./EntityPanel";
import type { ActionInfoResponse } from "./types";

// ── Helpers ──

interface StateItem {
  id: number | string;
  type?: string;
  question_clues?: string[];
  discovered_clues?: string[];
  candidate?: string | null;
  candidate_strength?: number | null;
}

function parseStateItem(raw: unknown): StateItem | null {
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  if (o.id == null) return null;
  return {
    id: o.id as number | string,
    type: typeof o.type === "string" ? o.type : undefined,
    question_clues: Array.isArray(o.question_clues)
      ? (o.question_clues as unknown[]).filter((c): c is string => typeof c === "string")
      : [],
    discovered_clues: Array.isArray(o.discovered_clues)
      ? (o.discovered_clues as unknown[]).filter((c): c is string => typeof c === "string")
      : [],
    candidate:
      typeof o.candidate === "string" && o.candidate.trim()
        ? o.candidate.trim()
        : null,
    candidate_strength:
      typeof o.candidate_strength === "number" ? o.candidate_strength : null,
  };
}

function extractPrevItems(prevState: unknown): StateItem[] {
  if (!prevState || typeof prevState !== "object") return [];
  const o = prevState as Record<string, unknown>;
  if (!Array.isArray(o.state)) return [];
  return (o.state as unknown[]).map(parseStateItem).filter((x): x is StateItem => x !== null);
}

function extractNewItems(result: unknown): StateItem[] {
  if (!result || typeof result !== "object" || Array.isArray(result)) return [];
  const o = result as Record<string, unknown>;
  const newStates = o.new_states;
  if (!Array.isArray(newStates)) return [];

  // new_states is an array of full state objects; pick the first one's .state array
  // (multiple new_states = multiple branches; use the first for display)
  for (const ns of newStates) {
    if (ns && typeof ns === "object" && !Array.isArray(ns)) {
      const inner = (ns as Record<string, unknown>).state;
      if (Array.isArray(inner)) {
        return (inner as unknown[]).map(parseStateItem).filter((x): x is StateItem => x !== null);
      }
    }
  }
  return [];
}

function itemKey(item: StateItem): string {
  return `id:${String(item.id)}`;
}

function displayName(item: StateItem): string {
  if (item.type) return item.type;
  if (item.question_clues && item.question_clues.length > 0) {
    return item.question_clues[0];
  }
  return `Entity ${item.id}`;
}

function allClues(prev?: StateItem, next?: StateItem): string[] {
  const set = new Set<string>();
  for (const item of [prev, next]) {
    if (!item) continue;
    for (const c of item.question_clues ?? []) set.add(c);
    for (const c of item.discovered_clues ?? []) set.add(c);
  }
  return [...set];
}

function discoveredOnly(prev?: StateItem, next?: StateItem): string[] {
  const set = new Set<string>();
  for (const item of [prev, next]) {
    if (!item) continue;
    for (const c of item.discovered_clues ?? []) set.add(c);
  }
  return [...set];
}

// ── Main derivation ──

export function deriveEntitiesFromActionInfo(info: ActionInfoResponse): {
  knownEntities: Entity[];
  unknownEntities: Entity[];
  candidateEntities: CandidateEntity[];
} {
  const knownEntities: Entity[] = [];
  const unknownEntities: Entity[] = [];
  const candidateEntities: CandidateEntity[] = [];

  const prevItems = extractPrevItems(info.previous_state);
  const newItems = extractNewItems(info.result);

  const prevByKey = new Map(prevItems.map((it) => [itemKey(it), it]));
  const newByKey = new Map(newItems.map((it) => [itemKey(it), it]));

  const allKeys = new Set([...prevByKey.keys(), ...newByKey.keys()]);

  for (const key of allKeys) {
    const prev = prevByKey.get(key);
    const next = newByKey.get(key);

    const ref = next ?? prev!;
    const name = displayName(ref);
    const type = ref.type;

    const prevCandidate = prev?.candidate ?? null;
    const nextCandidate = next?.candidate ?? null;

    const prevStrength = prev?.candidate_strength ?? null;
    const nextStrength = next?.candidate_strength ?? null;

    const discovered = discoveredOnly(prev, next);
    const questionClues = allClues(prev, next);

    if (prevCandidate === null && nextCandidate === null) {
      // Unknown
      unknownEntities.push({
        name,
        type,
        ...(questionClues.length ? { discoveredClues: questionClues } : {}),
      });
      continue;
    }

    // At least one side has a candidate → Known
    const candidateValue = nextCandidate ?? prevCandidate!;
    const strength = nextStrength ?? prevStrength;
    const fromNewState = prevCandidate === null && nextCandidate !== null;

    knownEntities.push({
      name,
      value: candidateValue,
      type,
      fromNewState,
      ...(discovered.length ? { discoveredClues: discovered } : {}),
    });

    // Build candidate entry with confidence
    const confidence = strength != null
      ? (strength > 1 ? strength / 100 : strength)
      : 1;
    candidateEntities.push({
      name,
      candidates: [{ value: candidateValue, confidence }],
    });
  }

  // Fallback when API has no structured state arrays at all.
  // Prefer a concise hypothesis preview rather than dumping raw JSON.
  if (prevItems.length === 0 && newItems.length === 0) {
    if (info.result && typeof info.result === "object" && !Array.isArray(info.result)) {
      const answerPreview = (info.result as Record<string, unknown>).answer_preview;
      if (typeof answerPreview === "string" && answerPreview.trim()) {
        knownEntities.push({
          name: "Answer",
          value: answerPreview.trim(),
          type: "hypothesis",
          fromNewState: true,
        });
      }
    } else if (typeof info.result === "string" && info.result.trim()) {
      const s = info.result.trim();
      knownEntities.push({
        name: "Result",
        value: s.length > 2000 ? `${s.slice(0, 2000)}…` : s,
        type: "result",
      });
    }
    if (info.previous_state != null && unknownEntities.length === 0) {
      unknownEntities.push({
        name: "Previous state",
        type: "state",
      });
    }
  }

  return { knownEntities, unknownEntities, candidateEntities };
}
