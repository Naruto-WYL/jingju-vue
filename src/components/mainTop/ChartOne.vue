<template>
  <div class="rtn-page">
    <div class="stage-strip">
      <button
        v-for="stage in stageOptions"
        :key="stage.key"
        class="stage-btn"
        :class="{ active: selectedStage === stage.key }"
        @click="selectedStage = stage.key"
      >
        <span>{{ stage.name }}</span>
        <small>{{ stage.desc }}</small>
      </button>
    </div>

    <main class="dashboard">
      <section class="center-panel panel">
        <div class="panel-title row-title">
          <span>角色关系 → 主题结构 → 叙事结构</span>
          <span class="hint">点击线条可查看说明</span>
        </div>

        <div class="summary-row">
          <strong>{{ currentStageName }}</strong>
          <span>{{ currentSummary.event }}</span>
        </div>

        <div class="flow-wrap">
          <svg
            ref="svgRef"
            class="flow-svg"
            :viewBox="`0 0 ${svgWidth} ${svgHeight}`"
            preserveAspectRatio="xMidYMid meet"
          >
            <!-- 背景水墨纹理线 -->
            <g opacity="0.25">
              <path
                v-for="(line, index) in inkLines"
                :key="index"
                :d="line"
                fill="none"
                stroke="#d9c8a9"
                stroke-width="1"
              />
            </g>

            <!-- 三列标题 -->
            <g class="column-title">
              <text :x="relationX" y="36">角色关系</text>
              <text :x="themeX" y="36">主题结构</text>
              <text :x="narrativeX" y="36">叙事结构</text>
            </g>

            <!-- 连接线：关系 -> 主题 -->
            <g>
              <path
                v-for="item in visibleLinks"
                :key="item.id + '-rt'"
                class="flow-link"
                :class="{ active: activeLink && activeLink.id === item.id }"
                :d="makeCurve(item.relationPos, item.themePos)"
                :stroke="item.color"
                :stroke-width="item.strength"
                @mouseenter="activeLink = item"
                @mouseleave="activeLink = null"
                @click="activeLink = item"
              />
            </g>

            <!-- 连接线：主题 -> 叙事 -->
            <g>
              <path
                v-for="item in visibleLinks"
                :key="item.id + '-tn'"
                class="flow-link"
                :class="{ active: activeLink && activeLink.id === item.id }"
                :d="makeCurve(item.themePos, item.narrativePos)"
                :stroke="item.color"
                :stroke-width="item.strength"
                @mouseenter="activeLink = item"
                @mouseleave="activeLink = null"
                @click="activeLink = item"
              />
            </g>

            <!-- 关系节点 -->
            <g>
              <g
                v-for="node in relationNodes"
                :key="node.name"
                class="flow-node"
                :class="{ faded: !isNodeActive(node.name, 'relation') }"
                :transform="`translate(${relationX}, ${node.y})`"
              >
                <circle r="17" :fill="node.color" />
                <circle r="21" fill="none" stroke="#6f1d1b" stroke-dasharray="4 4" opacity="0.55" />
                <text x="34" y="-2">{{ node.name }}</text>
                <text x="34" y="16" class="node-sub">{{ node.desc }}</text>
              </g>
            </g>

            <!-- 主题节点 -->
            <g>
              <g
                v-for="node in themeNodes"
                :key="node.name"
                class="flow-node theme-node"
                :class="{ faded: !isNodeActive(node.name, 'theme') }"
                :transform="`translate(${themeX}, ${node.y})`"
              >
                <rect x="-20" y="-18" width="40" height="36" rx="12" :fill="node.color" />
                <text x="34" y="-2">{{ node.name }}</text>
                <text x="34" y="16" class="node-sub">{{ node.desc }}</text>
              </g>
            </g>

            <!-- 叙事节点 -->
            <g>
              <g
                v-for="node in narrativeNodes"
                :key="node.name"
                class="flow-node narrative-node"
                :class="{ faded: !isNodeActive(node.name, 'narrative') }"
                :transform="`translate(${narrativeX}, ${node.y})`"
              >
                <path
                  d="M -22 -16 L 18 -16 L 26 0 L 18 16 L -22 16 L -14 0 Z"
                  :fill="node.color"
                />
                <text x="38" y="-2">{{ node.name }}</text>
                <text x="38" y="16" class="node-sub">{{ node.desc }}</text>
              </g>
            </g>
          </svg>

          <!-- 线条说明浮层 -->
          <div v-if="activeLink" class="link-detail">
            <h4>{{ activeLink.relation }} → {{ activeLink.theme }} → {{ activeLink.narrative }}</h4>
            <p>{{ activeLink.detail }}</p>
            <div class="detail-row">
              <span>阶段：{{ activeLink.stageName }}</span>
              <span>强度：{{ activeLink.strength }}</span>
            </div>
          </div>
        </div>

      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const selectedStage = ref('all')
