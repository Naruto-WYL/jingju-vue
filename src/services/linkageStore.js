import { computed, reactive } from 'vue'

const LINKAGE_URL = '/data/linkage_plays.json'
export const STANDARD_TRADES = ['老生', '丑', '武生', '小生', '净', '旦', '外', '正旦', '末', '武将', '老旦', '花旦', '青衣']

export const linkageState = reactive({
  ready: false,
  loading: false,
  error: '',
  plays: [],
  roleRows: [],
  tradeVectorPatterns: [],
  mainFlows: [],
  selectedPlayId: '',
  selectedCharacterId: '',
  selectedTrade: '',
  selectedThemeIds: [],
  selectedSceneId: '',
  selectedFlowId: '',
  source: '',
})

let loadPromise = null

export const selectedPlay = computed(() => findPlayById(linkageState.selectedPlayId))
export const selectedCharacter = computed(() => findCharacterById(linkageState.selectedCharacterId))
export const selectedThemeSet = computed(() => new Set(linkageState.selectedThemeIds))

export async function loadLinkageData() {
  if (linkageState.ready) return snapshot()
  if (loadPromise) return loadPromise

  linkageState.loading = true
  linkageState.error = ''

  loadPromise = fetch(`${LINKAGE_URL}?t=${Date.now()}`, { cache: 'no-store' })
    .then((response) => {
      if (!response.ok) throw new Error(`linkage data ${response.status}`)
      return response.json()
    })
    .then((data) => {
      linkageState.plays = Array.isArray(data.plays) ? data.plays : []
      linkageState.roleRows = Array.isArray(data.roleRows) ? data.roleRows : []
      linkageState.tradeVectorPatterns = Array.isArray(data.tradeVectorPatterns) ? data.tradeVectorPatterns : []
      linkageState.mainFlows = Array.isArray(data.mainFlows) ? data.mainFlows : []
      linkageState.ready = true

      if (!linkageState.selectedPlayId && linkageState.plays.length) {
        setSelection(
          {
            selectedPlayId: linkageState.plays[0].play_id,
            selectedFlowId: linkageState.plays[0].flow_id || '',
          },
          'init',
        )
      }

      return snapshot()
    })
    .catch((error) => {
      linkageState.error = error instanceof Error ? error.message : 'linkage data load failed'
      throw error
    })
    .finally(() => {
      linkageState.loading = false
      loadPromise = null
    })

  return loadPromise
}

export function findPlayById(playId) {
  return linkageState.plays.find((play) => play.play_id === playId) || null
}

export function findPlayByTitle(title) {
  return linkageState.plays.find((play) => play.title === title) || null
}

export function findCharacterById(characterId) {
  for (const play of linkageState.plays) {
    const character = play.characters?.find((item) => item.character_id === characterId)
    if (character) return { ...character, play }
  }
  return null
}

export function findCharacterByName(playId, name) {
  const play = findPlayById(playId)
  const character = play?.characters?.find((item) => item.name === name)
  return character ? { ...character, play } : null
}

export function selectPlay(playId, source = 'external') {
  const play = findPlayById(playId)
  if (!play) return

  const changedPlay = linkageState.selectedPlayId !== playId
  setSelection(
    {
      selectedPlayId: playId,
      selectedFlowId: play.flow_id || '',
      selectedCharacterId: changedPlay ? '' : linkageState.selectedCharacterId,
      selectedTrade: changedPlay ? '' : linkageState.selectedTrade,
      selectedThemeIds: changedPlay ? topThemeIds(play) : linkageState.selectedThemeIds,
      selectedSceneId: changedPlay ? firstSceneId(play) : linkageState.selectedSceneId,
    },
    source,
  )
}

export function selectFlow(flowId, source = 'external') {
  const flow = linkageState.mainFlows.find((item) => item.id === flowId)
  const playId = flow?.representativePlayId || flow?.scripts?.[0] || linkageState.selectedPlayId
  const play = findPlayById(playId)
  if (!play) return

  setSelection(
    {
      selectedPlayId: play.play_id,
      selectedFlowId: flowId,
      selectedCharacterId: '',
      selectedTrade: '',
      selectedThemeIds: topThemeIds(play),
      selectedSceneId: firstSceneId(play),
    },
    source,
  )
}

