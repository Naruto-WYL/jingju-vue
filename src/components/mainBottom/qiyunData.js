export const QIYUN_CSV_URL = '/数据表合集/4/jingju_scene_dynamics_from_pdf_new.csv'

export const STAGE_ORDER = ['凝缩', '开端', '发展', '转折', '高潮', '结局']
export const FIVE_STAGE_LABELS = ['开端', '发展', '转折', '高潮', '结局']

export const streamColorNames = ['表演形式', '角色活跃', '冲突强度', '关系变化', '情绪波动', '综合剧情']
export const streamColorsStroke = ['#28598B', '#34704B', '#A65327', '#624D7A', '#B5312C', '#333333']
export const streamColorsFill = [
  'rgba(40,89,139,0.05)',
  'rgba(52,112,75,0.05)',
  'rgba(166,83,39,0.05)',
  'rgba(98,77,122,0.05)',
  'rgba(181,49,44,0.05)',
  'rgba(51,51,51,0.05)',
]

export const compareKeys = ['flat', 'frontPeak', 'backPeak', 'midPeak', 'multiPeak']
export const compareColorsStroke = ['#4D6666', '#B35C37', '#624D7A', '#34704B', '#28598B']
export const compareTypeMeta = {
  flat: {
    name: '平稳型',
    definition:
      '平稳型指叙事张力在开端、发展、转折、高潮、结局五个阶段中保持低幅度摆动，戏剧能量不依赖单一爆点，而通过连续、均衡的情境推进维持观看动力。',
    rule: '按开端、发展、转折、高潮、结局计算阶段均值；最高值与最低值差距小于18个百分点时归入此类。',
  },
  frontPeak: {
    name: '前峰型',
    definition:
      '前峰型指全剧最高叙事能量集中在开端，故事一开始即抛出危机、冲突或强情绪，后续段落主要承担解释、周旋、消化与收束功能。',
    rule: '五阶段中开端的综合剧情强度为最高点，且整体呈高开低走或前段明显支配全剧。',
  },
  backPeak: {
    name: '后峰型',
    definition:
      '后峰型指叙事能量在前中段持续蓄积，开端与发展阶段主要负责铺垫、隐忍或推进，核心冲突在高潮或结局阶段集中释放。',
    rule: '五阶段中高潮或结局为最高点，且整体呈低开高走或后段明显支配全剧。',
  },
  midPeak: {
    name: '中峰型',
    definition:
      '中峰型指叙事张力呈“两端收束、中段拱起”的拱形结构，发展或转折阶段承担主要戏剧压力，开端用于导入，结局回落为解释或伦理归位。',
    rule: '五阶段中发展或转折为最高点，且中段强度明显高于开端和结局。',
  },
  multiPeak: {
    name: '多峰型',
    definition:
      '多峰型指全剧存在两个及以上显著张力高点，叙事在冲突释放与重新蓄势之间反复摆动，形成多次上升、回落和再爆发。',
    rule: '五阶段曲线出现至少两处接近主峰的高点，或上升、回落方向发生两次及以上明显反转。',
  },
}

let qiyunDatasetPromise = null

export async function loadQiyunDataset() {
  if (qiyunDatasetPromise) return qiyunDatasetPromise

  qiyunDatasetPromise = fetch(encodeURI(`${QIYUN_CSV_URL}?t=${Date.now()}`), { cache: 'no-store' })
    .then((response) => {
      if (!response.ok) throw new Error(`CSV 加载失败：${response.status}`)
      return response.text()
    })
    .then((text) => {
      const scripts = buildScriptsFromCsv(parseCsv(text))
      return {
        scripts,
        stageBuckets: buildStageBuckets(scripts),
        compareScripts: buildCompareTypeScripts(scripts),
      }
    })

  return qiyunDatasetPromise
}

export function parseCsv(text) {
  const rows = []
  let row = []
  let cell = ''
  let inQuotes = false
  const normalized = String(text || '').replace(/^\uFEFF/, '')

  for (let i = 0; i < normalized.length; i++) {
    const ch = normalized[i]
    const next = normalized[i + 1]
    if (inQuotes) {
      if (ch === '"' && next === '"') {
        cell += '"'
        i++
      } else if (ch === '"') {
        inQuotes = false
      } else {
        cell += ch
      }
    } else if (ch === '"') {
      inQuotes = true
    } else if (ch === ',') {
      row.push(cell)
      cell = ''
    } else if (ch === '\n') {
      row.push(cell.replace(/\r$/, ''))
      rows.push(row)
      row = []
      cell = ''
    } else {
      cell += ch
    }
  }

  if (cell.length || row.length) {
    row.push(cell.replace(/\r$/, ''))
    rows.push(row)
  }

  const header = rows.shift() || []
  return rows
    .filter((item) => item.some((value) => value !== ''))
    .map((item) => Object.fromEntries(header.map((name, index) => [name, item[index] ?? ''])))
}