const activeLink = ref(null)

const svgWidth = 1000
const svgHeight = 520

const relationX = 90
const themeX = 420
const narrativeX = 735

const stages = [
  {
    key: 'start',
    short: '开端',
    name: '阶段一：开端',
    desc: '寻夫入京',
    event: '秦香莲带子进京寻夫',
  },
  {
    key: 'develop',
    short: '发展',
    name: '阶段二：发展',
    desc: '拒认妻儿',
    event: '陈世美拒认妻儿',
  },
  {
    key: 'conflict',
    short: '冲突',
    name: '阶段三：冲突',
    desc: '秦香莲告状',
    event: '秦香莲向包拯申诉',
  },
  {
    key: 'climax',
    short: '高潮',
    name: '阶段四：高潮',
    desc: '抗权审判',
    event: '皇权势力干预审判，包拯抗权',
  },
  {
    key: 'ending',
    short: '结局',
    name: '阶段五：结局',
    desc: '铡美昭雪',
    event: '包拯铡陈世美，秦香莲昭雪',
  },
]

const stageOptions = [
  {
    key: 'all',
    name: '全剧',
    desc: '查看完整演化链条',
  },
  ...stages,
]

const currentStageName = computed(() => {
  const target = stageOptions.find((item) => item.key === selectedStage.value)
  return target ? target.name : '全剧'
})

const summaries = {
  all: {
    event: '从秦香莲寻夫到包拯铡美，完整呈现伦理冲突、公案审判、权力斗争和秩序恢复。',
    roleChange: '秦香莲：妻子→受害者→申诉者→昭雪者；陈世美：丈夫→负心者→被告→罪犯；包拯：审判者→抗权清官。',
    analysis: '全剧形成“家庭伦理启动—公案审判推进—权力斗争高潮—秩序恢复结局”的稳定模式。',
  },
  start: {
    event: '秦香莲带着子女进京寻找陈世美。',
    roleChange: '秦香莲主要以妻子、母亲身份出现，陈世美仍处于丈夫、父亲的伦理位置。',
    analysis: '这一阶段主要建立家庭伦理基础，为后续伦理破裂制造前提。',
  },
  develop: {
    event: '陈世美拒认秦香莲和子女，家庭伦理关系发生断裂。',
    roleChange: '夫妻关系转化为夫妻破裂，父子关系转化为身份否认。',
    analysis: '角色关系变化直接激活家庭伦理主题，使私人家庭矛盾成为剧情冲突来源。',
  },
  conflict: {
    event: '秦香莲向包拯申诉，公堂审判结构开始介入。',
    roleChange: '秦香莲从妻子转化为受害者和申诉者，包拯成为审判者。',
    analysis: '家庭伦理问题被转化为公案审判问题，叙事从私人冲突进入公共司法空间。',
  },
  climax: {
    event: '皇权势力干预审判，包拯与权势发生正面对抗。',
    roleChange: '包拯从审判者进一步转化为抗权清官，皇权势力成为新的对立方。',
    analysis: '权力斗争主题增强，审判叙事被推向高潮，戏剧张力达到最高点。',
  },
  ending: {
    event: '包拯最终铡陈世美，秦香莲获得昭雪。',
    roleChange: '陈世美由被告转化为罪犯，秦香莲由受害者转化为被昭雪者。',
    analysis: '结局完成对家庭伦理、公案正义和社会秩序的共同修复。',
  },
}

