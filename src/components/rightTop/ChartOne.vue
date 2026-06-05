<template>
  <div class="play-chord-shell">
    <div class="play-chord-panel">
      <article v-for="(item, index) in displaySlots" :key="index" class="play-chord-card">
        <!-- 每个容器都会实例化一个 G2 官方 type: 'chord' 图表，一个图表对应一个剧本。 -->
        <div :ref="(el) => setChartRef(el, index)" class="g2-play-chord" />

        <label class="play-picker">
          <!-- 剧本选择入口：每个小块下方都能单独换剧本，换完会立刻重绘这一块的 G2 chord。 -->
          <select v-model="selectedPlayIds[index]">
            <option v-for="play in playOptions" :key="play.playId" :value="play.playId">
              {{ play.title }}
            </option>
          </select>
        </label>
      </article>
    </div>
  </div>
</template>

<script setup>
import { Chart } from '@antv/g2'
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { groupRowsByPlay, useThemeCsv } from './themeCsv'

const { rows } = useThemeCsv()

// 数据入口：
// 前端读取 backend/data/theme_analysis.csv，经由 /api/theme-analysis 接口进入这里。
// CSV 中同一个 play_id 有几行 theme，这个剧本的和弦图圆周就有几个主题分区。
const plays = computed(() => groupRowsByPlay(rows.value))

// 展示数量入口：
// 右上图一现在固定展示 4 个单剧本和弦图；后续想改数量，只改这里即可。
const PLAY_COUNT = 4

// 剧本选择状态：
// selectedPlayIds[index] 对应第 index 个小块底部下拉框当前选中的剧本。
const selectedPlayIds = ref([])

// 主题颜色入口：
// 圆周上的不同颜色/分区表示不同主题。后续 CSV 新增主题时，可在这里补色。
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
  未识别主题: '#b9a98c',
}

// G2 颜色备用入口：
// 当主题名不在 themeColors 中时，用这组颜色循环兜底。
const fallbackThemeColors = ['#5B8FF9', '#5AD8A6', '#F6BD16', '#E86452', '#6D5BD0', '#FF99C3']

// 剧目类型颜色入口：
// 内部弦/条带颜色按 play.genre 映射。一个小图代表一个剧本，所以这个剧本内的弦统一使用该剧目类型色。
const genreColors = {
  传统: '#d6aa55',
  公案: '#2f8b7d',
  神怪: '#7d6ab4',
  三国: '#cf6a4c',
  水浒: '#5d95c8',
  战争: '#b9823d',
  爱情: '#c06a96',
  宫廷: '#9c6a4e',
  汉代: '#bf7b48',
  宋代: '#7f9f64',
  明代: '#8a6ab0',
  秦代: '#c26c78',
  楚汉悲歌: '#e86452',
  公案伦理: '#2f8b7d',
  三国谋略: '#5b8ff9',
  婚恋公案: '#c06a96',
  神话爱情: '#7d6ab4',
  家国亲情: '#d8a146',
  武戏冲突: '#6d597a',
  宫廷情感: '#9c6a4e',
  生活喜剧: '#5ad8a6',
}

const chartRefs = ref([])
const chartInstances = []

const playMap = computed(() => new Map(plays.value.map((play) => [play.playId, play])))

const playOptions = computed(() =>
  plays.value
    .slice()
    .sort((a, b) => b.themes.length - a.themes.length || dominantShare(b) - dominantShare(a)),
)

const displaySlots = computed(() =>
  selectedPlayIds.value.slice(0, PLAY_COUNT).map((playId) => ({
    playId,
    play: playMap.value.get(playId),
  })),
)

// 数据变化时自动补齐选择：
// 1. CSV 加载完成后，自动挑一批代表性剧本作为默认值。
// 2. 固定补齐 4 个小块，每个小块仍可通过下方剧本下拉框单独切换。
watch(
  plays,
  () => {
    reconcileSelectedPlays()
  },
  { immediate: true },
)

watch(
  displaySlots,
  async () => {
    await renderCharts()
  },
  { deep: true, flush: 'post' },
)

onBeforeUnmount(() => destroyCharts())

// 容器引用入口：
// Vue v-for 下每个 DOM 容器单独传给 G2，确保每个剧本都有独立 chord 实例。
function setChartRef(el, index) {
  if (el) chartRefs.value[index] = el
}

function reconcileSelectedPlays() {
  if (plays.value.length === 0) return

  const validIds = new Set(plays.value.map((play) => play.playId))
  const nextIds = selectedPlayIds.value.filter((id) => validIds.has(id)).slice(0, PLAY_COUNT)
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
  chartRefs.value = chartRefs.value.slice(0, PLAY_COUNT)
}

