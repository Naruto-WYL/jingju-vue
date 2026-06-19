import { loadQiyunDataset } from '../components/mainBottom/qiyunData'

export const FEATURED_PLAY_TITLES = ['逍遥津', '莲花湖', '万花船', '北汉王', '十三妹']

let catalogPromise = null

export async function loadPlayCatalog() {
  if (catalogPromise) return catalogPromise

  catalogPromise = loadQiyunDataset().then((dataset) => {
    const featuredRank = new Map(FEATURED_PLAY_TITLES.map((title, index) => [title, index]))
    const seen = new Set()

    return Object.values(dataset.scripts || {})
      .map((script) => ({
        id: String(script.scriptId || script.key || '').trim(),
        title: String(script.plainName || script.name || '')
          .replace(/[《》]/g, '')
          .trim(),
      }))
      .filter((play) => {
        if (!play.id || !play.title || seen.has(play.title)) return false
        seen.add(play.title)
        return true
      })
      .sort((a, b) => {
        const rankA = featuredRank.has(a.title) ? featuredRank.get(a.title) : 999
        const rankB = featuredRank.has(b.title) ? featuredRank.get(b.title) : 999
        return rankA - rankB || a.title.localeCompare(b.title, 'zh-Hans-CN')
      })
  })

  return catalogPromise
}

export function pinFeaturedPlays(items, getTitle = (item) => item?.title || item?.plainName || '') {
  const featuredRank = new Map(FEATURED_PLAY_TITLES.map((title, index) => [title, index]))
  return items.slice().sort((a, b) => {
    const titleA = getTitle(a)
    const titleB = getTitle(b)
    const rankA = featuredRank.has(titleA) ? featuredRank.get(titleA) : 999
    const rankB = featuredRank.has(titleB) ? featuredRank.get(titleB) : 999
    return rankA - rankB
  })
}
