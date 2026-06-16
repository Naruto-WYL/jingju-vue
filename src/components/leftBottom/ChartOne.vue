<template>
  <div class="role-poster">
    <svg ref="svgRef" class="poster-svg" role="img" aria-label="脸谱人物词云"></svg>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as d3 from 'd3'

import chouImage from '../../assets/词云2/chou3.png'
import danImage from '../../assets/词云2/dan3.png'
import jingImage from '../../assets/词云2/jing3.png'
import shengImage from '../../assets/词云2/sheng3.png'
import { findCharacterById, findPlayById, linkageState, loadLinkageData } from '../../services/linkageStore'

const svgRef = ref(null)

const W = 600
const H = 288
const fontFamily = '"SimHei", "Microsoft YaHei", sans-serif'
const V_GAP = 12
const CENTER_GAP = 132
const CELL_W = (W - CENTER_GAP) / 2
const CELL_H = (H - V_GAP) / 2
const RIGHT_X = CELL_W + CENTER_GAP
const MIN_WORD_SIZE = 7
const MAX_WORD_SIZE = 22
const WORD_DENSITY = 1.45
const WORD_GAP = 0
const CENTER_STEP = 2
const MAX_WORD_LAYOUT_CACHE = 80
const ROLE_ORDER = [
  {
    key: 'sheng',
    major: '生',
    src: shengImage,
    imageScale: 1.08,
    bgColor: '#D1B25B',
    box: { x: 0, y: 0, w: CELL_W, h: CELL_H },
    baseWords: [
      ['忠义', 10],
      ['家国', 9],
      ['正气', 8],
      ['唱念', 8],
      ['儒雅', 7],
      ['担纲', 7],
      ['稳健', 7],
      ['叙事', 6],
      ['气度', 6],
      ['护国', 5],
      ['将帅', 5],
      ['道白', 5],
      ['父子', 4],
      ['关目', 4],
      ['沉着', 4],
      ['抒怀', 4],
    ],
  },
  {
    key: 'dan',
    major: '旦',
    src: danImage,
    imageScale: 1.08,
    bgColor: '#D98AA8',
    box: { x: 0, y: CELL_H + V_GAP, w: CELL_W, h: CELL_H },
    baseWords: [
      ['婉转', 10],
      ['水袖', 9],
      ['青衣', 8],
      ['花旦', 8],
      ['柔情', 8],
      ['闺阁', 7],
      ['唱腔', 7],
      ['身段', 7],
      ['离合', 6],
      ['团圆', 6],
      ['清丽', 6],
      ['抒情', 5],
      ['含蓄', 5],
      ['念白', 5],
      ['流转', 5],
      ['才情', 4],
      ['绣阁', 4],
      ['情义', 4],
      ['婉约', 4],
      ['端庄', 4],
      ['思念', 3],
      ['明眸', 3],
      ['顾盼', 3],
      ['轻盈', 3],
    ],
  },
  {
    key: 'jing',
    major: '净',
    src: jingImage,
    imageScale: 1.12,
    bgColor: '#71AFC3',
    box: { x: RIGHT_X, y: 0, w: CELL_W, h: CELL_H },
    baseWords: [
      ['威武', 10],
      ['脸谱', 9],
      ['忠勇', 8],
      ['豪迈', 8],
      ['锣鼓', 8],
      ['靠旗', 7],
      ['武净', 7],
      ['亮相', 7],
      ['刚烈', 6],
      ['气势', 6],
      ['冲突', 6],
      ['战阵', 5],
      ['义胆', 5],
      ['雄浑', 5],
      ['开打', 5],
      ['高亢', 4],
      ['肃杀', 4],
      ['对峙', 4],
      ['震慑', 4],
      ['秩序', 4],
      ['阵前', 3],
      ['金鼓', 3],
      ['激昂', 3],
      ['厚重', 3],
    ],
  },
  {
    key: 'chou',
    major: '丑',
    src: chouImage,
    imageScale: 1.0,
    bgColor: '#96B86D',
    box: { x: RIGHT_X, y: CELL_H + V_GAP, w: CELL_W, h: CELL_H },
    baseWords: [
      ['机敏', 10],
      ['诙谐', 9],
      ['市井', 8],
      ['差役', 8],
      ['滑稽', 8],
      ['念白', 7],
      ['插科', 7],
      ['打诨', 7],
      ['幽默', 6],
      ['灵动', 6],
      ['小花脸', 6],
      ['圆场', 5],
      ['节奏', 5],
      ['俏皮', 5],
      ['身段', 5],
      ['节外生枝', 4],
      ['市井烟火', 4],
      ['调笑', 4],
      ['机锋', 4],
      ['点破', 4],
      ['变通', 3],
      ['轻快', 3],
      ['逗趣', 3],
      ['俐落', 3],
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
  ],
  () => {
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
      .attr('fill', layout.role.active ? '#101010' : '#2b241d')
      .attr('opacity', (word) => word.opacity)
      .text((word) => word.text)

  })
}

