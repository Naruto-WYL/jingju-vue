<template>
  <section ref="panelRef" class="vertical-upset-panel" aria-label="主题组合矩阵图">
    <div v-if="loading" class="upset-state">主题组合加载中...</div>
    <div v-else-if="error" class="upset-state upset-state--error">{{ error }}</div>
    <svg v-else ref="svgRef" class="vertical-upset-svg" role="img" aria-label="跨剧本主题组合纵向矩阵图" />

    <button v-if="activeFilterLabel" class="upset-return-btn" type="button" @click="returnToFullThemeCombos">
      返回全图
    </button>

    <div ref="tooltipRef" class="upset-tooltip" />
  </section>
</template>

<script setup>
import * as d3 from 'd3'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { clearLoopFilter, loopFilterState } from '../../services/loopFilterStore'

const PLAY_URL = '/data/theme_matrix_play_full.csv'
const AGGREGATE_URL = '/data/theme_matrix_combo_full.csv'
const HIGHLIGHT_URL = '/data/theme_matrix_highlight_full.csv'
const CORE_BAR_URL = '/data/theme_matrix_core_bar_full.csv'

const H = {
  playId: '剧本ID',
  title: '剧本名称',
  category: '剧目类别',
  coreRelation: '核心关系',
  coreTheme: '核心主题',
  secondaryThemes: '次要主题集合',
  themeCombo: '主题组合',
  themeComboDisplay: '主题组合显示',
  comboId: '主题组合ID',
  count: '剧本数量',
  matrixOrder: '矩阵行排序',
  primaryCoreTheme: '主要核心主题',
  coreThemeDistribution: '核心主题分布',
  primaryRelation: '主要核心关系',
  relationDistribution: '核心关系分布',
  representativeTitles: '代表剧目列表',
  playIdList: '剧本ID列表',
  theme: '主题',
  themeOrder: '主题序号',
  comboOrder: '组合内顺序',
  coreThemeCount: '核心主题剧本数',
  occurrenceCount: '参与主题组合剧本数',
  comboTypeCount: '参与组合种类数',
}

const THEME_ORDER = [
  '忠义家国',
  '政治权力',
  '婚恋姻缘',
  '家庭亲情',
  '公案冤狱',
  '除暴侠义',
  '战争武略',
  '恩怨报偿',
  '善恶转化',
  '礼教品格',
  '宗教祥瑞',
  '文人世情',
]

const RELATION_THEME_MAP = {
  亲属关系: ['家庭亲情', '礼教品格', '忠义家国', '恩怨报偿'],
  婚恋关系: ['婚恋姻缘', '家庭亲情', '礼教品格', '文人世情'],
  权力关系: ['政治权力', '忠义家国', '战争武略', '礼教品格'],
  同盟关系: ['忠义家国', '战争武略', '除暴侠义', '政治权力'],
  冲突关系: ['战争武略', '恩怨报偿', '善恶转化', '除暴侠义'],
  审判与恩怨关系: ['公案冤狱', '恩怨报偿', '善恶转化', '礼教品格'],
}

const themePalette = [
  '#b64a3a',
  '#d9853f',
  '#ad697d',
  '#4f9689',
  '#7f73a8',
  '#567f9b',
  '#7f9667',
  '#9a7350',
  '#c46f43',
  '#6e8d73',
  '#5d83a3',
  '#a56b88',
]

const TOP_COMBO_LIMIT = 18

const panelRef = ref(null)
const svgRef = ref(null)
const tooltipRef = ref(null)
const playRows = ref([])
const aggregateRows = ref([])
const highlightRows = ref([])
const coreBarRows = ref([])
const loading = ref(false)
const error = ref('')
let resizeObserver = null

const activeFilterLabel = computed(() => {
  const scope = loopFilterState.scope
  const flow = loopFilterState.flow
  if (!scope) return ''
  if (scope.type === 'relation') return scope.relationType
  if (scope.type === 'theme') return `${scope.relationType} / ${scope.themeCombo}`
  if (scope.type === 'flow' && flow) return `${flow.relationType} / ${flow.themeCombo}`
  return ''
})