const currentSummary = computed(() => summaries[selectedStage.value] || summaries.all)

const rawLinks = [
  {
    id: 'l1',
    stage: 'start',
    stageName: '阶段一：开端',
    relation: '夫妻 / 母子关系',
    theme: '家庭伦理',
    narrative: '身份建立',
    strength: 4,
    color: '#b85c38',
    detail: '秦香莲以妻子、母亲身份登场，家庭伦理关系被首先建立，为后续冲突提供基础。',
  },
  {
    id: 'l2',
    stage: 'develop',
    stageName: '阶段二：发展',
    relation: '夫妻破裂',
    theme: '家庭伦理',
    narrative: '关系冲突',
    strength: 6,
    color: '#a83232',
    detail: '陈世美拒认妻儿，使夫妻关系由亲密伦理关系转化为尖锐对立，家庭伦理主题被强化。',
  },
  {
    id: 'l3',
    stage: 'develop',
    stageName: '阶段二：发展',
    relation: '父子断裂',
    theme: '道德失范',
    narrative: '身份否认',
    strength: 4,
    color: '#c27c3c',
    detail: '陈世美否认子女身份，使父子伦理被破坏，人物道德失范成为叙事矛盾的一部分。',
  },
  {
    id: 'l4',
    stage: 'conflict',
    stageName: '阶段三：冲突',
    relation: '申诉关系',
    theme: '公案审判',
    narrative: '案件提出',
    strength: 5,
    color: '#2f6f73',
    detail: '秦香莲向包拯申诉，家庭伦理矛盾进入公堂，私人冲突被转化为公共审判问题。',
  },
  {
    id: 'l5',
    stage: 'conflict',
    stageName: '阶段三：冲突',
    relation: '审判关系',
    theme: '公案审判',
    narrative: '审判推进',
    strength: 5,
    color: '#457b9d',
    detail: '包拯与陈世美之间形成审判者和被告的关系，推动剧情进入调查、对质和审理环节。',
  },
  {
    id: 'l6',
    stage: 'climax',
    stageName: '阶段四：高潮',
    relation: '清官抗权',
    theme: '权力斗争',
    narrative: '审判高潮',
    strength: 7,
    color: '#7f1d1d',
    detail: '皇权势力干预审判，包拯坚持法理，使普通公案升级为清官与权势的正面对抗。',
  },
  {
    id: 'l7',
    stage: 'ending',
    stageName: '阶段五：结局',
    relation: '昭雪关系',
    theme: '复仇伸冤',
    narrative: '真相揭示与惩罚',
    strength: 6,
    color: '#8a6f3d',
    detail: '陈世美被惩处，秦香莲获得昭雪，伦理秩序和司法秩序被重新确认。',
  },
  {
    id: 'l8',
    stage: 'ending',
    stageName: '阶段五：结局',
    relation: '秩序恢复',
    theme: '家庭伦理',
    narrative: '秩序恢复',
    strength: 5,
    color: '#9b5c2e',
    detail: '结局并非单纯惩罚个人，而是通过审判完成家庭伦理、法律正义和社会秩序的修复。',
  },
]

const relationNodes = [
  {
    name: '夫妻 / 母子关系',
    desc: '伦理基础',
    y: 90,
    color: '#c96b4b',
  },
  {
    name: '夫妻破裂',
    desc: '冲突起点',
    y: 145,
    color: '#a83232',
  },
  {
    name: '父子断裂',
    desc: '身份否认',
    y: 200,
    color: '#c27c3c',
  },
  {
    name: '申诉关系',
    desc: '受害者进入公堂',
    y: 255,
    color: '#2f6f73',
  },
  {
    name: '审判关系',
    desc: '清官审理',
    y: 310,
    color: '#457b9d',
  },
  {
    name: '清官抗权',
    desc: '法理对抗权势',
    y: 365,
    color: '#7f1d1d',
  },
  {
    name: '昭雪关系',
    desc: '受害者获得正义',
    y: 420,
    color: '#8a6f3d',
  },
  {
    name: '秩序恢复',
    desc: '关系重新定位',
    y: 475,
    color: '#9b5c2e',
  },
]

