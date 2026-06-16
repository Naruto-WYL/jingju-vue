<template>
  <div class="trade-pattern-panel">
    <div class="role-selector">
      <label class="selector-field">
        <span>剧目</span>
        <select v-model="selectedScript">
          <option v-for="script in scripts" :key="script" :value="script">{{ script }}</option>
        </select>
      </label>

      <div class="period-field">
        <span>时期</span>
        <strong>{{ currentPeriod || '暂无' }}</strong>
      </div>

      <label class="selector-field">
        <span>角色</span>
        <select v-model="selectedRole">
          <option v-for="role in roles" :key="role" :value="role">{{ role }}</option>
        </select>
      </label>

      <div class="trade-badge" :class="{ 'is-inferred': isInferredTrade, 'is-known': isKnownTrade }">
        <span>行当</span>
        <strong>{{ currentTrade || '暂无' }}</strong>
      </div>
    </div>

    <div class="role-feature-summary">
      <span class="summary-label">当前角色候选特征</span>
      <span v-for="feature in currentRoleFeatures" :key="feature" class="summary-chip">{{ feature }}</span>
    </div>

    <div class="dotplot-wrap">
      <div v-if="hoveredTrade" class="trade-preview-card">
        <img :src="getTradeIconUrl(previewTrade)" :alt="previewTrade" />
        <div>
          <strong>{{ previewTrade || '行当' }}</strong>
          <p>{{ previewMeta.desc }}</p>
          <span v-for="tag in previewMeta.tags" :key="tag">{{ tag }}</span>
        </div>
      </div>
      <svg ref="chartRef" class="trade-dotplot" role="img" aria-label="行当特征点图" />
      <div v-if="loading" class="chart-state">数据加载中...</div>
      <div v-else-if="errorMessage" class="chart-state chart-state--error">{{ errorMessage }}</div>
      <div v-else-if="!heatmapRows.length" class="chart-state">暂无点图数据</div>
    </div>

    <p class="inference-note">{{ inferenceNote }}</p>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as d3 from 'd3'
import {
  findCharacterById,
  findPlayById,
  findPlayByTitle,
  linkageState,
  loadLinkageData,
  selectCharacter,
  selectTrade,
  STANDARD_TRADES,
  standardizeTrade,
} from '../../services/linkageStore'

const ROLE_URL = '/数据表合集/1/Table1_Role_Inference.csv'
const HEATMAP_URL = '/数据表合集/1/Table2_Trade_Vector_Patterns.csv'
const minChartWidth = 467
const chartHeight = 470
const chartLayout = {
  top: 28,
  right: 70,
  bottom: 40,
  left: 80,
  iconRadius: 15,
  pointRadius: 3.2,
}

const metricLabels = {
  male_ratio: '男',
  female_ratio: '女',
  youth_ratio: '青年',
  middle_age_ratio: '中年',
  old_age_ratio: '老年',
  scholar_ratio: '谋士',
  general_ratio: '武将',
  official_ratio: '官员',
  servant_ratio: '仆役',
  commoner_ratio: '平民',
  maid_ratio: '丫鬟',
  score_zhongyi: '忠义',
  score_zhimou: '智谋',
  score_yongwu: '勇武',
  score_jiaozha: '狡诈',
  score_baozao: '暴躁',
  appear_ratio: '出场',
  sing_ratio: '唱段',
  fight_ratio: '打斗',
  cry_ratio: '哭',
  laugh_ratio: '笑',
  sample_count: '样本数',
}
const metricColors = {
  male_ratio: '#3b6ea8',
  female_ratio: '#c76d8c',
  youth_ratio: '#4c9a8a',
  middle_age_ratio: '#7aa36f',
  old_age_ratio: '#9a8f6a',
  scholar_ratio: '#6b8fbf',
  general_ratio: '#b96b3c',
  official_ratio: '#8b5e83',
  servant_ratio: '#9a7a4f',
  commoner_ratio: '#7f8c6a',
  maid_ratio: '#c7869b',
  score_zhongyi: '#1f78b4',
  score_zhimou: '#2a9d8f',
  score_yongwu: '#7fb069',
  score_jiaozha: '#d6b93b',
  score_baozao: '#c23b4b',
  appear_ratio: '#e76f51',
  sing_ratio: '#f4a261',
  fight_ratio: '#8e5ea2',
  cry_ratio: '#4c78a8',
  laugh_ratio: '#88b04b',
}
const metricGroups = [
  {
    name: '人物属性',
    color: 'rgba(118, 154, 183, 0.18)',
    metrics: [
      'male_ratio',
      'female_ratio',
      'youth_ratio',
      'middle_age_ratio',
      'old_age_ratio',
      'scholar_ratio',
      'general_ratio',
      'official_ratio',
      'servant_ratio',
      'commoner_ratio',
      'maid_ratio',
    ],
  },
  {
    name: '性格标签',
    color: 'rgba(232, 211, 158, 0.26)',
    metrics: ['score_zhongyi', 'score_zhimou', 'score_yongwu', 'score_jiaozha', 'score_baozao'],
  },
  {
    name: '表演提示',
    color: 'rgba(151, 185, 161, 0.2)',
    metrics: ['appear_ratio', 'sing_ratio', 'fight_ratio', 'cry_ratio', 'laugh_ratio'],
  },
]
const tradeMeta = {
  老生: {
    tags: ['中老年', '忠正', '唱念'],
    desc: '多表现中老年男性，常承担忠义、伦理与叙事推进功能。',
    mode: '老生类角色通常表现为“中老年男性身份 + 忠正伦理功能 + 唱念叙事”的组合特征。',
  },
  丑: {
    tags: ['滑稽', '念做', '小民'],
    desc: '多承担喜剧、调度与市井叙事功能，表演偏念做与笑闹。',
    mode: '丑类角色通常表现为“市井或仆从身份 + 滑稽功能 + 念做笑闹”的组合特征。',
  },
  武生: {
    tags: ['武将', '勇武', '打斗'],
    desc: '多表现武将、英雄类角色，偏重身段、打斗和勇武气质。',
    mode: '武生类角色通常表现为“武将/英雄身份 + 勇武性格 + 打斗表演”的组合特征。',
  },
  小生: {
    tags: ['青年', '书生', '唱念'],
    desc: '多表现青年男性、书生公子，气质偏文雅、抒情与唱念。',
    mode: '小生类角色通常表现为“青年/书生身份 + 唱念较多 + 文雅或智谋性格”的组合特征。',
  },
  净: {
    tags: ['刚烈', '权势', '冲突'],
    desc: '多表现性格强烈或权势人物，常承担冲突、暴烈与戏剧张力。',
    mode: '净类角色通常表现为“权势或强性格人物 + 刚烈暴躁 + 冲突推动”的组合特征。',
  },
  旦: {
    tags: ['女性', '端庄', '唱段'],
    desc: '多表现女性角色，常承载婚恋、伦理、悲情等主题。',
    mode: '旦类角色通常表现为“女性身份 + 端庄情感功能 + 唱段或悲情表达”的组合特征。',
  },
  外: {
    tags: ['长者', '忠义', '辅助'],
    desc: '多为年长男性或辅助角色，常连接情节与伦理判断。',
    mode: '外类角色通常表现为“长者/辅助身份 + 忠义伦理 + 情节连接”的组合特征。',
  },
  正旦: {
    tags: ['女性', '端庄', '悲情'],
    desc: '偏端庄、严肃的女性角色，常与伦理、婚恋和悲情叙事相关。',
    mode: '正旦类角色通常表现为“端庄女性身份 + 伦理婚恋叙事 + 悲情表达”的组合特征。',
  },
  末: {
    tags: ['男性', '辅助', '叙事'],
    desc: '常承担辅助叙事、传递关系或推动情节的角色功能。',
    mode: '末类角色通常表现为“男性辅助身份 + 关系传递 + 叙事推进”的组合特征。',
  },
  武将: {
    tags: ['武职', '勇武', '行动'],
    desc: '偏武职身份和行动功能，常与战斗、出场和冲突相关。',
    mode: '武将类角色通常表现为“武职身份 + 勇武行动 + 冲突或战斗场面”的组合特征。',
  },
  老旦: {
    tags: ['老年女性', '伦理', '唱段'],
    desc: '多表现年长女性，常承载家庭伦理和情感叙事。',
    mode: '老旦类角色通常表现为“年长女性身份 + 家庭伦理 + 情感唱段”的组合特征。',
  },
  花旦: {
    tags: ['青年女性', '活泼', '念做'],
    desc: '多表现活泼机敏的青年女性，表演上偏念做和生活气息。',
    mode: '花旦类角色通常表现为“青年女性身份 + 活泼机敏 + 念做生活化”的组合特征。',
  },
  青衣: {
    tags: ['女性', '端庄', '悲情'],
    desc: '多表现端庄、抒情的女性主角，唱段和悲情表达较突出。',
    mode: '青衣类角色通常表现为“端庄女性主角 + 抒情唱段 + 悲情伦理”的组合特征。',
  },
}
const visibleThreshold = 0

