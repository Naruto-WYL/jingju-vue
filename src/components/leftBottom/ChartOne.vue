<template>
  <div class="role-poster">
    <svg ref="svgRef" class="poster-svg" role="img" aria-label="脸谱人物词云"></svg>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as d3 from 'd3'

import choumowaiImage from '../../assets/词云/choumowai.png'
import hualaodanImage from '../../assets/词云/hualaodan.png'
import jingjueImage from '../../assets/词云/jingjue.png'
import laoshengImage from '../../assets/词云/laosheng.png'
import xiaowushengImage from '../../assets/词云/xiaowusheng.png'
import zhengqingdanImage from '../../assets/词云/zhengqingdan.png'
import { characterWordProfiles } from './characterWordProfiles'
import { findCharacterById, findPlayById, linkageState, loadLinkageData } from '../../services/linkageStore'

const svgRef = ref(null)

const W = 528
const H = 288
const fontFamily = '"SimHei", "Microsoft YaHei", sans-serif'
const COL_GAP = 3
const ROW_GAP = 3
const CELL_W = (W - COL_GAP * 2) / 3
const CELL_H = (H - ROW_GAP) / 2
const MIN_WORD_SIZE = 5.5
const MAX_WORD_SIZE = 20
const WORD_DENSITY = 1.35
const WORD_GAP = 0
const CENTER_STEP = 2
const MAX_WORD_LAYOUT_CACHE = 80
const roleTypeMap = {
  laosheng: ['老生'],
  xiaowusheng: ['小生', '武生'],
  zhengqingdan: ['旦', '正旦', '青衣'],
  hualaodan: ['花旦', '老旦'],
  jingjue: ['净', '武净'],
  choumowai: ['丑', '末', '外'],
}
const ROLE_ORDER = [
  {
    key: 'laosheng',
    major: '老生类',
    src: laoshengImage,
    imageScale: 1,
    bgColor: '#D1B25B',
    box: { x: 0, y: 0, w: CELL_W, h: CELL_H },
    baseWords: [
      ['老生', 10],
      ['忠义', 10],
      ['家国', 9],
      ['正气', 8],
      ['儒雅', 8],
      ['稳健', 7],
      ['担当', 7],
      ['道白', 7],
      ['唱念', 6],
      ['父子', 6],
      ['君臣', 6],
      ['忠孝', 5],
      ['护国', 5],
      ['沉着', 5],
      ['叙事核心', 4],
      ['伦理秩序', 4],
    ],
  },
  {
    key: 'xiaowusheng',
    major: '小武生类',
    src: xiaowushengImage,
    imageScale: 1,
    bgColor: '#C96B3C',
    box: { x: CELL_W + COL_GAP, y: 0, w: CELL_W, h: CELL_H },
    baseWords: [
      ['小生', 10],
      ['武生', 10],
      ['英气', 9],
      ['少年', 8],
      ['武艺', 8],
      ['身段', 7],
      ['冲突', 7],
      ['出征', 7],
      ['侠义', 6],
      ['成长', 6],
      ['情义', 6],
      ['行动推进', 5],
      ['英雄气', 5],
      ['战斗', 5],
      ['勇武', 4],
      ['转折角色', 4],
    ],
  },
  {
    key: 'zhengqingdan',
    major: '正青旦类',
    src: zhengqingdanImage,
    imageScale: 1,
    bgColor: '#D98BA2',
    box: { x: (CELL_W + COL_GAP) * 2, y: 0, w: CELL_W, h: CELL_H },
    baseWords: [
      ['正旦', 10],
      ['青衣', 10],
      ['旦', 9],
      ['端庄', 9],
      ['贞烈', 8],
      ['情感', 8],
      ['水袖', 7],
      ['抒情', 7],
      ['命运', 7],
      ['伦理', 6],
      ['哀怨', 6],
      ['家庭', 6],
      ['忠贞', 5],
      ['内心独白', 5],
      ['情节牵引', 4],
      ['女性叙事', 4],
    ],
  },
  {
    key: 'hualaodan',
    major: '花老旦类',
    src: hualaodanImage,
    imageScale: 1,
    bgColor: '#B76C8E',
    box: { x: 0, y: CELL_H + ROW_GAP, w: CELL_W, h: CELL_H },
    baseWords: [
      ['花旦', 10],
      ['老旦', 10],
      ['灵动', 9],
      ['生活气', 8],
      ['机敏', 8],
      ['活泼', 7],
      ['世情', 7],
      ['母性', 7],
      ['家族', 6],
      ['情趣', 6],
      ['对白', 6],
      ['人物反差', 5],
      ['日常叙事', 5],
      ['亲情', 5],
      ['喜剧色彩', 4],
      ['关系调节', 4],
    ],
  },
  {
    key: 'jingjue',
    major: '净角类',
    src: jingjueImage,
    imageScale: 1,
    bgColor: '#8F3B2E',
    box: { x: CELL_W + COL_GAP, y: CELL_H + ROW_GAP, w: CELL_W, h: CELL_H },
    baseWords: [
      ['净', 10],
      ['武净', 10],
      ['脸谱', 9],
      ['威严', 9],
      ['权力', 8],
      ['刚烈', 8],
      ['冲突核心', 7],
      ['忠奸', 7],
      ['豪气', 7],
      ['武力', 6],
      ['对抗', 6],
      ['气势', 6],
      ['阵营', 5],
      ['惩恶', 5],
      ['强关系', 4],
      ['戏剧张力', 4],
    ],
  },
  {
    key: 'choumowai',
    major: '丑末外类',
    src: choumowaiImage,
    imageScale: 1,
    bgColor: '#7C9A6D',
    box: { x: (CELL_W + COL_GAP) * 2, y: CELL_H + ROW_GAP, w: CELL_W, h: CELL_H },
    baseWords: [
      ['丑', 10],
      ['末', 9],
      ['外', 9],
      ['诙谐', 8],
      ['辅助角色', 8],
      ['过场', 7],
      ['插科打诨', 7],
      ['民间气', 7],
      ['旁观者', 6],
      ['信息传递', 6],
      ['关系补充', 6],
      ['节奏调节', 5],
      ['社会侧面', 5],
      ['人物衬托', 5],
      ['情节连接', 4],
      ['叙事缓冲', 4],
    ],
  },
]