export function buildScriptsFromCsv(rows) {
  const groups = new Map()

  rows.forEach((row) => {
    const id = (row['剧本编号'] || `${row['剧本名']}-${groups.size}`).trim()
    if (!groups.has(id)) groups.set(id, [])
    groups.get(id).push(row)
  })

  const rawScripts = {}

  groups.forEach((items, id) => {
    const scriptName = items[0]['剧本名'] || id
    const sourceScenes = items
      .map((row, rowIndex) => {
        const sceneNo = parseSceneOrder(row['场次'], rowIndex)
        return {
          sceneId: `${id}_scene_${String(sceneNo).padStart(2, '0')}`,
          sceneNo,
          stage: row['阶段'] || '未分段',
          theme: row['场次对应主题'] || '未识别主题',
          label: row['场次'] || '未命名场次',
          order: sceneNo,
          data: [
            numeric(row, '表演形式强度'),
            numeric(row, '角色活跃度'),
            numeric(row, '冲突强度'),
            numeric(row, '关系变化强度'),
            numeric(row, '情绪强度'),
            numeric(row, '综合剧情强度'),
          ],
          roles: [numeric(row, '生占比'), numeric(row, '旦占比'), numeric(row, '净占比'), numeric(row, '丑占比')],
          speed: numeric(row, '基准流速'),
          turb: numeric(row, '湍流震荡值'),
          desc: row['剧作动力学分析'] || '暂无剧作动力学分析。',
        }
      })
      .sort((a, b) => a.order - b.order)

    const rawStages = unique(sourceScenes.map((scene) => scene.stage)).sort(compareStageOrder)
    const actualScenes = normalizeSceneStageOrder(sourceScenes, rawStages)
    const stages = unique(actualScenes.map((scene) => scene.stage)).sort(compareStageOrder)
    const displayScenes =
      actualScenes.length === 1
        ? [spreadCondensedSceneData(actualScenes[0])]
        : actualScenes.map((scene) => (scene.stage === '凝缩' ? spreadCondensedSceneData(scene) : scene))

    const scenes = [
      {
        sceneId: `${id}_scene_00`,
        sceneNo: 0,
        stage: '起步',
        theme: '大幕初启',
        label: '起步',
        data: [0, 0, 0, 0, 0, 0],
        roles: [25, 25, 25, 25],
        speed: 0.02,
        turb: 5,
        desc: `《${scriptName}》气韵推演即将开始。`,
      },
      ...displayScenes,
    ]

    const stageProgress = {}
    stages.forEach((stage) => {
      const index =
        stage === '结局' ? scenes.map((scene) => scene.stage).lastIndexOf(stage) : scenes.findIndex((scene) => scene.stage === stage)
      stageProgress[stage] = index <= 0 ? 0 : index / Math.max(1, scenes.length - 1)
    })

    rawScripts[id] = {
      key: id,
      scriptId: id,
      name: `《${scriptName}》`,
      plainName: scriptName,
      mode: inferModeName(scenes),
      stages,
      stageCount: stages.length,
      stageProgress,
      axisXLabels: displayScenes.map((scene) => scene.label),
      scenes,
    }
  })

  const bestByName = {}
  Object.entries(rawScripts).forEach(([key, script]) => {
    const current = bestByName[script.plainName]
    const currentScript = current ? rawScripts[current] : null
    const isBetter =
      !currentScript ||
      script.stageCount > currentScript.stageCount ||
      (script.stageCount === currentScript.stageCount && script.scenes.length > currentScript.scenes.length)
    if (isBetter) bestByName[script.plainName] = key
  })

  const scripts = {}
  Object.entries(bestByName)
    .sort((a, b) => a[0].localeCompare(b[0], 'zh-Hans-CN'))
    .forEach(([, key]) => {
      scripts[key] = rawScripts[key]
    })
  return scripts
}

export function buildStageBuckets(scripts) {
  const buckets = {}
  Object.entries(scripts).forEach(([key, script]) => {
    const count = script.stageCount || script.stages.length || 1
    if (!buckets[count]) buckets[count] = []
    buckets[count].push(key)
  })
  Object.values(buckets).forEach((keys) =>
    keys.sort((a, b) => scripts[a].plainName.localeCompare(scripts[b].plainName, 'zh-Hans-CN')),
  )
  return buckets
}

export function stageCountLabel(count) {
  return Number(count) === 1 ? '1阶段' : `${count}阶段`
}