const highlightThemesByCombo = computed(() => {
  const map = new Map()

  highlightRows.value.forEach((row) => {
    const comboId = field(row, H.comboId)
    const theme = field(row, H.theme)
    if (!comboId || !THEME_ORDER.includes(theme)) return
    if (!map.has(comboId)) map.set(comboId, [])
    map.get(comboId).push({
      theme,
      order: toNumber(field(row, H.comboOrder), 999),
    })
  })

  map.forEach((items, comboId) => {
    const ordered = items
      .slice()
      .sort((a, b) => a.order - b.order || THEME_ORDER.indexOf(a.theme) - THEME_ORDER.indexOf(b.theme))
      .map((item) => item.theme)
    map.set(comboId, uniqueByThemeOrder(ordered))
  })

  return map
})

const coreBarByTheme = computed(() => {
  const map = new Map()
  coreBarRows.value.forEach((row) => {
    const theme = field(row, H.theme)
    if (theme) map.set(theme, row)
  })
  return map
})

const upsetData = computed(() => buildUpsetData())

watch(
  [upsetData, loading, error, activeFilterLabel],
  async () => {
    await nextTick()
    renderUpset()
  },
  { deep: true, flush: 'post' },
)

onMounted(async () => {
  resizeObserver = new ResizeObserver(() => renderUpset())
  if (panelRef.value) resizeObserver.observe(panelRef.value)
  await loadRows()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
})

async function loadRows() {
  loading.value = true
  error.value = ''

  try {
    const [playResponse, aggregateResponse, highlightResponse, coreBarResponse] = await Promise.all([
      fetch(`${PLAY_URL}?t=${Date.now()}`, { cache: 'no-store' }),
      fetch(`${AGGREGATE_URL}?t=${Date.now()}`, { cache: 'no-store' }),
      fetch(`${HIGHLIGHT_URL}?t=${Date.now()}`, { cache: 'no-store' }),
      fetch(`${CORE_BAR_URL}?t=${Date.now()}`, { cache: 'no-store' }),
    ])

    if (!playResponse.ok) throw new Error(`剧本级主题矩阵读取失败：${playResponse.status}`)
    if (!aggregateResponse.ok) throw new Error(`主题组合统计读取失败：${aggregateResponse.status}`)
    if (!highlightResponse.ok) throw new Error(`主题组合亮点长表读取失败：${highlightResponse.status}`)
    if (!coreBarResponse.ok) throw new Error(`核心主题柱状读取失败：${coreBarResponse.status}`)

    const [playText, aggregateText, highlightText, coreBarText] = await Promise.all([
      playResponse.text(),
      aggregateResponse.text(),
      highlightResponse.text(),
      coreBarResponse.text(),
    ])

    playRows.value = d3.csvParse(playText.replace(/^\uFEFF/, ''))
    aggregateRows.value = d3.csvParse(aggregateText.replace(/^\uFEFF/, ''))
    highlightRows.value = d3.csvParse(highlightText.replace(/^\uFEFF/, ''))
    coreBarRows.value = d3.csvParse(coreBarText.replace(/^\uFEFF/, ''))
  } catch (readError) {
    error.value = readError instanceof Error ? readError.message : '主题组合矩阵数据读取失败'
  } finally {
    loading.value = false
  }
}

