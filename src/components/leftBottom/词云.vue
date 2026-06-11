<template>
  <div class="role-poster">
    <canvas ref="canvasRef" class="poster-canvas"></canvas>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';

import personImage from '../../assets/词云/生.jpg';
import danImage from '../../assets/词云/旦.jpg';
import jingImage from '../../assets/词云/净.jpg';

const canvasRef = ref(null);

const W = 900;
const H = 360;

const PANEL_W = 260;
const PANEL_H = 330;

const ROLE_GAP = 30;
const ROLE_START_X = 15;
const ROLE_START_Y = 15;

const RENDER_QUALITY = 4;

const MAX_WORDS_PER_ROLE = 88;
const REPEAT_SMALL_WORDS = 3;

const MIN_FONT_SIZE = 8;
const MAX_FONT_SIZE = 36;

const WORD_GAP = 1.2;
const MASK_SAMPLE_STEP = 4;

const textFont = '"FangSong", "STFangsong", "KaiTi", "STKaiti", "STSong", "SimSun", serif';

const roleWordSources = {
  sheng: [
    ['老生', 100],
    ['武生', 86],
    ['小生', 82],
    ['须生', 76],
    ['红生', 68],
    ['文生', 64],
    ['娃娃生', 58],
    ['穷生', 52],
    ['唱腔', 90],
    ['念白', 82],
    ['身段', 78],
    ['台步', 74],
    ['亮相', 72],
    ['起霸', 68],
    ['走边', 66],
    ['圆场', 64],
    ['板眼', 62],
    ['西皮', 60],
    ['二黄', 58],
    ['锣鼓', 56],
    ['梨园', 54],
    ['科班', 52],
    ['角儿', 50],
    ['戏曲', 48],
    ['行头', 46],
    ['髯口', 44],
    ['马鞭', 42],
    ['靠旗', 40],
    ['把子', 38],
    ['功架', 36],
    ['唱念做打', 34],
    ['忠义', 32],
    ['儒雅', 30],
    ['英武', 28],
    ['气口', 26],
    ['腔韵', 24],
    ['文武兼备', 22],
    ['台风', 20],
  ],
  dan: [
    ['青衣', 100],
    ['花旦', 88],
    ['刀马旦', 82],
    ['武旦', 78],
    ['老旦', 72],
    ['闺门旦', 66],
    ['彩旦', 58],
    ['水袖', 90],
    ['唱腔', 86],
    ['身段', 80],
    ['台步', 76],
    ['亮相', 72],
    ['念白', 68],
    ['圆场', 66],
    ['眼神', 64],
    ['手势', 62],
    ['板眼', 60],
    ['西皮', 58],
    ['二黄', 56],
    ['锣鼓', 54],
    ['梨园', 52],
    ['科班', 50],
    ['角儿', 48],
    ['戏服', 46],
    ['行头', 44],
    ['云肩', 42],
    ['霞帔', 40],
    ['凤冠', 38],
    ['裙褶', 36],
    ['唱念做打', 34],
    ['含蓄', 32],
    ['端庄', 30],
    ['灵巧', 28],
    ['柔婉', 26],
    ['腔韵', 24],
    ['情态', 22],
    ['台风', 20],
  ],
  jing: [
    ['脸谱', 100],
    ['花脸', 90],
    ['铜锤花脸', 84],
    ['架子花脸', 78],
    ['武净', 72],
    ['正净', 66],
    ['副净', 60],
    ['唱腔', 86],
    ['亮相', 82],
    ['功架', 78],
    ['身段', 74],
    ['念白', 70],
    ['台步', 68],
    ['锣鼓', 66],
    ['板眼', 64],
    ['西皮', 62],
    ['二黄', 60],
    ['行头', 58],
    ['靠旗', 56],
    ['把子', 54],
    ['髯口', 52],
    ['勾脸', 50],
    ['谱式', 48],
    ['油彩', 46],
    ['梨园', 44],
    ['科班', 42],
    ['角儿', 40],
    ['戏曲', 38],
    ['唱念做打', 36],
    ['威严', 34],
    ['刚烈', 32],
    ['忠勇', 30],
    ['豪迈', 28],
    ['粗犷', 26],
    ['气势', 24],
    ['台风', 22],
  ],
};