export function selectCharacter(characterId, source = 'external') {
  const result = findCharacterById(characterId)
  if (!result) return

  const themeIds = result.linked_theme_ids?.length ? result.linked_theme_ids : topThemeIds(result.play)
  setSelection(
    {
      selectedPlayId: result.play.play_id,
      selectedFlowId: result.play.flow_id || '',
      selectedCharacterId: result.character_id,
      selectedTrade: result.standard_trade || standardizeTrade(result.trade) || result.trade || '',
      selectedThemeIds: themeIds,
      selectedSceneId: result.primary_scene_id || firstSceneId(result.play),
    },
    source,
  )
}

export function selectTrade(playId, trade, source = 'external') {
  const play = findPlayById(playId)
  if (!play || !trade) return

  const standardTrade = standardizeTrade(trade)
  const characters =
    play.characters?.filter((character) => {
      return (
        standardizeTrade(character.standard_trade || character.trade) === standardTrade ||
        standardizeTrade(character.major_trade) === standardTrade
      )
    }) || []
  const themeIds = unique(characters.flatMap((character) => character.linked_theme_ids || []))
  const sceneId = bestSceneForCharacters(play, new Set(characters.map((character) => character.character_id)))

  setSelection(
    {
      selectedPlayId: play.play_id,
      selectedFlowId: play.flow_id || '',
      selectedCharacterId: characters.length === 1 ? characters[0].character_id : '',
      selectedTrade: standardTrade,
      selectedThemeIds: themeIds.length ? themeIds : topThemeIds(play),
      selectedSceneId: sceneId || firstSceneId(play),
    },
    source,
  )
}

export function selectScene(sceneId, source = 'external') {
  const play = linkageState.plays.find((item) => item.scenes?.some((scene) => scene.scene_id === sceneId))
  if (!play) return

  setSelection(
    {
      selectedPlayId: play.play_id,
      selectedFlowId: play.flow_id || '',
      selectedSceneId: sceneId,
    },
    source,
  )
}

export function selectTheme(playId, themeIds, source = 'external') {
  const play = findPlayById(playId)
  if (!play) return

  setSelection(
    {
      selectedPlayId: play.play_id,
      selectedFlowId: play.flow_id || '',
      selectedThemeIds: Array.isArray(themeIds) ? themeIds : [themeIds].filter(Boolean),
    },
    source,
  )
}

export function clearLinkageFocus(source = 'external') {
  const play = findPlayById(linkageState.selectedPlayId)
  setSelection(
    {
      selectedCharacterId: '',
      selectedTrade: '',
      selectedThemeIds: play ? topThemeIds(play) : [],
      selectedSceneId: play ? firstSceneId(play) : '',
    },
    source,
  )
}

function setSelection(patch, source) {
  Object.assign(linkageState, patch, { source })
}

function snapshot() {
  return {
    plays: linkageState.plays,
    roleRows: linkageState.roleRows,
    tradeVectorPatterns: linkageState.tradeVectorPatterns,
    mainFlows: linkageState.mainFlows,
  }
}

function topThemeIds(play) {
  return (play?.themes || []).slice(0, 2).map((theme) => theme.theme_id)
}

function firstSceneId(play) {
  return play?.scenes?.[0]?.scene_id || ''
}

function bestSceneForCharacters(play, characterIds) {
  let bestScene = null
  let bestScore = -1

  for (const scene of play.scenes || []) {
    const score = (scene.character_ids || []).filter((id) => characterIds.has(id)).length
    if (score > bestScore) {
      bestScene = scene
      bestScore = score
    }
  }

  return bestScore > 0 ? bestScene?.scene_id : ''
}

function unique(values) {
  return Array.from(new Set(values.filter(Boolean)))
}

export function standardizeTrade(trade) {
  const value = String(trade || '').trim().replace(/[（(].*?[）)]/g, '')
  if (!value) return ''
  if (STANDARD_TRADES.includes(value)) return value
  if (value === '生') return '老生'
  if (value === '娃娃生') return '小生'
  if (value === '武旦') return '旦'
  if (value === '贴旦') return '旦'
  if (value === '二旦') return '旦'
  if (value === '彩旦') return '花旦'
  if (value === '花衫') return '花旦'
  if (value === '付' || value === '副') return '丑'
  if (value.includes('老生')) return '老生'
  if (value.includes('小生')) return '小生'
  if (value.includes('武生')) return '武生'
  if (value.includes('老旦')) return '老旦'
  if (value.includes('花旦')) return '花旦'
  if (value.includes('青衣')) return '青衣'
  if (value.includes('正旦')) return '正旦'
  if (value.includes('旦')) return '旦'
  if (value.includes('净')) return '净'
  if (value.includes('丑')) return '丑'
  if (value.includes('末')) return '末'
  if (value.includes('外')) return '外'
  return value
}
