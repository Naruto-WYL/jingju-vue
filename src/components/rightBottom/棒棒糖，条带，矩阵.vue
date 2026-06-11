<template>
  <section ref="panelRef" class="vertical-upset-panel" aria-label="纵向版主题组合 UpSet 图">
    <div v-if="loading" class="upset-state">主题组合加载中...</div>
    <div v-else-if="error" class="upset-state upset-state--error">{{ error }}</div>
    <svg v-else ref="svgRef" class="vertical-upset-svg" role="img" aria-label="跨剧本主题组合纵向 UpSet 图" />
    <div ref="tooltipRef" class="upset-tooltip" />
  </section>
</template>

<script setup>
import * as d3 from 'd3'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { groupRowsByPlay, useThemeCsv } from './themeCsv'

const { rows, loading, error } = useThemeCsv()

const panelRef = ref(null)
const svgRef = ref(null)
const tooltipRef = ref(null)

const MIN_THEME_SHARE = 0.16
const TOP_COMBO_LIMIT = 18
const KAI_FONT = '"STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif'

const THEME_ORDER = [
  '家庭伦理',
  '隐恋情感',
  '身份变换',
  '公案审判',
  '复仇伸冤',
  '忠义家国',
  '战争冲突',
  '权力斗争',
]

const themeAlias = new Map([
  ['1', '家庭伦理'],
  ['2', '隐恋情感'],
  ['3', '身份变换'],
  ['4', '公案审判'],
  ['5', '复仇伸冤'],
  ['家庭伦理', '家庭伦理'],
  ['婚恋情感', '隐恋情感'],
  ['隐恋情感', '隐恋情感'],
  ['爱情牺牲', '隐恋情感'],
  ['才子佳人', '隐恋情感'],
  ['触景伤情', '隐恋情感'],
  ['身份变换', '身份变换'],
  ['真假识别', '身份变换'],
  ['恃才傲物', '身份变换'],
  ['公案审判', '公案审判'],
  ['审判', '公案审判'],
  ['复仇伸冤', '复仇伸冤'],
  ['复仇', '复仇伸冤'],
  ['女性冤情', '复仇伸冤'],
  ['忠义家国', '忠义家国'],
  ['忠君爱国', '忠义家国'],
  ['忠直殉志', '忠义家国'],
  ['忠贞守节', '忠义家国'],
  ['战争冲突', '战争冲突'],
  ['战争策略', '战争冲突'],
  ['权力斗争', '权力斗争'],
  ['权谋斗争', '权力斗争'],
  ['谋略联盟', '权力斗争'],
])

const themePalette = [
  '#b64a3a',
  '#d9853f',
  '#567f9b',
  '#4f9689',
  '#7f73a8',
  '#9a7350',
  '#7f9667',
  '#ad697d',
]

let resizeObserver = null

const plays = computed(() =>
  groupRowsByPlay(rows.value).filter((play) => play.playId && play.themes.length),
)

const upsetData = computed(() => buildUpsetData(plays.value))

watch(
  [upsetData, loading, error],
  async () => {
    await nextTick()
    renderUpset()
  },
  { deep: true, flush: 'post' },
)

onMounted(async () => {
  resizeObserver = new ResizeObserver(() => renderUpset())
  if (panelRef.value) resizeObserver.observe(panelRef.value)

  await nextTick()
  renderUpset()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
})

function buildUpsetData(sourcePlays) {
  const themeCounts = new Map(THEME_ORDER.map((theme) => [theme, 0]))
  const comboCounts = new Map()
  const comboPlayTitles = new Map()

  sourcePlays.forEach((play) => {
    const selectedThemes = combinationThemes(play)
    if (!selectedThemes.length) return

    selectedThemes.forEach((theme) => {
      themeCounts.set(theme, (themeCounts.get(theme) || 0) + 1)
    })

    const key = selectedThemes.join('|')
    comboCounts.set(key, (comboCounts.get(key) || 0) + 1)

    if (!comboPlayTitles.has(key)) comboPlayTitles.set(key, [])
    comboPlayTitles.get(key).push(play.title || play.playId || '未知剧本')
  })

  const themes = THEME_ORDER.map((name, index) => ({
    name,
    index,
    count: themeCounts.get(name) || 0,
    color: themePalette[index % themePalette.length],
  }))

  const colorMap = new Map(themes.map((theme) => [theme.name, theme.color]))
  const combos = Array.from(comboCounts.entries())
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'zh-Hans-CN'))
    .slice(0, TOP_COMBO_LIMIT)
    .map(([key, count], index) => {
      const comboThemes = key.split('|')
      return {
        key,
        count,
        index,
        themes: comboThemes,
        color: colorMap.get(comboThemes[0]) || themePalette[index % themePalette.length],
        playTitles: comboPlayTitles.get(key) || [],
      }
    })

  return { themes, combos }
}

