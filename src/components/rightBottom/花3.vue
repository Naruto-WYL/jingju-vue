<template>
  <div ref="shellRef" class="play-plum-shell">
    <div v-if="loading" class="theme-state">主题数据加载中...</div>

    <div v-else-if="error" class="theme-state theme-state--error">
      {{ error }}
    </div>

    <div v-else class="play-plum-panel">
      <article
        v-for="(item, slotIndex) in flowerSlots"
        :key="`${slotIndex}-${item.playId}`"
        class="play-plum-card"
      >
        <svg
          class="plum-svg"
          :viewBox="`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`"
          preserveAspectRatio="xMidYMid meet"
          role="img"
          :aria-label="item.play ? `${item.play.title}主题花瓣图` : '主题花瓣图'"
          @mouseleave="hideTooltip"
        >
          <g :transform="`translate(${SVG_WIDTH / 2}, ${SVG_HEIGHT / 2})`">
            <g class="plum-petal-layer">
              <path
                v-for="petal in item.petals"
                :key="petal.uid"
                class="plum-petal"
                :class="{
                  'plum-petal--active': hoveredPetalKey === petal.uid,
                  'plum-petal--dim': hoveredPetalKey && hoveredPetalKey !== petal.uid && hoveredSlotIndex === slotIndex,
                }"
                :d="petal.path"
                :fill="petal.color"
                @mouseenter="showTooltip($event, item.play, petal, slotIndex)"
                @mousemove="moveTooltip"
                @mouseleave="hideTooltip"
              >
                <title>
                  {{ petal.name }}：{{ formatPercent(petal.share) }}
                </title>
              </path>

              <path
                v-for="petal in item.petals"
                :key="`${petal.uid}-vein`"
                class="plum-petal-vein"
                :d="petal.veinPath"
              />
            </g>

            <text
              v-for="petal in item.petals.filter((p) => p.showLabel)"
              :key="`${petal.uid}-label`"
              class="plum-percent-label"
              :x="petal.labelX"
              :y="petal.labelY"
              :style="{ fontSize: `${petal.labelSize}px` }"
              text-anchor="middle"
              dominant-baseline="middle"
            >
              {{ formatPercent(petal.share) }}
            </text>

            <g
              class="plum-center"
              @click="switchToNextPlay(slotIndex)"
            >
              <circle
                :r="CENTER_RADIUS + 2"
                class="plum-center-outer"
              />

              <circle
                :r="CENTER_RADIUS"
                class="plum-center-main"
              />

              <circle
                v-for="dot in centerDots"
                :key="dot.key"
                :cx="dot.x"
                :cy="dot.y"
                :r="dot.r"
                class="plum-center-dot"
              />

              <foreignObject
                :x="-CENTER_RADIUS * 0.82"
                :y="-CENTER_RADIUS * 0.38"
                :width="CENTER_RADIUS * 1.64"
                :height="CENTER_RADIUS * 0.76"
              >
                <div class="plum-center-select-wrap">
                  <select
                    class="plum-center-select"
                    :value="item.playId"
                    @mousedown.stop
                    @click.stop
                    @change="changePlay(slotIndex, $event.target.value)"
                  >
                    <option
                      v-for="play in playOptions"
                      :key="play.playId"
                      :value="play.playId"
                    >
                      {{ play.title }}
                    </option>
                  </select>
                </div>
              </foreignObject>
            </g>
          </g>
        </svg>
      </article>

      <div ref="tooltipRef" class="plum-tooltip" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'

const THEME_CSV_URL = `${import.meta.env.BASE_URL}数据表合集/3/theme_analysis.csv`

const PLAY_COUNT = 4

const SVG_WIDTH = 320
const SVG_HEIGHT = 250
const CENTER_RADIUS = 28

const rows = ref([])
const loading = ref(true)
const error = ref('')

const shellRef = ref(null)
const tooltipRef = ref(null)

const selectedPlayIds = ref([])

const hoveredPetalKey = ref('')
const hoveredSlotIndex = ref(-1)

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

const flowerSlots = computed(() => {
  return displaySlots.value.map((item, slotIndex) => {
    if (!item.play) {
      return {
        ...item,
        petals: [],
      }
    }

    return {
      ...item,
      petals: buildPetalData(item.play, slotIndex),
    }
  })
})

const centerDots = computed(() => {
  const dots = []
  const count = 10
  const radius = CENTER_RADIUS * 0.62

  for (let index = 0; index < count; index += 1) {
    const angle = toRadians((360 / count) * index - 90)
    dots.push({
      key: `dot-${index}`,
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
      r: index % 2 === 0 ? 2.1 : 1.6,
    })
  }

  return dots
})

onMounted(async () => {
  await loadThemeCsv()
})

watch(
  plays,
  () => {
    reconcileSelectedPlays()
  },
  { immediate: true },
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
}

