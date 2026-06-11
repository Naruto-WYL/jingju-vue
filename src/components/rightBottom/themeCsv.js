import { onMounted, ref } from 'vue'

// 前端主题分析数据入口：
// 现在前端直接读取 public/数据表合集/3/theme_analysis.csv。
// 也就是说，你直接改这个 CSV 后，刷新页面就能看到变化。
export const THEME_CSV_URL = '/数据表合集/3/theme_analysis.csv'

export function useThemeCsv() {
  const rows = ref([])
  const loading = ref(true)
  const error = ref('')

  onMounted(async () => {
    try {
      // 加时间戳是为了避免浏览器缓存 CSV，保证你手动改 CSV 后刷新就生效。
      const response = await fetch(`${THEME_CSV_URL}?t=${Date.now()}`, { cache: 'no-store' })
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
      rows.value = parseThemeCsv(await response.text())
    } catch (err) {
      error.value = `主题CSV读取失败：${err.message}`
    } finally {
      loading.value = false
    }
  })

  return { rows, loading, error }
}

export function parseThemeCsv(text) {
  const [headerLine, ...lines] = text.trim().split(/\r?\n/)
  const headers = splitCsvLine(headerLine)

  return lines
    .filter(Boolean)
    .map((line) => {
      const values = splitCsvLine(line)
      const row = Object.fromEntries(headers.map((header, index) => [header, values[index] || '']))
      return {
        ...row,
        score: Number(row.score || 0),
        share: Number(row.share || 0),
        rank: Number(row.rank || 0),
      }
    })
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

export function groupRowsByPlay(rows) {
  const map = new Map()
  rows.forEach((row) => {
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
  return Array.from(map.values()).map((play) => ({
    ...play,
    themes: play.themes.sort((a, b) => b.share - a.share),
  }))
}
