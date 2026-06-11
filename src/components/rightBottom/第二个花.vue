<template>
  <div ref="shellRef" class="play-plum-shell">
    <div v-if="loading" class="theme-state">主题数据加载中...</div>

    <div v-else-if="error" class="theme-state theme-state--error">
      {{ error }}
    </div>

    <div v-else class="play-plum-panel">
      <article
        v-for="(item, index) in displaySlots"
        :key="`${index}-${item.playId}`"
        class="play-plum-card"
      >
        <div
          :ref="(el) => setPlumRef(el, index)"
          class="plum-chart"
        />
      </article>

      <div ref="tooltipRef" class="plum-tooltip" />
    </div>
  </div>
</template>

<script setup>
import * as d3 from 'd3'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const THEME_CSV_URL = `${import.meta.env.BASE_URL}数据表合集/3/theme_analysis.csv`

const KAI_FONT = '"STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif'

const PLAY_COUNT = 4
const rows = ref([])

const loading = ref(true)

const error = ref('')

const shellRef = ref(null)

const tooltipRef = ref(null)

const plumRefs = ref([])

const selectedPlayIds = ref([])

let resizeObserver = null

let renderFrame = 0

const themeColors = {
  家庭伦理: '#ad3936',
  婚恋情感: '#ae688a',
  身份变换: '#4f7da8',
  公案审判: '#26776f',
  复仇伸冤: '#8b2a25',
  忠义家国: '#cd9744',
  战争冲突: '#6d597a',
  权力斗争: '#7f5539',
  英雄悲情: '#d35f50',
  忠义抉择: '#4f7da8',
  家国冲突: '#7f5539',
  爱情牺牲: '#c06a96',
  命运转折: '#b9823d',
  家庭冲突: '#ad3936',
  女性冤情: '#ae688a',
  伦理秩序: '#8b2a25',
  亲情选择: '#cd9744',
  谋略联盟: '#5b8ff9',
  战争策略: '#6d597a',
  盟友试探: '#2f8b7d',
  真假识别: '#d8a146',
  人情交易: '#9c6a4e',
  才子遭嫉: '#8a6ab0',
  忠直殉志: '#bf7b48',
  人蛇情缘: '#7d6ab4',
  反抗礼法: '#c26c78',
  水漫金山: '#5d95c8',
  神佛干预: '#6d5bd0',
  其他主题: '#b9a98c',
  未识别主题: '#b9a98c',
}

const fallbackThemeColors = [
  '#8f2f24',
  '#2f6f73',
  '#b8893a',
  '#9f5f7f',
  '#6d597a',
  '#7f5539',
  '#557c55',
]

const plays = computed(() => groupRowsByPlay(rows.value))

const playMap = computed(() => {
  return new Map(plays.value.map((play) => [play.playId, play]))
})

const playOptions = computed(() => {
  return plays.value
    .slice()
    .sort((a, b) => {
      return b.themes.length - a.themes.length || dominantShare(b) - dominantShare(a)
    })
})

const displaySlots = computed(() => {
  return selectedPlayIds.value.slice(0, PLAY_COUNT).map((playId) => {
    return {
      playId,
      play: playMap.value.get(playId),
    }
  })
})

onMounted(async () => {
  window.addEventListener('resize', scheduleRenderPlums)

  await loadThemeCsv()

  await nextTick()

  setupResizeObserver()

  scheduleRenderPlums()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', scheduleRenderPlums)

  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }

  if (renderFrame) {
    cancelAnimationFrame(renderFrame)
    renderFrame = 0
  }
})

watch(
  plays,
  () => {
    reconcileSelectedPlays()
  },
  { immediate: true },
)

watch(
  displaySlots,
  () => {
    scheduleRenderPlums()
  },
  { deep: true, flush: 'post' },
)

