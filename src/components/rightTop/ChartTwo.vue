<template>
  <div class="upset-panel">
    <svg class="upset-chart" viewBox="0 0 560 360" role="img" aria-label="跨剧本主题组合UpSet图">
      <g class="top-bars">
        <line x1="132" y1="112" x2="542" y2="112" />
        <g v-for="(combo, index) in topCombos" :key="combo.key">
          <rect
            :x="comboX(index) - barWidth / 2"
            :y="112 - combo.barHeight"
            :width="barWidth"
            :height="combo.barHeight"
            :fill="combo.color"
            rx="2"
          />
          <title>{{ combo.label }}：{{ combo.count }} 个剧本</title>
        </g>
      </g>

      <g class="set-bars">
        <g v-for="(theme, index) in themes" :key="theme.name">
          <rect
            :x="18"
            :y="matrixY(index) - 6"
            :width="theme.barWidth"
            height="10"
            rx="2"
          />
          <text class="theme-label" :x="116" :y="matrixY(index) + 4">{{ theme.name }}</text>
          <title>{{ theme.name }}：{{ theme.count }} 个剧本</title>
        </g>
      </g>

      <g class="matrix">
        <g v-for="(combo, comboIndex) in topCombos" :key="`matrix-${combo.key}`">
          <line
            v-if="combo.themeIndexes.length > 1"
            :x1="comboX(comboIndex)"
            :x2="comboX(comboIndex)"
            :y1="matrixY(Math.min(...combo.themeIndexes))"
            :y2="matrixY(Math.max(...combo.themeIndexes))"
            :stroke="combo.color"
          />
          <circle
            v-for="(theme, themeIndex) in themes"
            :key="`${combo.key}-${theme.name}`"
            :cx="comboX(comboIndex)"
            :cy="matrixY(themeIndex)"
            :r="combo.themeIndexes.includes(themeIndex) ? 4.5 : 2.3"
            :fill="combo.themeIndexes.includes(themeIndex) ? combo.color : 'rgba(88, 68, 51, 0.16)'"
          />
        </g>
      </g>

      <g class="axis-labels">
        <text x="132" y="18">组合剧本数</text>
        <text x="18" y="338">单主题剧本数</text>
        <text x="542" y="338" text-anchor="end">每列为一种主题组合</text>
      </g>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { groupRowsByPlay, useThemeCsv } from './themeCsv'

const { rows } = useThemeCsv()

// UpSet 可调参数：
// MIN_THEME_SHARE 控制一个主题进入某个剧本组合的最低占比。
// TOP_COMBO_LIMIT 控制最多显示多少个主题组合列。
// 如果后期后端已经给出每个剧本的主题标签，可只保留这些参数调筛选强度。
const MIN_THEME_SHARE = 0.16
const TOP_COMBO_LIMIT = 26

const themePalette = ['#d65f5f', '#8c5fb0', '#2f8b7d', '#d8a146', '#5d95c8', '#8fbf63', '#c06a96', '#9c6a4e']
const barWidth = 9

const plays = computed(() => groupRowsByPlay(rows.value))

const themes = computed(() => {
  const counts = new Map()
  plays.value.forEach((play) => {
    combinationThemes(play).forEach((theme) => counts.set(theme, (counts.get(theme) || 0) + 1))
  })

  const max = Math.max(1, ...counts.values())
  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([name, count], index) => ({
      name,
      count,
      color: themePalette[index % themePalette.length],
      barWidth: 12 + (count / max) * 86,
    }))
})

const topCombos = computed(() => {
  const themeIndexMap = new Map(themes.value.map((theme, index) => [theme.name, index]))
  const comboCounts = new Map()

  plays.value.forEach((play) => {
    const selected = combinationThemes(play).filter((theme) => themeIndexMap.has(theme))
    if (!selected.length) return

    // 数据入口说明：
    // 每个 play 会根据 CSV 中 share >= MIN_THEME_SHARE 的主题形成一个组合。
    // key 就是 UpSet 点阵中一列亮起的主题集合。
    const key = selected.sort((a, b) => themeIndexMap.get(a) - themeIndexMap.get(b)).join('|')
    comboCounts.set(key, (comboCounts.get(key) || 0) + 1)
  })

  const max = Math.max(1, ...comboCounts.values())
  return Array.from(comboCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, TOP_COMBO_LIMIT)
    .map(([key, count], index) => {
      const names = key.split('|')
      const themeIndexes = names.map((name) => themeIndexMap.get(name)).filter(Number.isFinite)
      return {
        key,
        label: names.join(' + '),
        count,
        themeIndexes,
        color: themePalette[themeIndexes[0] % themePalette.length] || '#d8a146',
        barHeight: 6 + (count / max) * 88,
        index,
      }
    })
})

function combinationThemes(play) {
  const selected = play.themes.filter((theme) => theme.share >= MIN_THEME_SHARE).map((theme) => theme.name)
  return selected.length ? selected : play.themes.slice(0, 2).map((theme) => theme.name)
}

function comboX(index) {
  const width = 410
  const count = Math.max(1, topCombos.value.length - 1)
  return 132 + (index / count) * width
}

function matrixY(index) {
  return 138 + index * 23
}
</script>

<style scoped>
.upset-panel {
  height: 100%;
  min-height: 0;
}

.upset-chart {
  width: 100%;
  height: 100%;
}

.top-bars line {
  stroke: rgba(88, 68, 51, 0.24);
}

.set-bars rect {
  fill: rgba(48, 39, 32, 0.78);
}

.theme-label {
  fill: #405a7a;
  font-size: 11px;
  font-weight: 800;
  text-anchor: end;
}

.matrix line {
  stroke-width: 2;
  stroke-linecap: round;
  opacity: 0.8;
}

.axis-labels text {
  fill: #5f5348;
  font-size: 10px;
  font-weight: 700;
}
</style>