function buildRoleDefinitions() {
  const selectedCharacter = findCharacterById(linkageState.selectedCharacterId)
  const selectedPlay = selectedCharacter?.play || findPlayById(linkageState.selectedPlayId)
  const activeMajor = getMajorTrade(
    selectedCharacter?.major_trade ||
      selectedCharacter?.standard_trade ||
      selectedCharacter?.trade ||
      linkageState.selectedTrade,
  )

  return ROLE_ORDER.map((role) => {
    const activeCharacter =
      selectedCharacter && activeMajor === role.major ? selectedCharacter : null
    const representative = activeCharacter || pickRepresentativeCharacter(selectedPlay, role.major)
    const words = representative
      ? buildCharacterWords(representative, selectedPlay || representative.play, role.baseWords)
      : role.baseWords

    return {
      ...role,
      active: activeMajor === role.major,
      dimmed: Boolean(activeMajor && activeMajor !== role.major),
      words,
    }
  })
}

function pickRepresentativeCharacter(play, major) {
  const characters = play?.characters || []
  return characters
    .filter((character) =>
      getMajorTrade(character.major_trade || character.standard_trade || character.trade) === major
    )
    .sort((a, b) => characterScore(b) - characterScore(a))[0]
}

function characterScore(character) {
  return (
    Number(character.importance || 0) * 100 +
    Number(character.network_rank ? 10 / character.network_rank : 0) +
    Number(character.scene_count || 0) * 3 +
    Number(character.speech_count || 0) * 0.08
  )
}

function buildCharacterWords(character, play, baseWords) {
  const pairs = [
    [character.name, 13],
    [character.role_level_label, levelWeight(character.role_level)],
    ...buildMetricWords(character),
    ...buildThemeWords(character, play),
    ...buildRelationWords(character, play),
    ...buildSceneWords(character, play),
    ...baseWords.slice(0, 10).map(([text, weight]) => [text, Math.max(3, weight - 3)]),
  ]

  return mergeWordPairs(pairs).slice(0, 24)
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
  if (text.includes('旦') || text.includes('青衣')) return '旦'
  if (text.includes('净')) return '净'
  if (text.includes('丑') || text.includes('付')) return '丑'
  if (text.includes('生') || ['末', '外', '武将'].includes(text)) return '生'
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
  const imageBox = fitImage(image, role.box, 0, role.imageScale || 1)
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
  const scale = Math.min((box.w - padding * 2) / image.width, (box.h - padding * 2) / image.height) * multiplier
  const w = image.width * scale
  const h = image.height * scale

  return {
    x: box.x + (box.w - w) / 2,
    y: box.y + (box.h - h) / 2,
    w,
    h,
  }
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
          measured.width + 3,
          size * 1.06 + 3,
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
  place-items: center;
  border-radius: 2px;
}

.poster-svg {
  display: block;
  width: min(100%, 540px);
  height: 100%;
  max-height: 100%;
  aspect-ratio: 16 / 9;
}

.poster-svg :deep(.role-figure) {
  opacity: 0;
}

.poster-svg :deep(.role-cloud) {
  opacity: 1;
  transition: opacity 0.22s ease, filter 0.22s ease;
}

.poster-svg :deep(.role-cloud.is-active) {
  filter: drop-shadow(0 0 9px rgba(98, 38, 24, 0.22));
}

.poster-svg :deep(.role-cloud.is-dimmed) {
  opacity: 0.18;
}

.poster-svg :deep(.word-layer text) {
  paint-order: stroke;
  stroke: rgba(255, 250, 238, 0.24);
  stroke-linejoin: round;
  stroke-width: 0.8px;
}
</style>