const chartRef = ref(null)
const hoveredTrade = ref('')
const roleRows = ref([])
const heatmapRows = ref([])
const selectedScript = ref('')
const selectedRole = ref('')
const loading = ref(false)
const errorMessage = ref('')

defineProps({
  stats: {
    type: Object,
    default: () => ({}),
  },
})

let resizeObserver = null
let syncingFromLinkage = false

const scripts = computed(() => unique(roleRows.value.map((row) => row.script_name)).sort((a, b) => a.localeCompare(b, 'zh-Hans-CN')))

const currentScriptRows = computed(() => roleRows.value.filter((row) => row.script_name === selectedScript.value))

const roles = computed(() =>
  unique(currentScriptRows.value.map((row) => row.role_name)).sort((a, b) => a.localeCompare(b, 'zh-Hans-CN')),
)

const selectedRoleRow = computed(
  () => currentScriptRows.value.find((row) => row.role_name === selectedRole.value) || currentScriptRows.value[0] || null,
)

const currentPeriod = computed(() => selectedRoleRow.value?.historical_period || currentScriptRows.value[0]?.historical_period || '')
const currentTrade = computed(() => selectedRoleRow.value?.trade || '')
const currentTradeName = computed(() => cleanTradeName(currentTrade.value))
const isInferredTrade = computed(() => currentTrade.value.includes('推断'))
const isKnownTrade = computed(() => currentTrade.value.includes('已知'))

const tradeNames = computed(() => {
  const available = new Set(heatmapRows.value.map((row) => row.clean_trade).filter(Boolean))
  const ordered = STANDARD_TRADES.filter((trade) => available.has(trade))
  return ordered.length ? ordered : heatmapRows.value.map((row) => row.clean_trade).filter(Boolean)
})

const metrics = computed(() => {
  const firstRow = heatmapRows.value[0]
  if (!firstRow) return []
  const available = new Set(Object.keys(firstRow).filter((key) => key !== 'clean_trade'))
  return metricGroups.flatMap((group) => group.metrics.filter((metric) => available.has(metric)))
})

const currentRoleFeatures = computed(() => {
  const role = selectedRoleRow.value
  if (!role) return []

  const baseFeatures = [role.sex, role.age, role.identity, role.character_label].filter(Boolean)
  const scoreFeatures = [
    { label: '忠义高', value: role.score_zhongyi },
    { label: '智谋高', value: role.score_zhimou },
    { label: '勇武高', value: role.score_yongwu },
    { label: '狡诈高', value: role.score_jiaozha },
    { label: '暴躁高', value: role.score_baozao },
    { label: '出场高', value: role.appear_ratio },
    { label: '唱段高', value: role.sing_ratio },
    { label: '打斗高', value: role.fight_ratio },
    { label: '哭诉高', value: role.cry_ratio },
    { label: '笑闹高', value: role.laugh_ratio },
  ]
    .filter((item) => Number(item.value) > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 3)
    .map((item) => item.label)

  return unique([...baseFeatures, ...scoreFeatures]).slice(0, 8)
})

const previewTrade = computed(() => hoveredTrade.value || currentTradeName.value || tradeNames.value[0] || '')
const previewMeta = computed(() => tradeMeta[previewTrade.value] || { tags: [], desc: '暂无行当说明。', mode: '' })

const cells = computed(() =>
  heatmapRows.value.flatMap((row) =>
    metrics.value.map((metric) => ({
      trade: row.clean_trade,
      metric,
      label: metricLabels[metric] || metric,
      value: Number(row[metric]) || 0,
    })),
  ),
)