function combinationThemes(play) {
  const picked = play.themes
    .filter((theme) => Number(theme.share || 0) >= MIN_THEME_SHARE)
    .map((theme) => normalizeThemeName(theme.name))
    .filter(Boolean)

  const fallback = play.themes
    .slice(0, 3)
    .map((theme) => normalizeThemeName(theme.name))
    .filter(Boolean)

  return uniqueOrderedThemes(picked.length ? picked : fallback)
}

function normalizeThemeName(name) {
  const value = String(name || '').trim()
  const normalized = themeAlias.get(value)
  return THEME_ORDER.includes(normalized) ? normalized : ''
}

function uniqueOrderedThemes(names) {
  const selected = new Set(names)
  return THEME_ORDER.filter((theme) => selected.has(theme))
}

function renderUpset() {
  if (loading.value || error.value || !panelRef.value || !svgRef.value) return

  const width = Math.max(280, Math.round(panelRef.value.clientWidth || 0))
  const height = Math.max(260, Math.round(panelRef.value.clientHeight || 0))
  const svg = d3.select(svgRef.value)

  svg.selectAll('*').remove()
  hideTooltip()

  svg
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'none')

  const data = upsetData.value
  if (!data.combos.length) {
    drawEmptyState(svg, width, height)
    return
  }

  const margin = {
    top: 3,
    right: 8,
    bottom: 8,
    left: 8,
  }

  const rightBarsWidth = Math.max(126, Math.min(158, width * 0.46))
  const rightBarsGap = 8
  const matrixLeft = margin.left
  const matrixMaxRight = width - margin.right - rightBarsWidth - rightBarsGap
  const matrixWidth = Math.min(matrixMaxRight - matrixLeft, Math.max(150, width * 0.5))
  const matrixRight = matrixLeft + matrixWidth
  const topHeight = Math.max(72, Math.min(96, height * 0.22))
  const matrixTop = topHeight + 3
  const matrixBottom = height - margin.bottom

  const xBand = d3
    .scaleBand()
    .domain(data.themes.map((theme) => theme.name))
    .range([matrixLeft, matrixRight])
    .paddingInner(0.24)
    .paddingOuter(0.1)

  const themeX = (themeName) => xBand(themeName) + xBand.bandwidth() / 2

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
    .append('line')
    .attr('class', 'theme-count-stem')
    .attr('x1', (theme) => layout.themeX(theme.name))
    .attr('x2', (theme) => layout.themeX(theme.name))
    .attr('y1', chartBottom)
    .attr('y2', (theme) => yScale(theme.count))
    .attr('stroke', (theme) => theme.color)
    .attr('stroke-opacity', (theme) => (theme.count ? 0.58 : 0.2))

  groups
    .append('circle')
    .attr('class', 'theme-count-dot')
    .attr('cx', (theme) => layout.themeX(theme.name))
    .attr('cy', (theme) => yScale(theme.count))
    .attr('r', (theme) => (theme.count ? 6.2 + Math.sqrt(theme.count / maxCount) * 2.8 : 4.2))
    .attr('fill', (theme) => theme.color)
    .attr('stroke', '#fff8e8')
    .attr('stroke-width', 1.4)
}

function drawVerticalMatrix(svg, data, layout) {
  const labelTop = layout.y + 4
  const labelBottom = labelTop + 58
  const lineTop = labelBottom + 4
  const lineBottom = layout.bottom - 2
  const rowScale = d3
    .scalePoint()
    .domain(data.combos.map((combo) => combo.key))
    .range([lineTop + 6, lineBottom - 6])
    .padding(0.28)

  const comboMax = Math.max(1, d3.max(data.combos, (combo) => combo.count) || 1)
  const rightSquareSize = 8
  const rightSquareGap = 2
  const rightSegmentCount = Math.max(
    6,
    Math.floor((layout.rightBarsWidth - 14) / (rightSquareSize + rightSquareGap)),
  )
  const rightFillScale = d3.scaleLinear().domain([0, comboMax]).range([0, rightSegmentCount])

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
    const activeXs = combo.themes
      .map((theme) => layout.themeX(theme))
      .filter((value) => Number.isFinite(value))

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
    .selectAll('.combo-count-cell')
    .data((combo) => {
      const filledCount = Math.max(1, Math.round(rightFillScale(combo.count)))
      return d3.range(rightSegmentCount).map((segmentIndex) => ({
        comboIndex: combo.index,
        themes: combo.themes,
        color: combo.color,
        filled: segmentIndex < filledCount,
        segmentIndex,
      }))
    })
    .join('rect')
    .attr('class', (cell) => `combo-count-cell${cell.filled ? ' combo-count-cell--filled' : ''}`)
    .attr('x', (cell) => layout.rightBarsX + cell.segmentIndex * (rightSquareSize + rightSquareGap))
    .attr('y', -4)
    .attr('width', rightSquareSize)
    .attr('height', rightSquareSize)
    .attr('rx', 1.4)
    .attr('fill', (cell) => (cell.filled ? cell.color : 'rgba(88, 68, 51, 0.11)'))

  comboRows
    .append('text')
    .attr('class', 'combo-count-label')
    .attr('x', layout.rightBarsX + rightSegmentCount * (rightSquareSize + rightSquareGap) + 1)
    .attr('dy', '0.32em')
    .text((combo) => combo.count)

  comboRows
    .append('rect')
    .attr('class', 'combo-hover-zone')
    .attr('x', layout.left)
    .attr('y', -7)
    .attr('width', layout.rightBarsX + layout.rightBarsWidth - layout.left)
    .attr('height', 14)
}