const textMeasureCanvas = document.createElement('canvas')
const textMeasureContext = textMeasureCanvas.getContext('2d')
const imageCache = new Map()
const maskCache = new Map()
const wordLayoutCache = new Map()
let destroyed = false
let renderToken = 0
let tradeProfileSeed = 0

onMounted(async () => {
  await loadLinkageData().catch(() => null)
  await nextTick()
  await render()
})

watch(
  () => [
    linkageState.ready,
    linkageState.selectedPlayId,
    linkageState.selectedCharacterId,
    linkageState.selectedTrade,
    linkageState.selectedSceneId,
    linkageState.selectedThemeIds.join('|'),
    linkageState.source,
  ],
  () => {
    if (linkageState.source === 'leftTopTrade') {
      tradeProfileSeed += 1
    }
    void render()
  },
)

onBeforeUnmount(() => {
  destroyed = true
  renderToken += 1
  d3.select(svgRef.value).selectAll('*').remove()
})

async function render() {
  const svgElement = svgRef.value
  if (!svgElement) return

  const token = ++renderToken
  await document.fonts?.ready

  const roles = buildRoleDefinitions()
  const roleLayouts = await Promise.all(roles.map(prepareRoleLayout))
  if (destroyed || token !== renderToken) return

  const svg = d3.select(svgElement)
  svg.selectAll('*').remove()
  svg.attr('viewBox', `0 0 ${W} ${H}`).attr('preserveAspectRatio', 'xMidYMid meet')

  const defs = svg.append('defs')

  roleLayouts.forEach((layout) => {
    const maskId = `role-word-mask-${layout.role.key}`
    const clipId = `role-figure-clip-${layout.role.key}`

    defs
      .append('clipPath')
      .attr('id', clipId)
      .append('rect')
      .attr('x', layout.role.box.x)
      .attr('y', layout.role.box.y)
      .attr('width', layout.role.box.w)
      .attr('height', layout.role.box.h)

    defs
      .append('mask')
      .attr('id', maskId)
      .attr('maskUnits', 'userSpaceOnUse')
      .attr('mask-type', 'alpha')
      .style('mask-type', 'alpha')
      .append('image')
      .attr('href', layout.maskUrl)
      .attr('x', layout.role.box.x)
      .attr('y', layout.role.box.y)
      .attr('width', layout.role.box.w)
      .attr('height', layout.role.box.h)

    const group = svg
      .append('g')
      .attr('class', `role-cloud${layout.role.active ? ' is-active' : ''}${layout.role.dimmed ? ' is-dimmed' : ''}`)

    group
      .append('rect')
      .attr('class', 'role-shape-bg')
      .attr('x', layout.role.box.x)
      .attr('y', layout.role.box.y)
      .attr('width', layout.role.box.w)
      .attr('height', layout.role.box.h)
      .attr('fill', layout.role.bgColor || '#E8D8B6')
      .attr('fill-opacity', layout.role.active ? 0.86 : 0.58)
      .attr('mask', `url(#${maskId})`)
    group
      .append('image')
      .attr('class', 'role-figure')
      .attr('href', layout.role.src)
      .attr('x', layout.imageBox.x)
      .attr('y', layout.imageBox.y)
      .attr('width', layout.imageBox.w)
      .attr('height', layout.imageBox.h)
      .attr('clip-path', `url(#${clipId})`)

    group
      .append('g')
      .attr('class', 'word-layer')
      .attr('mask', `url(#${maskId})`)
      .selectAll('text')
      .data(layout.words)
      .join('text')
      .attr('x', (word) => layout.role.box.x + word.x)
      .attr('y', (word) => layout.role.box.y + word.y)
      .attr('transform', (word) => {
        const x = layout.role.box.x + word.x
        const y = layout.role.box.y + word.y
        return `rotate(${word.rotate},${x},${y})`
      })
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('font-family', fontFamily)
      .attr('font-size', (word) => word.size)
      .attr('font-weight', 700)
      .attr('fill', '#2b241d')
      .attr('opacity', (word) => word.opacity)
      .text((word) => word.text)

  })
}