const themeNodes = [
  {
    name: '家庭伦理',
    desc: '夫妻、父子、母子伦理',
    y: 120,
    color: '#d8a48f',
  },
  {
    name: '道德失范',
    desc: '负心、背义、身份否认',
    y: 205,
    color: '#d0a15f',
  },
  {
    name: '公案审判',
    desc: '申诉、审理、对质',
    y: 290,
    color: '#83a9b3',
  },
  {
    name: '权力斗争',
    desc: '皇权干预与清官抗权',
    y: 375,
    color: '#a94f4f',
  },
  {
    name: '复仇伸冤',
    desc: '昭雪与惩罚',
    y: 455,
    color: '#b7a16a',
  },
]

const narrativeNodes = [
  {
    name: '身份建立',
    desc: '交代人物伦理位置',
    y: 80,
    color: '#e1c3ad',
  },
  {
    name: '关系冲突',
    desc: '伦理关系破裂',
    y: 135,
    color: '#c56b58',
  },
  {
    name: '身份否认',
    desc: '制造道德冲突',
    y: 190,
    color: '#c8955e',
  },
  {
    name: '案件提出',
    desc: '私人冲突进入公堂',
    y: 245,
    color: '#79a9a4',
  },
  {
    name: '审判推进',
    desc: '调查、对质、审理',
    y: 300,
    color: '#6f9fba',
  },
  {
    name: '审判高潮',
    desc: '清官对抗权力',
    y: 355,
    color: '#a13e3e',
  },
  {
    name: '真相揭示与惩罚',
    desc: '罪责确认',
    y: 420,
    color: '#b49d63',
  },
  {
    name: '秩序恢复',
    desc: '伦理和法理收束',
    y: 480,
    color: '#9b7c48',
  },
]

const visibleLinks = computed(() => {
  const links =
    selectedStage.value === 'all'
      ? rawLinks
      : rawLinks.filter((item) => item.stage === selectedStage.value)

  return links.map((item) => {
    const relationNode = relationNodes.find((node) => node.name === item.relation)
    const themeNode = themeNodes.find((node) => node.name === item.theme)
    const narrativeNode = narrativeNodes.find((node) => node.name === item.narrative)

    return {
      ...item,
      relationPos: {
        x: relationX + 18,
        y: relationNode ? relationNode.y : 0,
      },
      themePos: {
        x: themeX - 22,
        y: themeNode ? themeNode.y : 0,
      },
      narrativePos: {
        x: narrativeX - 28,
        y: narrativeNode ? narrativeNode.y : 0,
      },
    }
  })
})

function makeCurve(start, end) {
  const midX = (start.x + end.x) / 2
  return `M ${start.x} ${start.y} C ${midX} ${start.y}, ${midX} ${end.y}, ${end.x} ${end.y}`
}

function isNodeActive(name, type) {
  if (selectedStage.value === 'all' && !activeLink.value) return true

  const links = visibleLinks.value

  if (activeLink.value) {
    if (type === 'relation') return activeLink.value.relation === name
    if (type === 'theme') return activeLink.value.theme === name
    if (type === 'narrative') return activeLink.value.narrative === name
  }

  if (type === 'relation') return links.some((item) => item.relation === name)
  if (type === 'theme') return links.some((item) => item.theme === name)
  if (type === 'narrative') return links.some((item) => item.narrative === name)

  return true
}

const inkLines = [
  'M20 460 C180 410, 260 500, 390 445 S620 400, 820 470',
  'M60 80 C160 120, 260 40, 390 100 S640 130, 890 70',
  'M120 250 C240 210, 310 310, 450 265 S700 210, 930 280',
]
</script>

<style scoped>
.rtn-page {
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 0;
  box-sizing: border-box;
  color: #3f352b;
  background: transparent;
  font-family:
    "Microsoft YaHei",
    "PingFang SC",
    "Noto Serif SC",
    sans-serif;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 8px;
}