const dotplotPoints = computed(() =>
  cells.value
    .filter((cell) => cell.value > visibleThreshold)
    .map((cell) => {
      const isActive = cell.trade === currentTradeName.value
      return {
        ...cell,
        isActive,
        pointColor: isActive ? metricColors[cell.metric] || '#8b6f47' : '#b8b0a3',
        metricLabel: cell.label,
        valueLabel: cell.value.toFixed(4),
      }
    }),
)

const tradeScores = computed(() => {
  const role = selectedRoleRow.value
  if (!role) return []

  const roleVector = metrics.value.map((metric) => getRoleMetricValue(role, metric))

  return heatmapRows.value.map((row) => {
    const tradeVector = metrics.value.map((metric) => Number(row[metric]) || 0)
    return {
      trade: row.clean_trade,
      score: cosineSimilarity(roleVector, tradeVector),
    }
  })
})

const inferenceNote = computed(() => {
  const role = selectedRoleRow.value
  const trade = currentTradeName.value || '该行当'
  const base = [role?.sex, role?.age, role?.identity, role?.character_label].filter(Boolean).join('、')
  const highFeatures = currentRoleFeatures.value
    .filter((feature) => ![role?.sex, role?.age, role?.identity, role?.character_label].includes(feature))
    .slice(0, 3)
    .join('、')
  const modeTags = tradeMeta[trade]?.tags?.join('、') || '该行当典型特征'
  return `推断解释：${selectedRole.value || '当前角色'}具有${base || '若干人物属性'}等特征，并在${highFeatures || '关键指标'}上接近“${trade}”候选模式，因此识别为${trade}。\n典型模式：${trade}通常对应${modeTags}。`
})

onMounted(async () => {
  await loadData()

  if (chartRef.value) {
    resizeObserver = new ResizeObserver(() => drawDotplot())
    resizeObserver.observe(chartRef.value)
  }
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  d3.select(chartRef.value).selectAll('*').remove()
})

watch(scripts, (nextScripts) => {
  if (!selectedScript.value && nextScripts.length) {
    const play = findPlayById(linkageState.selectedPlayId)
    selectedScript.value = play?.title && nextScripts.includes(play.title) ? play.title : nextScripts[0]
  }
})

watch(roles, (nextRoles) => {
  if (!nextRoles.includes(selectedRole.value)) {
    selectedRole.value = nextRoles[0] || ''
  }
})

watch([dotplotPoints, currentTradeName, tradeScores], async () => {
  await nextTick()
  drawDotplot()
})

watch(
  () => [linkageState.selectedPlayId, linkageState.selectedCharacterId, linkageState.selectedTrade],
  () => {
    syncFromLinkage()
  },
)

async function loadData() {
  loading.value = true
  errorMessage.value = ''

  try {
    const linkageData = await loadLinkageData()
    if (linkageData.roleRows?.length) {
      roleRows.value = linkageData.roleRows.map(normalizeLinkageRoleRow)
      const standardHeatmapRows = await d3.csv(encodeURI(HEATMAP_URL), normalizeHeatmapRow).catch(() => [])
      heatmapRows.value = standardHeatmapRows.length ? standardHeatmapRows : buildHeatmapRowsFromRoles(roleRows.value)
      syncFromLinkage()
      return
    }

    const [roleData, heatmapData] = await Promise.all([
      d3.csv(encodeURI(ROLE_URL), normalizeRoleRow),
      d3.csv(encodeURI(HEATMAP_URL), normalizeHeatmapRow),
    ])
    roleRows.value = roleData
    heatmapRows.value = heatmapData
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '数据读取失败'
  } finally {
    loading.value = false
  }
}

function normalizeRoleRow(row) {
  return {
    play_id: text(csvValue(row, 'play_id')),
    character_id: text(csvValue(row, 'character_id')),
    script_id: text(csvValue(row, 'script_id')),
    script_name: text(csvValue(row, 'script_name')),
    historical_period: text(csvValue(row, 'historical_period')),
    role_name: text(csvValue(row, 'role_name')),
    trade: text(csvValue(row, 'trade')),
    sex: cleanListLike(csvValue(row, 'sex')),
    age: cleanListLike(csvValue(row, 'age')),
    identity: cleanListLike(csvValue(row, 'identity')),
    character_label: text(csvValue(row, 'character_label')),
    score_zhongyi: Number(csvValue(row, 'score_zhongyi')) || 0,
    score_zhimou: Number(csvValue(row, 'score_zhimou')) || 0,
    score_yongwu: Number(csvValue(row, 'score_yongwu')) || 0,
    score_jiaozha: Number(csvValue(row, 'score_jiaozha')) || 0,
    score_baozao: Number(csvValue(row, 'score_baozao')) || 0,
    appear_ratio: Number(csvValue(row, 'appear_ratio')) || 0,
    sing_ratio: Number(csvValue(row, 'sing_ratio')) || 0,
    fight_ratio: Number(csvValue(row, 'fight_ratio')) || 0,
    cry_ratio: Number(csvValue(row, 'cry_ratio')) || 0,
    laugh_ratio: Number(csvValue(row, 'laugh_ratio')) || 0,
    primary_scene_id: text(csvValue(row, 'primary_scene_id')),
    linked_theme_ids: text(csvValue(row, 'linked_theme_ids')),
  }
}

function normalizeHeatmapRow(row) {
  return Object.fromEntries(Object.entries(row).map(([key, value]) => [key, key === 'clean_trade' ? text(value) : Number(value) || 0]))
}

function normalizeLinkageRoleRow(row) {
  const rawTrade = text(row.trade)
  const trade = text(row.standard_trade) || standardizeTrade(rawTrade)
  const majorTrade = majorTradeFromStandard(trade)
  const themeIds = parseThemeIds(row.linked_theme_ids)

  return {
    play_id: text(row.play_id),
    character_id: text(row.character_id),
    script_id: text(row.play_id),
    script_name: text(row.script_name),
    historical_period: '传统京剧',
    role_name: text(row.role_name),
    trade,
    source_trade: rawTrade,
    sex: inferSex(majorTrade || trade),
    age: inferAge(trade),
    identity: inferIdentity(trade),
    character_label: text(row.character_type),
    ...profileMetrics(trade, majorTrade),
    score_zhongyi: hasAny(themeIds, ['theme_loyalty', 'theme_chivalry']) ? 1 : 0.25,
    score_zhimou: hasAny(themeIds, ['theme_power', 'theme_trial']) ? 1 : 0.18,
    score_yongwu: hasAny(themeIds, ['theme_war', 'theme_chivalry']) ? 1 : 0.2,
    score_jiaozha: hasAny(themeIds, ['theme_power', 'theme_trial']) && majorTrade !== '生' ? 0.72 : 0.12,
    score_baozao: hasAny(themeIds, ['theme_war', 'theme_chivalry']) && majorTrade === '净' ? 0.78 : 0.18,
    appear_ratio: Number(row.appearance_ratio) || 0,
    sing_ratio: Number(row.lyric_density) || 0,
    fight_ratio: Number(row.action_intensity) || 0,
    cry_ratio: Number(row.emotion_intensity) || 0,
    laugh_ratio: majorTrade === '丑' ? Math.max(0.65, Number(row.relation_strength) || 0) : Number(row.relation_strength) || 0,
    centrality: Number(row.centrality) || 0,
    role_level: text(row.role_level),
    network_rank: Number(row.network_rank) || 999,
    primary_scene_id: text(row.primary_scene_id),
    linked_theme_ids: themeIds.join('|'),
  }
}