async function renderCharts() {
  await nextTick()
  destroyCharts()

  displaySlots.value.forEach((item, index) => {
    const container = chartRefs.value[index]
    const play = item.play
    const links = play ? buildPlayLinks(play) : []
    if (!container || !play || links.length === 0) return

    const chart = new Chart({
      container,
      theme: 'classic',
      autoFit: true,
    })

    // G2 官方和弦图入口：
    // 这里使用的是官方示例同款 type: 'chord'。
    // links 的 source/target 是主题，value 是主题组合共现强度。
    chart.options({
      type: 'chord',
      autoFit: true,
      data: {
        value: {
          links,
        },
      },
      layout: {
        nodeWidthRatio: 0.055,
      },
      scale: {
        color: {
          type: 'ordinal',
          range: colorRangeForPlay(play),
        },
      },
      style: {
        labelFontSize: 8,
        labelFill: '#5f5348',
        labelFontWeight: 700,
        nodeStroke: 'rgba(255, 248, 235, 0.88)',
        nodeLineWidth: 0.8,
        linkFill: genreColor(play.genre),
        linkFillOpacity: 0.48,
        linkStroke: genreColor(play.genre),
        linkStrokeOpacity: 0.18,
      },
      tooltip: {
        items: [
          { field: 'playTitle', name: '剧本' },
          { field: 'genre', name: '剧目类型' },
          { field: 'source', name: '主题A' },
          { field: 'target', name: '主题B' },
          { field: 'value', name: '共现强度' },
        ],
      },
      interaction: [
        {
          type: 'elementHighlight',
          background: true,
        },
      ],
    })

    chart.render()
    chartInstances.push(chart)
  })
}

function destroyCharts() {
  while (chartInstances.length) {
    const chart = chartInstances.pop()
    chart.destroy()
  }
}

function pickRepresentativePlays(sourcePlays, limit) {
  const buckets = new Map()
  sourcePlays.forEach((play) => {
    const count = play.themes.length
    if (!buckets.has(count)) buckets.set(count, [])
    buckets.get(count).push(play)
  })

  const selected = []
  const selectedIds = new Set()
  const counts = Array.from(buckets.keys()).sort((a, b) => a - b)

  // 默认剧本规则：
  // 第一轮按主题数量分层抽样，让 1/2/3/4/5 个主题的剧本都有机会出现。
  counts.forEach((count) => {
    const candidates = buckets.get(count).slice().sort((a, b) => dominantShare(b) - dominantShare(a))
    candidates.slice(0, 2).forEach((play) => {
      if (selected.length >= limit || selectedIds.has(play.playId)) return
      selected.push(play)
      selectedIds.add(play.playId)
    })
  })

  // 第二轮补足：
  // 优先选主题较丰富、主主题占比较高的剧本，让默认画面更有信息量。
  sourcePlays
    .slice()
    .sort((a, b) => b.themes.length - a.themes.length || dominantShare(b) - dominantShare(a))
    .forEach((play) => {
      if (selected.length >= limit || selectedIds.has(play.playId)) return
      selected.push(play)
      selectedIds.add(play.playId)
    })

  return selected
}

function buildPlayLinks(play) {
  const themes = normalizedThemes(play)
  const links = []

  // 共现强度入口：
  // 同一剧本中的主题两两组合；value 用两个主题占比的几何均值计算。
  // 如果后端后续能提取真实“主题-主题共现次数”，可以在这里用真实共现值替换 value。
  for (let left = 0; left < themes.length; left += 1) {
    for (let right = left + 1; right < themes.length; right += 1) {
      const strength = Math.sqrt(themes[left].share * themes[right].share)
      const value = Number((strength * 100).toFixed(2))
      links.push({
        source: themes[left].name,
        target: themes[right].name,
        value,
        genre: play.genre,
        playTitle: play.title,
      })
      links.push({
        source: themes[right].name,
        target: themes[left].name,
        value: Number((value * 0.72).toFixed(2)),
        genre: play.genre,
        playTitle: play.title,
      })
    }
  }

  // 单主题兜底：
  // G2 chord 需要 link 才能渲染；只有一个主题时加一个自连接，表达“该剧本只有单一核心主题”。
  if (themes.length === 1) {
    links.push({
      source: themes[0].name,
      target: themes[0].name,
      value: Number((themes[0].share * 100).toFixed(2)),
      genre: play.genre,
      playTitle: play.title,
    })
  }

  return links
}

function normalizedThemes(play) {
  const validThemes = play.themes.filter((theme) => theme.name)
  const total = validThemes.reduce((sum, theme) => sum + Number(theme.share || 0), 0) || 1
  return validThemes.map((theme) => ({
    ...theme,
    share: Number(theme.share || 0) / total,
  }))
}

function colorRangeForPlay(play) {
  return normalizedThemes(play).map((theme) => themeColor(theme.name))
}

function dominantShare(play) {
  return Math.max(0, ...play.themes.map((theme) => Number(theme.share || 0)))
}

function themeColor(name) {
  if (themeColors[name]) return themeColors[name]
  const code = Array.from(String(name)).reduce((sum, char) => sum + char.charCodeAt(0), 0)
  return fallbackThemeColors[code % fallbackThemeColors.length]
}

function genreColor(genre) {
  return genreColors[genre] || '#d6aa55'
}
</script>

<style scoped>
.play-chord-shell {
  height: 100%;
  min-height: 0;
}

.play-picker {
  display: block;
  min-width: 0;
}

.play-picker select {
  width: 100%;
  height: 24px;
  min-width: 0;
  border: 1px solid rgba(95, 83, 72, 0.18);
  border-radius: 6px;
  color: #5f5348;
  font-size: 11px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.72);
}

.play-chord-panel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(2, minmax(0, 1fr));
  gap: 6px;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.play-chord-card {
  display: grid;
  grid-template-rows: minmax(0, 1fr) 24px;
  gap: 3px;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.24);
}

.g2-play-chord {
  width: 100%;
  height: 100%;
  min-height: 0;
}
</style>