const roles = [
  {
    name: '生',
    src: personImage,
    x: ROLE_START_X,
    y: ROLE_START_Y,
    color: 'rgba(181, 197, 188, 0.78)',
    textColor: 'rgba(45, 55, 47, 0.94)',
    strongTextColor: 'rgba(28, 34, 28, 0.98)',
    wordKey: 'sheng',
  },
  {
    name: '旦',
    src: danImage,
    x: ROLE_START_X + PANEL_W + ROLE_GAP,
    y: ROLE_START_Y,
    color: 'rgba(224, 153, 125, 0.78)',
    textColor: 'rgba(88, 53, 43, 0.94)',
    strongTextColor: 'rgba(55, 31, 25, 0.98)',
    wordKey: 'dan',
  },
  {
    name: '净',
    src: jingImage,
    x: ROLE_START_X + (PANEL_W + ROLE_GAP) * 2,
    y: ROLE_START_Y,
    color: 'rgba(207, 188, 129, 0.8)',
    textColor: 'rgba(78, 64, 35, 0.94)',
    strongTextColor: 'rgba(47, 39, 21, 0.98)',
    wordKey: 'jing',
  },
];

const importantAnchors = [
  { x: 0.5, y: 0.5, angle: -5 },
  { x: 0.43, y: 0.36, angle: 10 },
  { x: 0.58, y: 0.62, angle: -11 },
  { x: 0.34, y: 0.52, angle: 17 },
  { x: 0.67, y: 0.43, angle: -16 },
  { x: 0.42, y: 0.72, angle: 8 },
  { x: 0.61, y: 0.28, angle: 13 },
  { x: 0.52, y: 0.79, angle: -2 },
  { x: 0.25, y: 0.38, angle: -18 },
  { x: 0.73, y: 0.58, angle: 18 },
];

let resizeTimer = null;

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();

    img.onload = () => resolve(img);

    img.onerror = reject;

    img.src = src;
  });
}

function createRoleMask(img) {
  const canvas = document.createElement('canvas');

  canvas.width = PANEL_W;
  canvas.height = PANEL_H;

  const ctx = canvas.getContext('2d');

  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, PANEL_W, PANEL_H);

  const scale = Math.min((PANEL_W * 1.08) / img.width, (PANEL_H * 1.08) / img.height);

  const dw = img.width * scale;
  const dh = img.height * scale;

  const dx = (PANEL_W - dw) / 2;
  const dy = (PANEL_H - dh) / 2;

  ctx.drawImage(img, dx, dy, dw, dh);

  const imageData = ctx.getImageData(0, 0, PANEL_W, PANEL_H);

  const data = imageData.data;

  let mask = new Uint8Array(PANEL_W * PANEL_H);

  for (let i = 0; i < PANEL_W * PANEL_H; i += 1) {
    const r = data[i * 4];
    const g = data[i * 4 + 1];
    const b = data[i * 4 + 2];
    const a = data[i * 4 + 3];

    const isNotWhite = a > 8 && !(r > 238 && g > 238 && b > 238);

    if (isNotWhite) {
      mask[i] = 1;
    }
  }

  mask = keepLargestComponent(mask);
  mask = dilate(mask, 2);
  mask = fillHoles(mask);
  mask = erode(mask, 1);

  return mask;
}

