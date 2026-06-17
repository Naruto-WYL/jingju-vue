import type { LoopFlow, ScriptRecord } from '../types/loop';

const DATA_URL = '/data/loop_data.json';
const CLOSURE_CSV_URL = '/data/loop_closure_limited.csv';

interface LoopDataset {
  flows: LoopFlow[];
  scripts: ScriptRecord[];
}

export async function loadDemoDataset(): Promise<LoopDataset> {
  try {
    const csvDataset = await loadClosureCsvDataset();
    if (csvDataset.flows.length) return csvDataset;
  } catch (error) {
    console.warn('closure csv fallback to json', error);
  }

  const response = await fetch(DATA_URL);
  if (!response.ok) {
    throw new Error(`无法读取闭环数据：${DATA_URL} (${response.status})`);
  }

  const dataset = await response.json();
  return {
    flows: Array.isArray(dataset.flows) ? dataset.flows : [],
    scripts: Array.isArray(dataset.scripts) ? dataset.scripts : [],
  };
}

async function loadClosureCsvDataset(): Promise<LoopDataset> {
  const response = await fetch(`${CLOSURE_CSV_URL}?t=${Date.now()}`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`cannot load closure csv: ${response.status}`);

  const rows = parseCsv(await response.text());
  const scripts: ScriptRecord[] = [];
  const flows = rows
    .map((row, index) => {
      const flow = normalizeClosureFlow(row, index);
      scripts.push(...buildScriptRecords(row, flow));
      return flow;
    })
    .filter((flow) => flow.relationType && flow.themeCombo && flow.narrativeType);

  return { flows, scripts };
}

function normalizeClosureFlow(row: Record<string, string>, index: number): LoopFlow {
  const id = value(row, '闭环ID') || `loop-${String(index).padStart(3, '0')}`;
  const relationType = value(row, '角色关系类型');
  const theme = value(row, '主题');
  const scriptIds = splitList(value(row, '剧本ID列表'));
  const narrativeCurve = parseCurve(value(row, '叙事平均曲线'));
  const evolutionCurve = parseCurve(value(row, '关系强度平均曲线'));

  return {
    id,
    relationType,
    themeCombo: theme,
    narrativeType: value(row, '叙事结构线'),
    evolutionType: value(row, '关系演化结局'),
    count: numberValue(row, '剧本数量') || scriptIds.length || 1,
    scripts: scriptIds.length ? scriptIds.map((scriptId, scriptIndex) => scriptRecordId(id, scriptId, scriptIndex)) : [scriptRecordId(id, id, 0)],
    narrativeCurve,
    evolutionCurve,
    waveType: value(row, '波动型'),
    waveDescription: value(row, '波动说明'),
    outcomeDescription: value(row, '结局释义'),
  };
}

