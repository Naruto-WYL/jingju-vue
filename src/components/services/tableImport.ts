import type { LoopFlow, ScriptRecord } from '../types/loop';

const DATA_URL = '/data/loop_data.json';

interface LoopDataset {
  flows: LoopFlow[];
  scripts: ScriptRecord[];
}

export async function loadDemoDataset(): Promise<LoopDataset> {
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