function keepLargestComponent(mask) {
  const visited = new Uint8Array(PANEL_W * PANEL_H);

  let best = [];

  for (let i = 0; i < mask.length; i += 1) {
    if (!mask[i] || visited[i]) continue;

    const queue = [i];
    const component = [];

    visited[i] = 1;

    while (queue.length) {
      const current = queue.pop();

      component.push(current);

      const x = current % PANEL_W;
      const y = Math.floor(current / PANEL_W);

      const neighbors = [
        current - 1,
        current + 1,
        current - PANEL_W,
        current + PANEL_W,
      ];

      for (const next of neighbors) {
        if (next < 0 || next >= mask.length) continue;

        const nx = next % PANEL_W;
        const ny = Math.floor(next / PANEL_W);

        if (Math.abs(nx - x) + Math.abs(ny - y) !== 1) continue;

        if (!mask[next] || visited[next]) continue;

        visited[next] = 1;

        queue.push(next);
      }
    }

    if (component.length > best.length) {
      best = component;
    }
  }

  const result = new Uint8Array(PANEL_W * PANEL_H);

  best.forEach(index => {
    result[index] = 1;
  });

  return result;
}

function dilate(mask, radius) {
  const result = new Uint8Array(PANEL_W * PANEL_H);

  for (let y = 0; y < PANEL_H; y += 1) {
    for (let x = 0; x < PANEL_W; x += 1) {
      let hit = false;

      for (let dy = -radius; dy <= radius && !hit; dy += 1) {
        for (let dx = -radius; dx <= radius; dx += 1) {
          const nx = x + dx;
          const ny = y + dy;

          if (nx < 0 || ny < 0 || nx >= PANEL_W || ny >= PANEL_H) continue;

          if (mask[ny * PANEL_W + nx]) {
            hit = true;
            break;
          }
        }
      }

      if (hit) {
        result[y * PANEL_W + x] = 1;
      }
    }
  }

  return result;
}

function erode(mask, radius) {
  const result = new Uint8Array(PANEL_W * PANEL_H);

  for (let y = 0; y < PANEL_H; y += 1) {
    for (let x = 0; x < PANEL_W; x += 1) {
      let keep = true;

      for (let dy = -radius; dy <= radius && keep; dy += 1) {
        for (let dx = -radius; dx <= radius; dx += 1) {
          const nx = x + dx;
          const ny = y + dy;

          if (nx < 0 || ny < 0 || nx >= PANEL_W || ny >= PANEL_H) {
            keep = false;
            break;
          }

          if (!mask[ny * PANEL_W + nx]) {
            keep = false;
            break;
          }
        }
      }

      if (keep) {
        result[y * PANEL_W + x] = 1;
      }
    }
  }

  return result;
}

function fillHoles(mask) {
  const outside = new Uint8Array(PANEL_W * PANEL_H);

  const queue = [];

  for (let x = 0; x < PANEL_W; x += 1) {
    queue.push(x);
    queue.push((PANEL_H - 1) * PANEL_W + x);
  }

  for (let y = 0; y < PANEL_H; y += 1) {
    queue.push(y * PANEL_W);
    queue.push(y * PANEL_W + PANEL_W - 1);
  }

  while (queue.length) {
    const current = queue.pop();

    if (outside[current] || mask[current]) continue;

    outside[current] = 1;

    const x = current % PANEL_W;
    const y = Math.floor(current / PANEL_W);

    const neighbors = [
      current - 1,
      current + 1,
      current - PANEL_W,
      current + PANEL_W,
    ];

    for (const next of neighbors) {
      if (next < 0 || next >= mask.length) continue;

      const nx = next % PANEL_W;
      const ny = Math.floor(next / PANEL_W);

      if (Math.abs(nx - x) + Math.abs(ny - y) !== 1) continue;

      if (!outside[next] && !mask[next]) {
        queue.push(next);
      }
    }
  }

  const result = new Uint8Array(PANEL_W * PANEL_H);

  for (let i = 0; i < mask.length; i += 1) {
    result[i] = mask[i] || !outside[i] ? 1 : 0;
  }

  return result;
}

