<template>
  <div class="play-chord-shell">
    <div v-if="loading" class="theme-state">主题数据加载中...</div>
    <div v-else-if="error" class="theme-state theme-state--error">{{ error }}</div>

    <div v-else class="play-chord-panel" :class="{ 'is-focused': focusedPlayId }">
      <article
        v-for="(item, index) in displaySlots"
        :key="item.playId || index"
        class="play-chord-card"
        :class="{ 'is-focus-card': focusedPlayId && index === 0 }"
      >
        <div v-if="focusedPlayId && index === 0 && item.play" class="focus-tree-shell">
          <svg class="relation-theme-tree" viewBox="0 0 360 330" role="img" aria-label="角色关系主题树状图">
            <g class="tree-root-links">
              <path v-for="group in relationThemeTree(item.play).groups" :key="`root-${group.id}`" :d="rootRelationPath(group)" />
            </g>

            <g class="tree-theme-links">
              <template v-for="group in relationThemeTree(item.play).groups" :key="`themes-${group.id}`">
                <path
                  v-for="themeId in group.themeIds"
                  :key="`${group.id}-${themeId}`"
                  :d="relationThemePath(group, relationThemeTree(item.play).themeById.get(themeId))"
                  :class="{ active: isActiveTreeRelation(group.id), dimmed: hasActiveTreeRelation() && !isActiveTreeRelation(group.id) }"
                />
              </template>
            </g>

            <g class="tree-root-node" :transform="`translate(${relationThemeTree(item.play).root.x},${relationThemeTree(item.play).root.y})`">
              <circle r="27" />
              <text class="root-name" text-anchor="middle" y="3">{{ relationThemeTree(item.play).root.name }}</text>
            </g>

            <g
              v-for="group in relationThemeTree(item.play).groups"
              :key="group.id"
              class="tree-relation-group"
              :class="{ active: isActiveTreeRelation(group.id), dimmed: hasActiveTreeRelation() && !isActiveTreeRelation(group.id) }"
              :transform="`translate(${group.x},${group.y})`"
              @mouseenter="hoveredTreeRelationId = group.id"
              @mouseleave="hoveredTreeRelationId = ''"
              @click="selectedTreeRelationId = selectedTreeRelationId === group.id ? '' : group.id"
            >
              <rect class="group-card" :x="-group.width / 2" y="-29" :width="group.width" height="62" rx="15" />
              <rect class="relation-label-bg" x="-28" y="-39" width="56" height="19" rx="10" />
              <text class="relation-type" text-anchor="middle" y="-26">{{ group.type }}</text>
              <g
                v-for="person in group.people"
                :key="person.id"
                class="relation-person-node"
                :transform="`translate(${person.x},${person.y})`"
              >
                <circle class="person-core" r="14" />
                <text class="relation-person" text-anchor="middle" y="3.5">{{ person.name }}</text>
              </g>
            </g>

            <g
              v-for="theme in relationThemeTree(item.play).themes"
              :key="theme.id"
              class="tree-theme-node"
              :class="{ active: isTreeThemeActive(theme.id), dimmed: hasActiveTreeRelation() && !isTreeThemeActive(theme.id) }"
              :transform="`translate(${theme.x},${theme.y})`"
            >
              <rect class="theme-card" :x="-theme.width / 2" y="-24" :width="theme.width" height="48" rx="10" />
              <circle class="theme-marker" :cx="theme.trackX" cy="-10" r="3.5" :fill="themeColor(theme.name)" />
              <text class="theme-name" text-anchor="start" :x="theme.labelX" y="-6.5">{{ theme.name }}</text>
              <rect class="theme-track" :x="theme.trackX" y="5" :width="theme.trackWidth" height="5" rx="2.5" />
              <rect
                class="theme-progress"
                :x="theme.trackX"
                y="5"
                :width="Math.max(4, theme.trackWidth * theme.share)"
                height="5"
                rx="2.5"
                :fill="themeColor(theme.name)"
              />
              <text class="theme-percent" text-anchor="end" :x="theme.percentX" y="20">{{ formatPercent(theme.share) }}</text>
            </g>
          </svg>
        </div>

        <div v-else class="play-visual-zone">
          <div :ref="(el) => setChartRef(el, index)" class="g2-play-chord" />
        </div>

        <button
          v-if="focusedPlayId && index === 0"
          class="play-focus-close"
          type="button"
          aria-label="关闭联动主题图"
          @click="clearFocusedPlay"
        >
          <span aria-hidden="true">×</span>
        </button>

        <label v-if="!focusedPlayId" class="play-picker">
          <PlaySelect
            :model-value="item.playId"
            :options="playSelectOptions"
            :max-visible="5"
            :disabled="Boolean(focusedPlayId)"
            @change="handlePlayPickerChange(index, $event)"
          />
        </label>
      </article>
    </div>
  </div>
</template>

<script setup>
import { Chart } from '@antv/g2'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import PlaySelect from '../PlaySelect.vue'
import { clearLinkageFocus, linkageState, loadLinkageData } from '../../services/linkageStore'
import { loadPlayCatalog } from '../../services/playCatalog'

const THEME_CSV_URL = `${import.meta.env.BASE_URL}数据表合集/3/theme_analysis.csv`
const KAI_FONT = '"STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif'
const PLAY_COUNT = 4

const rows = ref([])
const loading = ref(true)
const error = ref('')

const selectedPlayIds = ref([])
const chartRefs = ref([])
const chartInstances = []
const hoveredTreeRelationId = ref('')
const selectedTreeRelationId = ref('')
const playCatalog = ref([])

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