.stage-strip {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 6px;
  min-height: 0;
}

.dashboard {
  display: grid;
  min-height: 0;
  height: 100%;
}

.panel {
  border: 1px solid rgba(112, 76, 46, 0.2);
  border-radius: 8px;
  background: rgba(255, 250, 240, 0.72);
}

.center-panel {
  padding: 8px;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.panel-title {
  font-weight: 700;
  font-size: 13px;
  color: #5f241f;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.panel-title::before {
  content: "";
  width: 4px;
  height: 14px;
  border-radius: 99px;
  background: #8f2d2d;
}

.row-title {
  justify-content: space-between;
}

.hint {
  font-size: 11px;
  font-weight: 400;
  color: #8b7b69;
}

.stage-btn {
  min-width: 0;
  height: 42px;
  padding: 5px 8px;
  text-align: center;
  border: 1px solid rgba(112, 76, 46, 0.18);
  border-radius: 8px;
  background: rgba(248, 239, 220, 0.7);
  color: #4b3b2b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.stage-btn span {
  display: block;
  overflow: hidden;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stage-btn small {
  display: block;
  overflow: hidden;
  margin-top: 2px;
  color: #7c6d5c;
  font-size: 10px;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stage-btn:hover {
  border-color: rgba(130, 40, 36, 0.4);
}

.stage-btn.active {
  background: #8f2d2d;
  color: #fff8ea;
  border-color: #8f2d2d;
  box-shadow: 0 8px 18px rgba(143, 45, 45, 0.18);
}

.stage-btn.active small {
  color: #f3ddc6;
}

.summary-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  margin-bottom: 6px;
  padding: 6px 8px;
  border: 1px solid rgba(112, 76, 46, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.42);
  color: #68523e;
  font-size: 12px;
  line-height: 1.25;
}

.summary-row strong {
  flex: 0 0 auto;
  color: #6f231f;
}

.summary-row span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.flow-wrap {
  position: relative;
  height: calc(100% - 58px);
  min-height: 0;
  border-radius: 8px;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(255, 250, 238, 0.9), rgba(244, 235, 216, 0.8)),
    repeating-linear-gradient(
      90deg,
      rgba(120, 90, 60, 0.04) 0,
      rgba(120, 90, 60, 0.04) 1px,
      transparent 1px,
      transparent 80px
    );
  border: 1px solid rgba(110, 72, 40, 0.14);
}

.flow-svg {
  width: 100%;
  height: 100%;
}

.column-title text {
  font-size: 16px;
  font-weight: 700;
  fill: #5f241f;
  text-anchor: middle;
}

.flow-link {
  fill: none;
  opacity: 0.42;
  cursor: pointer;
  stroke-linecap: round;
  transition: all 0.2s ease;
}

.flow-link:hover,
.flow-link.active {
  opacity: 0.95;
  filter: drop-shadow(0 0 4px rgba(120, 50, 30, 0.35));
}

.flow-node {
  cursor: default;
  transition: all 0.2s ease;
}

.flow-node text {
  font-size: 13px;
  font-weight: 700;
  fill: #3d3329;
}

.flow-node .node-sub {
  font-size: 10px;
  font-weight: 400;
  fill: #7b6c5b;
}

.flow-node.faded {
  opacity: 0.22;
}

.link-detail {
  position: absolute;
  left: 12px;
  bottom: 12px;
  width: min(420px, calc(100% - 24px));
  padding: 10px 12px;
  border-radius: 8px;
  color: #3f3328;
  background: rgba(255, 248, 230, 0.95);
  border: 1px solid rgba(130, 68, 40, 0.22);
  box-shadow: 0 10px 24px rgba(70, 47, 26, 0.14);
}

.link-detail h4 {
  margin: 0 0 6px;
  color: #6f231f;
  font-size: 13px;
}

.link-detail p {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
}

.detail-row {
  display: flex;
  gap: 16px;
  margin-top: 6px;
  font-size: 12px;
  color: #8b5c38;
}

@media (max-width: 900px) {
  .stage-strip {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .flow-wrap {
    height: 430px;
  }
}
</style>