function drawVerticalLabel(group, text, x, y) {
  const label = group
    .append('text')
    .attr('class', 'vertical-theme-label')
    .attr('x', x)
    .attr('y', y)
    .attr('text-anchor', 'middle')

  Array.from(text).forEach((char, index) => {
    label
      .append('tspan')
      .attr('x', x)
      .attr('dy', index === 0 ? 0 : 12)
      .text(char)
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
  svg.selectAll('.combo-row')
    .attr('opacity', (combo) => (combo.index === comboIndex ? 1 : 0.22))

  svg.selectAll('.matrix-dot')
    .attr('opacity', (cell) => (cell.comboIndex === comboIndex ? 1 : cell.active ? 0.18 : 0.06))
    .attr('r', (cell) => {
      if (cell.comboIndex !== comboIndex) return cell.active ? 5.1 : 2.3
      return cell.active ? 7 : 3
    })

  svg.selectAll('.combo-count-cell')
    .attr('opacity', (cell) => (cell.comboIndex === comboIndex ? 1 : 0.18))

  svg.selectAll('.combo-connector')
    .attr('opacity', function connectorOpacity() {
      return d3.select(this.parentNode).datum().index === comboIndex ? 0.82 : 0.12
    })
}

function highlightTheme(svg, themeName) {
  svg.selectAll('.theme-count-group')
    .attr('opacity', (theme) => (theme.name === themeName ? 1 : 0.28))

  svg.selectAll('.theme-column')
    .attr('opacity', (theme) => (theme.name === themeName ? 1 : 0.32))

  svg.selectAll('.matrix-dot')
    .attr('opacity', (cell) => {
      if (cell.theme === themeName && cell.active) return 1
      return cell.active ? 0.18 : 0.06
    })
    .attr('r', (cell) => (cell.theme === themeName && cell.active ? 7 : cell.active ? 5.1 : 2.3))

  svg.selectAll('.combo-row')
    .attr('opacity', (combo) => (combo.themes.includes(themeName) ? 1 : 0.24))

  svg.selectAll('.combo-count-cell')
    .attr('opacity', (cell) => (cell.themes.includes(themeName) ? 0.95 : 0.18))
}

function clearHighlight(svg) {
  svg.selectAll('.theme-count-group').attr('opacity', 1)
  svg.selectAll('.theme-column').attr('opacity', 1)
  svg.selectAll('.combo-row').attr('opacity', 1)
  svg.selectAll('.combo-count-cell').attr('opacity', 1)
  svg.selectAll('.combo-connector').attr('opacity', 0.7)
  svg.selectAll('.matrix-dot')
    .attr('opacity', 1)
    .attr('r', (cell) => (cell.active ? 5.7 : 2.5))
}

function comboTooltip(combo) {
  const themes = combo.themes.map(escapeHtml).join('、')
  return `
    <strong>主题组合</strong>
    <span>${themes}</span>
    <em>${combo.count} 个剧本</em>
  `
}

function themeTooltip(theme) {
  return `
    <strong>${escapeHtml(theme.name)}</strong>
    <span>出现在 ${theme.count} 个剧本中</span>
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

.vertical-upset-svg :deep(.combo-count-label) {
  fill: #66574b;
  font-size: 8.5px;
  font-weight: 700;
}

.vertical-upset-svg :deep(.theme-count-stem) {
  stroke-width: 3.4;
  stroke-linecap: round;
  opacity: 0.74;
}

.vertical-upset-svg :deep(.theme-count-dot) {
  filter: drop-shadow(0 1px 2px rgba(70, 40, 22, 0.16));
}

.vertical-upset-svg :deep(.theme-count-group),
.vertical-upset-svg :deep(.theme-column),
.vertical-upset-svg :deep(.combo-row) {
  cursor: pointer;
}

.vertical-upset-svg :deep(.vertical-theme-label) {
  fill: #332820;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 12px;
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

.vertical-upset-svg :deep(.combo-count-cell) {
  stroke: rgba(255, 250, 238, 0.82);
  stroke-width: 0.7;
}

.vertical-upset-svg :deep(.combo-count-cell--filled) {
  filter: drop-shadow(0 1px 1px rgba(70, 40, 22, 0.1));
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

.upset-tooltip {
  position: absolute;
  z-index: 5;
  display: none;
  max-width: 180px;
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