const fallbackThemeColors = [
  '#5B8FF9',
  '#5AD8A6',
  '#F6BD16',
  '#E86452',
  '#6D5BD0',
  '#FF99C3',
]

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

const plays = computed(() => groupRowsByPlay(rows.value))

const playMap = computed(() => new Map(plays.value.map((play) => [play.playId, play])))

const rankedPlays = computed(() =>
  plays.value
    .slice()
    .sort((a, b) => b.themes.length - a.themes.length || dominantShare(b) - dominantShare(a)),
)
const playSelectOptions = computed(() => {
  if (playCatalog.value.length) {
    const localPlayIdByTitle = new Map(plays.value.map((play) => [play.title, play.playId]))
    return playCatalog.value.map((play) => ({
      value: localPlayIdByTitle.get(play.title) || play.id,
      label: play.title,
    }))
  }
  return rankedPlays.value.map((play) => ({ value: play.playId, label: play.title }))
})

const focusedPlayId = computed(() => {
  if (!isLinkageTriggerSource()) return ''
  return playMap.value.has(linkageState.selectedPlayId) ? linkageState.selectedPlayId : ''
})

const displaySlots = computed(() => {
  if (focusedPlayId.value) {
    return [
      {
        playId: focusedPlayId.value,
        play: playMap.value.get(focusedPlayId.value),
      },
    ]
  }

  return selectedPlayIds.value.slice(0, PLAY_COUNT).map((playId) => ({
    playId,
    play: playMap.value.get(playId),
  }))
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

watch(
  displaySlots,
  async () => {
    await renderCharts()
  },
  { deep: true, flush: 'post' },
)

watch(
  () => linkageState.selectedThemeIds.slice(),
  async () => {
    await renderCharts()
  },
  { deep: true, flush: 'post' },
)

watch(
  () => [focusedPlayId.value, linkageState.selectedCharacterId, linkageState.selectedTrade],
  () => {
    hoveredTreeRelationId.value = ''
    selectedTreeRelationId.value = ''
  },
)

onBeforeUnmount(() => {
  destroyCharts()
})

async function loadThemeCsv() {
  loading.value = true
  error.value = ''

  try {
    const [linkageData, catalog] = await Promise.all([
      loadLinkageData(),
      loadPlayCatalog().catch(() => []),
    ])
    playCatalog.value = catalog
    if (linkageData.plays?.length) {
      rows.value = linkageData.plays.flatMap((play) => (play.themes || []).map((theme) => normalizeLinkageTheme(play, theme)))
      return
    }

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

function normalizeLinkageTheme(play, theme) {
  return {
    play_id: play.play_id,
    title: play.title,
    genre: play.themes?.[0]?.theme || '传统',
    collection: '五剧本联动',
    theme_id: theme.theme_id,
    theme: theme.theme,
    score: Number(theme.score) || 0,
    share: Number(theme.share) || 0,
    rank: Number(theme.rank) || 0,
  }
}

function setChartRef(el, index) {
  if (el) {
    chartRefs.value[index] = el
  }
}

function handlePlayPickerChange(index, value) {
  const playId = String(value || '')
  if (!playId) return

  selectedPlayIds.value[index] = playId
}

function clearFocusedPlay() {
  clearLinkageFocus('rightBottomClear')
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

  rankedPlays.value.forEach((play) => {
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
  if (focusedPlayId.value) return

  displaySlots.value.forEach((item, index) => {
    const container = chartRefs.value[index]
    const play = item.play
    const links = play ? buildPlayLinks(play) : []
    const hasThemeFocus = isLinkageTriggerSource() && linkageState.selectedThemeIds.length > 0

    if (!container || !play || !links.length) return

    const chartSizing = getChordChartSizing(container, Boolean(focusedPlayId.value && index === 0))

    const chart = new Chart({
      container,
      theme: 'classic',
      autoFit: true,
    })

    chart.options({
      type: 'chord',
      autoFit: true,
      paddingTop: chartSizing.paddingTop,
      paddingRight: chartSizing.paddingX,
      paddingBottom: chartSizing.paddingBottom,
      paddingLeft: chartSizing.paddingX,
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
        labelFontFamily: KAI_FONT,
        labelFontSize: chartSizing.labelFontSize,
        labelFill: (datum) => (hasThemeFocus && isFocusedChordDatum(datum, play) ? '#8b1f1b' : '#4f3a2b'),
        labelFontWeight: (datum) => (hasThemeFocus && isFocusedChordDatum(datum, play) ? 1000 : 800),
        labelConnector: true,
        labelConnectorLength: 5,
        labelConnectorLength2: 5,
        labelConnectorDistance: 0,

        nodeStroke: (datum) => (hasThemeFocus && isFocusedChordDatum(datum, play) ? '#8b1f1b' : 'rgba(255, 248, 235, 0.88)'),
        nodeLineWidth: (datum) => (hasThemeFocus && isFocusedChordDatum(datum, play) ? 2.4 : 0.8),
        nodeFillOpacity: (datum) => (hasThemeFocus ? (isFocusedChordDatum(datum, play) ? 1 : 0.32) : 0.95),

        linkFill: (datum) => (hasThemeFocus && datum.isFocus ? '#b23b32' : genreColor(play.genre)),
        linkFillOpacity: (datum) => (hasThemeFocus ? (datum.isFocus ? 0.82 : 0.1) : 0.48),
        linkStroke: (datum) => (hasThemeFocus && datum.isFocus ? '#7a1f1b' : genreColor(play.genre)),
        linkStrokeOpacity: (datum) => (hasThemeFocus ? (datum.isFocus ? 0.68 : 0.05) : 0.18),
      },
      tooltip: false,
      interaction: {
        elementHighlight: {
          background: true,
        },
        tooltip: false,
      },
    })

    chart.render()
    chartInstances.push(chart)
  })
}

function getChordChartSizing(container, isFocused = false) {
  const rect = container.getBoundingClientRect()
  const minSide = Math.min(rect.width || 0, rect.height || 0)

  if (isFocused) {
    return {
      labelFontSize: minSide < 180 ? 11 : 12.5,
      paddingX: 0,
      paddingTop: 0,
      paddingBottom: 0,
    }
  }

  if (minSide < 120) {
    return {
      labelFontSize: 10.5,
      paddingX: 14,
      paddingTop: 10,
      paddingBottom: 8,
    }
  }

  if (minSide < 170) {
    return {
      labelFontSize: 11,
      paddingX: 16,
      paddingTop: 12,
      paddingBottom: 9,
    }
  }

  return {
    labelFontSize: 12,
    paddingX: 22,
    paddingTop: 16,
    paddingBottom: 11,
  }
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

    if (!buckets.has(count)) {
      buckets.set(count, [])
    }

    buckets.get(count).push(play)
  })

  const selected = []
  const selectedIds = new Set()
  const counts = Array.from(buckets.keys()).sort((a, b) => a - b)

  counts.forEach((count) => {
    const candidates = buckets
      .get(count)
      .slice()
      .sort((a, b) => dominantShare(b) - dominantShare(a))

    candidates.slice(0, 2).forEach((play) => {
      if (selected.length >= limit) return
      if (selectedIds.has(play.playId)) return

      selected.push(play)
      selectedIds.add(play.playId)
    })
  })

  sourcePlays
    .slice()
    .sort((a, b) => b.themes.length - a.themes.length || dominantShare(b) - dominantShare(a))
    .forEach((play) => {
      if (selected.length >= limit) return
      if (selectedIds.has(play.playId)) return

      selected.push(play)
      selectedIds.add(play.playId)
    })

  return selected
}

function buildPlayLinks(play) {
  const themes = normalizedThemes(play)
  const links = []

  for (let left = 0; left < themes.length; left += 1) {
    for (let right = left + 1; right < themes.length; right += 1) {
      const strength = Math.sqrt(themes[left].share * themes[right].share)
      const value = Number((strength * 100).toFixed(2))

      links.push({
        source: themes[left].name,
        target: themes[right].name,
        sourceThemeId: themes[left].themeId,
        targetThemeId: themes[right].themeId,
        isFocus: isFocusedTheme(themes[left].themeId) || isFocusedTheme(themes[right].themeId),
        value,
        genre: play.genre,
        playTitle: play.title,
      })

      links.push({
        source: themes[right].name,
        target: themes[left].name,
        sourceThemeId: themes[right].themeId,
        targetThemeId: themes[left].themeId,
        isFocus: isFocusedTheme(themes[right].themeId) || isFocusedTheme(themes[left].themeId),
        value: Number((value * 0.72).toFixed(2)),
        genre: play.genre,
        playTitle: play.title,
      })
    }
  }

  if (themes.length === 1) {
    links.push({
      source: themes[0].name,
      target: themes[0].name,
      sourceThemeId: themes[0].themeId,
      targetThemeId: themes[0].themeId,
      isFocus: isFocusedTheme(themes[0].themeId),
      value: Number((themes[0].share * 100).toFixed(2)),
      genre: play.genre,
      playTitle: play.title,
    })
  }

  return links
}

function isFocusedTheme(themeId) {
  return isLinkageTriggerSource() && linkageState.selectedThemeIds.includes(themeId)
}

function isFocusedChordDatum(datum, play) {
  if (!isLinkageTriggerSource() || !linkageState.selectedThemeIds.length) return false
  if (datum?.isFocus) return true

  const focusIds = new Set(linkageState.selectedThemeIds)
  const focusNames = new Set(
    normalizedThemes(play)
      .filter((theme) => focusIds.has(theme.themeId))
      .map((theme) => theme.name),
  )
  const values = new Set()
  collectThemeDatumValues(datum, values)

  return Array.from(values).some((value) => focusIds.has(value) || focusNames.has(value))
}

function collectThemeDatumValues(value, values) {
  if (value === null || value === undefined) return

  if (typeof value !== 'object') {
    values.add(text(value))
    return
  }

  ;['themeId', 'sourceThemeId', 'targetThemeId', 'id', 'key', 'name', 'theme', 'source', 'target'].forEach((key) => {
    if (value[key] !== undefined) values.add(text(value[key]))
  })

  if (value.data && value.data !== value) {
    collectThemeDatumValues(value.data, values)
  }
}

function text(value) {
  return String(value ?? '').trim()
}

function isLinkageTriggerSource() {
  return linkageState.source === 'leftTopIcon' || linkageState.source === 'rightTopNode'
}

function focusedCharacterCount(play) {
  const fullPlay = linkagePlay(play)
  if (!fullPlay) return 0
  const trade = normalizeTrade(linkageState.selectedTrade)
  if (!trade) return linkageState.selectedCharacterId ? 1 : fullPlay.characters?.length || 0
  return (
    fullPlay.characters?.filter((character) => {
      return (
        normalizeTrade(character.standard_trade || character.trade) === trade ||
        normalizeTrade(character.major_trade) === trade
      )
    }).length || 0
  )
}

function focusedSceneLabel(play) {
  const scene = focusedScene(play)
  return scene?.scene_label || scene?.stage_type || '-'
}

function focusedSceneText(play) {
  const scene = focusedScene(play)
  if (!scene) return '当前联动暂未匹配到具体场次。'
  const stage = scene.stage_type ? `${scene.stage_type} · ` : ''
  const summary = scene.summary || '暂无场景摘要'
  return `${stage}${summary}`
}

function focusedScene(play) {
  const fullPlay = linkagePlay(play)
  return fullPlay?.scenes?.find((scene) => scene.scene_id === linkageState.selectedSceneId) || null
}

function linkagePlay(play) {
  return linkageState.plays.find((item) => item.play_id === play?.playId) || null
}

function relationThemeTree(play) {
  const fullPlay = linkagePlay(play)
  const characters = fullPlay?.characters || []
  const allRelations = fullPlay?.relations || []
  const root = treeRootCharacter(fullPlay)
  const visibleThemes = normalizedThemes(play).slice(0, 6)
  const compactThemes = visibleThemes.length > 5
  const themes = visibleThemes
    .map((theme, index, source) => ({
      id: theme.themeId,
      name: theme.name,
      share: theme.share,
      x: spacedPosition(index, source.length, compactThemes ? 30 : 43, compactThemes ? 330 : 317),
      // 同层主题上下错排，给相邻主题卡片留出文字空间。
      y: index % 2 === 0 ? 246 : 300,
      width: compactThemes ? 60 : 82,
      trackX: compactThemes ? -20 : -30,
      trackWidth: compactThemes ? 40 : 60,
      labelX: compactThemes ? -12 : -22,
      percentX: compactThemes ? 20 : 30,
    }))
  const themeById = new Map(themes.map((theme) => [theme.id, theme]))
  const characterById = new Map(characters.map((character) => [character.character_id, character]))

  const relations = allRelations
    .filter(
      (relation) =>
        relation.source_character_id === root.character_id ||
        relation.target_character_id === root.character_id,
    )
    .sort((a, b) => Number(b.weight || 0) - Number(a.weight || 0))
    .slice(0, 6)
    .map((relation) => {
      const otherId =
        relation.source_character_id === root.character_id
          ? relation.target_character_id
          : relation.source_character_id
      const other = characterById.get(otherId)
      return {
        id: relation.relation_id,
        type: relation.relation_label || relation.relation_type || '人物互动',
        person: other?.name || (relation.source_character_id === root.character_id ? relation.target : relation.source),
        weight: Number(relation.weight || 0),
        themeIds: inferredRelationThemes(root, other, relation, themeById),
      }
    })
  const grouped = new Map()
  relations.forEach((relation) => {
    const current = grouped.get(relation.type) || {
      id: `group-${relation.type}`,
      type: relation.type,
      people: [],
      themeIds: new Set(),
      totalWeight: 0,
    }
    current.people.push({
      id: relation.id,
      name: relation.person,
      weight: relation.weight,
    })
    relation.themeIds.forEach((id) => current.themeIds.add(id))
    current.totalWeight += relation.weight
    grouped.set(relation.type, current)
  })

  const groups = Array.from(grouped.values())
    .map((group) => ({
      ...group,
      themeIds: Array.from(group.themeIds),
      width: Math.max(72, 42 + group.people.length * 34),
      themeCenter:
        Array.from(group.themeIds)
          .map((id) => themeById.get(id)?.x)
          .filter(Number.isFinite)
          .reduce((sum, value, index, values) => sum + value / values.length, 0) || 180,
    }))
    .sort((a, b) => a.themeCenter - b.themeCenter || b.totalWeight - a.totalWeight)
  const totalWidth = groups.reduce((sum, group) => sum + group.width, 0) + Math.max(0, groups.length - 1) * 8
  let cursor = (360 - totalWidth) / 2
  groups.forEach((group) => {
    group.x = cursor + group.width / 2
    group.y = 140
    group.people = group.people.map((person, index, source) => ({
      ...person,
      x: spacedPosition(index, source.length, -group.width / 2 + 23, group.width / 2 - 23),
      y: index % 2 === 0 ? 3 : 19,
    }))
    cursor += group.width + 8
  })

  return {
    root: {
      id: root.character_id,
      name: root.name || '核心角色',
      trade: root.standard_trade || root.trade || root.major_trade || '未定',
      x: 180,
      y: 42,
    },
    relations,
    groups,
    themes,
    themeById,
  }
}

function treeRootCharacter(play) {
  const characters = play?.characters || []
  const selected = characters.find(
    (character) => character.character_id === linkageState.selectedCharacterId,
  )
  if (selected) return selected

  const trade = normalizeTrade(linkageState.selectedTrade)
  const tradeCharacters = trade
    ? characters.filter((character) =>
        [character.standard_trade, character.trade, character.major_trade]
          .map(normalizeTrade)
          .includes(trade),
      )
    : []

  return [...tradeCharacters, ...characters]
    .filter(
      (character, index, source) =>
        source.findIndex((item) => item.character_id === character.character_id) === index,
    )
    .sort(
      (a, b) =>
        Number(b.importance || 0) - Number(a.importance || 0) ||
        Number(a.network_rank || 999) - Number(b.network_rank || 999),
    )[0] || { character_id: '', name: '核心角色' }
}

function inferredRelationThemes(root, other, relation, themeById) {
  const rootThemes = new Set(root?.linked_theme_ids || [])
  const otherThemes = new Set(other?.linked_theme_ids || [])
  const result = new Set([...rootThemes].filter((id) => otherThemes.has(id)))
  const relationType = text(relation.relation_type)

  if (relationType === 'power' && themeById.has('theme_power')) result.add('theme_power')
  if (relationType === 'command') {
    if (themeById.has('theme_power')) result.add('theme_power')
    if (themeById.has('theme_war')) result.add('theme_war')
  }
  if (relationType === 'conflict') {
    otherThemes.forEach((id) => result.add(id))
    rootThemes.forEach((id) => result.add(id))
  }

  if (!result.size) {
    otherThemes.forEach((id) => result.add(id))
    rootThemes.forEach((id) => result.add(id))
  }

  return Array.from(result).filter((id) => themeById.has(id))
}

function spacedPosition(index, count, start, end) {
  if (count <= 1) return (start + end) / 2
  return start + ((end - start) * index) / (count - 1)
}

function rootRelationPath(relation) {
  return `M 180 69 C 180 92, ${relation.x} 88, ${relation.x} ${relation.y - 39}`
}

function relationThemePath(relation, theme) {
  if (!theme) return ''
  const startY = relation.y + 33
  const endY = theme.y - 24
  const middleY = startY + (endY - startY) * 0.56
  return `M ${relation.x} ${startY} C ${relation.x} ${middleY}, ${theme.x} ${middleY}, ${theme.x} ${endY}`
}

function activeTreeRelationId() {
  return hoveredTreeRelationId.value || selectedTreeRelationId.value
}

function hasActiveTreeRelation() {
  return Boolean(activeTreeRelationId())
}

function isActiveTreeRelation(relationId) {
  return activeTreeRelationId() === relationId
}

function isTreeThemeActive(themeId) {
  const activeId = activeTreeRelationId()
  if (!activeId) return true
  const focusedPlay = playMap.value.get(focusedPlayId.value)
  const relation = relationThemeTree(focusedPlay).groups.find((item) => item.id === activeId)
  return relation?.themeIds.includes(themeId) || false
}

function roleCarriers(play) {
  const fullPlay = linkagePlay(play)
  const characters = fullPlay?.characters || []
  const relations = fullPlay?.relations || []
  if (!characters.length) return []

  const maxScene = Math.max(1, ...characters.map((item) => Number(item.scene_count || 0)))
  const maxSpeech = Math.max(1, ...characters.map((item) => Number(item.speech_count || 0)))
  const relationStrength = new Map()

  relations.forEach((relation) => {
    const weight = Number(relation.weight || 0)
    relationStrength.set(
      relation.source_character_id,
      (relationStrength.get(relation.source_character_id) || 0) + weight,
    )
    relationStrength.set(
      relation.target_character_id,
      (relationStrength.get(relation.target_character_id) || 0) + weight,
    )
  })

  const maxRelation = Math.max(1, ...relationStrength.values())
  const selectedThemes = new Set(linkageState.selectedThemeIds)

  return characters
    .map((character) => {
      const importance = Number(character.importance || 0)
      const sceneRatio = Number(character.scene_count || 0) / maxScene
      const speechRatio = Number(character.speech_count || 0) / maxSpeech
      const relationRatio = (relationStrength.get(character.character_id) || 0) / maxRelation
      const linkedIds = character.linked_theme_ids || []
      const themeMatch = linkedIds.some((id) => selectedThemes.has(id))
      const isSelected = character.character_id === linkageState.selectedCharacterId
      return {
        id: character.character_id,
        name: character.name,
        trade: character.standard_trade || character.trade || character.major_trade || '未定',
        level: character.role_level_label || '角色',
        themes: (character.linked_themes || []).slice(0, 2),
        score: Math.round(
          Math.min(1, importance * 0.55 + sceneRatio * 0.2 + speechRatio * 0.15 + relationRatio * 0.1) * 100,
        ),
        focusOrder: isSelected ? 2 : themeMatch ? 1 : 0,
      }
    })
    .sort((a, b) => b.focusOrder - a.focusOrder || b.score - a.score)
    .slice(0, 3)
    .map((item, index) => ({ ...item, rank: index + 1 }))
}

function relationMechanisms(play) {
  const fullPlay = linkagePlay(play)
  const relations = fullPlay?.relations || []
  const characters = fullPlay?.characters || []
  const selectedTrade = normalizeTrade(linkageState.selectedTrade)
  const focusedIds = new Set(
    characters
      .filter((character) => {
        if (character.character_id === linkageState.selectedCharacterId) return true
        if (!selectedTrade) return false
        return [character.standard_trade, character.trade, character.major_trade]
          .map(normalizeTrade)
          .includes(selectedTrade)
      })
      .map((character) => character.character_id),
  )

  const focusedRelations = focusedIds.size
    ? relations.filter(
        (relation) =>
          focusedIds.has(relation.source_character_id) || focusedIds.has(relation.target_character_id),
      )
    : []
  const source = focusedRelations.length >= 2 ? focusedRelations : relations
  const grouped = new Map()

  source.forEach((relation) => {
    const name = relation.relation_label || relation.relation_type || '人物互动'
    const current = grouped.get(name) || { name, count: 0, weight: 0 }
    current.count += 1
    current.weight += Number(relation.weight || 0)
    grouped.set(name, current)
  })

  const rows = Array.from(grouped.values())
    .sort((a, b) => b.count - a.count || b.weight - a.weight)
    .slice(0, 5)
  const maxCount = Math.max(1, ...rows.map((item) => item.count))

  return rows.map((item) => ({
    ...item,
    percent: Math.max(8, Math.round((item.count / maxCount) * 100)),
  }))
}

function narrativeStages(play) {
  const fullPlay = linkagePlay(play)
  const scenes = fullPlay?.scenes || []
  const order = ['开端', '发展', '高潮', '转折', '结局']
  const grouped = new Map(order.map((name) => [name, []]))

  scenes.forEach((scene) => {
    const name = order.includes(scene.stage_type) ? scene.stage_type : '发展'
    grouped.get(name).push(scene)
  })

  return order.map((name) => {
    const items = grouped.get(name)
    const average = items.length
      ? items.reduce((sum, scene) => sum + Number(scene.metrics?.plot_strength || 0), 0) / items.length
      : 0
    return {
      name,
      count: items.length,
      value: Math.round(average * 100),
      percent: Math.max(items.length ? 8 : 2, Math.round(average * 100)),
      active: items.some((scene) => scene.scene_id === linkageState.selectedSceneId),
    }
  })
}

function themeSummary(play) {
  return normalizedThemes(play)
    .slice()
    .sort((a, b) => {
      const rankA = Number.isFinite(a.rank) && a.rank > 0 ? a.rank : 999
      const rankB = Number.isFinite(b.rank) && b.rank > 0 ? b.rank : 999
      return b.share - a.share || rankA - rankB
    })
    .slice(0, 6)
}

function formatPercent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`
}

function normalizeTrade(value) {
  return text(value).replace(/[（(].*?[）)]/g, '')
}

function normalizedThemes(play) {
  const validThemes = play.themes.filter((theme) => theme.name)
  const total = validThemes.reduce((sum, theme) => sum + Number(theme.share || 0), 0) || 1

  return validThemes.map((theme) => ({
    ...theme,
    themeId: text(theme.themeId || theme.theme_id || theme.id || theme.name),
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

function parseThemeCsv(text) {
  const cleanText = String(text || '').trim()

  if (!cleanText) return []

  const [headerLine, ...lines] = cleanText.split(/\r?\n/)
  const headers = splitCsvLine(headerLine).map((header) => header.trim())

  return lines
    .filter((line) => line.trim())
    .map((line) => {
      const values = splitCsvLine(line)
      const row = Object.fromEntries(headers.map((header, index) => [header, values[index] || '']))

      return {
        play_id: String(row.play_id || '').trim(),
        title: String(row.title || '').trim(),
        genre: String(row.genre || '').trim(),
        collection: String(row.collection || '').trim(),
        theme_id: String(row.theme_id || '').trim(),
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
      themeId: row.theme_id,
      name: row.theme,
      score: row.score,
      share: row.share,
      rank: row.rank,
    })
  })

  return Array.from(map.values()).map((play) => ({
    ...play,
    themes: play.themes
      .slice()
      .sort((a, b) => {
        const rankA = Number.isFinite(a.rank) && a.rank > 0 ? a.rank : 999
        const rankB = Number.isFinite(b.rank) && b.rank > 0 ? b.rank : 999

        return rankA - rankB || b.share - a.share
      }),
  }))
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
</script>

<style scoped>
.play-chord-shell {
  width: 100%;
  height: 100%;
  min-height: 0;
  background: #FBF6E9;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
}

.play-chord-panel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(2, minmax(0, 1fr));
  gap: 0;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: #FBF6E9;
}

.play-chord-card {
  position: relative;
  display: grid;
  grid-template-rows: minmax(0, 1fr) 24px;
  gap: 2px;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border: none;
  border-radius: 0;
  background: #FBF6E9;
  box-shadow: none;
}

.play-chord-card.is-focus-card {
  display: grid;
  grid-template-rows: minmax(0, 1fr);
  gap: 0;
}

.play-visual-zone {
  min-width: 0;
  min-height: 0;
}

.play-visual-zone.has-theme-dashboard {
  position: relative;
  inset: auto;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  height: auto;
  padding: 0;
}

.play-focus-close {
  position: absolute;
  top: 6px;
  right: 8px;
  z-index: 2;
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 1px solid rgba(139, 42, 37, 0.3);
  border-radius: 50%;
  background: rgba(255, 252, 244, 0.9);
  color: #8b2a25;
  cursor: pointer;
}

.play-focus-close span {
  display: block;
  width: 14px;
  height: 14px;
  font-family: Arial, sans-serif;
  font-size: 18px;
  font-weight: 700;
  line-height: 13px;
  text-align: center;
}

.play-chord-panel.is-focused {
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
}

.g2-play-chord {
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: visible;
}

.play-chord-panel.is-focused .g2-play-chord {
  position: relative;
  inset: auto;
  min-width: 0;
  min-height: 0;
}

.focus-tree-shell {
  position: relative;
  min-width: 0;
  min-height: 0;
  height: 100%;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 7%, rgba(196, 153, 83, 0.09), transparent 24%),
    #fbf6e9;
}

.relation-theme-tree {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.tree-root-links path,
.tree-theme-links path {
  fill: none;
  stroke: rgba(126, 94, 67, 0.24);
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.15;
  transition: opacity 0.18s ease, stroke-width 0.18s ease;
}

.tree-theme-links path {
  stroke: #b49b7b;
  opacity: 0.62;
  stroke-opacity: 0.72;
  stroke-width: 1.3;
}

.tree-root-links path.active,
.tree-theme-links path.active {
  opacity: 1;
  stroke-width: 2.1;
}

.tree-root-links path.active {
  stroke: #8f3026;
}

.tree-theme-links path.active {
  stroke: #9a4034;
}

.tree-root-links path.dimmed,
.tree-theme-links path.dimmed {
  opacity: 0.16;
}

.tree-root-node circle {
  fill: #fffaf0;
  stroke: #9c4032;
  stroke-width: 2.2;
}

.root-name {
  fill: #7f2e25;
  font-family: "STKaiti", "KaiTi", serif;
  font-size: 15px;
  font-weight: 900;
}

.tree-relation-group {
  cursor: pointer;
  transition: opacity 0.18s ease;
}

.tree-relation-group .group-card {
  fill: #fffdf8;
  stroke: #d8c9b4;
  stroke-width: 1.15;
}

.tree-relation-group .relation-label-bg {
  fill: #8f3b30;
  stroke: #fffaf0;
  stroke-width: 1.5;
}

.tree-relation-group .person-core {
  fill: #f4ead9;
  stroke: #aa7b4a;
  stroke-width: 1.2;
}

.tree-relation-group.active .group-card {
  stroke: #9b4939;
  stroke-width: 1.4;
}

.tree-relation-group.active .person-core {
  fill: #9a4034;
  stroke: #dcbf82;
}

.tree-relation-group.active .relation-person {
  fill: #fffaf0;
}

.tree-relation-group.dimmed {
  opacity: 0.34;
}

.relation-type {
  fill: #fff9ec;
  font-family: "STKaiti", "KaiTi", serif;
  font-size: 9.5px;
  font-weight: 900;
}

.relation-person {
  fill: #52392e;
  font-family: "Microsoft YaHei", "STKaiti", serif;
  font-size: 8.5px;
  font-weight: 700;
  pointer-events: none;
}

.tree-theme-node {
  transition: opacity 0.18s ease;
}

.tree-theme-node .theme-card {
  fill: #fffdf8;
  stroke: #d8c9b4;
  stroke-width: 1.1;
}

.tree-theme-node.active .theme-card {
  fill: #fffdf7;
  stroke: rgba(143, 62, 49, 0.58);
  stroke-width: 1.25;
}

.tree-theme-node.dimmed {
  opacity: 0.28;
}

.tree-theme-node .theme-name {
  fill: #4f392f;
  font-family: "Microsoft YaHei", "STKaiti", serif;
  font-size: 10px;
  font-weight: 700;
}

.tree-theme-node .theme-track {
  fill: rgba(106, 76, 52, 0.08);
}

.tree-theme-node .theme-percent {
  fill: #75594a;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 8px;
  font-weight: 700;
}

.focus-dashboard {
  display: grid;
  grid-template-columns: 0.92fr 1.08fr;
  grid-template-rows: 0.9fr 1.1fr;
  gap: 7px;
  min-width: 0;
  min-height: 0;
  height: 100%;
  padding: 5px 4px 3px;
  box-sizing: border-box;
  background:
    linear-gradient(rgba(126, 88, 48, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(126, 88, 48, 0.035) 1px, transparent 1px),
    #fbf6e9;
  background-size: 20px 20px;
}

.focus-block {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  padding: 8px 9px 7px;
  border: 1px solid rgba(115, 75, 43, 0.14);
  border-radius: 5px;
  background: rgba(255, 252, 244, 0.82);
  box-shadow: 0 2px 8px rgba(78, 48, 29, 0.035);
}

.focus-block header {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 28px;
  margin-bottom: 6px;
  border-bottom: 1px solid rgba(115, 75, 43, 0.1);
}

.focus-block header > span {
  color: rgba(143, 47, 36, 0.42);
  font-family: Georgia, serif;
  font-size: 17px;
  font-weight: 700;
}

.focus-block header div {
  display: flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
}

.focus-block header b {
  color: #6f271f;
  font-size: 14px;
  font-weight: 900;
  white-space: nowrap;
}

.focus-block header small {
  overflow: hidden;
  color: #9a806a;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 8.5px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.theme-detail-list {
  display: grid;
  gap: 4px;
  margin-top: 7px;
}

.theme-detail-row {
  display: grid;
  grid-template-columns: 7px minmax(42px, 0.8fr) minmax(45px, 1fr) 28px;
  align-items: center;
  gap: 5px;
  min-width: 0;
  opacity: 0.64;
}

.theme-detail-row:first-child,
.theme-detail-row.active {
  opacity: 1;
}

.theme-detail-row > i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.theme-detail-row b {
  overflow: hidden;
  color: #544035;
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.theme-detail-row > span,
.role-score,
.relation-bar-row > span {
  height: 5px;
  overflow: hidden;
  border-radius: 99px;
  background: rgba(104, 76, 52, 0.09);
}

.theme-detail-row em,
.role-score em,
.relation-bar-row em {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.theme-detail-row strong {
  color: #7b382d;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 9px;
  text-align: right;
}

.role-carry-list {
  display: grid;
  gap: 2px;
}

.role-carry-row {
  display: grid;
  grid-template-columns: 15px minmax(52px, 0.72fr) minmax(58px, 1fr) minmax(40px, 0.7fr) 21px;
  align-items: center;
  gap: 4px;
  min-height: 17px;
  min-width: 0;
}

.role-rank {
  color: #b28a55;
  font-family: Georgia, serif;
  font-size: 10px;
  font-weight: 700;
}

.role-name {
  min-width: 0;
}

.role-name b,
.role-name small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.role-name b {
  color: #4f382d;
  font-size: 10.5px;
}

.role-name small {
  color: #a08973;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 7.5px;
}

.role-theme-tags {
  display: flex;
  gap: 2px;
  min-width: 0;
  overflow: hidden;
}

.role-theme-tags i {
  overflow: hidden;
  padding: 1px 3px;
  border: 1px solid;
  border-radius: 99px;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 7px;
  font-style: normal;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.role-score em {
  background: linear-gradient(90deg, #c99b50, #8f3026);
}

.role-carry-row > strong {
  color: #7b382d;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 8.5px;
  text-align: right;
}

.relation-bars {
  display: grid;
  gap: 5px;
}

.relation-bar-row {
  display: grid;
  grid-template-columns: minmax(45px, 0.72fr) minmax(55px, 1fr) 26px 20px;
  align-items: center;
  gap: 5px;
}

.relation-bar-row b {
  overflow: hidden;
  color: #554036;
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.relation-bar-row em {
  background: #9f4a38;
}

.relation-bar-row strong,
.relation-bar-row small {
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 8px;
  text-align: right;
}

.relation-bar-row strong {
  color: #7b382d;
}

.relation-bar-row small {
  color: #aa9078;
}

.focus-evidence {
  margin: 7px 0 0;
  padding-top: 6px;
  overflow: hidden;
  border-top: 1px dashed rgba(115, 75, 43, 0.15);
  color: #796251;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 8.5px;
  font-weight: 600;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.stage-columns {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  align-items: end;
  gap: 5px;
  height: calc(100% - 36px);
  min-height: 74px;
}

.stage-column {
  display: grid;
  grid-template-rows: 14px minmax(38px, 1fr) 15px 12px;
  align-items: end;
  min-width: 0;
  height: 100%;
  text-align: center;
}

.stage-column > strong {
  color: #9b7f67;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 8px;
}

.stage-column > span {
  position: relative;
  display: flex;
  align-items: end;
  justify-content: center;
  width: 70%;
  height: 100%;
  margin: auto;
  overflow: hidden;
  border-radius: 3px 3px 0 0;
  background: rgba(108, 78, 52, 0.06);
}

.stage-column em {
  display: block;
  width: 100%;
  min-height: 2px;
  border-radius: inherit;
  background: #c59b5b;
}

.stage-column.active em {
  background: #8f3026;
}

.stage-column.active > b {
  color: #8f3026;
}

.stage-column > b {
  overflow: hidden;
  color: #5d4638;
  font-size: 9px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stage-column > small {
  color: #a38a74;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 7.5px;
}

.theme-dashboard {
  position: relative;
  top: auto;
  right: auto;
  bottom: auto;
  z-index: 2;
  display: grid;
  grid-template-columns: minmax(82px, 0.8fr) minmax(110px, 1fr) minmax(150px, 1.45fr) minmax(90px, 1fr);
  align-items: center;
  gap: 5px;
  width: auto;
  min-width: 0;
  min-height: 0;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 2px 4px 1px;
  color: #4b3328;
  font-family: "Microsoft YaHei", sans-serif;
  background: rgba(251, 246, 233, 0.96);
  border-top: 1px solid rgba(143, 47, 36, 0.1);
  scrollbar-color: rgba(143, 47, 36, 0.32) #FBF6E9;
  scrollbar-width: thin;
}

.theme-dashboard::-webkit-scrollbar {
  height: 6px;
}

.theme-dashboard::-webkit-scrollbar-track {
  background: #FBF6E9;
}

.theme-dashboard::-webkit-scrollbar-thumb {
  background: rgba(143, 47, 36, 0.3);
  border: 2px solid #FBF6E9;
  border-radius: 999px;
}

.focus-meta-line {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 6px;
  margin-bottom: 0;
  color: #806a58;
  font-size: 11px;
  font-weight: 800;
  line-height: 1.2;
}

.theme-stack {
  display: flex;
  width: 100%;
  height: 12px;
  min-height: 12px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(143, 47, 36, 0.08);
}

.theme-stack i {
  min-width: 4px;
  height: 100%;
}

.theme-rank-list {
  display: flex;
  gap: 4px;
  margin-top: 0;
  min-width: 0;
  overflow: hidden;
}

.theme-rank-row {
  display: grid;
  grid-template-columns: 8px minmax(36px, 1fr) 30px;
  align-items: center;
  gap: 4px;
  flex: 1 1 0;
  min-width: 0;
  opacity: 0.62;
}

.theme-rank-row.active,
.theme-rank-row:first-child {
  opacity: 1;
}

.theme-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.theme-rank-row b {
  overflow: hidden;
  color: #4b3328;
  font-size: 10.5px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.theme-rank-row i {
  display: none;
}

.theme-rank-row em {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.theme-rank-row strong {
  color: #8f2f24;
  font-size: 10.5px;
  font-weight: 900;
  text-align: right;
}

.focus-scene-text {
  flex: initial;
  min-height: 0;
  margin: 0;
  overflow: hidden;
  color: #5c4636;
  font-size: 10.5px;
  font-weight: 700;
  line-height: 1.38;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  scrollbar-color: rgba(143, 47, 36, 0.34) #FBF6E9;
  scrollbar-width: thin;
}

.focus-scene-text::-webkit-scrollbar {
  width: 6px;
}

.focus-scene-text::-webkit-scrollbar-track {
  background: #FBF6E9;
}

.focus-scene-text::-webkit-scrollbar-thumb {
  background: rgba(143, 47, 36, 0.32);
  border: 2px solid #FBF6E9;
  border-radius: 999px;
}

.play-picker {
  display: flex;
  justify-content: center;
  min-width: 0;
  padding: 0 10px 2px;
}

.play-picker .play-select {
  width: 72%;
  height: 22px;
  min-width: 0;

  border: 1px solid rgba(142, 47, 36, 0.38);
  border-radius: 6px;
  outline: none;

  color: #50301c;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 13px;
  font-weight: 900;

  background:
    linear-gradient(180deg, rgba(255, 248, 232, 0.94), rgba(242, 224, 188, 0.94)),
    #f4e8cf;

  cursor: pointer;
}

.play-picker .play-select:hover {
  border-color: rgba(142, 47, 36, 0.38);
  color: #50301c;
}

.play-picker .play-select:focus-within {
  border-color: rgba(142, 47, 36, 0.74);
  box-shadow: 0 0 0 2px rgba(212, 166, 74, 0.24);
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