function buildUpsetData() {
  const colorMap = new Map(THEME_ORDER.map((theme, index) => [theme, themePalette[index % themePalette.length]]))

  const themes = THEME_ORDER.map((name, index) => {
    const barRow = coreBarByTheme.value.get(name)
    return {
      name,
      index,
      count: toNumber(field(barRow, H.coreThemeCount), 0),
      occurrenceCount: toNumber(field(barRow, H.occurrenceCount), 0),
      comboTypeCount: toNumber(field(barRow, H.comboTypeCount), 0),
      color: colorMap.get(name) || themePalette[index % themePalette.length],
    }
  })

  const combos = aggregateRows.value
    .map((row, index) => {
      const comboId = field(row, H.comboId)
      const themesInCombo = comboThemesFromRow(row)
      const primaryCoreTheme = field(row, H.primaryCoreTheme) || themesInCombo[0] || ''
      const primaryRelation = field(row, H.primaryRelation)
      return {
        key: comboId || themesInCombo.join('|') || String(index),
        comboId,
        index,
        rowOrder: toNumber(field(row, H.matrixOrder), index + 1),
        themes: themesInCombo,
        count: toNumber(field(row, H.count), 0),
        color: colorMap.get(primaryCoreTheme) || colorMap.get(themesInCombo[0]) || themePalette[index % themePalette.length],
        primaryCoreTheme,
        primaryRelation,
        relationDistribution: parseDistribution(field(row, H.relationDistribution)),
        coreThemeDistribution: parseDistribution(field(row, H.coreThemeDistribution)),
        representativeTitles: splitList(field(row, H.representativeTitles)).slice(0, 8),
        playIds: splitList(field(row, H.playIdList)),
      }
    })
    .filter((combo) => combo.themes.length && combo.count > 0)
    .sort((a, b) => a.rowOrder - b.rowOrder || b.count - a.count || a.key.localeCompare(b.key, 'zh-CN'))
    .slice(0, TOP_COMBO_LIMIT)
    .map((combo, index) => ({ ...combo, index }))

  return { themes, combos, totalPlays: playRows.value.length }
}

function comboThemesFromRow(row) {
  const comboId = field(row, H.comboId)
  const highlighted = highlightThemesByCombo.value.get(comboId)
  if (highlighted?.length) return highlighted
  return uniqueByThemeOrder(splitList(field(row, H.themeCombo, H.themeComboDisplay)))
}

function playThemes(play) {
  const flags = THEME_ORDER.filter((theme) => toNumber(field(play, `主题_${theme}`), 0) > 0)
  if (flags.length) return flags
  return uniqueByThemeOrder(splitList(field(play, H.themeCombo, H.secondaryThemes)))
}

function renderUpset() {
  if (loading.value || error.value || !panelRef.value || !svgRef.value) return

  const width = Math.max(280, Math.round(panelRef.value.clientWidth || 0))
  const height = Math.max(260, Math.round(panelRef.value.clientHeight || 0))
  const svg = d3.select(svgRef.value)

  svg.selectAll('*').remove()
  hideTooltip()
  svg.attr('viewBox', `0 0 ${width} ${height}`).attr('preserveAspectRatio', 'none')

  const data = upsetData.value
  if (!data.themes.length || !data.combos.length) {
    drawEmptyState(svg, width, height)
    return
  }

  const margin = { top: 3, right: 8, bottom: 8, left: 8 }
  const matrixLeft = margin.left
  const matrixMaxRight = width - margin.right
  const matrixWidth = matrixMaxRight - matrixLeft
  const matrixRight = matrixLeft + matrixWidth
  const topHeight = Math.max(72, Math.min(96, height * 0.22))
  const matrixTop = topHeight + 3
  const matrixBottom = height - margin.bottom

  const xBand = d3
    .scaleBand()
    .domain(data.themes.map((theme) => theme.name))
    .range([matrixLeft, matrixRight])
    .paddingInner(data.themes.length > 7 ? 0.18 : 0.3)
    .paddingOuter(0.08)

  const themeX = (themeName) => {
    const value = xBand(themeName)
    return Number.isFinite(value) ? value + xBand.bandwidth() / 2 : Number.NaN
  }

  drawTopThemeBars(svg, data, {
    xBand,
    themeX,
    y: margin.top,
    height: topHeight - margin.top - 6,
    left: matrixLeft,
    right: matrixRight,
  })

  drawVerticalMatrix(svg, data, {
    themeX,
    xBand,
    y: matrixTop,
    bottom: matrixBottom,
    left: matrixLeft,
    right: matrixRight,
  })

  applyLoopHighlight(svg, data, true)
}