function drawMaskShape(ctx, mask, role) {
  const imageData = ctx.createImageData(PANEL_W, PANEL_H);

  for (let i = 0; i < mask.length; i += 1) {
    if (!mask[i]) continue;

    imageData.data[i * 4] = 100;
    imageData.data[i * 4 + 1] = 100;
    imageData.data[i * 4 + 2] = 100;
    imageData.data[i * 4 + 3] = 190;
  }

  const temp = document.createElement('canvas');

  temp.width = PANEL_W;
  temp.height = PANEL_H;

  const tctx = temp.getContext('2d');

  tctx.putImageData(imageData, 0, 0);

  tctx.globalCompositeOperation = 'source-in';

  tctx.fillStyle = role.color;
  tctx.fillRect(0, 0, PANEL_W, PANEL_H);

  ctx.drawImage(temp, role.x, role.y);
}

function isInside(mask, x, y) {
  if (x < 0 || y < 0 || x >= PANEL_W || y >= PANEL_H) return false;

  return mask[Math.floor(y) * PANEL_W + Math.floor(x)] === 1;
}

function buildMaskCenters(mask) {
  const centers = [];

  for (let y = 8; y < PANEL_H - 8; y += 3) {
    for (let x = 8; x < PANEL_W - 8; x += 3) {
      if (!isInside(mask, x, y)) continue;

      const dx = x - PANEL_W / 2;
      const dy = y - PANEL_H / 2;

      const centerDistance = Math.sqrt(dx * dx + dy * dy);

      const noise = pseudoRandom(`${x}-${y}`) * 28;

      centers.push({
        x,
        y,
        score: centerDistance + noise,
      });
    }
  }

  return centers.sort((a, b) => a.score - b.score);
}

function pseudoRandom(seed) {
  let h = 2166136261;

  const str = String(seed);

  for (let i = 0; i < str.length; i += 1) {
    h ^= str.charCodeAt(i);
    h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24);
  }

  return ((h >>> 0) % 10000) / 10000;
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

function buildDenseWords(source) {
  const weights = source.map(item => item[1]);

  const maxWeight = Math.max(...weights);
  const minWeight = Math.min(...weights);

  const words = [];

  source.forEach(([text, weight], index) => {
    const t = (weight - minWeight) / Math.max(1, maxWeight - minWeight);

    const size = index === 0
      ? MAX_FONT_SIZE
      : Math.round(lerp(13, 30, Math.pow(t, 0.82)));

    const anchor = importantAnchors[index] || makeRandomAnchor(text, index);

    words.push({
      id: `${text}-main-${index}`,
      text,
      size,
      minSize: Math.max(MIN_FONT_SIZE, size - 7),
      rank: index,
      anchor,
      opacity: index < 3 ? 0.96 : index < 10 ? 0.88 : 0.78,
      weight: index < 3 ? 700 : 600,
      isMain: index < 3,
    });
  });

  for (let repeat = 0; repeat < REPEAT_SMALL_WORDS; repeat += 1) {
    source.forEach(([text, weight], index) => {
      if (words.length >= MAX_WORDS_PER_ROLE) return;

      const t = (weight - minWeight) / Math.max(1, maxWeight - minWeight);

      const size = Math.round(lerp(8, 17, Math.pow(t, 0.72)) - repeat * 1.2);

      const safeSize = clamp(size, MIN_FONT_SIZE, 17);

      words.push({
        id: `${text}-small-${repeat}-${index}`,
        text,
        size: safeSize,
        minSize: Math.max(7, safeSize - 3),
        rank: source.length + repeat * source.length + index,
        anchor: makeRandomAnchor(`${text}-${repeat}`, index + repeat * 19),
        opacity: repeat === 0 ? 0.72 : repeat === 1 ? 0.62 : 0.52,
        weight: 500,
        isMain: false,
      });
    });
  }

  return words.sort((a, b) => {
    if (b.size !== a.size) return b.size - a.size;

    return a.rank - b.rank;
  });
}