export function getFiveStageValues(script) {
  if (!script) return null
  const actualScenes = script.scenes.slice(1)
  const values = FIVE_STAGE_LABELS.map((stage) => {
    const matched = actualScenes.filter((scene) => scene.stage === stage)
    if (!matched.length) return null
    return matched.reduce((sum, scene) => sum + scene.data[5], 0) / matched.length
  })
  return values.some((value) => value === null) ? null : values
}

export function classifyFiveStageCurve(values) {
  if (!values?.length) return ''
  const max = Math.max(...values)
  const min = Math.min(...values)
  const peakIndex = values.indexOf(max)
  const nearPeakCount = values.filter((value) => max - value <= 8 && value - min >= 12).length
  let turns = 0
  let lastSign = 0

  for (let i = 1; i < values.length; i++) {
    const delta = values[i] - values[i - 1]
    const sign = Math.abs(delta) < 8 ? 0 : Math.sign(delta)
    if (sign && lastSign && sign !== lastSign) turns++
    if (sign) lastSign = sign
  }

  if (max - min < 18) return 'flat'
  if (nearPeakCount >= 2 || turns >= 2) return 'multiPeak'
  if (peakIndex === 0) return 'frontPeak'
  if (peakIndex === 1 || peakIndex === 2) return 'midPeak'
  return 'backPeak'
}

export function buildCompareTypeScripts(scripts) {
  const buckets = Object.fromEntries(compareKeys.map((key) => [key, []]))

  Object.entries(scripts).forEach(([key, script]) => {
    const values = getFiveStageValues(script)
    if (!values) return
    const typeKey = classifyFiveStageCurve(values)
    buckets[typeKey].push({ key, script, values })
  })

  const built = {}
  const prototypeCurves = {
    flat: [58, 60, 59, 61, 58],
    frontPeak: [90, 66, 48, 38, 32],
    backPeak: [30, 42, 55, 76, 90],
    midPeak: [34, 58, 88, 58, 34],
    multiPeak: [78, 38, 84, 42, 76],
  }
  const fallbackReps = {
    flat: ['《哭秦庭》'],
    frontPeak: ['《双尽忠》'],
    backPeak: ['《九龙杯》', '《贺后骂殿》'],
    midPeak: ['《三娘教子》'],
    multiPeak: ['《草桥关》'],
  }

  compareKeys.forEach((typeKey) => {
    const samples = buckets[typeKey]
    const meta = compareTypeMeta[typeKey]
    const curveValues = prototypeCurves[typeKey]
    const reps = samples.length
      ? samples
          .map((sample) => ({
            name: sample.script.name,
            distance: sample.values.reduce((sum, value, index) => sum + Math.abs(value - curveValues[index]), 0),
          }))
          .sort((a, b) => a.distance - b.distance || a.name.localeCompare(b.name, 'zh-Hans-CN'))
          .slice(0, 4)
          .map((rep) => rep.name)
      : fallbackReps[typeKey]

    built[typeKey] = {
      key: typeKey,
      name: meta.name,
      mode: meta.name,
      definition: meta.definition,
      rule: meta.rule,
      sampleCount: samples.length,
      reps,
      stages: FIVE_STAGE_LABELS,
      axisXLabels: FIVE_STAGE_LABELS,
      scenes: [
        { stage: '起步', theme: '大幕初启', label: '起步', data: [0, 0, 0, 0, 0, 0], roles: [25, 25, 25, 25], speed: 0, turb: 0, desc: '' },
        ...FIVE_STAGE_LABELS.map((stage, index) => ({
          stage,
          theme: stage,
          label: stage,
          data: [0, 0, 0, 0, 0, curveValues[index]],
          roles: [25, 25, 25, 25],
          speed: 0,
          turb: 0,
          desc: `${meta.name}在“${stage}”阶段的原型综合剧情强度为${curveValues[index]}%。`,
        })),
      ],
    }
  })

  return built
}

export function findScriptKeyByPlay(scripts, playId, title = '') {
  if (playId && scripts[playId]) return playId
  const cleanTitle = String(title || '').replace(/[《》]/g, '')
  return (
    Object.keys(scripts).find((key) => {
      const script = scripts[key]
      return script.plainName === cleanTitle || script.name === title || script.name === `《${cleanTitle}》`
    }) || ''
  )
}

export function sceneNoFromSceneId(sceneId) {
  const match = String(sceneId || '').match(/scene_(\d+)$/)
  return match ? Number(match[1]) : 0
}

function numeric(row, key) {
  const value = Number(row[key])
  return Number.isFinite(value) ? value : 0
}