async function loadThemeCsv() {
  loading.value = true
  error.value = ''

  try {
    const response = await fetch(`${THEME_CSV_URL}?t=${Date.now()}`, {
      cache: 'no-store',
    })

    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`)
    }

    const text = await response.text()

    rows.value = parseThemeCsv(text)
  } catch (err) {
    error.value = `主题CSV读取失败：${err.message}`
    rows.value = []
  } finally {
    loading.value = false
  }
}

function setupResizeObserver() {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }

  if (typeof ResizeObserver === 'undefined') return

  resizeObserver = new ResizeObserver(() => {
    scheduleRenderPlums()
  })

  if (shellRef.value) {
    resizeObserver.observe(shellRef.value)
  }
}

function setPlumRef(el, index) {
  if (el) {
    plumRefs.value[index] = el
  }
}

function reconcileSelectedPlays() {
  if (!plays.value.length) {
    selectedPlayIds.value = []
    return
  }

  const validIds = new Set(plays.value.map((play) => play.playId))

  const nextIds = selectedPlayIds.value
    .filter((id) => validIds.has(id))
    .slice(0, PLAY_COUNT)

  const usedIds = new Set(nextIds)

  const defaults = pickRepresentativePlays(plays.value, PLAY_COUNT)

  defaults.forEach((play) => {
    if (nextIds.length >= PLAY_COUNT) return
    if (usedIds.has(play.playId)) return

    nextIds.push(play.playId)
    usedIds.add(play.playId)
  })

  playOptions.value.forEach((play) => {
    if (nextIds.length >= PLAY_COUNT) return
    if (usedIds.has(play.playId)) return

    nextIds.push(play.playId)
    usedIds.add(play.playId)
  })

  selectedPlayIds.value = nextIds
  plumRefs.value = plumRefs.value.slice(0, PLAY_COUNT)
}

function scheduleRenderPlums() {
  if (renderFrame) {
    cancelAnimationFrame(renderFrame)
  }

  renderFrame = requestAnimationFrame(async () => {
    renderFrame = 0
    await renderPlums()
  })
}

async function renderPlums() {
  await nextTick()

  hideTooltip()

  displaySlots.value.forEach((item, index) => {
    const container = plumRefs.value[index]
    const play = item.play

    if (!container) return

    d3.select(container).selectAll('*').remove()

    if (!play) return

    renderSinglePlum(container, play, index)
  })
}

function createHeartCloverLeafPath(angleDegree, rootRadius, length, halfWidth) {
  const angle = toRadians(angleDegree)

  const ux = Math.cos(angle)
  const uy = Math.sin(angle)

  const px = -uy
  const py = ux

  const point = (localX, localY) => {
    const x = ux * localX + px * localY
    const y = uy * localX + py * localY

    return `${x.toFixed(2)},${y.toFixed(2)}`
  }

  const heartMinY = -17
  const heartMaxY = 11.92
  const heartRangeY = heartMaxY - heartMinY
  const heartHalfX = 16

  const points = []

  const steps = 96

  for (let i = 0; i <= steps; i += 1) {
    const t = Math.PI + Math.PI * 2 * (i / steps)

    const rawX = 16 * Math.pow(Math.sin(t), 3)

    const rawY =
      13 * Math.cos(t) -
      5 * Math.cos(2 * t) -
      2 * Math.cos(3 * t) -
      Math.cos(4 * t)

    const radial = (rawY - heartMinY) / heartRangeY

    const localX = rootRadius + radial * length

    const localY = rawX / heartHalfX * halfWidth

    points.push(point(localX, localY))
  }

  return `M ${points[0]} L ${points.slice(1).join(' L ')} Z`
}
function renderSinglePlum(container, play, slotIndex) {
  const width = Math.max(190, container.clientWidth || 260)

  const height = Math.max(150, container.clientHeight || 190)

  const cx = width / 2

  const cy = height * 0.5

  const minSide = Math.min(width, height)

  const themes = buildPlumThemes(play)

  const petalCount = Math.max(themes.length, 1)

  const centerRadius = minSide * 0.18

  const angleStepDegree = 360 / petalCount

  const petalGapDegree = Math.min(angleStepDegree * 0.16, 12)

  const rootRadius = centerRadius * 0.42

  const baseLeafLength = minSide * (
    petalCount <= 4
      ? 0.31
      : petalCount <= 6
        ? 0.29
        : petalCount <= 8
          ? 0.265
          : 0.235
  )

  const svg = d3
    .select(container)
    .append('svg')
    .attr('class', 'plum-svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')

  const chartGroup = svg
    .append('g')
    .attr('class', 'plum-chart-group')
    .attr('transform', `translate(${cx}, ${cy})`)

  const petalData = themes.map((theme, index) => {
    const angleDegree = -90 + index * angleStepDegree

    const length = baseLeafLength + minSide * 0.03 * Math.sqrt(theme.share)

    const middleRadius = rootRadius + length * 0.68

    const safeHalfWidth = Math.tan(toRadians((angleStepDegree - petalGapDegree) / 2)) * middleRadius * 0.72

    const maxHalfWidth = minSide * (
      petalCount <= 4
        ? 0.17
        : petalCount <= 6
          ? 0.135
          : petalCount <= 8
            ? 0.105
            : 0.078
    )

    const minHalfWidth = minSide * (
      petalCount <= 4
        ? 0.105
        : petalCount <= 6
          ? 0.082
          : 0.06
    )

    const halfWidth = Math.max(
      minHalfWidth,
      Math.min(maxHalfWidth, safeHalfWidth),
    )

    return {
      ...theme,
      angleDegree,
      rootRadius,
      length,
      halfWidth,
    }
  })

  chartGroup
    .selectAll('.plum-petal-back')
    .data(petalData)
    .join('path')
    .attr('class', 'plum-petal-back')
    .attr('d', (d) => {
      return createHeartCloverLeafPath(
        d.angleDegree,
        d.rootRadius,
        d.length,
        d.halfWidth * 1.08,
      )
    })
    .attr('fill', 'none')
    .attr('stroke', 'rgba(105, 70, 35, 0.38)')
    .attr('stroke-width', 3)
    .attr('stroke-linejoin', 'round')
    .attr('pointer-events', 'none')

  const petals = chartGroup
    .selectAll('.plum-petal')
    .data(petalData)
    .join('path')
    .attr('class', 'plum-petal')
    .attr('d', (d) => {
      return createHeartCloverLeafPath(
        d.angleDegree,
        d.rootRadius,
        d.length,
        d.halfWidth,
      )
    })
    .attr('fill', (d) => themeColor(d.name))
    .attr('stroke', 'rgba(255, 249, 235, 0.98)')
    .attr('stroke-width', 1.5)
    .attr('stroke-linejoin', 'round')
    .attr('opacity', 0.96)
    .style('cursor', 'pointer')

  chartGroup
    .selectAll('.plum-petal-vein')
    .data(petalData)
    .join('path')
    .attr('class', 'plum-petal-vein')
    .attr('d', (d) => {
      return createPetalVeinPath(d.angleDegree, d.rootRadius, d.length)
    })
    .attr('fill', 'none')
    .attr('stroke', 'rgba(255, 250, 238, 0.38)')
    .attr('stroke-width', 1)
    .attr('stroke-linecap', 'round')
    .attr('pointer-events', 'none')

  petals
    .on('mouseenter', (event, d) => {
      chartGroup.selectAll('.plum-petal').attr('opacity', 0.28)

      chartGroup.selectAll('.plum-petal-vein').attr('opacity', 0.16)

      d3.select(event.currentTarget).attr('opacity', 1)

      showTooltip(event, play, d)
    })
    .on('mousemove', (event) => {
      moveTooltip(event)
    })
    .on('mouseleave', () => {
      chartGroup.selectAll('.plum-petal').attr('opacity', 0.96)

      chartGroup.selectAll('.plum-petal-vein').attr('opacity', 1)

      hideTooltip()
    })

  drawPercentLabels(chartGroup, petalData, petalCount)

  const center = chartGroup
    .append('g')
    .attr('class', 'plum-center')
    .style('cursor', 'pointer')
    .on('click', () => {
      switchToNextPlay(slotIndex)
    })

  center
    .append('circle')
    .attr('r', centerRadius)
    .attr('fill', 'rgba(255, 247, 229, 0.98)')
    .attr('stroke', 'rgba(154, 108, 61, 0.52)')
    .attr('stroke-width', 1.6)

  center
    .append('circle')
    .attr('r', centerRadius * 0.78)
    .attr('fill', 'none')
    .attr('stroke', 'rgba(173, 57, 54, 0.18)')
    .attr('stroke-width', 0.9)

  drawCenterSelect(center, play, slotIndex, centerRadius)
}
 
function createPetalVeinPath(angleDegree, rootRadius, length) {
  const angle = toRadians(angleDegree)

  const ux = Math.cos(angle)
  const uy = Math.sin(angle)

  const point = (localX, localY) => {
    const x = ux * localX
    const y = uy * localX

    return `${x.toFixed(2)},${y.toFixed(2)}`
  }

  const start = rootRadius + length * 0.08

  const middle = rootRadius + length * 0.45

  const end = rootRadius + length * 0.73

  return [
    `M ${point(start, 0)}`,
    `C ${point(middle, 0)} ${point(middle, 0)} ${point(end, 0)}`,
  ].join(' ')
}


function drawPercentLabels(chartGroup, petalData, petalCount) {
  const minVisibleShare = petalCount >= 8 ? 0.06 : 0.035

  chartGroup
    .selectAll('.plum-percent-label')
    .data(petalData.filter((theme) => theme.share >= minVisibleShare))
    .join('text')
    .attr('class', 'plum-percent-label')
    .attr('x', (d) => {
      const angle = toRadians(d.angleDegree)

      const distance = d.rootRadius + d.length * 0.55

      return Math.cos(angle) * distance
    })
    .attr('y', (d) => {
      const angle = toRadians(d.angleDegree)

      const distance = d.rootRadius + d.length * 0.55

      return Math.sin(angle) * distance
    })
    .attr('dy', '0.35em')
    .attr('text-anchor', 'middle')
    .style('font-size', petalCount >= 8 ? '9px' : '12px')
    .text((d) => formatPercent(d.share))
}

function drawCenterSelect(center, play, slotIndex, centerRadius) {
  const selectWidth = centerRadius * 1.85
const selectHeight = centerRadius * 0.9
  const foreignObject = center
    .append('foreignObject')
    .attr('x', -selectWidth / 2)
    .attr('y', -selectHeight / 2)
    .attr('width', selectWidth)
    .attr('height', selectHeight)

  const wrap = foreignObject
    .append('xhtml:div')
    .attr('class', 'plum-center-select-wrap')

  const select = wrap
    .append('select')
    .attr('class', 'plum-center-select')
    .on('mousedown', (event) => {
      event.stopPropagation()
    })
    .on('click', (event) => {
      event.stopPropagation()
    })
    .on('change', (event) => {
      selectedPlayIds.value[slotIndex] = event.target.value
    })

  select
    .selectAll('option')
    .data(playOptions.value)
    .join('option')
    .attr('value', (d) => d.playId)
    .text((d) => d.title)

  select.property('value', play.playId)
}


function switchToNextPlay(slotIndex) {
  if (!playOptions.value.length) return

  const currentId = selectedPlayIds.value[slotIndex]

  const currentIndex = playOptions.value.findIndex((play) => play.playId === currentId)

  const nextIndex = currentIndex >= 0
    ? (currentIndex + 1) % playOptions.value.length
    : 0

  selectedPlayIds.value[slotIndex] = playOptions.value[nextIndex].playId
}

function showTooltip(event, play, theme) {
  if (!tooltipRef.value) return

  tooltipRef.value.innerHTML = `
    <div class="tip-title">${escapeHtml(theme.name)}</div>
    <div class="tip-line">
      <span>剧本</span>
      <strong>${escapeHtml(play.title)}</strong>
    </div>
    <div class="tip-line">
      <span>占比</span>
      <strong>${formatPercent(theme.share)}</strong>
    </div>
    <div class="tip-line">
      <span>得分</span>
      <strong>${formatNumber(theme.score)}</strong>
    </div>
  `

  tooltipRef.value.classList.add('plum-tooltip--visible')

  moveTooltip(event)
}

function moveTooltip(event) {
  if (!tooltipRef.value || !shellRef.value) return

  const [x, y] = d3.pointer(event, shellRef.value)

  const shellWidth = shellRef.value.clientWidth || 0

  const tooltipWidth = tooltipRef.value.offsetWidth || 140

  const left = x + tooltipWidth + 24 > shellWidth ? x - tooltipWidth - 14 : x + 14

  tooltipRef.value.style.left = `${left}px`

  tooltipRef.value.style.top = `${y + 12}px`
}

function hideTooltip() {
  if (!tooltipRef.value) return

  tooltipRef.value.classList.remove('plum-tooltip--visible')
}

function buildPlumThemes(play) {
  const themes = normalizedThemes(play)
    .filter((theme) => theme.name && theme.share > 0)
    .sort((a, b) => {
      const rankA = Number.isFinite(a.rank) && a.rank > 0 ? a.rank : 999
      const rankB = Number.isFinite(b.rank) && b.rank > 0 ? b.rank : 999

      return rankA - rankB || b.share - a.share
    })

  if (!themes.length) {
    return [
      {
        name: '未识别主题',
        share: 1,
        score: 0,
        rank: 999,
      },
    ]
  }

  return themes
}



function normalizedThemes(play) {
  const validThemes = play.themes.filter((theme) => theme.name)

  const total = validThemes.reduce((sum, theme) => {
    return sum + Number(theme.share || 0)
  }, 0) || 1

  return validThemes.map((theme) => {
    return {
      ...theme,
      share: Number(theme.share || 0) / total,
    }
  })
}

function dominantCombination(play) {
  const topThemes = normalizedThemes(play)
    .filter((theme) => theme.name && theme.share > 0)
    .sort((a, b) => b.share - a.share)
    .slice(0, 2)

  if (!topThemes.length) return '暂无主题'

  return topThemes.map((theme) => theme.name).join(' + ')
}

function pickRepresentativePlays(sourcePlays, limit) {
  const selected = []

  const selectedIds = new Set()

  sourcePlays
    .slice()
    .sort((a, b) => {
      return b.themes.length - a.themes.length || dominantShare(b) - dominantShare(a)
    })
    .forEach((play) => {
      if (selected.length >= limit) return
      if (selectedIds.has(play.playId)) return

      selected.push(play)
      selectedIds.add(play.playId)
    })

  return selected
}

function dominantShare(play) {
  return Math.max(0, ...play.themes.map((theme) => Number(theme.share || 0)))
}

function themeColor(name) {
  if (themeColors[name]) return themeColors[name]

  const code = Array.from(String(name)).reduce((sum, char) => {
    return sum + char.charCodeAt(0)
  }, 0)

  return fallbackThemeColors[code % fallbackThemeColors.length]
}

function parseThemeCsv(text) {
  const cleanText = String(text || '').trim()

  if (!cleanText) return []

  const [headerLine, ...lines] = cleanText.split(/\r?\n/)

  const headers = splitCsvLine(headerLine).map((header) => header.trim())

  return lines
    .filter((line) => line.trim())
    .map((line) => {
      const values = splitCsvLine(line)

      const row = Object.fromEntries(
        headers.map((header, index) => [header, values[index] || '']),
      )

      return {
        play_id: String(row.play_id || '').trim(),
        title: String(row.title || '').trim(),
        genre: String(row.genre || '').trim(),
        collection: String(row.collection || '').trim(),
        theme: String(row.theme || '').trim(),
        score: toNumber(row.score),
        share: toShare(row.share),
        rank: toNumber(row.rank),
      }
    })
    .filter((row) => row.play_id && row.title && row.theme)
}

function splitCsvLine(line) {
  const cells = []

  let cell = ''

  let quoted = false

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index]

    const next = line[index + 1]

    if (char === '"' && quoted && next === '"') {
      cell += '"'
      index += 1
    } else if (char === '"') {
      quoted = !quoted
    } else if (char === ',' && !quoted) {
      cells.push(cell)
      cell = ''
    } else {
      cell += char
    }
  }

  cells.push(cell)

  return cells
}

function groupRowsByPlay(sourceRows) {
  const map = new Map()

  sourceRows.forEach((row) => {
    if (!map.has(row.play_id)) {
      map.set(row.play_id, {
        playId: row.play_id,
        title: row.title,
        genre: row.genre,
        collection: row.collection,
        themes: [],
      })
    }

    map.get(row.play_id).themes.push({
      name: row.theme,
      score: row.score,
      share: row.share,
      rank: row.rank,
    })
  })

  return Array.from(map.values()).map((play) => {
    return {
      ...play,
      themes: play.themes.slice().sort((a, b) => {
        const rankA = Number.isFinite(a.rank) && a.rank > 0 ? a.rank : 999
        const rankB = Number.isFinite(b.rank) && b.rank > 0 ? b.rank : 999

        return rankA - rankB || b.share - a.share
      }),
    }
  })
}

function toNumber(value) {
  const number = Number(String(value ?? '').replace('%', '').trim())

  return Number.isFinite(number) ? number : 0
}

function toShare(value) {
  const raw = String(value ?? '').trim()

  if (!raw) return 0

  const hasPercent = raw.includes('%')

  const number = Number(raw.replace('%', '').trim())

  if (!Number.isFinite(number)) return 0

  if (hasPercent) return number / 100

  return number > 1 ? number / 100 : number
}

function formatPercent(value) {
  const number = Number(value || 0) * 100

  if (number >= 10) {
    return `${number.toFixed(0)}%`
  }

  return `${number.toFixed(1)}%`
}

function formatNumber(value) {
  const number = Number(value || 0)

  if (!Number.isFinite(number)) return '0'

  return number.toFixed(2).replace(/\.00$/, '')
}

function toRadians(degree) {
  return degree * Math.PI / 180
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}
</script>

<style scoped>
.play-plum-shell {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
}

.play-plum-panel {
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(2, minmax(0, 1fr));
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 48%, rgba(255, 250, 235, 0.66), rgba(246, 236, 214, 0) 58%),
    transparent;
}

.play-plum-panel::before {
  content: "";
  position: absolute;
  left: 50%;
  top: 8%;
  bottom: 8%;
  width: 1px;
  background: linear-gradient(
    180deg,
    transparent,
    rgba(151, 111, 63, 0.2),
    rgba(143, 47, 36, 0.12),
    rgba(151, 111, 63, 0.2),
    transparent
  );
  pointer-events: none;
}

.play-plum-panel::after {
  content: "";
  position: absolute;
  left: 8%;
  right: 8%;
  top: 50%;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(151, 111, 63, 0.2),
    rgba(143, 47, 36, 0.12),
    rgba(151, 111, 63, 0.2),
    transparent
  );
  pointer-events: none;
}

.play-plum-card {
  position: relative;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: transparent;
}



.plum-chart {
  position: relative;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  overflow: visible;
}

.plum-chart :deep(.plum-svg) {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.plum-chart :deep(.plum-petal-back) {
  filter: drop-shadow(0 3px 8px rgba(74, 43, 24, 0.15));
}



.plum-chart :deep(.plum-petal) {
  filter: drop-shadow(0 2px 5px rgba(74, 43, 24, 0.1));
  transition:
    opacity 0.18s ease,
    filter 0.18s ease;
}

.plum-chart :deep(.plum-petal:hover) {
  filter: drop-shadow(0 5px 12px rgba(74, 43, 24, 0.18));
}



.plum-chart :deep(.plum-petal) {
  filter: drop-shadow(0 3px 7px rgba(74, 43, 24, 0.12));
  transition:
    opacity 0.18s ease,
    transform 0.18s ease,
    filter 0.18s ease;
}

.plum-chart :deep(.plum-petal:hover) {
  filter: drop-shadow(0 5px 10px rgba(74, 43, 24, 0.18));
}
.plum-chart :deep(.plum-center) {
  transition: transform 0.18s ease;
}

.plum-chart :deep(.plum-center:hover) {
  transform: scale(1.04);
}

.plum-chart :deep(.plum-percent-label) {
  fill: rgba(255, 250, 238, 0.96);
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 12px;
  font-weight: 900;
  paint-order: stroke;
  stroke: rgba(65, 39, 27, 0.3);
  stroke-width: 2.1px;
  pointer-events: none;
  user-select: none;
}

.plum-chart :deep(.plum-center-select-wrap) {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.plum-chart :deep(.plum-center-select) {
  width: 100%;
  height: 100%;
  border: none;
  outline: none;
  color: #6a3b2d;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 9px;
  font-weight: 900;
  text-align: center;
  text-align-last: center;
  background: transparent;
  cursor: pointer;
  appearance: none;
}

.plum-chart :deep(.plum-center-select:hover) {
  color: #8f2f24;
}


.plum-tooltip {
  position: absolute;
  z-index: 20;
  min-width: 126px;
  padding: 9px 10px;
  border: 1px solid rgba(150, 105, 55, 0.22);
  border-radius: 12px;
  color: #543624;
  background:
    linear-gradient(180deg, rgba(255, 251, 241, 0.98), rgba(247, 238, 218, 0.96)),
    #f7eedb;
  box-shadow: 0 8px 22px rgba(65, 38, 23, 0.14);
  opacity: 0;
  transform: translateY(4px);
  pointer-events: none;
  transition:
    opacity 0.14s ease,
    transform 0.14s ease;
}

.plum-tooltip--visible {
  opacity: 1;
  transform: translateY(0);
}

.plum-tooltip :deep(.tip-title) {
  margin-bottom: 6px;
  color: #8f2f24;
  font-size: 14px;
  font-weight: 900;
  letter-spacing: 0.04em;
}

.plum-tooltip :deep(.tip-line) {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 3px;
  font-size: 12px;
  line-height: 1.35;
}

.plum-tooltip :deep(.tip-line span) {
  color: rgba(92, 64, 42, 0.68);
}

.plum-tooltip :deep(.tip-line strong) {
  color: #4e3324;
  font-weight: 900;
}

.theme-state {
  display: grid;
  width: 100%;
  height: 100%;
  min-height: 0;
  place-items: center;
  color: #6b4628;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 15px;
  font-weight: 900;
}

.theme-state--error {
  color: #8f2f24;
}
</style>