function makeRandomAnchor(text, index) {
  const r1 = pseudoRandom(`${text}-${index}-x`);
  const r2 = pseudoRandom(`${text}-${index}-y`);
  const r3 = pseudoRandom(`${text}-${index}-a`);

  const angleList = [-24, -18, -12, -7, 0, 6, 11, 16, 22, 90, -90];

  const angleIndex = Math.floor(r3 * angleList.length);

  return {
    x: 0.18 + r1 * 0.64,
    y: 0.18 + r2 * 0.64,
    angle: angleList[angleIndex],
  };
}

function measureTextSize(ctx, text, size, weight) {
  ctx.save();

  ctx.font = `${weight} ${size}px ${textFont}`;

  const width = ctx.measureText(text).width;

  ctx.restore();

  return {
    width,
    height: size * 1.02,
  };
}

function getRotatedBounds(width, height, angle) {
  const rad = Math.abs((angle * Math.PI) / 180);

  const cos = Math.cos(rad);
  const sin = Math.sin(rad);

  return {
    width: width * cos + height * sin,
    height: width * sin + height * cos,
  };
}

function rectPoints(cx, cy, width, height, angle, step = MASK_SAMPLE_STEP) {
  const rad = (angle * Math.PI) / 180;

  const cos = Math.cos(rad);
  const sin = Math.sin(rad);

  const points = [];

  for (let y = -height / 2; y <= height / 2; y += step) {
    for (let x = -width / 2; x <= width / 2; x += step) {
      points.push({
        x: cx + x * cos - y * sin,
        y: cy + x * sin + y * cos,
      });
    }
  }

  points.push(
    {
      x: cx + (-width / 2) * cos - (-height / 2) * sin,
      y: cy + (-width / 2) * sin + (-height / 2) * cos,
    },
    {
      x: cx + (width / 2) * cos - (-height / 2) * sin,
      y: cy + (width / 2) * sin + (-height / 2) * cos,
    },
    {
      x: cx + (-width / 2) * cos - (height / 2) * sin,
      y: cy + (-width / 2) * sin + (height / 2) * cos,
    },
    {
      x: cx + (width / 2) * cos - (height / 2) * sin,
      y: cy + (width / 2) * sin + (height / 2) * cos,
    },
  );

  return points;
}

function rotatedRectInsideMask(mask, cx, cy, width, height, angle) {
  const points = rectPoints(cx, cy, width, height, angle);

  return points.every(point => isInside(mask, point.x, point.y));
}

function rectsOverlap(a, b, gap = WORD_GAP) {
  return (
    a.x < b.x + b.width + gap
    && a.x + a.width + gap > b.x
    && a.y < b.y + b.height + gap
    && a.y + a.height + gap > b.y
  );
}

function getAngleCandidates(word) {
  const base = word.anchor.angle;

  if (word.isMain) {
    return [base, 0, base > 0 ? base - 8 : base + 8];
  }

  if (Math.abs(base) === 90) {
    return [base, 0, base > 0 ? 14 : -14];
  }

  return [base, 0, base + 8, base - 8, base > 0 ? -base : Math.abs(base)];
}

function buildSpiralCandidates(word) {
  const targetX = word.anchor.x * PANEL_W;
  const targetY = word.anchor.y * PANEL_H;

  const candidates = [];

  const maxRadius = word.isMain ? 42 : 125;
  const radiusStep = word.isMain ? 7 : 9;
  const angleStep = word.isMain ? 36 : 22;

  candidates.push({
    x: targetX,
    y: targetY,
  });

  for (let radius = radiusStep; radius <= maxRadius; radius += radiusStep) {
    for (let angle = 0; angle < 360; angle += angleStep) {
      const rad = (angle * Math.PI) / 180;

      candidates.push({
        x: targetX + Math.cos(rad) * radius,
        y: targetY + Math.sin(rad) * radius,
      });
    }
  }

  return candidates;
}