function inferModeName(scenes) {
  const actual = scenes.slice(1)
  if (actual.length <= 2 || actual.some((scene) => scene.stage === '凝缩')) return '凝缩场次'
  const values = actual.map((scene) => scene.data[5])
  const max = Math.max(...values)
  const min = Math.min(...values)
  if (max - min < 18) return '平稳型'

  let turns = 0
  let lastSign = 0
  for (let i = 1; i < values.length; i++) {
    const delta = values[i] - values[i - 1]
    const sign = Math.abs(delta) < 5 ? 0 : Math.sign(delta)
    if (sign && lastSign && sign !== lastSign) turns++
    if (sign) lastSign = sign
  }

  if (turns >= 2) return '多峰型'
  const peakIndex = values.indexOf(max)
  const peakStage = actual[peakIndex]?.stage || ''
  if (peakStage === '开端') return '前峰型'
  if (peakStage === '发展' || peakStage === '转折') return '中峰型'
  return '后峰型'
}

function parseSceneOrder(label, fallbackIndex) {
  const text = String(label || '')
  const arabic = text.match(/\d+/)
  if (arabic) return Number(arabic[0])

  const chineseDigits = { 零: 0, '〇': 0, 一: 1, 二: 2, 两: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9 }
  const match = text.match(/第([一二两三四五六七八九十百〇零]+)场/)
  if (!match) return fallbackIndex + 1
  const raw = match[1]
  if (raw === '十') return 10
  if (raw.includes('十')) {
    const [tensRaw, onesRaw] = raw.split('十')
    const tens = tensRaw ? chineseDigits[tensRaw] : 1
    const ones = onesRaw ? chineseDigits[onesRaw] : 0
    return tens * 10 + ones
  }
  return [...raw].reduce((sum, char) => sum * 10 + (chineseDigits[char] ?? 0), 0) || fallbackIndex + 1
}

function normalizeSceneStageOrder(actualScenes, stages) {
  const orderedStages = stages.filter((stage) => STAGE_ORDER.includes(stage) && stage !== '凝缩')
  if (orderedStages.length <= 1) return actualScenes

  let searchFrom = 0
  const milestones = []
  orderedStages.forEach((stage) => {
    const foundIndex = actualScenes.findIndex((scene, index) => index >= searchFrom && scene.stage === stage)
    if (foundIndex !== -1) {
      milestones.push({ stage, index: foundIndex })
      searchFrom = foundIndex + 1
    }
  })

  if (milestones.length <= 1) return actualScenes

  const normalized = actualScenes.map((scene, index) => {
    let nearest = milestones[0]
    milestones.forEach((point) => {
      const distance = Math.abs(index - point.index)
      const nearestDistance = Math.abs(index - nearest.index)
      if (distance < nearestDistance || (distance === nearestDistance && point.index > nearest.index)) nearest = point
    })
    return { ...scene, originalStage: scene.stage, stage: nearest.stage }
  })

  if (orderedStages.includes('结局') && normalized.length) {
    normalized[normalized.length - 1] = { ...normalized[normalized.length - 1], stage: '结局' }
  }

  return normalized
}

function spreadCondensedSceneData(scene) {
  const values = scene.data.slice(0, 6)
  const allSame = values.every((value) => Math.abs(value - values[0]) < 0.001)
  if (!allSame) return scene

  const total = Math.max(35, Math.min(100, values[5] || values[0] || 70))
  const theme = `${scene.theme || ''}${scene.desc || ''}`
  const weights = [0.92, 0.86, 0.78, 0.7, 0.82]

  if (/武|战|杀|兵|打|擒|阵/.test(theme)) weights.splice(0, 5, 0.88, 0.82, 1, 0.66, 0.76)
  else if (/情|哭|泪|悲|恨|怨|母|子|夫妻|离/.test(theme)) weights.splice(0, 5, 0.68, 0.76, 0.58, 0.86, 1)
  else if (/谋|计|诈|议|问|说|劝|探/.test(theme)) weights.splice(0, 5, 0.72, 0.82, 0.66, 1, 0.74)
  else if (/审|冤|罪|法|告|辨/.test(theme)) weights.splice(0, 5, 0.7, 0.78, 0.9, 1, 0.88)

  const data = weights.map((weight) => Math.round(Math.max(18, Math.min(100, total * weight))))
  data.push(total)
  const turb = Math.max(scene.turb || 0, Math.round((Math.max(...data.slice(0, 5)) - Math.min(...data.slice(0, 5))) * 0.8))
  return { ...scene, data, turb }
}

function compareStageOrder(a, b) {
  const ia = STAGE_ORDER.indexOf(a)
  const ib = STAGE_ORDER.indexOf(b)
  return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib)
}

function unique(values) {
  return Array.from(new Set(values.filter(Boolean)))
}