function buildHeatmapRowsFromRoles(rows) {
  const numericMetrics = [
    'male_ratio',
    'female_ratio',
    'youth_ratio',
    'middle_age_ratio',
    'old_age_ratio',
    'scholar_ratio',
    'general_ratio',
    'official_ratio',
    'servant_ratio',
    'commoner_ratio',
    'maid_ratio',
    'score_zhongyi',
    'score_zhimou',
    'score_yongwu',
    'score_jiaozha',
    'score_baozao',
    'appear_ratio',
    'sing_ratio',
    'fight_ratio',
    'cry_ratio',
    'laugh_ratio',
  ]
  const grouped = d3.group(rows, (row) => standardizeTrade(row.trade))

  return STANDARD_TRADES.map((trade) => {
    const items = grouped.get(trade) || []
    const aggregate = { clean_trade: trade, ...profileMetrics(trade, majorTradeFromStandard(trade)) }
    numericMetrics.forEach((metric) => {
      aggregate[metric] = items.length ? d3.mean(items, (item) => getRoleMetricValue(item, metric)) || 0 : aggregate[metric] || 0
    })
    return aggregate
  })
}

function syncFromLinkage() {
  if (!roleRows.value.length) return
  const play = findPlayById(linkageState.selectedPlayId)
  const character = linkageState.selectedCharacterId ? findCharacterById(linkageState.selectedCharacterId) : null
  const scriptName = play?.title

  syncingFromLinkage = true

  if (scriptName && scripts.value.includes(scriptName)) {
    selectedScript.value = scriptName
  }

  const rows = scriptName ? roleRows.value.filter((row) => row.script_name === scriptName) : currentScriptRows.value
  const roleByCharacter = character ? rows.find((row) => row.character_id === character.character_id) : null
  const roleByTrade = linkageState.selectedTrade ? representativeRoleForTrade(rows, linkageState.selectedTrade, play) : null
  const nextRole = roleByCharacter?.role_name || roleByTrade?.role_name || selectedRole.value || rows[0]?.role_name || ''

  if (nextRole) selectedRole.value = nextRole

  nextTick(() => {
    syncingFromLinkage = false
  })
}

function handleTradePick(trade) {
  const play = findPlayByTitle(selectedScript.value)
  if (!play || !trade) return

  const pickedTrade = standardizeTrade(trade)
  const currentRole = selectedRoleRow.value
  const roleInPickedTrade =
    currentRole && currentRole.character_id && standardizeTrade(currentRole.trade) === pickedTrade
      ? currentRole
      : representativeRoleForTrade(currentScriptRows.value, pickedTrade, play)

  if (roleInPickedTrade?.character_id) {
    selectedRole.value = roleInPickedTrade.role_name
    selectCharacter(roleInPickedTrade.character_id, 'leftTopIcon')
    return
  }

  selectTrade(play.play_id, pickedTrade, 'leftTopIcon')
}

function representativeRoleForTrade(rows, trade, play) {
  const pickedTrade = standardizeTrade(trade)
  const roleByCharacterId = new Map(rows.filter((row) => row.character_id).map((row) => [row.character_id, row]))
  const rankedCharacter = (play?.characters || [])
    .filter((character) => standardizeTrade(character.standard_trade || character.trade) === pickedTrade)
    .slice()
    .sort((a, b) => {
      return (
        Number(b.importance || 0) - Number(a.importance || 0) ||
        Number(a.network_rank || 999) - Number(b.network_rank || 999) ||
        Number(a.role_order || 999) - Number(b.role_order || 999)
      )
    })
    .find((character) => roleByCharacterId.has(character.character_id))

  if (rankedCharacter) return roleByCharacterId.get(rankedCharacter.character_id)

  return rows
    .filter((row) => row.character_id && standardizeTrade(row.trade) === pickedTrade)
    .slice()
    .sort((a, b) => {
      return (
        Number(b.centrality || 0) - Number(a.centrality || 0) ||
        Number(a.network_rank || 999) - Number(b.network_rank || 999) ||
        a.role_name.localeCompare(b.role_name, 'zh-Hans-CN')
      )
    })[0]
}

