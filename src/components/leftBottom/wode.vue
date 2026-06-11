<template>
  <div class="face-cloud-grid">
    <article
      v-for="cloud in clouds"
      :key="cloud.title"
      class="face-cloud-card"
    >
      <!-- 彩色脸谱轮廓层 -->
      <div
        class="face-cloud-shape"
        :style="{
          background: cloud.faceColor,
          WebkitMaskImage: `url(${cloud.image})`,
          maskImage: `url(${cloud.image})`,
        }"
      ></div>

      <!-- 词云裁剪层 -->
      <div
        class="face-cloud-mask"
        :style="{
          WebkitMaskImage: `url(${cloud.image})`,
          maskImage: `url(${cloud.image})`,
        }"
      >
        <span
          v-for="(word, index) in cloud.denseWords"
          :key="`${cloud.title}-${index}`"
          class="cloud-word"
          :style="wordStyle(word, cloud, index)"
        >
          {{ word.text }}
        </span>
      </div>

      <strong>{{ cloud.title }}</strong>
    </article>
  </div>
</template>

<script setup>
import lianpu1 from '../../assets/image.png'
import lianpu2 from '../../assets/image.png'
import lianpu3 from '../../assets/image.png'

const clouds = [
  {
    title: '忠义武生',
    image: lianpu1,

    // 这里控制第一个脸谱轮廓颜色
    faceColor: 'rgba(185, 193, 179, 1) ',

    palette: ['#8b2a25', '#c28732', '#273b58', '#2f6f6d'],
    words: buildDenseWords([
      word('忠义', 26, 50, 32, 0),
      word('家国', 18, 28, 28, -14),
      word('冲突', 17, 66, 30, 10),
      word('对抗', 15, 34, 52, 8),
      word('高腔', 13, 64, 54, -12),
      word('将帅', 16, 50, 68, 0),
      word('秩序', 12, 26, 72, -8),
      word('牺牲', 14, 73, 70, 12),
    ]),
  },
  {
    title: '闺阁旦角',
    image: lianpu2,

    // 这里控制第二个脸谱轮廓颜色
    faceColor: 'rgba(208, 157, 134, 1) ',

    palette: ['#ae688a', '#8b2a25', '#c28732', '#4f5b7c'],
    words: buildDenseWords([
      word('情感', 25, 50, 31, 0),
      word('婚恋', 18, 30, 29, 13),
      word('团圆', 18, 67, 34, -10),
      word('念白', 14, 35, 54, -8),
      word('离散', 15, 61, 54, 10),
      word('闺阁', 16, 50, 68, 0),
      word('转折', 12, 26, 72, 12),
      word('抒情', 14, 72, 72, -12),
    ]),
  },
  {
    title: '净丑公案',
    image: lianpu3,

    // 这里控制第三个脸谱轮廓颜色
    faceColor: 'rgba(208, 195, 156, 1)',

    palette: ['#26776f', '#7f5539', '#8b2a25', '#c28732'],
    words: buildDenseWords([
      word('公案', 25, 50, 32, 0),
      word('审判', 18, 31, 33, -12),
      word('正邪', 18, 68, 32, 12),
      word('滑稽', 15, 34, 54, 8),
      word('冲突', 16, 62, 54, -8),
      word('做打', 14, 50, 68, 0),
      word('差役', 12, 27, 72, -10),
      word('裁决', 13, 73, 72, 10),
    ]),
  },
].map((cloud) => ({
  ...cloud,
  denseWords: cloud.words,
}))

function word(text, size, x, y, rotate) {
  return { text, size, x, y, rotate }
}

function buildDenseWords(seedWords) {
  const fillers = ['京剧', '唱', '念', '做', '打', '身段', '台词', '场次', '关系', '主题', '叙事', '情绪']
  const dense = [...seedWords]
  const rows = [18, 25, 32, 39, 46, 53, 60, 67, 74, 81]
  const cols = [22, 34, 46, 58, 70, 82]

  rows.forEach((y, rowIndex) => {
    cols.forEach((x, colIndex) => {
      const seed = seedWords[(rowIndex + colIndex) % seedWords.length]
      const filler = fillers[(rowIndex * cols.length + colIndex) % fillers.length]

      dense.push({
        text: (rowIndex + colIndex) % 3 === 0 ? seed.text : filler,
        size: 9 + ((rowIndex + colIndex) % 5) * 2,
        x: x + (rowIndex % 2) * 4 - 2,
        y,
        rotate: [-18, -9, 0, 8, 16][(rowIndex + colIndex) % 5],
      })
    })
  })

  return dense
}

function wordStyle(word, cloud, index) {
  return {
    left: `${word.x}%`,
    top: `${word.y}%`,
    fontSize: `${word.size}px`,
    color: cloud.palette[index % cloud.palette.length],
    transform: `translate(-50%, -50%) rotate(${word.rotate}deg)`,
  }
}
</script>

<style scoped>
.face-cloud-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  height: 100%;
  min-height: 0;
}

.face-cloud-card {
  position: relative;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border-radius: 8px;
}

/* 彩色脸谱轮廓层 */
.face-cloud-shape {
  position: absolute;
  inset: 7px 6px 24px;
  width: calc(100% - 12px);
  height: calc(100% - 31px);

  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;

  -webkit-mask-position: center;
  mask-position: center;

  -webkit-mask-size: contain;
  mask-size: contain;

  pointer-events: none;
  z-index: 0;
}

/* 词云区域 */
.face-cloud-mask {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;

  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;

  -webkit-mask-position: center;
  mask-position: center;

  -webkit-mask-size: contain;
  mask-size: contain;

  background: transparent;
}

.cloud-word {
  position: absolute;
  font-weight: 900;
  line-height: 1;
  white-space: nowrap;
  letter-spacing: 0;
  text-shadow:
    0 1px 0 rgba(255, 248, 235, 0.75),
    0 3px 8px rgba(65, 45, 35, 0.16);
}

.face-cloud-card strong {
  z-index: 2;
  display: block;
  padding: 4px 6px 6px;
  color: #5d5046;
  font-size: 11px;
  text-align: center;
}
</style>