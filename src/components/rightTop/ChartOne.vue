<template>
  <div class="rose-ring-panel">
    <svg class="rose-ring" viewBox="-220 -220 440 440" role="img" aria-label="主题组合比例环图">
      <g class="core-overlap">
        <circle
          v-for="theme in coreCircles"
          :key="theme.name"
          :cx="theme.x"
          :cy="theme.y"
          :r="theme.r"
          :fill="theme.color"
        />
        <text v-for="theme in coreCircles" :key="`${theme.name}-label`" :x="theme.x" :y="theme.y">
          {{ theme.short }}
        </text>
      </g>

      <g class="equal-play-ring">
        <path v-for="segment in playSegments" :key="segment.id" :d="segment.path" :fill="segment.fill" />
      </g>

      <g class="composition-ring">
        <path
          v-for="segment in compositionSegments"
          :key="segment.id"
          :d="segment.path"
          :fill="segment.color"
          :opacity="segment.opacity"
        />
      </g>

      <g class="wave-ring">
        <path
          v-for="arc in cooccurrenceArcs"
          :key="arc.id"
          :d="arc.path"
          :stroke="arc.color"
          :stroke-width="arc.width"
          :opacity="arc.opacity"
        />
      </g>
    </svg>

    <div class="rose-legend">
      <span v-for="theme in themeLegend" :key="theme.name">
        <i :style="{ background: theme.color }" />
        {{ theme.name }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const themeColors = {
  家庭伦理: '#ad3936',
  公案审判: '#26776f',
  忠义家国: '#cd9744',
  婚恋情感: '#ae688a',
  战争征伐: '#6d597a',
  神怪因果: '#7f5539',
}

const roseData = [
  {
    genre: '公案戏',
    plays: [
      { name: '铡美案', themes: { 公案审判: 0.48, 忠义家国: 0.22, 家庭伦理: 0.18, 婚恋情感: 0.12 } },
      { name: '四进士', themes: { 公案审判: 0.42, 家庭伦理: 0.26, 忠义家国: 0.18, 婚恋情感: 0.14 } },
    ],
  },
  {
    genre: '历史戏',
    plays: [
      { name: '空城计', themes: { 忠义家国: 0.44, 战争征伐: 0.28, 公案审判: 0.16, 家庭伦理: 0.12 } },
      { name: '群英会', themes: { 战争征伐: 0.38, 忠义家国: 0.34, 公案审判: 0.16, 家庭伦理: 0.12 } },
    ],
  },
  {
    genre: '家庭戏',
    plays: [
      { name: '三娘教子', themes: { 家庭伦理: 0.52, 忠义家国: 0.18, 婚恋情感: 0.18, 公案审判: 0.12 } },
      { name: '清风亭', themes: { 家庭伦理: 0.46, 婚恋情感: 0.22, 忠义家国: 0.18, 神怪因果: 0.14 } },
    ],
  },
  {
    genre: '婚恋戏',
    plays: [
      { name: '苏三起解', themes: { 婚恋情感: 0.4, 公案审判: 0.3, 家庭伦理: 0.2, 忠义家国: 0.1 } },
      { name: '红娘', themes: { 婚恋情感: 0.54, 家庭伦理: 0.2, 神怪因果: 0.14, 忠义家国: 0.12 } },
    ],
  },
  {
    genre: '战争戏',
    plays: [
      { name: '长坂坡', themes: { 战争征伐: 0.48, 忠义家国: 0.34, 公案审判: 0.12, 家庭伦理: 0.06 } },
    ],
  },
  {
    genre: '神怪戏',
    plays: [
      { name: '天女散花', themes: { 神怪因果: 0.5, 婚恋情感: 0.18, 家庭伦理: 0.18, 忠义家国: 0.14 } },
    ],
  },
]

const flatPlays = computed(() =>
  roseData.flatMap((group, genreIndex) =>
    group.plays.map((play) => ({
      ...play,
      genre: group.genre,
      genreIndex,
    })),
  ),
)

const coreCircles = computed(() => [
  { name: '家庭伦理', short: '家庭', x: -12, y: 12, r: 25, color: 'rgba(173, 57, 54, 0.4)' },
  { name: '公案审判', short: '公案', x: 0, y: 10, r: 25, color: 'rgba(38, 119, 111, 0.4)' },
  { name: '忠义家国', short: '忠义', x: 16, y: 17, r: 25, color: 'rgba(205, 151, 68, 0.4)' },
  { name: '婚恋情感', short: '婚恋', x: 14, y: -12, r: 25, color: 'rgba(174, 104, 138, 0.36)' },
])

const playSegments = computed(() => {
  const step = 360 / flatPlays.value.length
  return flatPlays.value.map((play, index) => ({
    id: `${play.genre}-${play.name}`,
    play,
    start: index * step,
    end: (index + 1) * step,
    fill: index % 2 ? 'rgba(255, 248, 235, 0.82)' : 'rgba(244, 226, 198, 0.72)',
    path: ringPath(55, 75, index * step, (index + 1) * step, 1),
  }))
})

const compositionSegments = computed(() =>
  playSegments.value.flatMap((playSegment, playIndex) => {
    const play = flatPlays.value[playIndex]
    const width = playSegment.end - playSegment.start
    const themes = normalizedThemes(play.themes)
    const themeWidth = width / themes.length

    return themes.map(([theme, ratio], themeIndex) => {
      const start = playSegment.start + themeWidth * themeIndex
      const end = start + themeWidth

      return {
        id: `${play.name}-${theme}-${themeIndex}`,
        theme,
        ratio,
        start,
        end,
        color: themeColors[theme] || '#9a8f80',
        opacity: 0.5 + ratio * 0.5,
        path: ringPath(80, 112 + ratio * 84, start, end, 0.35),
      }
    })
  }),
)

const cooccurrenceArcs = computed(() => {
  const groups = [
    { themes: ['家庭伦理', '婚恋情感'], start: 205, end: 328, strength: 0.9, color: '#ad3936' },
    { themes: ['公案审判', '忠义家国'], start: 0, end: 122, strength: 0.75, color: '#26776f' },
    { themes: ['战争征伐', '忠义家国'], start: 68, end: 248, strength: 0.68, color: '#cd9744' },
    { themes: ['神怪因果', '婚恋情感'], start: 292, end: 360, strength: 0.56, color: '#7f5539' },
  ]

  return groups.map((item, index) => ({
    id: item.themes.join('-'),
    color: item.color,
    width: 1.4 + item.strength * 4,
    opacity: 0.35 + item.strength * 0.45,
    path: arcPath(182 + index * 4, item.start, item.end),
  }))
})

const themeLegend = computed(() => Object.entries(themeColors).map(([name, color]) => ({ name, color })))

function normalizedThemes(themes) {
  const entries = Object.entries(themes)
  const total = entries.reduce((sum, [, value]) => sum + value, 0) || 1
  return entries.map(([theme, value]) => [theme, value / total])
}

function ringPath(innerRadius, outerRadius, startAngle, endAngle, gap = 0) {
  const start = startAngle + gap
  const end = endAngle - gap
  const largeArc = end - start > 180 ? 1 : 0
  const outerStart = polarPoint(outerRadius, start)
  const outerEnd = polarPoint(outerRadius, end)
  const innerEnd = polarPoint(innerRadius, end)
  const innerStart = polarPoint(innerRadius, start)

  return [
    `M ${outerStart.x} ${outerStart.y}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArc} 1 ${outerEnd.x} ${outerEnd.y}`,
    `L ${innerEnd.x} ${innerEnd.y}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${innerStart.x} ${innerStart.y}`,
    'Z',
  ].join(' ')
}

function arcPath(radius, startAngle, endAngle) {
  const start = polarPoint(radius, startAngle)
  const end = polarPoint(radius, endAngle)
  const largeArc = endAngle - startAngle > 180 ? 1 : 0
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y}`
}

function polarPoint(radius, angle) {
  const radians = ((angle - 90) * Math.PI) / 180
  return {
    x: Number((Math.cos(radians) * radius).toFixed(3)),
    y: Number((Math.sin(radians) * radius).toFixed(3)),
  }
}
</script>

<style scoped>
.rose-ring-panel {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 6px;
  height: 100%;
  min-height: 0;
}

.rose-ring {
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: visible;
}

.core-overlap circle {
  stroke: rgba(255, 248, 235, 0.72);
  stroke-width: 1.4;
  mix-blend-mode: multiply;
}

.core-overlap text {
  fill: rgba(48, 39, 32, 0.78);
  font-size: 11px;
  font-weight: 700;
  text-anchor: middle;
  dominant-baseline: middle;
  pointer-events: none;
}

.equal-play-ring path {
  stroke: rgba(104, 77, 57, 0.22);
  stroke-width: 0.8;
}

.composition-ring path {
  stroke: rgba(255, 248, 235, 0.7);
  stroke-width: 0.45;
}

.wave-ring path {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
  filter: drop-shadow(0 1px 2px rgba(61, 47, 38, 0.12));
}

.rose-legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 5px 8px;
  max-height: 42px;
  overflow: hidden;
  color: #5f5348;
  font-size: 10px;
}

.rose-legend span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.rose-legend i {
  width: 8px;
  height: 8px;
  border-radius: 2px;
}
</style>