function buildPlacementCandidates(centers, word) {
  const targetX = word.anchor.x * PANEL_W;
  const targetY = word.anchor.y * PANEL_H;

  const candidates = buildSpiralCandidates(word);

  const shuffledCenters = centers
    .map(center => {
      const dx = center.x - targetX;
      const dy = center.y - targetY;
      const distance = Math.sqrt(dx * dx + dy * dy);

      const noise = pseudoRandom(`${word.id}-${center.x}-${center.y}`) * 52;

      return {
        x: center.x,
        y: center.y,
        score: distance + noise,
      };
    })
    .sort((a, b) => a.score - b.score)
    .slice(0, word.isMain ? 260 : 620);

  candidates.push(...shuffledCenters);

  return candidates;
}

function findWordPlacement(ctx, mask, centers, placedRects, word) {
  const angles = getAngleCandidates(word);

  const candidates = buildPlacementCandidates(centers, word);

  for (let size = word.size; size >= word.minSize; size -= 1) {
    const measured = measureTextSize(ctx, word.text, size, word.weight);

    for (const angle of angles) {
      const textWidth = measured.width + 2;
      const textHeight = measured.height + 1;

      const bounds = getRotatedBounds(textWidth, textHeight, angle);

      for (const candidate of candidates) {
        const rect = {
          x: candidate.x - bounds.width / 2,
          y: candidate.y - bounds.height / 2,
          width: bounds.width,
          height: bounds.height,
        };

        if (!rotatedRectInsideMask(mask, candidate.x, candidate.y, textWidth, textHeight, angle)) continue;

        if (placedRects.some(placed => rectsOverlap(rect, placed))) continue;

        return {
          ...word,
          x: candidate.x,
          y: candidate.y,
          size,
          angle,
          rect,
        };
      }
    }
  }

  return null;
}

function drawWord(ctx, role, item) {
  ctx.save();

  const x = Math.round(role.x + item.x) + 0.5;
  const y = Math.round(role.y + item.y) + 0.5;

  ctx.translate(x, y);

  ctx.rotate((item.angle * Math.PI) / 180);

  ctx.font = `${item.weight} ${item.size}px ${textFont}`;

  ctx.fillStyle = item.isMain ? role.strongTextColor : role.textColor;

  ctx.globalAlpha = item.opacity;

  ctx.textAlign = 'center';

  ctx.textBaseline = 'middle';

  ctx.fillText(item.text, 0, 0);

  ctx.restore();
}

function drawWordsForRole(ctx, mask, role) {
  const centers = buildMaskCenters(mask);

  const words = buildDenseWords(roleWordSources[role.wordKey]);

  const placedRects = [];

  words.forEach(word => {
    const placed = findWordPlacement(ctx, mask, centers, placedRects, word);

    if (!placed) return;

    placedRects.push(placed.rect);

    drawWord(ctx, role, placed);
  });
}

async function render() {
  await document.fonts?.ready;

  const canvas = canvasRef.value;

  if (!canvas) return;

  const dpr = window.devicePixelRatio || 1;

  const ratio = dpr * RENDER_QUALITY;

  canvas.width = Math.round(W * ratio);
  canvas.height = Math.round(H * ratio);

  const ctx = canvas.getContext('2d');

  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);

  ctx.clearRect(0, 0, W, H);

  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';

  for (const role of roles) {
    const img = await loadImage(role.src);

    const mask = createRoleMask(img);

    drawMaskShape(ctx, mask, role);

    drawWordsForRole(ctx, mask, role);
  }
}

function handleResize() {
  window.clearTimeout(resizeTimer);

  resizeTimer = window.setTimeout(() => {
    render();
  }, 120);
}

onMounted(async () => {
  await nextTick();

  await render();

  window.addEventListener('resize', handleResize);
});

onBeforeUnmount(() => {
  window.clearTimeout(resizeTimer);

  window.removeEventListener('resize', handleResize);
});
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

.poster-canvas {
  display: block;
  width: min(100%, 900px);
  height: auto;
  aspect-ratio: 5 / 2;
  object-fit: contain;
}
</style>