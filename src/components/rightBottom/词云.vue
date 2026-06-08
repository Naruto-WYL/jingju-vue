<template>
  <div class="role-poster">
    <canvas ref="canvasRef" class="poster-canvas"></canvas>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue';

import personImage from '../../assets/词云/生.jpg';
import danImage from '../../assets/词云/旦.jpg';
import jingImage from '../../assets/词云/净.jpg';
import moImage from '../../assets/词云/丑.jpg';

const canvasRef = ref(null);

// 在384和640之间取中间值，适当放大
const W = 512;   // 384 * 1.33，取中间值
const H = 288;   // 216 * 1.33

const PANEL_W = 112;  // 84 * 1.33
const PANEL_H = 224;  // 168 * 1.33

const textFont = '"Microsoft YaHei", "PingFang SC", sans-serif';

// 每个角色独立的文字列表 - 字号适当增大（用作降级数据）
const roleWordSources = {
  sheng: [
    ['老生', 10],
    ['武生', 9],
    ['小生', 9],
    ['唱腔', 9],
    ['台步', 8],
    ['身段', 8],
    ['板眼', 8],
    ['念白', 7],
    ['亮相', 7],
    ['行头', 7],
    ['西皮', 7],
    ['二黄', 6],
    ['锣鼓', 6],
    ['戏曲', 6],
    ['梨园', 5],
    ['票友', 5],
    ['科班', 5],
    ['角儿', 4],
  ],
  dan: [
    ['青衣', 10],
    ['花旦', 9],
    ['水袖', 9],
    ['唱腔', 9],
    ['台步', 8],
    ['身段', 8],
    ['亮相', 8],
    ['行头', 7],
    ['念白', 7],
    ['板眼', 7],
    ['锣鼓', 7],
    ['戏曲', 6],
    ['梨园', 6],
    ['票友', 6],
    ['科班', 5],
    ['角儿', 5],
    ['戏服', 4],
    ['脸谱', 4],
  ],
  jing: [
    ['脸谱', 10],
    ['花脸', 9],
    ['武净', 9],
    ['唱腔', 9],
    ['亮相', 8],
    ['行头', 8],
    ['身段', 8],
    ['锣鼓', 7],
    ['念白', 7],
    ['板眼', 7],
    ['台步', 7],
    ['戏曲', 6],
    ['梨园', 6],
    ['角儿', 6],
    ['票友', 5],
    ['科班', 5],
    ['西皮', 4],
    ['二黄', 4],
  ],
  mo: [
    ['老末', 10],
    ['末角', 9],
    ['唱腔', 9],
    ['台步', 9],
    ['身段', 8],
    ['念白', 8],
    ['板眼', 8],
    ['行头', 7],
    ['亮相', 7],
    ['锣鼓', 7],
    ['戏曲', 6],
    ['梨园', 6],
    ['票友', 6],
    ['科班', 5],
    ['角儿', 5],
    ['脸谱', 4],
    ['水袖', 4],
    ['戏服', 4],
  ],
};

// API 配置
const API_CONFIG = {
  // 后端接口地址（根据实际项目修改）
  url: '/api/opera-words',
  // 请求超时时间（毫秒）
  timeout: 5000,
  // 缓存有效期（毫秒）- 24小时
  cacheDuration: 24 * 60 * 60 * 1000,
  // localStorage 缓存键
  cacheKey: 'opera_role_words_cache',
};

/**
 * 从 localStorage 获取缓存数据
 */
function getCachedWords() {
  try {
    const cached = localStorage.getItem(API_CONFIG.cacheKey);
    if (!cached) return null;

    const { data, timestamp } = JSON.parse(cached);
    const now = Date.now();

    // 检查缓存是否过期
    if (now - timestamp > API_CONFIG.cacheDuration) {
      localStorage.removeItem(API_CONFIG.cacheKey);
      return null;
    }

    return data;
  } catch (error) {
    console.warn('读取缓存失败:', error);
    return null;
  }
}

/**
 * 保存数据到 localStorage
 */
function setCachedWords(data) {
  try {
    const cacheData = {
      data,
      timestamp: Date.now(),
    };
    localStorage.setItem(API_CONFIG.cacheKey, JSON.stringify(cacheData));
  } catch (error) {
    console.warn('保存缓存失败:', error);
  }
}

