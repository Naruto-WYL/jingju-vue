<template>
  <section ref="panelRef" class="vertical-upset-panel" aria-label="纵向版主题组合 UpSet 图">
    <div v-if="loading" class="upset-state">主题组合加载中...</div>
    <div v-else-if="error" class="upset-state upset-state--error">{{ error }}</div>
    <svg v-else ref="svgRef" class="vertical-upset-svg" role="img" aria-label="跨剧本主题组合纵向 UpSet 图" />

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

const PLAY_URL = '/data/theme_combo_play_level.csv'
const AGGREGATE_URL = '/data/theme_combo_aggregate.csv'
const HIGHLIGHT_URL = '/data/theme_combo_highlights.csv'

const H = {
  playId: '剧本ID',
  title: '剧目名称',
  relationSet: '角色关系集合',
  coreTheme: '核心主题',
  secondaryThemes: '次要主题集合',
  themeCombo: '主题组合',
  themeComboDisplay: '主题组合显示',
  comboId: '组合ID',
  closedLoopIds: '闭环ID集合',
  narrativeSet: '叙事结构线集合',
  waveSet: '波动型集合',
  outcomeSet: '关系演化结局集合',
  count: '剧本数量',
  primaryCoreTheme: '主要核心主题',
  relationCoverage: '角色关系覆盖',
  representativeTitles: '代表剧目列表',
  theme: '主题',
  comboOrder: '组合内顺序',
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
const loading = ref(false)
const error = ref('')
let resizeObserver = null

const activeFilterLabel = computed(() => {
  const scope = loopFilterState.scope
  const flow = loopFilterState.flow
  if (!scope) return ''
  if (scope.type === 'relation') return scope.relationType
  if (scope.type === 'theme') return `${scope.relationType} / ${scope.themeCombo}`
  if (scope.type === 'flow' && flow) return `${flow.relationType} / ${flow.themeCombo} / ${flow.narrativeType}`
  return ''
})

const highlightThemesByCombo = computed(() => {
  const map = new Map()
  highlightRows.value.forEach((row) => {
    const comboId = text(row[H.comboId])
    const theme = text(row[H.theme])
    if (!comboId || !THEME_ORDER.includes(theme)) return
    if (!map.has(comboId)) map.set(comboId, [])
    map.get(comboId).push({
      theme,
      order: Number(row[H.comboOrder]) || 999,
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

const aggregateByComboId = computed(() => {
  const map = new Map()
  aggregateRows.value.forEach((row) => {
    const comboId = text(row[H.comboId])
    if (comboId) map.set(comboId, row)
  })
  return map
})

const filteredPlays = computed(() => playRows.value.filter((row) => playMatchesLoopFilter(row)))
const upsetData = computed(() => buildUpsetData(filteredPlays.value))

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
    const [playResponse, aggregateResponse, highlightResponse] = await Promise.all([
      fetch(`${PLAY_URL}?t=${Date.now()}`, { cache: 'no-store' }),
      fetch(`${AGGREGATE_URL}?t=${Date.now()}`, { cache: 'no-store' }),
      fetch(`${HIGHLIGHT_URL}?t=${Date.now()}`, { cache: 'no-store' }),
    ])
    if (!playResponse.ok) throw new Error(`剧本主题组合读取失败：${playResponse.status}`)
    if (!aggregateResponse.ok) throw new Error(`主题组合统计读取失败：${aggregateResponse.status}`)
    if (!highlightResponse.ok) throw new Error(`主题亮点长表读取失败：${highlightResponse.status}`)

    const [playText, aggregateText, highlightText] = await Promise.all([
      playResponse.text(),
      aggregateResponse.text(),
      highlightResponse.text(),
    ])
    playRows.value = d3.csvParse(playText.replace(/^\uFEFF/, ''))
    aggregateRows.value = d3.csvParse(aggregateText.replace(/^\uFEFF/, ''))
    highlightRows.value = d3.csvParse(highlightText.replace(/^\uFEFF/, ''))
  } catch (readError) {
    error.value = readError instanceof Error ? readError.message : '主题组合数据读取失败'
  } finally {
    loading.value = false
  }
}

function buildUpsetData(sourcePlays) {
  const activeThemes = activeThemeDomain(sourcePlays)
  const coreCounts = new Map(activeThemes.map((theme) => [theme, 0]))
  const occurrenceCounts = new Map(activeThemes.map((theme) => [theme, 0]))
  const comboMap = new Map()

  sourcePlays.forEach((play) => {
    const themes = comboThemes(play).filter((theme) => activeThemes.includes(theme))
    if (!themes.length) return

    const coreTheme = text(play[H.coreTheme])
    if (coreCounts.has(coreTheme)) coreCounts.set(coreTheme, (coreCounts.get(coreTheme) || 0) + 1)
    themes.forEach((theme) => occurrenceCounts.set(theme, (occurrenceCounts.get(theme) || 0) + 1))

    const comboId = text(play[H.comboId]) || themes.join('|')
    const key = comboId || themes.join('|')
    if (!comboMap.has(key)) {
      comboMap.set(key, {
        key,
        comboId,
        themes,
        count: 0,
        coreDistribution: new Map(),
        playTitles: [],
      })
    }

    const combo = comboMap.get(key)
    combo.count += 1
    combo.themes = uniqueByThemeOrder([...combo.themes, ...themes]).filter((theme) => activeThemes.includes(theme))
    combo.playTitles.push(text(play[H.title]) || text(play[H.playId]) || '未知剧本')
    if (coreTheme) combo.coreDistribution.set(coreTheme, (combo.coreDistribution.get(coreTheme) || 0) + 1)
  })

  const colorMap = new Map(activeThemes.map((theme, index) => [theme, themePalette[THEME_ORDER.indexOf(theme) % themePalette.length] || themePalette[index % themePalette.length]]))

  const themes = activeThemes.map((name, index) => ({
    name,
    index,
    count: coreCounts.get(name) || 0,
    occurrenceCount: occurrenceCounts.get(name) || 0,
    color: colorMap.get(name) || themePalette[index % themePalette.length],
  }))

  const combos = Array.from(comboMap.values())
    .map((combo, index) => {
      const aggregate = aggregateByComboId.value.get(combo.comboId)
      const themesInDomain = combo.themes.filter((theme) => activeThemes.includes(theme))
      const primaryCoreTheme = text(aggregate?.[H.primaryCoreTheme]) || topEntry(combo.coreDistribution) || themesInDomain[0] || ''

      return {
        ...combo,
        key: combo.key || themesInDomain.join('|'),
        index,
        themes: themesInDomain,
        color: colorMap.get(primaryCoreTheme) || colorMap.get(themesInDomain[0]) || themePalette[index % themePalette.length],
        primaryCoreTheme,
        relationCoverage: text(aggregate?.[H.relationCoverage]),
        representativeTitles: splitList(text(aggregate?.[H.representativeTitles])),
      }
    })
    .filter((combo) => combo.themes.length)
    .sort((a, b) => b.count - a.count || a.key.localeCompare(b.key, 'zh-CN'))
    .slice(0, TOP_COMBO_LIMIT)
    .map((combo, index) => ({ ...combo, index }))

  return { themes, combos, totalPlays: sourcePlays.length }
}

function activeThemeDomain(sourcePlays) {
  if (!loopFilterState.scope) return THEME_ORDER.slice()

  const selected = new Set()
  sourcePlays.forEach((play) => {
    comboThemes(play).forEach((theme) => selected.add(theme))
  })

  return THEME_ORDER.filter((theme) => selected.has(theme))
}

function comboThemes(play) {
  const comboId = text(play[H.comboId])
  const highlightThemes = highlightThemesByCombo.value.get(comboId)
  if (highlightThemes?.length) return highlightThemes
  return uniqueByThemeOrder(splitList(play[H.themeCombo]))
}

function playMatchesLoopFilter(play) {
  const scope = loopFilterState.scope
  if (!scope) return true

  const relations = splitList(play[H.relationSet])
  const themes = comboThemes(play)
  const closedLoopIds = splitList(play[H.closedLoopIds])
  const narratives = splitList(play[H.narrativeSet])
  const waves = splitList(play[H.waveSet])
  const outcomes = splitList(play[H.outcomeSet])
  const flow = loopFilterState.flow

  if (scope.type === 'relation') return relations.includes(scope.relationType)
  if (scope.type === 'theme') {
    return relations.includes(scope.relationType) && themes.includes(scope.themeCombo)
  }

  if (scope.type === 'flow' && flow) {
    if (flow.id && closedLoopIds.includes(flow.id)) return true
    return (
      relations.includes(flow.relationType) &&
      themes.includes(flow.themeCombo) &&
      narratives.includes(flow.narrativeType) &&
      (!flow.waveType || waves.includes(flow.waveType)) &&
      outcomes.includes(flow.evolutionType)
    )
  }

  return true
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
  const rightBarsWidth = Math.max(34, Math.min(46, width * 0.14))
  const rightBarsGap = 6
  const matrixLeft = margin.left
  const matrixMaxRight = width - margin.right - rightBarsWidth - rightBarsGap
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
    rightBarsX: matrixRight + rightBarsGap,
    rightBarsWidth,
  })

  if (activeFilterLabel.value) {
    svg
      .append('text')
      .attr('class', 'filter-label')
      .attr('x', matrixLeft)
      .attr('y', 15)
      .text(`中上联动：${activeFilterLabel.value}`)
  }
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
      clearHighlight(svg)
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
  const countBadgeWidth = layout.rightBarsWidth
  const countBadgeHeight = 20

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
      clearHighlight(svg)
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

  svg
    .append('line')
    .attr('class', 'right-count-divider')
    .attr('x1', layout.rightBarsX - 7)
    .attr('x2', layout.rightBarsX - 7)
    .attr('y1', lineTop)
    .attr('y2', lineBottom)

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
      clearHighlight(svg)
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
    .attr('class', 'combo-count-badge')
    .attr('x', layout.rightBarsX)
    .attr('y', -countBadgeHeight / 2)
    .attr('width', countBadgeWidth)
    .attr('height', countBadgeHeight)
    .attr('rx', 5)
    .attr('fill', (combo) => colorWithOpacity(combo.color, 0.14))
    .attr('stroke', (combo) => colorWithOpacity(combo.color, 0.42))

  comboRows
    .append('text')
    .attr('class', 'combo-count-label')
    .attr('x', layout.rightBarsX + countBadgeWidth / 2)
    .attr('dy', '0.32em')
    .attr('text-anchor', 'middle')
    .attr('fill', (combo) => combo.color)
    .text((combo) => combo.count)

  comboRows
    .append('rect')
    .attr('class', 'combo-hover-zone')
    .attr('x', layout.left)
    .attr('y', -7)
    .attr('width', layout.rightBarsX + layout.rightBarsWidth - layout.left)
    .attr('height', 14)
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
  svg.selectAll('.matrix-dot')
    .attr('opacity', (cell) => (cell.comboIndex === comboIndex ? 1 : cell.active ? 0.18 : 0.06))
    .attr('r', (cell) => {
      if (cell.comboIndex !== comboIndex) return cell.active ? 5.1 : 2.3
      return cell.active ? 7 : 3
    })
  svg.selectAll('.combo-count-badge, .combo-count-label').attr('opacity', (combo) => (combo.index === comboIndex ? 1 : 0.18))
  svg.selectAll('.combo-connector').attr('opacity', function connectorOpacity() {
    return d3.select(this.parentNode).datum().index === comboIndex ? 0.82 : 0.12
  })
}

function highlightTheme(svg, themeName) {
  svg.selectAll('.theme-count-group').attr('opacity', (theme) => (theme.name === themeName ? 1 : 0.28))
  svg.selectAll('.theme-column').attr('opacity', (theme) => (theme.name === themeName ? 1 : 0.32))
  svg.selectAll('.matrix-dot')
    .attr('opacity', (cell) => {
      if (cell.theme === themeName && cell.active) return 1
      return cell.active ? 0.18 : 0.06
    })
    .attr('r', (cell) => (cell.theme === themeName && cell.active ? 7 : cell.active ? 5.1 : 2.3))
  svg.selectAll('.combo-row').attr('opacity', (combo) => (combo.themes.includes(themeName) ? 1 : 0.24))
  svg.selectAll('.combo-count-badge, .combo-count-label').attr('opacity', (combo) => (combo.themes.includes(themeName) ? 0.95 : 0.18))
}

function clearHighlight(svg) {
  svg.selectAll('.theme-count-group').attr('opacity', 1)
  svg.selectAll('.theme-column').attr('opacity', 1)
  svg.selectAll('.combo-row').attr('opacity', 1)
  svg.selectAll('.combo-count-badge, .combo-count-label').attr('opacity', 1)
  svg.selectAll('.combo-connector').attr('opacity', 0.7)
  svg.selectAll('.matrix-dot').attr('opacity', 1).attr('r', (cell) => (cell.active ? 5.7 : 2.5))
}

function comboTooltip(combo) {
  const themes = combo.themes.map(escapeHtml).join('、')
  const representatives = (combo.representativeTitles.length ? combo.representativeTitles : combo.playTitles).slice(0, 6).map(escapeHtml).join('；')
  return `
    <strong>主题组合</strong>
    <span>${themes}</span>
    <em>${combo.count} 个剧本</em>
    <span>主要核心：${escapeHtml(combo.primaryCoreTheme || '未定')}</span>
    <span>${representatives}</span>
  `
}

function themeTooltip(theme) {
  return `
    <strong>${escapeHtml(theme.name)}</strong>
    <span>核心主题剧本：${theme.count} 个</span>
    <span>参与组合剧本：${theme.occurrenceCount} 个</span>
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

function splitList(value) {
  return text(value)
    .split(/[|｜;；、,，+＋]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function uniqueByThemeOrder(values) {
  const selected = new Set(values.filter((theme) => THEME_ORDER.includes(theme)))
  return THEME_ORDER.filter((theme) => selected.has(theme))
}

function topEntry(map) {
  return Array.from(map.entries()).sort((a, b) => b[1] - a[1])[0]?.[0] || ''
}

function text(value) {
  return String(value ?? '').trim()
}

function colorWithOpacity(color, opacity) {
  const parsedColor = d3.color(color)
  if (!parsedColor) return color
  parsedColor.opacity = opacity
  return parsedColor.formatRgb()
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
}

.vertical-upset-svg :deep(.filter-label) {
  fill: #8f2f24;
  font-size: 13px;
  font-weight: 900;
  paint-order: stroke;
  stroke: rgba(255, 253, 246, 0.82);
  stroke-width: 3px;
}

.vertical-upset-svg :deep(.combo-count-label) {
  font-size: 16px;
  font-weight: 1200;
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

.vertical-upset-svg :deep(.right-count-divider) {
  stroke: rgba(92, 68, 48, 0.16);
  stroke-width: 1;
}

.vertical-upset-svg :deep(.combo-count-badge) {
  stroke-width: 1;
  filter: drop-shadow(0 1px 1px rgba(70, 40, 22, 0.08));
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
  right: 14px;
  bottom: 12px;
  z-index: 4;
  min-width: 82px;
  height: 27px;
  padding: 0 12px;
  border: 1px solid rgba(143, 47, 36, 0.36);
  border-radius: 999px;
  color: #7a241d;
  background: #FBF6E9;
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
  background: #FBF6E9;
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