function buildRoleDefinitions() {
  const selectedCharacter = findCharacterById(linkageState.selectedCharacterId)
  const selectedPlay = selectedCharacter?.play || findPlayById(linkageState.selectedPlayId)
  const usesTradeProfile = linkageState.source === 'leftTopTrade'
  const characterForWords = usesTradeProfile ? null : selectedCharacter
  const activeMajor = getMajorTrade(
    characterForWords?.standard_trade ||
      linkageState.selectedTrade ||
      characterForWords?.trade ||
      characterForWords?.major_trade,
  )

  return ROLE_ORDER.map((role) => {
    const activeCharacter = characterForWords && activeMajor === role.key ? characterForWords : null
    const words = activeCharacter
      ? buildCharacterWords(activeCharacter, selectedPlay || activeCharacter.play, role.baseWords)
      : buildProfileWords(role.baseWords, role.key, usesTradeProfile && activeMajor === role.key)

    return {
      ...role,
      active: activeMajor === role.key,
      dimmed: Boolean(activeMajor && activeMajor !== role.key),
      words,
    }
  })
}

function buildProfileWords(baseWords, roleKey, shouldVary) {
  if (!shouldVary) return baseWords

  return baseWords
    .map(([text, weight], index) => {
      const jitter = deterministicRandom(`${tradeProfileSeed}-${roleKey}-${text}-${index}`) * 1.4
      return [text, Math.max(3, Number(weight) + jitter)]
    })
    .sort(
      (a, b) =>
        b[1] - a[1] ||
        deterministicRandom(`${tradeProfileSeed}-${roleKey}-${a[0]}`) -
          deterministicRandom(`${tradeProfileSeed}-${roleKey}-${b[0]}`),
    )
}