function drawDotplot() {
  const svgElement = chartRef.value
  if (!svgElement) return

  const svg = d3.select(svgElement)
  svg.selectAll('*').remove()

  const svgWidth = Math.max(minChartWidth, Math.round(svgElement.clientWidth || minChartWidth))
  const svgHeight = chartHeight
  const isCompact = true
  const margin = chartLayout
  const iconRadius = chartLayout.iconRadius
  const pointRadius = chartLayout.pointRadius

  svg
    .classed('is-compact', isCompact)
    .attr('width', svgWidth)
    .attr('height', svgHeight)
    .attr('viewBox', `0 0 ${svgWidth} ${svgHeight}`)
    .attr('preserveAspectRatio', 'xMinYMin meet')

  if (!dotplotPoints.value.length) return

  const plotWidth = svgWidth - margin.left - margin.right
  const plotHeight = svgHeight - margin.top - margin.bottom
  const x = d3.scalePoint().domain(metrics.value).range([margin.left, margin.left + plotWidth]).padding(0.2)
  const y = d3.scalePoint().domain(tradeNames.value).range([margin.top + iconRadius, margin.top + plotHeight - iconRadius]).padding(0.12)
  const scoreX = margin.left + plotWidth + 12
  const scoreBarWidth = 30
  const headerY = margin.top - 2
  const groupY = margin.top - 22
  const rowHeight = Math.max(24, Math.min(36, plotHeight / Math.max(tradeNames.value.length, 1) * 0.82))
  
  const axisGroupY = margin.top + plotHeight + 16

  const groups = metricGroups
    .map((group) => ({
      ...group,
      metrics: group.metrics.filter((metric) => metrics.value.includes(metric)),
    }))
    .filter((group) => group.metrics.length)

  const groupLayer = svg.append('g').attr('class', 'feature-groups')
  groups.forEach((group) => {
    const groupPad = 3
    const start = x(group.metrics[0]) - groupPad
    const end = x(group.metrics[group.metrics.length - 1]) + groupPad
    groupLayer
      .append('rect')
      .attr('x', start)
      .attr('y', groupY)
      .attr('width', end - start)
      .attr('height', plotHeight + 33)
      .attr('rx', 5)
      .attr('fill', group.color)
    groupLayer
      .append('text')
      .attr('class', isCompact ? 'is-compact' : null)
      .attr('x', (start + end) / 2)
      .attr('y', headerY)
      .attr('text-anchor', 'middle')
      .text(group.name)
  })

  svg
    .append('rect')
    .attr('class', 'score-panel-bg')
    .attr('x', scoreX - 10)
    .attr('y', groupY)
    .attr('width', svgWidth - scoreX - 6)
    .attr('height', plotHeight + 34)
    .attr('rx', 8)

  svg
    .append('g')
    .attr('class', 'trade-row-hit-areas')
    .selectAll('rect')
    .data(tradeNames.value)
    .join('rect')
    .attr('class', (trade) => (trade === currentTradeName.value ? 'is-active' : 'is-muted'))
    .attr('x', margin.left - 70)
    .attr('y', (trade) => y(trade) - rowHeight / 2)
    .attr('width', plotWidth + 128)
    .attr('height', rowHeight)
    .attr('rx', rowHeight / 2)
    .on('mouseenter', (event, trade) => {
      hoveredTrade.value = trade
    })
    .on('mouseleave', () => {
      hoveredTrade.value = ''
    })
    .on('click', (event, trade) => {
      event.stopPropagation()
      handleTradePick(trade)
    })

  svg
    .append('g')
    .attr('class', 'active-row-bg')
    .selectAll('rect')
    .data(tradeNames.value.filter((trade) => trade === currentTradeName.value))
    .join('rect')
    .attr('x', margin.left - 66)
    .attr('y', (trade) => y(trade) - 12)
    .attr('width', plotWidth + 76)
    .attr('height', 24)
    .attr('rx', 12)

  svg
    .append('g')
    .attr('class', 'track-lines')
    .selectAll('line')
    .data(tradeNames.value)
    .join('line')
    .attr('class', (trade) => (trade === currentTradeName.value ? 'is-active' : 'is-muted'))
    .attr('x1', margin.left + 1)
    .attr('x2', margin.left + plotWidth -2)
    .attr('y1', (trade) => y(trade))
    .attr('y2', (trade) => y(trade))

  const icon = svg
    .append('g')
    .attr('class', 'trade-icons')
    .selectAll('g')
    .data(tradeNames.value)
    .join('g')
    .attr('class', (trade) => (trade === currentTradeName.value ? 'is-active' : 'is-muted'))
    .attr('transform', (trade) => `translate(${margin.left - 56},${y(trade)})`)
    .on('mouseenter', (event, trade) => {
      hoveredTrade.value = trade
    })
    .on('mouseleave', () => {
      hoveredTrade.value = ''
    })
    .on('click', (event, trade) => {
      event.stopPropagation()
      handleTradePick(trade)
    })

  icon.append('circle').attr('r', iconRadius)
  icon
    .append('image')
    .attr('href', (trade) => getTradeIconUrl(trade))
    .attr('x', -iconRadius + 2)
    .attr('y', -iconRadius + 2)
    .attr('width', iconRadius * 2 - 4)
    .attr('height', iconRadius * 2 - 4)
    .attr('preserveAspectRatio', 'xMidYMid meet')
  icon
    .append('text')
    .attr('x', iconRadius + 6)
    .attr('y', 4)
    .attr('class', 'trade-label')
    .text((trade) => trade)

  svg
    .append('g')
    .attr('class', 'feature-points')
    .selectAll('circle')
    .data(dotplotPoints.value)
    .join('circle')
    .attr('class', (d) => (d.isActive ? 'is-active' : 'is-muted'))
    .attr('cx', (d) => x(d.metric))
    .attr('cy', (d) => y(d.trade))
    .attr('r', (d) => (d.isActive ? pointRadius + 1.8 : pointRadius - 0.8))
    .attr('fill', (d) => d.pointColor)
    .attr('fill-opacity', (d) => (d.isActive ? 0.96 : 0.36))
    .attr('stroke', (d) => (d.isActive ? '#4a1f1a' : 'rgba(72, 49, 37, 0.25)'))
    .attr('stroke-width', (d) => (d.isActive ? 1.15 : 0.5))
    .style('cursor', 'pointer')
    .on('mouseenter', (event, d) => {
      hoveredTrade.value = d.trade
    })
    .on('mouseleave', () => {
      hoveredTrade.value = ''
    })
    .on('click', (event, d) => {
      event.stopPropagation()
      handleTradePick(d.trade)
    })
    .append('title')
    .text((d) => `${d.trade} - ${d.metricLabel}: ${d.valueLabel}`)

  const scoreRows = svg
    .append('g')
    .attr('class', 'match-scores')
    .selectAll('g')
    .data(tradeScores.value)
    .join('g')
    .attr('class', (d) => (d.trade === currentTradeName.value ? 'is-active' : 'is-muted'))
    .attr('transform', (d) => `translate(${scoreX},${y(d.trade)})`)
    .style('cursor', 'pointer')
    .on('mouseenter', (event, d) => {
      hoveredTrade.value = d.trade
    })
    .on('mouseleave', () => {
      hoveredTrade.value = ''
    })
    .on('click', (event, d) => {
      event.stopPropagation()
      handleTradePick(d.trade)
    })

  scoreRows.append('line').attr('x1', 0).attr('x2', scoreBarWidth).attr('y1', 0).attr('y2', 0)
  scoreRows
    .append('line')
    .attr('class', 'score-fill')
    .attr('x1', 0)
    .attr('x2', (d) => Math.max(2, scoreBarWidth * d.score))
    .attr('y1', 0)
    .attr('y2', 0)
  scoreRows
    .append('text')
    .attr('class', 'score-value')
    .attr('x', scoreBarWidth + 6)
    .attr('y', 3)
    .text((d) => d.score.toFixed(2))

  svg
    .append('text')
    .attr('class', 'score-title')
    .attr('x', scoreX)
    .attr('y', headerY)
    .text('匹配分')

  svg
    .append('g')
    .attr('class', 'axis axis-x')
    .attr('transform', `translate(0,${axisGroupY})`)
    .call(
      d3
        .axisBottom(x)
        .tickSize(6)
        .tickPadding(12)
        .tickFormat((metric) => metricLabels[metric] || metric),
    )
    .selectAll('text')
    .attr('text-anchor', 'middle')
    .attr('class', 'is-compact')
    .attr('dy', '0.8em')
    .each(function (metric) {
      const textSelection = d3.select(this)
      const label = metricLabels[metric] || metric
      textSelection.text('')
      Array.from(label).forEach((char, index) => {
        textSelection
          .append('tspan')
          .attr('x', 0)
          .attr('dy', index === 0 ? 0 : '0.95em')
          .text(char)
      })
    })
}

