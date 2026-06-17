export interface LoopFilters {
  relation: string;
  narrative: string;
  evolution: string;
  limit: number;
}

export interface LoopFlow {
  id: string;
  relationType: string;
  themeCombo: string;
  narrativeType: string;
  evolutionType: string;
  count: number;
  scripts: string[];
  narrativeCurve?: number[];
  evolutionCurve?: number[];
  waveType?: string;
  waveDescription?: string;
  outcomeDescription?: string;
}

export interface ScriptRecord {
  id: string;
  title: string;
  period?: string;
  path?: string;
  relationType?: string;
  themeCombo?: string;
  mainTheme?: string;
  subThemes?: string[];
  narrativeType?: string;
  narrativeCurve?: number[];
  evolutionType?: string;
  evolutionCurve?: number[];
  topPair?: string;
  topRelations?: Array<{
    a: string;
    b: string;
    strength: number;
    type: string;
  }>;
  sceneCount?: number;
  network?: {
    roleCount?: number;
    density?: number;
    centerRole?: string;
  };
  stageEvents?: Array<{
    stage: string;
    event: string;
    tension: number;
    roles?: string[];
    keywords?: string[];
  }>;
  relationEvidence?: Array<{
    pair: string;
    stage: string;
    evidence: string;
    strength: number;
  }>;
  themeEvidence?: Array<{
    theme: string;
    evidence: string;
    weight: number;
  }>;
  detailTags?: string[];
}