function buildCharacterWords(character, play, baseWords) {
  const generatedProfile = characterWordProfiles[character.character_id]?.words || []
  const pairs = [
    ...generatedProfile,
    [character.name, 15],
    [character.role_level_label, levelWeight(character.role_level)],
    ...buildMetricWords(character),
    ...buildThemeWords(character, play),
    ...buildRelationWords(character, play),
    ...buildSceneWords(character, play),
    ...baseWords.slice(0, 6).map(([text, weight]) => [text, Math.max(3, weight - 4)]),
  ]

  return mergeWordPairs(pairs).slice(0, 28)
}

function levelWeight(level) {
  if (level === 'core') return 10
  if (level === 'major') return 8
  return 6
}

function buildMetricWords(character) {
  const words = []
  const importance = Number(character.importance || 0)
  const sceneCount = Number(character.scene_count || 0)
  const speechCount = Number(character.speech_count || 0)
  const mentionCount = Number(character.mention_count || 0)

  if (importance >= 0.62) words.push(['核心枢纽', 10])
  else if (importance >= 0.38) words.push(['主要推动', 8])
  else words.push(['情节补足', 6])

  if (sceneCount >= 6) words.push(['贯穿多场', 8])
  else if (sceneCount >= 3) words.push(['多场照应', 6])

  if (speechCount >= 28) words.push(['唱念密集', 8])
  else if (speechCount >= 12) words.push(['对白推进', 6])

  if (mentionCount >= 30) words.push(['反复被提', 6])

  return words
}

function buildThemeWords(character, play) {
  const themeNames = new Map((play?.themes || []).map((theme) => [theme.theme_id, theme.theme]))
  const linkedThemes = [
    ...(character.linked_themes || []),
    ...(character.linked_theme_ids || []).map((id) => themeNames.get(id)),
  ]

  return uniqueText(linkedThemes)
    .filter(Boolean)
    .slice(0, 4)
    .map((theme, index) => [theme, 9 - index])
}

function buildRelationWords(character, play) {
  const relations = (play?.relations || [])
    .filter(
      (relation) =>
        relation.source_character_id === character.character_id ||
        relation.target_character_id === character.character_id,
    )
    .sort((a, b) => Number(b.weight || 0) - Number(a.weight || 0))
    .slice(0, 4)

  const words = []
  relations.forEach((relation, index) => {
    const otherName =
      relation.source_character_id === character.character_id ? relation.target : relation.source
    words.push([otherName, 8 - Math.min(index, 3)])
    words.push([relation.relation_label || relation.relation_type, 7 - Math.min(index, 3)])
  })

  return words
}

function buildSceneWords(character, play) {
  const sceneIds = new Set(character.scene_ids || [])
  const scenes = (play?.scenes || [])
    .filter((scene) => sceneIds.has(scene.scene_id))
    .sort((a, b) => Number(b.metrics?.plot_strength || 0) - Number(a.metrics?.plot_strength || 0))
    .slice(0, 3)

  const words = []
  scenes.forEach((scene, index) => {
    words.push([scene.stage_type, 6 - index])
    words.push([scene.conflict_type, 6 - index])
    const summary = String(scene.summary || '').replace(/[，。、；：“”\s]/g, '')
    if (summary.length >= 2) words.push([summary.slice(0, 6), 5 - index])
  })

  return words
}

function mergeWordPairs(pairs) {
  const merged = new Map()

  pairs.forEach(([rawText, rawWeight]) => {
    const text = cleanWord(rawText)
    const weight = Number(rawWeight)
    if (!text || !Number.isFinite(weight)) return
    merged.set(text, Math.max(merged.get(text) || 0, weight))
  })

  return Array.from(merged, ([text, weight]) => [text, weight]).sort((a, b) => {
    return b[1] - a[1] || a[0].localeCompare(b[0], 'zh-Hans-CN')
  })
}