function getTradeIconUrl(trade) {
  return `/HD-svg/${encodeURIComponent(standardizeTrade(trade))}.png`
}

function unique(values) {
  return Array.from(new Set(values.map(text).filter(Boolean)))
}

function text(value) {
  return String(value ?? '').trim()
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}

function cleanListLike(value) {
  return text(value)
    .replace(/^[\[【]\s*/, '')
    .replace(/\s*[\]】]$/, '')
    .replace(/['"]/g, '')
    .replace(/\s*,\s*/g, '｜')
}

function parseThemeIds(value) {
  if (Array.isArray(value)) return value.map(text).filter(Boolean)
  return text(value)
    .split(/[|,，、\s]+/)
    .map(text)
    .filter(Boolean)
}

function hasAny(values, candidates) {
  const valueSet = new Set(values)
  return candidates.some((candidate) => valueSet.has(candidate))
}

function majorTradeFromStandard(trade) {
  const standard = standardizeTrade(trade)
  if (['旦', '正旦', '青衣', '花旦', '老旦'].includes(standard)) return '旦'
  if (['老生', '小生', '武生', '末', '外', '武将'].includes(standard)) return '生'
  if (standard === '净') return '净'
  if (standard === '丑') return '丑'
  return standard
}

function inferSex(trade) {
  const standard = standardizeTrade(trade)
  return ['旦', '正旦', '青衣', '花旦', '老旦'].includes(standard) ? '女性' : '男性'
  return text(trade).includes('旦') ? '女性' : '男性'
}

function inferAge(trade) {
  const standard = standardizeTrade(trade)
  if (['小生', '花旦'].includes(standard)) return '青年'
  if (['老生', '老旦', '外'].includes(standard)) return '老年'
  return '中年'
  const value = text(trade)
  if (value.includes('娃娃')) return '少年'
  if (value.includes('小生') || value.includes('花旦')) return '青年'
  if (value.includes('老')) return '老年'
  return '中年'
}

function inferIdentity(trade) {
  const standard = standardizeTrade(trade)
  const map = {
    老生: '君臣',
    丑: '市井',
    武生: '武职',
    小生: '书生',
    净: '权臣',
    旦: '女性',
    外: '长辈',
    正旦: '女性',
    末: '辅助',
    武将: '武职',
    老旦: '长辈',
    花旦: '女性',
    青衣: '女性',
  }
  return map[standard] || '人物'
  const value = text(trade)
  if (value.includes('小生')) return '书生'
  if (value.includes('净')) return '权臣'
  if (value.includes('丑')) return '市井'
  if (value.includes('老旦')) return '长辈'
  if (value.includes('旦')) return '女性'
  if (value.includes('老生')) return '君臣'
  return '人物'
}

function profileMetrics(trade, majorTrade) {
  const standard = standardizeTrade(trade)
  const standardMajor = majorTradeFromStandard(standard)
  return {
    male_ratio: standardMajor === '旦' ? 0 : 1,
    female_ratio: standardMajor === '旦' ? 1 : 0,
    youth_ratio: ['小生', '花旦'].includes(standard) ? 1 : 0,
    middle_age_ratio: ['老生', '老旦', '外'].includes(standard) ? 0 : 0.7,
    old_age_ratio: ['老生', '老旦', '外'].includes(standard) ? 1 : 0,
    scholar_ratio: standard === '小生' ? 1 : 0.12,
    general_ratio: ['武生', '武将', '净'].includes(standard) ? 0.9 : 0.12,
    official_ratio: ['老生', '净', '外'].includes(standard) ? 0.82 : 0.18,
    servant_ratio: standard === '丑' || standard === '末' ? 0.55 : 0.08,
    commoner_ratio: standard === '丑' ? 0.78 : 0.22,
    maid_ratio: ['旦', '正旦', '青衣', '花旦'].includes(standard) ? 0.32 : 0,
  }
  const value = text(trade)
  const major = text(majorTrade)
  return {
    male_ratio: major === '旦' ? 0 : 1,
    female_ratio: major === '旦' ? 1 : 0,
    youth_ratio: value.includes('小生') || value.includes('花旦') || value.includes('娃娃') ? 1 : 0,
    middle_age_ratio: value.includes('老') || value.includes('娃娃') ? 0 : 0.7,
    old_age_ratio: value.includes('老') ? 1 : 0,
    scholar_ratio: value.includes('小生') ? 1 : 0.15,
    general_ratio: major === '净' || value.includes('生') ? 0.55 : 0.1,
    official_ratio: major === '净' || value.includes('老生') ? 0.82 : 0.18,
    servant_ratio: major === '丑' ? 0.5 : 0.1,
    commoner_ratio: major === '丑' ? 0.75 : 0.22,
    maid_ratio: value.includes('旦') ? 0.28 : 0,
  }
}

function csvValue(row, key) {
  if (key in row) return row[key]
  const matchedKey = Object.keys(row).find((rowKey) => rowKey.replace(/^\uFEFF/, '') === key)
  return matchedKey ? row[matchedKey] : ''
}

function cleanTradeName(value) {
  return standardizeTrade(text(value).replace(/[（(].*?[）)]/g, ''))
  return text(value).replace(/[（(].*?[）)]/g, '')
}

function getRoleMetricValue(role, metric) {
  if (!role) return 0

  if (role[metric] !== undefined && role[metric] !== '') {
    const directValue = Number(role[metric])
    if (Number.isFinite(directValue)) return directValue
  }

  const sex = text(role.sex)
  const age = text(role.age)
  const identity = text(role.identity)
  const metricMap = {
    male_ratio: hasToken(sex, ['男', '男性']) ? 1 : 0,
    female_ratio: hasToken(sex, ['女', '女性']) ? 1 : 0,
    youth_ratio: hasToken(age, ['少年', '青年']) ? 1 : 0,
    middle_age_ratio: hasToken(age, ['中年']) ? 1 : 0,
    old_age_ratio: hasToken(age, ['老年']) ? 1 : 0,
    scholar_ratio: hasToken(identity, ['谋士', '书生', '文士', '儒生']) ? 1 : 0,
    general_ratio: hasToken(identity, ['武将']) ? 1 : 0,
    official_ratio: hasToken(identity, ['权臣', '朝官', '帝王', '诸侯', '太监', '官员']) ? 1 : 0,
    servant_ratio: hasToken(identity, ['家院', '差役', '仆从', '随从']) ? 1 : 0,
    commoner_ratio: hasToken(identity, ['平民']) ? 1 : 0,
    maid_ratio: hasToken(identity, ['丫鬟', '侍女']) ? 1 : 0,
  }

  if (metric in metricMap) return metricMap[metric]
  return Math.max(Number(role[metric]) || 0, getCharacterLabelMetricValue(role.character_label, metric))
}

function hasToken(value, candidates) {
  const source = text(value)
  return candidates.some((candidate) => source.split('｜').includes(candidate) || source.includes(candidate))
}

function getCharacterLabelMetricValue(label, metric) {
  const source = text(label)
  const keywordMap = {
    score_zhongyi: ['忠', '义', '忠义', '忠诚', '正直', '仁义'],
    score_zhimou: ['智', '谋', '机智', '聪慧', '聪明', '足智多谋', '灵敏'],
    score_yongwu: ['勇', '武', '英勇', '勇猛', '威武'],
    score_jiaozha: ['狡', '诈', '奸', '诡计', '阴险'],
    score_baozao: ['暴', '躁', '刚烈', '急躁', '鲁莽'],
  }
  return keywordMap[metric]?.some((keyword) => source.includes(keyword)) ? 1 : 0
}

function cosineSimilarity(a, b) {
  const dot = a.reduce((sum, value, index) => sum + value * b[index], 0)
  const normA = Math.sqrt(a.reduce((sum, value) => sum + value * value, 0))
  const normB = Math.sqrt(b.reduce((sum, value) => sum + value * value, 0))

  if (!normA || !normB) return 0
  return dot / (normA * normB)
}
</script>

<style scoped>
.trade-pattern-panel {
  display: grid;
  grid-template-rows: 56px 52px 480px 85px;
  gap: 6px;
  width: var(--left-top-content-width, 467px);
  height: 100%;
  min-height: 0;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
}

.role-selector {
  display: grid;
  grid-template-columns: minmax(120px, 1.75fr) minmax(74px, 0.75fr) minmax(104px, 0.95fr) minmax(82px, 0.7fr);
  grid-template-rows: 56px;
  height: 56px;
  gap: 5px;
  align-items: end;
}

.role-feature-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
  overflow: hidden;
  height: 52px;
  color: #5f5147;
  font-size: 12px;
  font-weight: 700;
}

.summary-label {
  flex: 0 0 100%;
  height: 18px;
  color: #8b2a25;
  font-size: 15px;
  font-weight: 900;
  line-height: 18px;
  white-space: nowrap;
}

.summary-chip {
  flex: 1 1 0;
  min-width: 0;
  max-width: none;
  height: 24px;
  padding: 2px 5px;
  overflow: hidden;
  border: 1px solid rgba(139, 42, 37, 0.16);
  border-radius: 999px;
  background: rgba(255, 246, 229, 0.78);
  line-height: 18px;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selector-field,
.period-field,
.trade-badge {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.selector-field span,
.period-field span,
.trade-badge span {
  color: #6b5b4d;
  font-size: 15px;
  font-weight: 700;
  line-height: 1;
}

.selector-field select,
.period-field strong,
.trade-badge strong {
  display: flex;
  align-items: center;
  width: 100%;
  min-width: 0;
  height: 30px;
  padding: 0 7px;
  border: 1px solid rgba(111, 20, 24, 0.16);
  border-radius: 5px;
  color: #352d27;
  background: rgba(255, 252, 244, 0.78);
  font-size: 15px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selector-field select {
  outline: none;
}

.selector-field select:focus {
  border-color: rgba(155, 47, 42, 0.55);
  box-shadow: 0 0 0 2px rgba(155, 47, 42, 0.1);
}

.trade-badge strong {
  justify-content: center;
  border-color: rgba(111, 20, 24, 0.34);
  color: #fff7ea;
  background:
    linear-gradient(135deg, rgba(111, 20, 24, 0.92), rgba(185, 91, 41, 0.9)),
    #8b2a25;
  box-shadow: inset 0 0 0 1px rgba(255, 247, 234, 0.26);
}

.trade-badge.is-known strong {
  background:
    linear-gradient(135deg, rgba(39, 59, 88, 0.94), rgba(47, 111, 109, 0.86)),
    #273b58;
}

.trade-badge.is-inferred strong {
  background:
    linear-gradient(135deg, rgba(111, 20, 24, 0.94), rgba(194, 135, 50, 0.92)),
    #8b2a25;
}

.dotplot-wrap {
  position: relative;
  width: var(--left-top-content-width, 467px);
  height: 480px;
  overflow: hidden;
  border: none;
  border-radius: 0;
  background: transparent;
}

.trade-preview-card {
  position: absolute;
  z-index: 2;
  top: 4px;
  left: 0;
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr);
  gap: 6px;
  width: 158px;
  padding: 6px;
  border: 1px solid rgba(139, 42, 37, 0.18);
  border-radius: 8px;
  background: rgba(255, 252, 244, 0.9);
  box-shadow: 0 6px 16px rgba(67, 48, 35, 0.1);
  pointer-events: none;
}

.trade-preview-card img {
  width: 46px;
  height: 46px;
  object-fit: contain;
}

.trade-preview-card strong {
  display: block;
  color: #8b2a25;
  font-size: 12px;
  font-weight: 900;
  line-height: 1.1;
}

.trade-preview-card p {
  display: -webkit-box;
  margin: 2px 0 3px;
  overflow: hidden;
  color: #65574c;
  font-size: 9px;
  line-height: 1.25;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.trade-preview-card span {
  display: inline-block;
  margin: 0 3px 2px 0;
  color: #8b2a25;
  font-size: 10px;
  font-weight: 800;
}

.trade-dotplot {
  display: block;
  width: 100%;
  height: 480px;
}

.trade-dotplot :deep(text) {
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
}

.trade-dotplot :deep(.active-row-bg rect) {
  fill: rgba(145, 45, 38, 0.11);
  stroke: rgba(145, 45, 38, 0.42);
  stroke-width: 1;
  pointer-events: none;
}

.trade-dotplot :deep(.trade-row-hit-areas rect) {
  fill: transparent;
  cursor: pointer;
  pointer-events: all;
}

.trade-dotplot :deep(.trade-row-hit-areas rect:hover) {
  fill: rgba(145, 45, 38, 0.06);
}

.trade-dotplot :deep(.feature-groups rect) {
  stroke: rgba(103, 84, 65, 0.08);
  stroke-width: 1;
}

.trade-dotplot :deep(.feature-groups text) {
  fill: #6d5f53;
  font-size: 20px;
  font-weight: 900;
}

.trade-dotplot :deep(.feature-groups text.is-compact) {
  font-size: 12px;
}

.trade-dotplot :deep(.track-lines line.is-muted) {
  stroke: rgba(42, 40, 36, 0.34);
  stroke-width: 1.2;
  stroke-linecap: round;
  pointer-events: none;
}

.trade-dotplot :deep(.track-lines line.is-active) {
  stroke: #8b2a25;
  stroke-width: 3;
  stroke-linecap: round;
  pointer-events: none;
}

.trade-dotplot :deep(.trade-icons g) {
  cursor: pointer;
}

.trade-dotplot :deep(.trade-icons circle) {
  fill: rgba(255, 252, 244, 0.92);
  stroke: rgba(144, 92, 43, 0.84);
  stroke-width: 1.35;
}

.trade-dotplot :deep(.trade-icons g.is-muted) {
  opacity: 0.62;
}

.trade-dotplot :deep(.trade-icons g.is-active circle) {
  fill: rgba(255, 246, 229, 0.98);
  stroke: #8b2a25;
  stroke-width: 2.2;
}

.trade-dotplot :deep(.trade-icons g:hover circle) {
  stroke: #8b2a25;
  stroke-width: 1.8;
}

.trade-dotplot :deep(.trade-icons image) {
  transform-box: fill-box;
  transform-origin: center;
  transition:
    filter 0.14s ease,
    transform 0.14s ease;
}

.trade-dotplot :deep(.trade-icons g:hover image) {
  filter: drop-shadow(0 3px 6px rgba(70, 45, 28, 0.22));
  transform: scale(1.16);
}

.trade-dotplot :deep(.trade-label) {
  fill: #4a3a2f;
  font-size: 21px;
  font-weight: 800;
}

.trade-dotplot :deep(.trade-icons g.is-active .trade-label) {
  fill: #8b2a25;
  font-size: 24px;
  font-weight: 900;
}

.trade-dotplot.is-compact :deep(.trade-label) {
  font-size: 12px;
}

.trade-dotplot.is-compact :deep(.trade-icons g.is-active .trade-label) {
  font-size: 14px;
}

.trade-dotplot :deep(.trade-icons .trade-label) {
  paint-order: stroke;
  stroke: rgba(246, 235, 213, 0.72);
  stroke-width: 2px;
}

.trade-dotplot :deep(.feature-points circle) {
  transition:
    fill-opacity 0.14s ease,
    r 0.14s ease;
}

.trade-dotplot :deep(.match-scores line) {
  stroke: rgba(84, 74, 64, 0.22);
  stroke-width: 5;
  stroke-linecap: round;
}

.trade-dotplot :deep(.match-scores .score-fill) {
  stroke: rgba(93, 124, 112, 0.58);
}

.trade-dotplot :deep(.match-scores.is-active line) {
  stroke: rgba(139, 42, 37, 0.18);
}

.trade-dotplot :deep(.match-scores.is-active .score-fill) {
  stroke: #8b2a25;
}

.trade-dotplot :deep(.match-scores text) {
  fill: rgba(75, 65, 55, 0.52);
  font-size: 18px;
  font-weight: 700;
}

.trade-dotplot.is-compact :deep(.match-scores text) {
  font-size: 11px;
}

.trade-dotplot.is-compact :deep(.match-scores .score-value) {
  display: none;
}

.trade-dotplot :deep(.match-scores.is-active text) {
  fill: #8b2a25;
  font-weight: 900;
}

.trade-dotplot :deep(.score-title) {
  fill: #6b5b4d;
  font-size: 16px;
  font-weight: 800;
}

.trade-dotplot.is-compact :deep(.score-title) {
  font-size: 12px;
}

.trade-dotplot :deep(.axis path) {
  stroke: rgba(87, 76, 66, 0.56);
}

.trade-dotplot :deep(.axis line) {
  stroke: rgba(87, 76, 66, 0.38);
}

.trade-dotplot :deep(.axis text) {
  fill: #5d5249;
  font-size: 22px;
  font-weight: 800;
}

.trade-dotplot :deep(.axis text.is-compact) {
  font-size: 12px;
}

.trade-dotplot :deep(.score-panel-bg) {
  fill: rgba(255, 252, 244, 0.32);
  stroke: rgba(103, 84, 65, 0.08);
  stroke-width: 1;
}

.chart-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #6a5b4f;
  font-size: 12px;
  pointer-events: none;
}

.chart-state--error {
  color: #9b2f2a;
}

.inference-note {
  margin: 0;
  display: -webkit-box;
  width: var(--left-top-content-width, 467px);
  height: 85px;
  max-height: 85px;
  padding: 8px 10px;
  overflow: hidden;
  color: #5c4e43;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.45;
  overflow-wrap: anywhere;
  white-space: pre-line;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.inference-note {
  border-left: 3px solid rgba(139, 42, 37, 0.62);
  background: rgb(236 209 158 / 52%);
}

@media (max-width: 980px) {
  .role-selector {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
