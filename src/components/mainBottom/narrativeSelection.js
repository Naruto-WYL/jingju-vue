const STAGE_TEMPLATE = [
  { name: '开端', start: 0, end: 0.15, rhythm: '文戏铺垫' },
  { name: '发展', start: 0.15, end: 0.48, rhythm: '文武交替' },
  { name: '转折', start: 0.48, end: 0.64, rhythm: '冲突转折' },
  { name: '高潮', start: 0.64, end: 0.84, rhythm: '武戏/冲突集中' },
  { name: '结局', start: 0.84, end: 1, rhythm: '文戏收束' },
]

export function normalizeMetricRow(row) {
  return {
    scriptId: text(row['剧本ID']),
    scriptName: text(row['剧本名称']),
    category: text(row['剧目类别']),
    roleCount: toNumber(row['角色总数']),
    edgeCount: toNumber(row['实际关系数']),
    density: toNumber(row['网络密度']),
    centralization: toNumber(row['度中心化']),
  }
}

export function selectComplexScripts(rows, limit = 10) {
  const usableRows = rows.filter((row) => row.scriptId && row.scriptName && row.roleCount > 0)
  const maxRoles = Math.max(...usableRows.map((row) => row.roleCount), 1)
  const maxEdges = Math.max(...usableRows.map((row) => row.edgeCount), 1)

  return usableRows
    .map((row) => ({
      ...row,
      complexityScore:
        (row.roleCount / maxRoles) * 0.36 +
        (row.edgeCount / maxEdges) * 0.44 +
        Math.max(0, 1 - row.density) * 0.1 +
        row.centralization * 0.1,
    }))
    .sort((a, b) => b.complexityScore - a.complexityScore)
    .slice(0, limit)
}

export function buildGeneratedSceneRows(script, rank) {
  const sceneCount = getSceneCount(script)
  const pattern = getPatternProfile(script, rank)
  const relationScale = Math.max(1, script.edgeCount / Math.max(1, sceneCount))
  const roleScale = Math.max(1, script.roleCount / Math.max(1, sceneCount))

  return Array.from({ length: sceneCount }, (_, index) => {
    const progress = sceneCount > 1 ? index / (sceneCount - 1) : 0.5
    const pulse = getNarrativePulse(progress, pattern)
    const stageType = getStageAtProgress(progress).name
    const conflict = clamp(1.2 + pulse * 8.2 + script.centralization * 2.2 + getWave(progress, rank, 0.8), 0, 10)
    const emotion = clamp(1.6 + pulse * 7.4 + (1 - script.density) * 1.4 + getWave(progress, rank + 3, 0.9), 0, 10)
    const performance = clamp(2.0 + pulse * 6.6 + roleScale * 0.45 + getWave(progress, rank + 7, 1.1), 0, 10)
    const activity = clamp(2.4 + Math.min(7, roleScale * 1.15) + pulse * 2.8, 0, 10)
    const relationChanges = Math.max(0, Math.round(relationScale * (0.35 + pulse * 1.25)))
    const plotStrength = clamp(
      performance * 0.18 + conflict * 0.28 + emotion * 0.24 + activity * 0.12 + Math.min(10, relationChanges) * 0.18,
      0,
      10,
    )

      return {
        scriptId: script.scriptId,
        scriptName: script.scriptName,
        category: script.category,
        roleCount: script.roleCount,
        edgeCount: script.edgeCount,
        density: script.density,
        centralization: script.centralization,
        sceneName: `第${numberToChinese(index + 1)}场`,
      stageType,
      sequence: index + 1,
      performanceDensity: Number(performance.toFixed(2)),
      conflictStrength: Number(conflict.toFixed(2)),
      emotionStrength: Number(emotion.toFixed(2)),
      roleActivity: Number(activity.toFixed(2)),
      relationChanges,
      plotStrength: Number(plotStrength.toFixed(2)),
      summary: buildSceneSummary(script, stageType, index + 1, sceneCount, pattern.name),
    }
  })
}