function cleanWord(value) {
  const text = String(value || '').trim()
  if (!text || text === 'undefined' || text === 'null') return ''
  return text.length > 8 ? text.slice(0, 8) : text
}

function uniqueText(values) {
  return Array.from(new Set(values.filter(Boolean)))
}

function getMajorTrade(trade) {
  const text = String(trade || '').trim()
  if (!text) return ''
  const cleanTrade = text.replace(/[（(].*?[）)]/g, '')

  for (const [key, trades] of Object.entries(roleTypeMap)) {
    if (trades.includes(cleanTrade)) return key
  }

  for (const [key, trades] of Object.entries(roleTypeMap)) {
    if (trades.some((candidate) => candidate !== '旦' && cleanTrade.includes(candidate))) return key
  }

  if (cleanTrade.includes('付') || cleanTrade.includes('副')) return 'choumowai'
  return ''
}

async function prepareRoleLayout(role) {
  const { imageBox, mask, maskUrl, centers } = await prepareRoleMask(role)
  const layoutKey = getWordLayoutKey(role)
  let words = wordLayoutCache.get(layoutKey)

  if (!words) {
    words = layoutWords(role.words, mask, role.box.w, role.box.h, centers)
    rememberWordLayout(layoutKey, words)
  }

  return {
    role,
    imageBox,
    maskUrl,
    words,
  }
}

async function prepareRoleMask(role) {
  const maskKey = getRoleMaskKey(role)
  if (maskCache.has(maskKey)) return maskCache.get(maskKey)

  const image = await loadImage(role.src)
  const imageBox = fitImage(image, role.box, 1, role.imageScale || 1)
  const { mask, maskUrl } = createAlphaMask(image, role.box, imageBox)
  const centers = buildCenters(mask, role.box.w, role.box.h, CENTER_STEP)
  const value = { imageBox, mask, maskUrl, centers }
  maskCache.set(maskKey, value)

  return value
}

function getRoleMaskKey(role) {
  const { x, y, w, h } = role.box
  return [role.key, role.src, x, y, w, h, role.imageScale || 1].join('|')
}

function getWordLayoutKey(role) {
  return [
    role.key,
    role.box.w,
    role.box.h,
    role.words.map(([text, weight]) => `${text}:${weight}`).join(','),
  ].join('|')
}

function rememberWordLayout(key, words) {
  if (wordLayoutCache.size >= MAX_WORD_LAYOUT_CACHE) {
    const firstKey = wordLayoutCache.keys().next().value
    wordLayoutCache.delete(firstKey)
  }

  wordLayoutCache.set(key, words)
}

function loadImage(src) {
  if (imageCache.has(src)) return imageCache.get(src)

  const promise = new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = (error) => {
      imageCache.delete(src)
      reject(error)
    }
    image.src = src
  })

  imageCache.set(src, promise)
  return promise
}

function fitImage(image, box, padding = 0, multiplier = 1) {
  const bounds = getImageAlphaBounds(image)
  const scale =
    Math.min(
      (box.w - padding * 2) / bounds.width,
      (box.h - padding * 2) / bounds.height,
    ) * multiplier
  const w = image.width * scale
  const h = image.height * scale

  return {
    x: box.x + (box.w - bounds.width * scale) / 2 - bounds.x * scale,
    y: box.y + (box.h - bounds.height * scale) / 2 - bounds.y * scale,
    w,
    h,
  }
}

function getImageAlphaBounds(image) {
  if (image.__alphaBounds) return image.__alphaBounds

  const canvas = document.createElement('canvas')
  canvas.width = image.width
  canvas.height = image.height
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  ctx.drawImage(image, 0, 0)
  const data = ctx.getImageData(0, 0, image.width, image.height).data
  let minX = image.width
  let minY = image.height
  let maxX = -1
  let maxY = -1

  for (let y = 0; y < image.height; y += 1) {
    for (let x = 0; x < image.width; x += 1) {
      if (data[(y * image.width + x) * 4 + 3] <= 28) continue
      minX = Math.min(minX, x)
      minY = Math.min(minY, y)
      maxX = Math.max(maxX, x)
      maxY = Math.max(maxY, y)
    }
  }

  image.__alphaBounds =
    maxX >= minX && maxY >= minY
      ? { x: minX, y: minY, width: maxX - minX + 1, height: maxY - minY + 1 }
      : { x: 0, y: 0, width: image.width, height: image.height }

  return image.__alphaBounds
}