function changePlay(slotIndex, playId) {
  const nextIds = selectedPlayIds.value.slice()
  nextIds[slotIndex] = playId
  selectedPlayIds.value = nextIds
  hideTooltip()
}

function switchToNextPlay(slotIndex) {
  if (!playOptions.value.length) return

  const currentId = selectedPlayIds.value[slotIndex]
  const currentIndex = playOptions.value.findIndex((play) => play.playId === currentId)

  const nextIndex = currentIndex >= 0
    ? (currentIndex + 1) % playOptions.value.length
    : 0

  changePlay(slotIndex, playOptions.value[nextIndex].playId)
}

function buildPetalData(play, slotIndex) {
  const themes = buildPlumThemes(play)
  const petalCount = Math.max(themes.length, 1)

  const angleStepDegree = 360 / petalCount
  const rootRadius = CENTER_RADIUS * 0.72

  const baseLength =
    petalCount <= 4 ? 86 :
    petalCount <= 6 ? 80 :
    petalCount <= 8 ? 73 :
    petalCount <= 10 ? 65 :
    58

  const maxHalfWidth =
    petalCount <= 4 ? 46 :
    petalCount <= 6 ? 39 :
    petalCount <= 8 ? 30 :
    petalCount <= 10 ? 24 :
    19

  const minHalfWidth =
    petalCount <= 6 ? 21 :
    petalCount <= 10 ? 15 :
    12

  return themes.map((theme, index) => {
    const angleDegree = -90 + index * angleStepDegree

    const length = baseLength + 20 * Math.sqrt(theme.share)

    const middleRadius = rootRadius + length * 0.56
    const safeHalfWidth = Math.tan(toRadians(angleStepDegree / 2)) * middleRadius * 0.74
    const halfWidth = clamp(safeHalfWidth, minHalfWidth, maxHalfWidth)

    const path = createFlowerPetalPath(angleDegree, rootRadius, length, halfWidth)
    const veinPath = createPetalVeinPath(angleDegree, rootRadius, length, halfWidth)

    const labelDistance = rootRadius + length * 0.68
    const labelAngle = toRadians(angleDegree)

    return {
      uid: `${slotIndex}-${play.playId}-${theme.name}-${index}`,
      name: theme.name,
      score: theme.score,
      share: theme.share,
      rank: theme.rank,
      color: themeColor(theme.name),
      angleDegree,
      rootRadius,
      length,
      halfWidth,
      path,
      veinPath,
      labelX: Math.cos(labelAngle) * labelDistance,
      labelY: Math.sin(labelAngle) * labelDistance,
      labelSize: petalCount >= 9 ? 9 : 12,
      showLabel: theme.share >= (petalCount >= 9 ? 0.055 : 0.035),
    }
  })
}

function createFlowerPetalPath(angleDegree, rootRadius, length, halfWidth) {
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

  const start = rootRadius
  const tip = rootRadius + length

  const neck = halfWidth * 0.16
  const w = halfWidth

  const shoulderX = start + length * 0.35
  const bellyX = start + length * 0.68
  const tipRoundX = start + length * 0.94

  return [
    `M ${point(start, -neck)}`,

    `C ${point(start + length * 0.08, -w * 0.52)} ${point(shoulderX, -w * 1.08)} ${point(bellyX, -w * 0.92)}`,

    `C ${point(tipRoundX, -w * 0.68)} ${point(tip + length * 0.05, -w * 0.22)} ${point(tip, 0)}`,

    `C ${point(tip + length * 0.05, w * 0.22)} ${point(tipRoundX, w * 0.68)} ${point(bellyX, w * 0.92)}`,

    `C ${point(shoulderX, w * 1.08)} ${point(start + length * 0.08, w * 0.52)} ${point(start, neck)}`,

    'Z',
  ].join(' ')
}