function drawTopThemeBars(svg, data, layout) {
  const chartTop = layout.y
  const chartBottom = layout.y + layout.height
  const maxCount = Math.max(1, d3.max(data.themes, (theme) => theme.count) || 1)
  const yScale = d3.scaleLinear().domain([0, maxCount]).nice().range([chartBottom - 3, chartTop + 9])

  const groups = svg
    .append('g')
    .attr('class', 'top-theme-bars')
    .selectAll('g')
    .data(data.themes)
    .join('g')
    .attr('class', 'theme-count-group')
    .on('pointerenter', (event, theme) => {
      highlightTheme(svg, theme.name)
      showTooltip(event, themeTooltip(theme))
    })
    .on('pointermove', moveTooltip)
    .on('pointerleave', () => {
      applyLoopHighlight(svg, data, true)
      hideTooltip()
    })

  groups
    .append('rect')
    .attr('class', 'theme-count-rect')
    .attr('x', (theme) => layout.xBand(theme.name) + layout.xBand.bandwidth() * 0.18)
    .attr('y', (theme) => yScale(theme.count))
    .attr('width', Math.max(6, layout.xBand.bandwidth() * 0.64))
    .attr('height', (theme) => chartBottom - yScale(theme.count))
    .attr('rx', 3)
    .attr('fill', (theme) => theme.color)
    .attr('opacity', (theme) => (theme.count ? 0.9 : 0.2))
}

function drawVerticalMatrix(svg, data, layout) {
  const labelTop = layout.y + 4
  const labelBottom = labelTop + 58
  const lineTop = labelBottom
  const lineBottom = layout.bottom - 2
  const rowScale = d3
    .scalePoint()
    .domain(data.combos.map((combo) => combo.key))
    .range([lineTop + 6, lineBottom - 6])
    .padding(0.28)

  const themeHeaders = svg
    .append('g')
    .attr('class', 'matrix-theme-headers')
    .selectAll('g')
    .data(data.themes)
    .join('g')
    .attr('class', 'theme-column')
    .attr('transform', (theme) => `translate(${layout.themeX(theme.name)},0)`)
    .on('pointerenter', (event, theme) => {
      highlightTheme(svg, theme.name)
      showTooltip(event, themeTooltip(theme))
    })
    .on('pointermove', moveTooltip)
    .on('pointerleave', () => {
      applyLoopHighlight(svg, data, true)
      hideTooltip()
    })

  themeHeaders.each(function appendVerticalLabel(theme) {
    drawVerticalLabel(d3.select(this), theme.name, 0, labelTop)
  })

  themeHeaders
    .append('line')
    .attr('class', 'theme-track')
    .attr('y1', lineTop)
    .attr('y2', lineBottom)
    .attr('stroke', 'rgba(92, 68, 48, 0.2)')

  const comboRows = svg
    .append('g')
    .attr('class', 'combo-rows')
    .selectAll('g')
    .data(data.combos)
    .join('g')
    .attr('class', 'combo-row')
    .attr('transform', (combo) => `translate(0,${rowScale(combo.key)})`)
    .on('pointerenter', (event, combo) => {
      highlightCombo(svg, combo.index)
      showTooltip(event, comboTooltip(combo))
    })
    .on('pointermove', moveTooltip)
    .on('pointerleave', () => {
      applyLoopHighlight(svg, data, true)
      hideTooltip()
    })

  comboRows.each(function drawComboConnector(combo) {
    const activeXs = combo.themes.map((theme) => layout.themeX(theme)).filter((value) => Number.isFinite(value))
    if (activeXs.length > 1) {
      d3.select(this)
        .append('line')
        .attr('class', 'combo-connector')
        .attr('x1', d3.min(activeXs))
        .attr('x2', d3.max(activeXs))
        .attr('stroke', combo.color)
    }
  })

  comboRows
    .selectAll('circle')
    .data((combo) =>
      data.themes.map((theme) => ({
        comboIndex: combo.index,
        comboKey: combo.key,
        comboId: combo.comboId,
        theme: theme.name,
        active: combo.themes.includes(theme.name),
        color: theme.color,
      })),
    )
    .join('circle')
    .attr('class', 'matrix-dot')
    .attr('cx', (cell) => layout.themeX(cell.theme))
    .attr('r', (cell) => (cell.active ? 5.7 : 2.5))
    .attr('fill', (cell) => (cell.active ? cell.color : 'rgba(88, 68, 51, 0.13)'))
    .attr('stroke', (cell) => (cell.active ? '#fff8e8' : 'transparent'))
    .attr('stroke-width', (cell) => (cell.active ? 0.8 : 0))

  comboRows
    .append('rect')
    .attr('class', 'combo-hover-zone')
    .attr('x', layout.left)
    .attr('y', -7)
    .attr('width', layout.right - layout.left)
    .attr('height', 14)
}