function createAlphaMask(image, box, imageBox) {
  const canvas = document.createElement('canvas')
  canvas.width = box.w
  canvas.height = box.h

  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, box.w, box.h)
  ctx.drawImage(image, imageBox.x - box.x, imageBox.y - box.y, imageBox.w, imageBox.h)

  const imageData = ctx.getImageData(0, 0, box.w, box.h)
  let mask = new Uint8Array(box.w * box.h)

  for (let index = 0; index < mask.length; index += 1) {
    const alpha = imageData.data[index * 4 + 3]
    if (alpha > 28) mask[index] = 1
  }

  mask = keepLargestComponent(mask, box.w, box.h)
  mask = erode(mask, box.w, box.h, 1)

  const maskData = ctx.createImageData(box.w, box.h)
  for (let index = 0; index < mask.length; index += 1) {
    const value = mask[index] ? 255 : 0
    maskData.data[index * 4] = value
    maskData.data[index * 4 + 1] = value
    maskData.data[index * 4 + 2] = value
    maskData.data[index * 4 + 3] = value
  }

  ctx.putImageData(maskData, 0, 0)

  return {
    mask,
    maskUrl: canvas.toDataURL('image/png'),
  }
}

function keepLargestComponent(mask, width, height) {
  const visited = new Uint8Array(width * height)
  let best = []

  for (let index = 0; index < mask.length; index += 1) {
    if (!mask[index] || visited[index]) continue

    const queue = [index]
    const component = []
    visited[index] = 1

    while (queue.length) {
      const current = queue.pop()
      component.push(current)

      for (const next of getNeighbors(current, width, height)) {
        if (!mask[next] || visited[next]) continue
        visited[next] = 1
        queue.push(next)
      }
    }

    if (component.length > best.length) best = component
  }

  const result = new Uint8Array(width * height)
  best.forEach((index) => {
    result[index] = 1
  })

  return result
}

function erode(mask, width, height, radius) {
  const result = new Uint8Array(width * height)

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      let keep = true

      for (let dy = -radius; dy <= radius && keep; dy += 1) {
        for (let dx = -radius; dx <= radius; dx += 1) {
          const nx = x + dx
          const ny = y + dy

          if (nx < 0 || ny < 0 || nx >= width || ny >= height || !mask[ny * width + nx]) {
            keep = false
            break
          }
        }
      }

      if (keep) result[y * width + x] = 1
    }
  }

  return result
}

function getNeighbors(index, width, height) {
  const x = index % width
  const y = Math.floor(index / width)
  const neighbors = []

  if (x > 0) neighbors.push(index - 1)
  if (x < width - 1) neighbors.push(index + 1)
  if (y > 0) neighbors.push(index - width)
  if (y < height - 1) neighbors.push(index + width)

  return neighbors
}