function buildScriptRecords(row: Record<string, string>, flow: LoopFlow): ScriptRecord[] {
  const sourceIds = splitList(value(row, '剧本ID列表'));
  const sourceTitles = splitList(value(row, '代表剧目列表'));
  const ids = sourceIds.length ? sourceIds : [flow.id];
  const narrativeCurve = flow.narrativeCurve?.length ? flow.narrativeCurve : [3, 4, 5, 4, 3];
  const evolutionCurve = flow.evolutionCurve?.length ? flow.evolutionCurve : narrativeCurve;
  const waveType = value(row, '波动型');
  const waveDescription = value(row, '波动说明');
  const outcome = value(row, '关系演化结局');
  const outcomeDescription = value(row, '结局释义');
  const themeScore = numberValue(row, '主题匹配均值');
  const relationScore = numberValue(row, '关系匹配均值');
  const path = value(row, '层级路径');

  return ids.map((sourceId, index) => {
    const title = sourceTitles[index] || sourceTitles[index % Math.max(1, sourceTitles.length)] || sourceId;
    const tension = normalizedCurve(narrativeCurve);

    return {
      id: scriptRecordId(flow.id, sourceId, index),
      title,
      path,
      relationType: flow.relationType,
      themeCombo: flow.themeCombo,
      mainTheme: flow.themeCombo,
      subThemes: [flow.themeCombo],
      narrativeType: flow.narrativeType,
      narrativeCurve,
      evolutionType: flow.evolutionType,
      evolutionCurve,
      topPair: `${flow.relationType} / ${flow.themeCombo}`,
      topRelations: [
        {
          a: flow.relationType,
          b: flow.themeCombo,
          strength: Math.max(1, Math.round((relationScore || flow.count) / 10)),
          type: flow.relationType,
        },
      ],
      sceneCount: narrativeCurve.length,
      network: {
        roleCount: Math.max(2, Math.round((relationScore || 60) / 12)),
        density: Number(((relationScore || 60) / 100).toFixed(2)),
        centerRole: flow.relationType,
      },
      stageEvents: tension.map((stageTension, stageIndex) => ({
        stage: stageName(stageIndex),
        event: `${waveType || flow.narrativeType}：${waveDescription || flow.themeCombo}`,
        tension: stageTension,
        roles: [flow.relationType],
        keywords: [flow.themeCombo, outcome].filter(Boolean),
      })),
      relationEvidence: [
        {
          pair: `${flow.relationType}-${flow.themeCombo}`,
          stage: flow.narrativeType,
          evidence: outcomeDescription || outcome,
          strength: Math.max(1, Math.round((relationScore || 60) / 12)),
        },
      ],
      themeEvidence: [
        {
          theme: flow.themeCombo,
          evidence: `${flow.relationType}下的${flow.themeCombo}主题，匹配均值${themeScore || '未标注'}`,
          weight: Math.max(1, Math.round((themeScore || 60) / 12)),
        },
      ],
      detailTags: [flow.relationType, flow.themeCombo, flow.narrativeType, waveType, outcome].filter(Boolean),
    };
  });
}

function parseCsv(csvText: string): Record<string, string>[] {
  const lines = csvText.replace(/^\uFEFF/, '').split(/\r?\n/).filter((line) => line.trim());
  const headers = parseCsvLine(lines[0] || '').map((header) => header.trim().replace(/^\uFEFF/, ''));

  return lines.slice(1).map((line) => {
    const cells = parseCsvLine(line);
    return Object.fromEntries(headers.map((header, index) => [header, (cells[index] || '').trim()]));
  });
}

function parseCsvLine(line: string): string[] {
  const cells: string[] = [];
  let current = '';
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];

    if (char === '"' && inQuotes && next === '"') {
      current += '"';
      index += 1;
      continue;
    }

    if (char === '"') {
      inQuotes = !inQuotes;
      continue;
    }

    if (char === ',' && !inQuotes) {
      cells.push(current);
      current = '';
      continue;
    }

    current += char;
  }

  cells.push(current);
  return cells;
}

function value(row: Record<string, string>, key: string) {
  return String(row[key] || '').trim();
}

function numberValue(row: Record<string, string>, key: string) {
  const number = Number(value(row, key));
  return Number.isFinite(number) ? number : 0;
}

function splitList(text: string) {
  return text
    .split(/[;；]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseCurve(text: string) {
  if (!text) return [];

  try {
    const values = JSON.parse(text);
    if (Array.isArray(values)) return values.map(Number).filter((item) => Number.isFinite(item));
  } catch {
    // Fall through to delimiter parsing.
  }

  return text
    .replace(/^\[/, '')
    .replace(/\]$/, '')
    .split(/[,\s;；]+/)
    .map(Number)
    .filter((item) => Number.isFinite(item));
}

function normalizedCurve(curve: number[]) {
  const values = curve.map(Number).filter((item) => Number.isFinite(item));
  if (!values.length) return [0.42, 0.52, 0.66, 0.54, 0.4];
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (max === min) return values.map(() => 0.5);
  return values.map((item) => Number((0.12 + ((item - min) / (max - min)) * 0.88).toFixed(3)));
}

function stageName(index: number) {
  return ['开端', '承接', '发展', '高潮', '转折', '收束', '余波', '回环', '清算', '终局'][index] || `阶段${index + 1}`;
}

function scriptRecordId(flowId: string, scriptId: string, index: number) {
  return `${flowId}::${scriptId || index}`;
}