function applyLoopHighlight(svg, data, animate = true) {
  const state = buildHighlightState(data)
  const transition = svg.transition().duration(animate ? 760 : 0).ease(d3.easeCubicOut)

  svg
    .selectAll('.theme-count-group')
    .transition(transition)
    .attr('opacity', (theme) => themeOpacity(state.themeLevel(theme.name), 'bar'))

  svg
    .selectAll('.theme-column')
    .transition(transition)
    .attr('opacity', (theme) => themeOpacity(state.themeLevel(theme.name), 'column'))

  svg
    .selectAll('.combo-row')
    .transition(transition)
    .attr('opacity', (combo) => comboOpacity(state.comboLevel(combo)))

  svg
    .selectAll('.combo-connector')
    .transition(transition)
    .attr('opacity', function connectorOpacity() {
      return connectorOpacityByLevel(state.comboLevel(d3.select(this.parentNode).datum()))
    })

  svg
    .selectAll('.matrix-dot')
    .transition(transition)
    .attr('opacity', (cell) => cellOpacity(cell, state))
    .attr('r', (cell) => cellRadius(cell, state))
}

function buildHighlightState(data) {
  const scope = normalizeScope()
  if (scope.type === 'none') {
    return {
      type: 'none',
      themeLevel: () => 'normal',
      comboLevel: () => 'normal',
      selectedThemes: new Set(),
      relatedThemes: new Set(THEME_ORDER),
    }
  }

  const selectedThemes = new Set(scope.themes || [])
  const matchedPlays = playRows.value.filter((play) => playMatchesScope(play, scope))
  const relatedThemes = new Set()
  const activeComboIds = new Set()

  if (scope.type === 'relation') {
    relationThemeFocus(scope.relation, matchedPlays).forEach((theme) => relatedThemes.add(theme))
    matchedPlays.forEach((play) => {
      const themes = playThemes(play)
      const comboId = field(play, H.comboId)
      if (comboId && themes.some((theme) => relatedThemes.has(theme))) activeComboIds.add(comboId)
    })
  } else {
    matchedPlays.forEach((play) => {
      playThemes(play).forEach((theme) => relatedThemes.add(theme))
      const comboId = field(play, H.comboId)
      if (comboId) activeComboIds.add(comboId)
    })
  }

  if (scope.type === 'relation' && !activeComboIds.size) {
    data.combos.forEach((combo) => {
      if (combo.relationDistribution.has(scope.relation) && combo.themes.some((theme) => relatedThemes.has(theme))) {
        if (combo.comboId) activeComboIds.add(combo.comboId)
      }
    })
  }

  if (scope.type !== 'relation') {
    selectedThemes.forEach((theme) => relatedThemes.add(theme))
  }

  const themeLevel = (theme) => {
    if (scope.type === 'relation') return relatedThemes.has(theme) ? 'primary' : 'dim'
    if (selectedThemes.has(theme)) return 'primary'
    if (relatedThemes.has(theme)) return 'secondary'
    return 'dim'
  }

  const comboLevel = (combo) => {
    if (activeComboIds.has(combo.comboId)) return 'primary'
    if (
      scope.type === 'relation' &&
      combo.relationDistribution.has(scope.relation) &&
      combo.themes.some((theme) => relatedThemes.has(theme))
    ) {
      return 'primary'
    }
    if (scope.type !== 'relation' && combo.themes.some((theme) => selectedThemes.has(theme))) return 'primary'
    if (combo.themes.some((theme) => relatedThemes.has(theme))) return 'secondary'
    return 'dim'
  }

  return { type: scope.type, themeLevel, comboLevel, selectedThemes, relatedThemes }
}