/**
 * 模拟后端数据请求接口
 * 在实际项目中，替换为真实的 API 请求
 */
async function fetchWordsFromAPI() {
  // 模拟网络延迟
  const delay = 500 + Math.random() * 1500;
  
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      // 模拟成功响应（90% 成功率）
      if (Math.random() > 0.1) {
        resolve({
          code: 200,
          message: 'success',
          data: {
            sheng: [
              ['老生', 10],
              ['武生', 9],
              ['小生', 9],
              ['唱腔', 9],
              ['台步', 8],
              ['身段', 8],
              ['板眼', 8],
              ['念白', 7],
              ['亮相', 7],
              ['行头', 7],
              ['西皮', 7],
              ['二黄', 6],
              ['锣鼓', 6],
              ['戏曲', 6],
              ['梨园', 5],
              ['票友', 5],
              ['科班', 5],
              ['角儿', 4],
            ],
            dan: [
              ['青衣', 10],
              ['花旦', 9],
              ['水袖', 9],
              ['唱腔', 9],
              ['台步', 8],
              ['身段', 8],
              ['亮相', 8],
              ['行头', 7],
              ['念白', 7],
              ['板眼', 7],
              ['锣鼓', 7],
              ['戏曲', 6],
              ['梨园', 6],
              ['票友', 6],
              ['科班', 5],
              ['角儿', 5],
              ['戏服', 4],
              ['脸谱', 4],
            ],
            jing: [
              ['脸谱', 10],
              ['花脸', 9],
              ['武净', 9],
              ['唱腔', 9],
              ['亮相', 8],
              ['行头', 8],
              ['身段', 8],
              ['锣鼓', 7],
              ['念白', 7],
              ['板眼', 7],
              ['台步', 7],
              ['戏曲', 6],
              ['梨园', 6],
              ['角儿', 6],
              ['票友', 5],
              ['科班', 5],
              ['西皮', 4],
              ['二黄', 4],
            ],
            mo: [
              ['老末', 10],
              ['末角', 9],
              ['唱腔', 9],
              ['台步', 9],
              ['身段', 8],
              ['念白', 8],
              ['板眼', 8],
              ['行头', 7],
              ['亮相', 7],
              ['锣鼓', 7],
              ['戏曲', 6],
              ['梨园', 6],
              ['票友', 6],
              ['科班', 5],
              ['角儿', 5],
              ['脸谱', 4],
              ['水袖', 4],
              ['戏服', 4],
            ],
          },
        });
      } else {
        // 模拟失败
        reject(new Error('Network error'));
      }
    }, delay);
  });

  // ============================================
  // 实际项目中替换为以下代码：
  // ============================================
  /*
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.timeout);

    const response = await fetch(API_CONFIG.url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    
    // 根据后端返回的数据结构调整
    if (result.code === 200) {
      return result;
    } else {
      throw new Error(result.message || 'API返回异常');
    }
  } catch (error) {
    console.error('请求文字列表失败:', error);
    throw error;
  }
  */
}

/**
 * 获取文字列表（主函数）
 * 优先级：API响应 > 缓存数据 > 本地降级数据
 */
async function getRoleWords() {
  // 1. 尝试从 API 获取
  try {
    console.log('正在从API获取文字列表...');
    const response = await fetchWordsFromAPI();
    
    // 验证数据格式
    if (response && response.data && validateWordsData(response.data)) {
      console.log('API请求成功，使用服务器数据');
      // 保存到缓存
      setCachedWords(response.data);
      return response.data;
    }
    
    throw new Error('API返回数据格式不正确');
  } catch (apiError) {
    console.warn('API请求失败，尝试使用缓存数据:', apiError.message);

    // 2. API失败，尝试使用缓存
    const cachedData = getCachedWords();
    if (cachedData && validateWordsData(cachedData)) {
      console.log('使用缓存数据');
      return cachedData;
    }

    // 3. 缓存也失败，使用本地降级数据
    console.log('使用本地降级数据');
    return roleWordSources;
  }
}

/**
 * 验证文字列表数据格式
 */