function createPetalVeinPath(angleDegree, rootRadius, length, halfWidth) {
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

  const start = rootRadius + length * 0.06
  const end = rootRadius + length * 0.72

  const sideStart = rootRadius + length * 0.3
  const sideEnd = rootRadius + length * 0.55

  return [
    `M ${point(start, 0)}`,
    `C ${point(start + length * 0.18, -halfWidth * 0.05)} ${point(end - length * 0.2, halfWidth * 0.05)} ${point(end, 0)}`,

    `M ${point(sideStart, 0)}`,
    `C ${point(sideStart + length * 0.1, -halfWidth * 0.12)} ${point(sideEnd, -halfWidth * 0.22)} ${point(sideEnd + length * 0.08, -halfWidth * 0.28)}`,

    `M ${point(sideStart, 0)}`,
    `C ${point(sideStart + length * 0.1, halfWidth * 0.12)} ${point(sideEnd, halfWidth * 0.22)} ${point(sideEnd + length * 0.08, halfWidth * 0.28)}`,
  ].join(' ')
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

function showTooltip(event, play, petal, slotIndex) {
  if (!tooltipRef.value || !play) return

  hoveredPetalKey.value = petal.uid
  hoveredSlotIndex.value = slotIndex

  tooltipRef.value.innerHTML = `
    <div class="tip-title">${escapeHtml(petal.name)}</div>
    <div class="tip-line">
      <span>剧本</span>
      <strong>${escapeHtml(play.title)}</strong>
    </div>
    <div class="tip-line">
      <span>占比</span>
      <strong>${formatPercent(petal.share)}</strong>
    </div>
    <div class="tip-line">
      <span>得分</span>
      <strong>${formatNumber(petal.score)}</strong>
    </div>
  `

  tooltipRef.value.classList.add('plum-tooltip--visible')
  moveTooltip(event)
}

function moveTooltip(event) {
  if (!tooltipRef.value || !shellRef.value) return

  const shellRect = shellRef.value.getBoundingClientRect()

  const x = event.clientX - shellRect.left
  const y = event.clientY - shellRect.top

  const shellWidth = shellRect.width || 0
  const shellHeight = shellRect.height || 0

  const tooltipWidth = tooltipRef.value.offsetWidth || 150
  const tooltipHeight = tooltipRef.value.offsetHeight || 80

  const left = x + tooltipWidth + 24 > shellWidth
    ? x - tooltipWidth - 14
    : x + 14

  const top = y + tooltipHeight + 24 > shellHeight
    ? y - tooltipHeight - 12
    : y + 12

  tooltipRef.value.style.left = `${Math.max(8, left)}px`
  tooltipRef.value.style.top = `${Math.max(8, top)}px`
}

function hideTooltip() {
  hoveredPetalKey.value = ''
  hoveredSlotIndex.value = -1

  if (!tooltipRef.value) return
  tooltipRef.value.classList.remove('plum-tooltip--visible')
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
        headers.map((header, index) => {
          return [header, values[index] || '']
        }),
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
  if (number >= 10) return `${number.toFixed(0)}%`
  return `${number.toFixed(1)}%`
}

function formatNumber(value) {
  const number = Number(value || 0)
  if (!Number.isFinite(number)) return '0'

  return number.toFixed(2).replace(/\.00$/, '')
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
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
  background: transparent;
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
    rgba(116, 86, 50, 0.18),
    rgba(116, 86, 50, 0.18),
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
    rgba(116, 86, 50, 0.18),
    rgba(116, 86, 50, 0.18),
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
  overflow: visible;
  background: transparent;
}

.plum-svg {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.plum-petal {
  cursor: pointer;
  stroke: rgba(255, 249, 235, 0.92);
  stroke-width: 1.4;
  stroke-linejoin: round;
  opacity: 0.96;
  filter: drop-shadow(0 4px 7px rgba(74, 43, 24, 0.15));
  transition:
    opacity 0.18s ease,
    transform 0.18s ease,
    filter 0.18s ease;
  transform-box: fill-box;
  transform-origin: center;
}

.plum-petal:hover,
.plum-petal--active {
  opacity: 1;
  filter: drop-shadow(0 6px 13px rgba(74, 43, 24, 0.22));
}

.plum-petal--dim {
  opacity: 0.32;
}

.plum-petal-vein {
  fill: none;
  stroke: rgba(255, 250, 238, 0.58);
  stroke-width: 1;
  stroke-linecap: round;
  pointer-events: none;
}

.plum-percent-label {
  fill: rgba(255, 250, 238, 0.98);
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-weight: 900;
  paint-order: stroke;
  stroke: rgba(66, 41, 27, 0.35);
  stroke-width: 2.5px;
  pointer-events: none;
  user-select: none;
}

.plum-center {
  cursor: pointer;
  transition: transform 0.18s ease;
}

.plum-center:hover {
  transform: scale(1.035);
}

.plum-center-outer {
  fill: rgba(255, 250, 238, 0.75);
  stroke: rgba(146, 100, 55, 0.28);
  stroke-width: 1;
}

.plum-center-main {
  fill: rgba(255, 246, 225, 1);
  stroke: rgba(146, 100, 55, 0.55);
  stroke-width: 1.5;
}

.plum-center-dot {
  fill: rgba(161, 87, 46, 0.55);
  pointer-events: none;
}

.plum-center-select-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.plum-center-select {
  width: 100%;
  height: 100%;
  border: none;
  outline: none;
  color: #6a3b2d;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 8.5px;
  font-weight: 900;
  line-height: 1;
  text-align: center;
  text-align-last: center;
  background: transparent;
  cursor: pointer;
  appearance: none;
}

.plum-center-select:hover {
  color: #8f2f24;
}

.plum-tooltip {
  position: absolute;
  z-index: 20;
  min-width: 128px;
  padding: 9px 10px;
  border: 1px solid rgba(150, 105, 55, 0.22);
  border-radius: 12px;
  color: #543624;
  background: rgba(255, 251, 241, 0.97);
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