function relationThemeFocus(relation, matchedPlays) {
  const mappedThemes = RELATION_THEME_MAP[relation]?.filter((theme) => THEME_ORDER.includes(theme))
  if (mappedThemes?.length) return mappedThemes

  const counts = new Map()
  matchedPlays.forEach((play) => {
    const theme = field(play, H.coreTheme)
    if (THEME_ORDER.includes(theme)) counts.set(theme, (counts.get(theme) || 0) + 1)
  })

  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1] || THEME_ORDER.indexOf(a[0]) - THEME_ORDER.indexOf(b[0]))
    .slice(0, 4)
    .map(([theme]) => theme)
}

function normalizeScope() {
  const scope = loopFilterState.scope
  const flow = loopFilterState.flow
  if (!scope) return { type: 'none' }

  if (scope.type === 'relation') {
    return { type: 'relation', relation: scope.relationType }
  }

  if (scope.type === 'theme') {
    return {
      type: 'theme',
      relation: scope.relationType,
      themes: extractThemes(scope.themeCombo),
    }
  }

  if (scope.type === 'flow' && flow) {
    return {
      type: 'theme',
      relation: flow.relationType,
      themes: extractThemes(flow.themeCombo),
    }
  }

  return { type: 'none' }
}

function playMatchesScope(play, scope) {
  const relation = field(play, H.coreRelation)
  const themes = playThemes(play)

  if (scope.type === 'relation') return relation === scope.relation
  if (scope.type === 'theme') {
    return relation === scope.relation && themes.some((theme) => scope.themes.includes(theme))
  }

  return true
}

function themeOpacity(level, part) {
  if (level === 'normal') return 1
  if (level === 'primary') return 1
  if (level === 'secondary') return part === 'bar' ? 0.5 : 0.48
  return part === 'bar' ? 0.12 : 0.16
}

function comboOpacity(level) {
  if (level === 'normal') return 1
  if (level === 'primary') return 0.96
  if (level === 'secondary') return 0.38
  return 0.12
}

function connectorOpacityByLevel(level) {
  if (level === 'normal') return 0.72
  if (level === 'primary') return 0.82
  if (level === 'secondary') return 0.28
  return 0.06
}

function cellOpacity(cell, state) {
  if (state.type === 'none') return 1
  if (!cell.active) return 0.04

  const themeLevel = state.themeLevel(cell.theme)
  const combo = upsetData.value.combos.find((item) => item.key === cell.comboKey)
  const comboLevel = combo ? state.comboLevel(combo) : 'dim'

  if (comboLevel === 'dim') return 0.08
  if (themeLevel === 'primary') return 1
  if (themeLevel === 'secondary') return 0.48
  return 0.12
}

function cellRadius(cell, state) {
  if (!cell.active) return state.type === 'none' ? 2.5 : 2.1
  const opacity = cellOpacity(cell, state)
  if (opacity >= 0.95) return 6.8
  if (opacity >= 0.45) return 5.3
  return 4.1
}

function drawVerticalLabel(group, labelText, x, y) {
  const label = group.append('text').attr('class', 'vertical-theme-label').attr('x', x).attr('y', y).attr('text-anchor', 'middle')

  Array.from(labelText).forEach((char, index) => {
    label.append('tspan').attr('x', x).attr('dy', index === 0 ? 0 : 15).text(char)
  })
}