function validateWordsData(data) {
  const requiredKeys = ['sheng', 'dan', 'jing', 'mo'];
  
  // 检查是否包含所有角色
  const hasAllKeys = requiredKeys.every(key => key in data);
  if (!hasAllKeys) {
    console.warn('数据缺少必要的角色键');
    return false;
  }

  // 检查每个角色的数据格式
  for (const key of requiredKeys) {
    const words = data[key];
    
    if (!Array.isArray(words)) {
      console.warn(`${key} 的文字列表不是数组`);
      return false;
    }

    // 检查每个词条的格式：[文字, 字号]
    const isValid = words.every(item => 
      Array.isArray(item) && 
      item.length === 2 && 
      typeof item[0] === 'string' && 
      typeof item[1] === 'number'
    );

    if (!isValid) {
      console.warn(`${key} 的文字列表格式不正确`);
      return false;
    }
  }

  return true;
}

// 为每个角色生成多层淡化的文字列表 - 3层比较合适
let roleWords = {};

// 调整角色位置，保持合适的间距
// 增加轮廓背景的不透明度
// 添加角色名称颜色
const roles = [
  {
    name: '生',
    src: personImage,
    x: 50,
    y: -5,
    color: 'rgba(176, 198, 214, 0.75)',
    textColor: 'rgba(90, 120, 140, 0.9)',
    wordKey: 'sheng',
  },
  {
    name: '旦',
    src: danImage,
    x: 150,
    y: -5,
    color: 'rgba(229, 158, 150, 0.75)',
    textColor: 'rgba(160, 90, 85, 0.9)',
    wordKey: 'dan',
  },
  {
    name: '净',
    src: jingImage,
    x: 255,
    y: -5,
    color: 'rgba(168, 168, 168, 0.75)',
    textColor: 'rgba(90, 90, 90, 0.9)',
    wordKey: 'jing',
  },
  {
    name: '末',
    src: moImage,
    x: 360,
    y: -5,
    color: 'rgba(222, 195, 112, 0.75)',
    textColor: 'rgba(150, 130, 60, 0.9)',
    wordKey: 'mo',
  },
];

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
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, PANEL_W, PANEL_H);

  const scale = Math.min(PANEL_W * 0.88 / img.width, PANEL_H * 0.88 / img.height);
  const dw = img.width * scale;
  const dh = img.height * scale;
  const dx = (PANEL_W - dw) / 2;
  const dy = 4;

  ctx.drawImage(img, dx, dy, dw, dh);

  const imageData = ctx.getImageData(0, 0, PANEL_W, PANEL_H);
  const data = imageData.data;
  let mask = new Uint8Array(PANEL_W * PANEL_H);

  for (let i = 0; i < PANEL_W * PANEL_H; i += 1) {
    const r = data[i * 4];
    const g = data[i * 4 + 1];
    const b = data[i * 4 + 2];

    const notWhite = !(r > 238 && g > 238 && b > 238);
    if (notWhite) mask[i] = 1;
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

    if (component.length > best.length) best = component;
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

      if (hit) result[y * PANEL_W + x] = 1;
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

      if (keep) result[y * PANEL_W + x] = 1;
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
      if (!outside[next] && !mask[next]) queue.push(next);
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
    imageData.data[i * 4 + 3] = 180;
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

function rectPoints(cx, cy, w, h, angle, step = 3) {
  const rad = (angle * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  const points = [];

  for (let y = -h / 2; y <= h / 2; y += step) {
    for (let x = -w / 2; x <= w / 2; x += step) {
      points.push({
        x: cx + x * cos - y * sin,
        y: cy + x * sin + y * cos,
      });
    }
  }

  return points;
}

function canPlace(mask, occupied, cx, cy, w, h, angle) {
  const points = rectPoints(cx, cy, w, h, angle);

  for (const p of points) {
    const x = Math.floor(p.x);
    const y = Math.floor(p.y);

    if (!isInside(mask, x, y)) return false;
    if (occupied[y * PANEL_W + x]) return false;
  }

  return true;
}

function occupy(occupied, cx, cy, w, h, angle) {
  const points = rectPoints(cx, cy, w + 2, h + 2, angle, 2);

  for (const p of points) {
    const x = Math.floor(p.x);
    const y = Math.floor(p.y);

    if (x >= 0 && y >= 0 && x < PANEL_W && y < PANEL_H) {
      occupied[y * PANEL_W + x] = 1;
    }
  }
}

function measureText(text, size) {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');

  ctx.font = `${size}px ${textFont}`;

  return {
    width: ctx.measureText(text).width,
    height: size * 1.1,
  };
}

function buildCenters(mask) {
  const centers = [];

  for (let y = 8; y < PANEL_H - 8; y += 3) {
    for (let x = 8; x < PANEL_W - 8; x += 3) {
      if (!isInside(mask, x, y)) continue;

      const dx = x - PANEL_W / 2;
      const dy = y - PANEL_H / 2;

      centers.push({
        x,
        y,
        score: Math.sqrt(dx * dx + dy * dy) + Math.random() * 10,
      });
    }
  }

  return centers.sort((a, b) => a.score - b.score);
}

function drawWord(ctx, role, item) {
  ctx.save();

  const x = Math.round(role.x + item.x) + 0.5;
  const y = Math.round(role.y + item.y) + 0.5;

  ctx.translate(x, y);
  ctx.rotate(item.angle * Math.PI / 180);

  ctx.font = `${item.size}px ${textFont}`;
  ctx.fillStyle = '#111';
  ctx.globalAlpha = 1;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  ctx.fillText(item.text, 0, 0);

  ctx.restore();
}

function layoutWords(ctx, mask, role) {
  const occupied = new Uint8Array(PANEL_W * PANEL_H);
  const centers = buildCenters(mask);
  const angles = [0, -15, 15, 90];

  // 使用该角色专属的文字列表
  const words = roleWords[role.wordKey] || [];
  if (!words.length) return;

  const expandedWords = [...words].sort((a, b) => b.size - a.size);

  for (const word of expandedWords) {
    let placed = false;

    for (let size = word.size; size >= 6 && !placed; size -= 1) {
      const measured = measureText(word.text, size);

      for (const angle of angles) {
        const w = measured.width + 3;
        const h = measured.height + 2;

        for (const center of centers) {
          if (canPlace(mask, occupied, center.x, center.y, w, h, angle)) {
            drawWord(ctx, role, {
              text: word.text,
              x: center.x,
              y: center.y,
              size,
              angle,
            });

            occupy(occupied, center.x, center.y, w, h, angle);
            placed = true;
            break;
          }
        }

        if (placed) break;
      }
    }
  }
}

/**
 * 生成多层淡化的文字列表
 */
function generateRoleWords(sources) {
  const words = {};
  
  Object.keys(sources).forEach(roleKey => {
    words[roleKey] = Array.from({ length: 3 }).flatMap((_, round) =>
      sources[roleKey].map(([text, size]) => ({
        text,
        size: Math.max(4, Math.round(size * (1 - round * 0.12))),
      }))
    );
  });

  return words;
}

async function render() {
  await document.fonts?.ready;

  const canvas = canvasRef.value;

// 获取屏幕像素比，例如高清屏一般是 2
const dpr = window.devicePixelRatio || 1;

// 再额外提高清晰度，2 基本够用，想更清楚可以改 3
const quality = 2.5;

// 最终绘制倍率
const ratio = dpr * quality;

// canvas 内部真实像素变大
canvas.width = Math.round(W * ratio);
canvas.height = Math.round(H * ratio);

// 注意：不要在这里改 canvas.style.width / height
// 让 CSS 继续控制现在的视觉大小

const ctx = canvas.getContext('2d');

// 把绘图坐标缩放回原来的 W / H 逻辑尺寸
ctx.setTransform(ratio, 0, 0, ratio, 0, 0);

// 清空画布
ctx.clearRect(0, 0, W, H);

// 图片缩放质量设高
ctx.imageSmoothingEnabled = true;
ctx.imageSmoothingQuality = 'high';

  // 获取文字列表（带降级处理）
  const wordSources = await getRoleWords();
  roleWords = generateRoleWords(wordSources);

  // 透明背景
  for (const role of roles) {
    const img = await loadImage(role.src);
    const mask = createRoleMask(img);

    drawMaskShape(ctx, mask, role);
    layoutWords(ctx, mask, role);

    ctx.save();
    ctx.font = `700 10px ${textFont}`;
    ctx.fillStyle = role.textColor;
    ctx.textAlign = 'center';
    ctx.fillText(role.name, role.x + PANEL_W / 2, role.y + PANEL_H - 103);
    ctx.restore();
  }

  console.log('海报渲染完成');
}

onMounted(async () => {
  await nextTick();
  render();
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
  width: min(100%, 540px);
  max-height: 100%;
  aspect-ratio: 16 / 9;
  object-fit: contain;
  transform: translateY(24px) scale(1.28);
  transform-origin: top center;
}
</style>