export function buildGeneratedStageRows(script) {
  const sceneCount = getSceneCount(script)

  return STAGE_TEMPLATE.map((stage) => {
    const start = Math.max(1, Math.floor(stage.start * sceneCount) + 1)
    const end = Math.max(start, Math.min(sceneCount, Math.ceil(stage.end * sceneCount)))

    return {
      scriptId: script.scriptId,
      scriptName: script.scriptName,
      stageType: stage.name,
      startScene: `第${numberToChinese(start)}场`,
      endScene: `第${numberToChinese(end)}场`,
      summary: `${script.scriptName}在${stage.name}阶段呈现${stage.rhythm}`,
      rhythm: stage.rhythm,
    }
  })
}

function getSceneCount(script) {
  return Math.max(10, Math.min(24, Math.round(8 + script.roleCount * 0.18 + Math.sqrt(script.edgeCount) * 0.72)))
}

function getPatternProfile(script, rank) {
  if (script.edgeCount > 180 || script.roleCount > 34) {
    return {
      name: '多峰群像型',
      peaks: [
        { center: 0.28, width: 0.08, weight: 0.78 },
        { center: 0.58, width: 0.1, weight: 0.88 },
        { center: 0.79, width: 0.07, weight: 1 },
      ],
    }
  }

  if (script.centralization > 0.52) {
    return {
      name: '主轴强转折型',
      peaks: [
        { center: 0.48, width: 0.12, weight: 0.72 },
        { center: 0.72, width: 0.08, weight: 1 },
      ],
    }
  }

  if (script.density < 0.28) {
    return {
      name: '散点多线推进型',
      peaks: [
        { center: 0.22, width: 0.09, weight: 0.62 },
        { center: 0.52, width: 0.11, weight: 0.8 },
        { center: 0.86, width: 0.08, weight: 0.92 },
      ],
    }
  }

  return {
    name: rank % 2 === 0 ? '后置高潮型' : '渐强推进型',
    peaks: [
      { center: 0.42, width: 0.15, weight: 0.55 },
      { center: 0.76, width: 0.11, weight: 1 },
    ],
  }
}

function getNarrativePulse(progress, pattern) {
  const peakValue = pattern.peaks.reduce((sum, peak) => {
    const distance = progress - peak.center
    return sum + peak.weight * Math.exp(-(distance * distance) / (2 * peak.width * peak.width))
  }, 0)
  const risingTension = 0.22 + progress * 0.34

  return clamp(peakValue * 0.72 + risingTension, 0, 1)
}

function getStageAtProgress(progress) {
  return STAGE_TEMPLATE.find((stage) => progress >= stage.start && progress <= stage.end) || STAGE_TEMPLATE.at(-1)
}

function getWave(progress, seed, size) {
  return Math.sin(progress * Math.PI * (2.2 + (seed % 3) * 0.35) + seed) * size
}

function buildSceneSummary(script, stageType, sceneNumber, sceneCount, patternName) {
  const roleText = `${script.roleCount}个角色`
  const relationText = `${script.edgeCount}组关系`
  const positionText = sceneNumber === sceneCount ? '收束全剧冲突' : `推进${stageType}阶段`

  return `${script.category || '剧目'}《${script.scriptName}》以${roleText}、${relationText}${positionText}，呈现${patternName}结构`
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}

function numberToChinese(value) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue) || numberValue <= 0) return text(value)

  const digits = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九']
  const integer = Math.floor(numberValue)

  if (integer < 10) return digits[integer]
  if (integer === 10) return '十'
  if (integer < 20) return `十${digits[integer % 10]}`
  if (integer < 100) {
    const tens = Math.floor(integer / 10)
    const ones = integer % 10
    return `${digits[tens]}十${ones ? digits[ones] : ''}`
  }

  return String(integer)
}

function text(value) {
  return String(value ?? '').trim()
}

function toNumber(value) {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : 0
}