function drawEmptyState(svg, width, height) {
  svg
    .append('text')
    .attr('class', 'empty-state')
    .attr('x', width / 2)
    .attr('y', height / 2)
    .attr('text-anchor', 'middle')
    .text('暂无可统计的主题组合')
}

function highlightCombo(svg, comboIndex) {
  svg.selectAll('.combo-row').attr('opacity', (combo) => (combo.index === comboIndex ? 1 : 0.22))
  svg
    .selectAll('.matrix-dot')
    .attr('opacity', (cell) => (cell.comboIndex === comboIndex ? 1 : cell.active ? 0.18 : 0.06))
    .attr('r', (cell) => {
      if (cell.comboIndex !== comboIndex) return cell.active ? 5.1 : 2.3
      return cell.active ? 7 : 3
    })
  svg.selectAll('.combo-connector').attr('opacity', function connectorOpacity() {
    return d3.select(this.parentNode).datum().index === comboIndex ? 0.82 : 0.12
  })
}

function highlightTheme(svg, themeName) {
  svg.selectAll('.theme-count-group').attr('opacity', (theme) => (theme.name === themeName ? 1 : 0.28))
  svg.selectAll('.theme-column').attr('opacity', (theme) => (theme.name === themeName ? 1 : 0.32))
  svg
    .selectAll('.matrix-dot')
    .attr('opacity', (cell) => {
      if (cell.theme === themeName && cell.active) return 1
      return cell.active ? 0.18 : 0.06
    })
    .attr('r', (cell) => (cell.theme === themeName && cell.active ? 7 : cell.active ? 5.1 : 2.3))
  svg.selectAll('.combo-row').attr('opacity', (combo) => (combo.themes.includes(themeName) ? 1 : 0.24))
}

function comboTooltip(combo) {
  const themes = combo.themes.map(escapeHtml).join('、')
  const representatives = (combo.representativeTitles.length ? combo.representativeTitles : combo.playIds).slice(0, 6).map(escapeHtml).join('；')
  return `
    <strong>主题组合</strong>
    <span>${themes}</span>
    <em>${combo.count} 个剧本</em>
    <span>主要核心主题：${escapeHtml(combo.primaryCoreTheme || '未定')}</span>
    <span>主要核心关系：${escapeHtml(combo.primaryRelation || '未定')}</span>
    <span>${representatives}</span>
  `
}

function themeTooltip(theme) {
  return `
    <strong>${escapeHtml(theme.name)}</strong>
    <span>核心主题剧本：${theme.count} 个</span>
    <span>参与组合剧本：${theme.occurrenceCount} 个</span>
    <span>参与组合种类：${theme.comboTypeCount} 种</span>
  `
}

function showTooltip(event, html) {
  if (!tooltipRef.value) return
  tooltipRef.value.innerHTML = html
  tooltipRef.value.style.display = 'grid'
  moveTooltip(event)
}

function moveTooltip(event) {
  if (!tooltipRef.value || !panelRef.value) return
  const panelRect = panelRef.value.getBoundingClientRect()
  const tooltipRect = tooltipRef.value.getBoundingClientRect()
  const x = event.clientX - panelRect.left + 12
  const y = event.clientY - panelRect.top + 12
  tooltipRef.value.style.left = `${Math.min(x, panelRect.width - tooltipRect.width - 8)}px`
  tooltipRef.value.style.top = `${Math.min(y, panelRect.height - tooltipRect.height - 8)}px`
}

function hideTooltip() {
  if (!tooltipRef.value) return
  tooltipRef.value.style.display = 'none'
}

function returnToFullThemeCombos() {
  clearLoopFilter()
  hideTooltip()
}

function extractThemes(value) {
  const themes = uniqueByThemeOrder(splitList(value))
  return themes.length ? themes : THEME_ORDER.filter((theme) => text(value).includes(theme))
}