function layoutWords(sourceWords, mask, width, height, cachedCenters = null) {
  const placedRects = []
  const centers = cachedCenters || buildCenters(mask, width, height, CENTER_STEP)

  const maxWeight = d3.max(sourceWords, (word) => word[1]) || 10
  const minWeight = d3.min(sourceWords, (word) => word[1]) || 3

  const sizeScale = d3
    .scaleSqrt()
    .domain([minWeight, maxWeight])
    .range([MIN_WORD_SIZE, MAX_WORD_SIZE])

  const words = expandWords(sourceWords, sizeScale, WORD_DENSITY)
  const layouts = []

  words.forEach((word, wordIndex) => {
    const rotations = getRotationCandidates(wordIndex, word.text)
    const preferredCenters = getPreferredCenters(centers, width, height, wordIndex, word)

    let placed = false

    for (let size = word.size; size >= MIN_WORD_SIZE && !placed; size -= 1) {
      const measured = measureText(word.text, size)

      for (const rotate of rotations) {
        const textBox = getRotatedBounds(
          measured.width + 0.8,
          size * 1.02 + 0.8,
          rotate
        )

        for (let index = 0; index < preferredCenters.length; index += 1) {
          const center = preferredCenters[index]

          const rect = {
            x: center.x - textBox.width / 2,
            y: center.y - textBox.height / 2,
            width: textBox.width,
            height: textBox.height,
          }

          if (!isRectInsideMask(mask, width, height, rect)) continue
          if (placedRects.some((placedRect) => rectsOverlap(rect, placedRect, WORD_GAP))) continue

          placedRects.push(rect)

          layouts.push({
            text: word.text,
            size,
            x: center.x,
            y: center.y,
            rotate,
            opacity: word.opacity,
          })

          placed = true
          break
        }

        if (placed) break
      }
    }
  })

  return layouts
}

function getPreferredCenters(centers, width, height, wordIndex, word) {
  const cx = width / 2
  const cy = height / 2

  const anchors = [
    { x: cx, y: cy },
    { x: width * 0.35, y: height * 0.32 },
    { x: width * 0.65, y: height * 0.32 },
    { x: width * 0.35, y: height * 0.52 },
    { x: width * 0.65, y: height * 0.52 },
    { x: width * 0.48, y: height * 0.70 },
    { x: width * 0.30, y: height * 0.70 },
    { x: width * 0.70, y: height * 0.70 },
  ]

  const anchor = anchors[wordIndex % anchors.length]

  const scored = centers.map((center) => {
    const dx = center.x - anchor.x
    const dy = center.y - anchor.y
    const distanceToAnchor = Math.sqrt(dx * dx + dy * dy)

    const randomOffset = deterministicRandom(
      `${word.text}-${wordIndex}-${center.x}-${center.y}`
    ) * 18

    return {
      ...center,
      localScore: distanceToAnchor + randomOffset,
    }
  })

  if (wordIndex < 8 && !word.isExtra) {
    return scored.sort((a, b) => a.localScore - b.localScore)
  }

  return scored.sort((a, b) => {
    const ringA = Math.floor(a.score / 24)
    const ringB = Math.floor(b.score / 24)

    if (ringA !== ringB) return ringA - ringB

    return (
      deterministicRandom(`${word.text}-${a.x}-${a.y}`) -
      deterministicRandom(`${word.text}-${b.x}-${b.y}`)
    )
  })
}
function expandWords(sourceWords, sizeScale, density = 1) {
  const expanded = []

  sourceWords.forEach(([text, weight], index) => {
    const baseSize = Math.round(sizeScale(weight))

    expanded.push({
      text,
      size: Math.max(MIN_WORD_SIZE, baseSize),
      opacity: 0.95,
      rank: index,
      isExtra: false,
    })

    const extraCount = Math.max(0, Math.round(density - 1))

    for (let i = 0; i < extraCount; i += 1) {
      const smallSize = Math.max(
        MIN_WORD_SIZE,
        Math.round(baseSize * (0.72 + deterministicRandom(text + i) * 0.14))
      )

      expanded.push({
        text,
        size: smallSize,
        opacity: 0.68 + deterministicRandom(text + i) * 0.18,
        rank: index + 1000 + i,
        isExtra: true,
      })
    }
  })

  return expanded.sort((a, b) => {
    if (a.isExtra !== b.isExtra) return a.isExtra ? 1 : -1
    return b.size - a.size || a.rank - b.rank
  })
}

function getRotationCandidates(index, text) {
  const base = Math.floor(deterministicRandom(text + index) * 6)

  const groups = [
    [0, -6, 6, -12, 12],
    [-4, 4, -10, 10, 0],
    [-8, 8, -15, 15, 0],
    [10, -10, 18, -18, 0],
    [-14, 14, -6, 6, 0],
    [5, -5, 13, -13, 0],
  ]

  if (index < 3) return [0, -5, 5, -10, 10]

  return groups[base]
}