function splitList(value) {
  return text(value)
    .split(/[|+;；、，,]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function uniqueByThemeOrder(values) {
  const selected = new Set(values.filter((theme) => THEME_ORDER.includes(theme)))
  return THEME_ORDER.filter((theme) => selected.has(theme))
}

function parseDistribution(value) {
  const map = new Map()
  splitList(value).forEach((item) => {
    const [name, count] = item.split(':').map((part) => part.trim())
    if (name) map.set(name, toNumber(count, 0))
  })
  return map
}

function field(row, ...names) {
  if (!row) return ''
  for (const name of names) {
    const value = text(row[name])
    if (value) return value
  }
  return ''
}

function toNumber(value, fallback = 0) {
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

function text(value) {
  return String(value ?? '').trim()
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}
</script>

<style scoped>
.vertical-upset-panel {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  color: #39251c;
  background: #FBF6E9;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
}

.vertical-upset-panel::before {
  position: absolute;
  inset: 10px 12px auto auto;
  width: 72px;
  height: 32px;
  border-top: 1px solid rgba(143, 47, 36, 0.08);
  border-right: 1px solid rgba(143, 47, 36, 0.08);
  border-radius: 0 10px 0 0;
  content: "";
  pointer-events: none;
}

.vertical-upset-svg {
  position: relative;
  z-index: 1;
  display: block;
  width: 100%;
  height: 100%;
  background: #FBF6E9;
}

.vertical-upset-svg :deep(.theme-count-rect) {
  filter: drop-shadow(0 1px 2px rgba(70, 40, 22, 0.12));
}

.vertical-upset-svg :deep(.theme-count-group),
.vertical-upset-svg :deep(.theme-column),
.vertical-upset-svg :deep(.combo-row) {
  cursor: pointer;
}

.vertical-upset-svg :deep(.vertical-theme-label) {
  fill: #332820;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 15px;
  font-weight: 900;
}

.vertical-upset-svg :deep(.theme-track) {
  stroke-width: 3.2;
  stroke-linecap: round;
  opacity: 1;
}

.vertical-upset-svg :deep(.combo-connector) {
  stroke-width: 4.2;
  stroke-linecap: round;
  opacity: 0.72;
}

.vertical-upset-svg :deep(.combo-hover-zone) {
  fill: transparent;
  pointer-events: all;
}

.vertical-upset-svg :deep(.empty-state) {
  fill: #6b4628;
  font-size: 13px;
  font-weight: 900;
}

.upset-return-btn {
  position: absolute;
  right: 12px;
  top: 4px;
  z-index: 4;
  min-width: 82px;
  height: 27px;
  padding: 0 12px;
  border: 1px solid rgba(143, 47, 36, 0.36);
  border-radius: 999px;
  color: #fff8ed;
  background: linear-gradient(135deg, #8f2f24, #3d1d17);
  box-shadow: 0 10px 22px rgba(82, 31, 18, 0.2);
  cursor: pointer;
  font-family: "STKaiti", "KaiTi", "Microsoft YaHei", sans-serif;
  font-size: 13px;
  font-weight: 900;
  line-height: 25px;
}

.upset-return-btn:hover {
  filter: brightness(1.08) saturate(1.18);
}

.upset-tooltip {
  position: absolute;
  z-index: 5;
  display: none;
  max-width: 190px;
  gap: 3px;
  padding: 7px 9px;
  border: 1px solid rgba(88, 68, 51, 0.16);
  border-radius: 7px;
  color: #39251c;
  font-size: 11px;
  line-height: 1.35;
  pointer-events: none;
  background: rgba(255, 253, 247, 0.96);
  box-shadow: 0 8px 18px rgba(70, 40, 22, 0.14);
}

.upset-tooltip :deep(strong) {
  color: #5b1e17;
  font-size: 12px;
}

.upset-tooltip :deep(span),
.upset-tooltip :deep(em) {
  display: block;
  font-style: normal;
}

.upset-tooltip :deep(em) {
  color: #7a241d;
  font-weight: 900;
}

.upset-state {
  display: grid;
  height: 100%;
  min-height: 0;
  place-items: center;
  color: #6b4628;
  font-size: 15px;
  font-weight: 900;
}

.upset-state--error {
  color: #8f2f24;
}
</style>