function buildCenters(mask, width, height, step = 1) {
  const centers = []
  const cx = width / 2
  const cy = height / 2

  for (let y = 5; y < height - 5; y += step) {
    for (let x = 5; x < width - 5; x += step) {
      if (!isInside(mask, width, height, x, y)) continue

      const dx = x - cx
      const dy = y - cy
      const distance = Math.sqrt(dx * dx + dy * dy)
      const noise = deterministicRandom(`${x}-${y}`) * 20

      centers.push({
        x,
        y,
        score: distance + noise,
      })
    }
  }

  return centers.sort((a, b) => {
    const ringA = Math.floor(a.score / 26)
    const ringB = Math.floor(b.score / 26)

    if (ringA !== ringB) return ringA - ringB

    return (
      deterministicRandom(`${a.x}-${a.y}`) -
      deterministicRandom(`${b.x}-${b.y}`)
    )
  })
}
function deterministicRandom(seed) {
  let hash = 0
  const str = String(seed)

  for (let i = 0; i < str.length; i += 1) {
    hash = (hash << 5) - hash + str.charCodeAt(i)
    hash |= 0
  }

  const value = Math.sin(hash) * 10000
  return value - Math.floor(value)
}
function measureText(text, size) {
  textMeasureContext.font = `700 ${size}px ${fontFamily}`

  return {
    width: textMeasureContext.measureText(text).width,
    height: size,
  }
}

function getRotatedBounds(width, height, rotate) {
  const rad = (rotate * Math.PI) / 180
  const cos = Math.abs(Math.cos(rad))
  const sin = Math.abs(Math.sin(rad))

  return {
    width: width * cos + height * sin,
    height: width * sin + height * cos,
  }
}

function isRectInsideMask(mask, width, height, rect) {
  const x0 = Math.floor(rect.x)
  const y0 = Math.floor(rect.y)
  const x1 = Math.ceil(rect.x + rect.width)
  const y1 = Math.ceil(rect.y + rect.height)

  if (x0 < 0 || y0 < 0 || x1 >= width || y1 >= height) return false

  for (let y = y0; y <= y1; y += 4) {
    for (let x = x0; x <= x1; x += 4) {
      if (!isInside(mask, width, height, x, y)) return false
    }
  }

  return (
    isInside(mask, width, height, x1, y0) &&
    isInside(mask, width, height, x0, y1) &&
    isInside(mask, width, height, x1, y1)
  )
}

function rectsOverlap(a, b, gap = 0) {
  return !(
    a.x + a.width + gap <= b.x ||
    b.x + b.width + gap <= a.x ||
    a.y + a.height + gap <= b.y ||
    b.y + b.height + gap <= a.y
  )
}

function isInside(mask, width, height, x, y) {
  if (x < 0 || y < 0 || x >= width || y >= height) return false
  return mask[Math.floor(y) * width + Math.floor(x)] === 1
}
</script>

<style scoped>
.role-poster {
  display: grid;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  place-items: stretch;
  border-radius: 2px;
  background: #FBF6E9;
}

.poster-svg {
  display: block;
  width: 100%;
  height: 100%;
}

.poster-svg :deep(.role-figure) {
  opacity: 0;
}

.poster-svg :deep(.role-cloud) {
  opacity: 1;
  transition: opacity 0.22s ease, filter 0.22s ease;
}

.poster-svg :deep(.role-cloud.is-active) {
  filter: drop-shadow(0 0 7px rgba(98, 38, 24, 0.18));
}

.poster-svg :deep(.role-cloud.is-dimmed) {
  opacity: 0.46;
}

.poster-svg :deep(.word-layer text) {
  paint-order: stroke;
  stroke: rgba(255, 250, 238, 0.34);
  stroke-linejoin: round;
  stroke-width: 0.65px;
}
</style>
