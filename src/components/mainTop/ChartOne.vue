<template>
  <main class="loop-embed app">
    <section class="workspace">
      <section class="view">
          <div v-if="viewMode === 'loop'" class="sunburst-legend">
            <span><b></b>内圈：角色关系</span>
            <span><b></b>主环：主题组合</span>
            <span><b></b>剧情起伏环带：叙事结构</span>
            <span><b></b>外柱：关系演化结局</span>
          </div>
      
          <button v-if="viewMode === 'detail'" class="view-toggle" type="button" @click="toggleViewMode">
            返回闭环环图
          </button>
          <svg ref="svgRef" role="img" aria-label="京剧闭环复合环图"></svg>
          <div class="chart-caption top-left">
            <strong>{{ viewMode === 'loop' ? '读图方式' : '下钻方式' }}</strong>
            <p>{{ viewMode === 'loop' ? '由内向外依次读取：角色关系 -> 主题组合 -> 叙事结构 -> 关系演化结局。' : '下钻后展示角色关系、主题组合、叙事节奏之间的协同连线。' }}</p>
            <p>{{ viewMode === 'loop' ? '外柱高度表示该闭环模式对应的剧本/记录数量。' : '点击任意连线后，右下角出现该路径关联剧本列表。' }}</p>
          </div>
          <div class="chart-caption top-right">
            <strong>{{ viewMode === 'loop' ? '剧情起伏环带' : '协同机制' }}</strong>
            <p>{{ viewMode === 'loop' ? '每段波带表示开端、发展、高潮、转折、收束的剧情张力走势。' : '实线表示关系到主题、主题到叙事，虚线表示叙事对关系的回塑。' }}</p>
            <template v-if="viewMode === 'loop'">
              <span v-for="item in narrativeLegend" :key="item.name"><i :style="{ background: item.color }"></i>{{ item.name }}</span>
            </template>
            <template v-else>
              <span><i style="background: #8f1516"></i>第一行：主题组合</span>
              <span><i style="background: #d6a53a"></i>第二行：叙事结构</span>
              <span><i style="background: #2b7fa3"></i>第三行：关系演化结局</span>
            </template>
          </div>
          <div class="chart-caption bottom-left">
            <strong>关系演化结局</strong>
            <span v-for="item in outcomeLegend" :key="item.name"><i :style="{ background: item.color }"></i>{{ item.name }}</span>
          </div>
          <div class="chart-caption bottom-right">
            <strong>当前模式</strong>
            <p>{{ patternDescription }}</p>
          </div>
          <div ref="tooltipRef" class="tooltip"></div>
        </section>
    </section>
    <Teleport to="body">
      <aside class="pet-assistant" :class="{ open: isOpen, dragging: isDragging }" :style="petStyle">
        <button
          class="pet-avatar"
          type="button"
          aria-label="打开京剧问答助手"
          @pointerdown="startDrag"
          @click="togglePanel"
        >
          <img class="pet-image" :src="PET_ASSISTANT_SRC" alt="" draggable="false" />
        </button>
        <span v-if="!isOpen" class="pet-callout">AI 问答 · 可拖动</span>
    
        <section v-if="isOpen" class="pet-panel">
          <header>
            <div>
              <strong>京剧剧本问答助手</strong>
              <p>可询问角色关系、主题、叙事结构与当前闭环路径。</p>
            </div>
            <button type="button" @click="isOpen = false">×</button>
          </header>
    
          <div class="pet-messages">
            <article v-for="message in messages" :key="message.id" :class="message.role">
              <span>{{ message.text }}</span>
            </article>
          </div>
    
          <div class="pet-prompts">
            <button v-for="prompt in prompts" :key="prompt" type="button" @click="ask(prompt)">
              {{ prompt }}
            </button>
          </div>
    
          <form class="pet-input" @submit.prevent="ask(input)">
            <input v-model="input" placeholder="问我：这个路径说明什么？" />
            <button type="submit">发送</button>
          </form>
        </section>
      </aside>
    </Teleport>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, reactive, ref, watch, watchEffect } from 'vue';
import './theme.css';
import { loadDemoDataset } from '../services/tableImport';
import { narrativeColors, outcomeColors, relationColors } from '../services/colorScales';
import { clearLoopFilter, setLoopFilter } from '../../services/loopFilterStore';
import type { LoopFilters, LoopFlow, ScriptRecord } from '../types/loop';

const LOOP_ASSET_BASE = '/%E6%95%B0%E6%8D%AE%E8%A1%A8%E5%90%88%E9%9B%86/5';
const PET_ASSISTANT_SRC = `${LOOP_ASSET_BASE}/pet-assistant.png`;
const CENTER_OPERA_SRC = `${LOOP_ASSET_BASE}/center-opera.jpg`;

const flows = ref<LoopFlow[]>([]);
const scripts = ref<ScriptRecord[]>([]);
const selectedFlow = ref<LoopFlow | null>(null);
const filters = ref<LoopFilters>({
  relation: '全部',
  narrative: '全部',
  evolution: '全部',
  limit: 30,
});

const visibleFlows = computed(() =>
  flows.value
    .filter((flow) => filters.value.relation === '全部' || flow.relationType === filters.value.relation)
    .filter((flow) => filters.value.narrative === '全部' || flow.narrativeType === filters.value.narrative)
    .filter((flow) => filters.value.evolution === '全部' || flow.evolutionType === filters.value.evolution)
    .sort((a, b) => b.count - a.count)
    .slice(0, filters.value.limit),
);

const activeFlow = computed(() => selectedFlow.value || visibleFlows.value[0] || null);
const props = reactive({
  flows: [] as LoopFlow[],
  scripts: [] as ScriptRecord[],
  selectedFlow: null as LoopFlow | null,
});

watchEffect(() => {
  props.flows = visibleFlows.value;
  props.scripts = scripts.value;
  props.selectedFlow = selectedFlow.value;
});

watch(visibleFlows, (next) => {
  if (!next.some((flow) => flow.id === selectedFlow.value?.id)) {
    selectedFlow.value = null;
    clearLoopFilter();
  }
});

onMounted(() => {
  loadDefaultData();
});

async function loadDefaultData() {
  const dataset = await loadDemoDataset();
  flows.value = dataset.flows;
  scripts.value = dataset.scripts;
  selectedFlow.value = null;
  clearLoopFilter();
}

function emit(event: 'select', flow: LoopFlow) {
  if (event === 'select') selectedFlow.value = flow;
}


interface NodeDatum {
  id?: string;
  name: string;
  depth: number;
  key?: string;
  value: number;
  parent?: NodeDatum;
  children: NodeDatum[];
  flows: LoopFlow[];
  start?: number;
  end?: number;
}

type SelectionScope =
  | { type: 'relation'; relationType: string; narrativeTypes?: string[] }
  | { type: 'theme'; relationType: string; themeCombo: string; narrativeTypes?: string[] }
  | { type: 'flow'; flowId: string; narrativeTypes?: string[] };

interface EdgeDetail {
  title: string;
  subtitle: string;
  flows: LoopFlow[];
}

const svgRef = ref<SVGSVGElement | null>(null);
const tooltipRef = ref<HTMLDivElement | null>(null);
const viewMode = ref<'loop' | 'detail'>('loop');
const selectionScope = ref<SelectionScope | null>(null);
const selectedEdgeDetail = ref<EdgeDetail | null>(null);

const narrativeLegend = Object.entries(narrativeColors).map(([name, color]) => ({ name, color }));
const outcomeLegend = Object.entries(outcomeColors).map(([name, color]) => ({ name, color }));

const viewTitle = computed(() => (viewMode.value === 'loop' ? '关系-主题-叙事闭环机制图' : '选中对象细分图'));

watch(
  () => [props.flows, props.selectedFlow],
  () => {
    if (selectionScope.value && !props.selectedFlow) {
      selectionScope.value = null;
    }
    draw();
  },
  { deep: true },
);

onMounted(() => {
  draw();
  window.addEventListener('resize', draw);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', draw);
});

const chartSubtitle = computed(() => {
  if (viewMode.value === 'detail') return selectedEdgeDetail.value ? `当前路径：${selectedEdgeDetail.value.subtitle}` : '全局协同网络：点击连线查看对应剧本。';
  const flow = props.selectedFlow;
  if (!flow) return '中心向外阅读：角色关系承载主题，主题组织叙事，叙事推进后反向塑造关系。';
  return `${flow.relationType} -> ${flow.themeCombo} -> ${flowNarrativeText(flow)} -> ${relationOutcome(flow)}`;
});

const badgeText = computed(() => {
  if (viewMode.value === 'detail') return selectedEdgeDetail.value ? `${detailScripts(selectedEdgeDetail.value.flows).length} 个剧本` : '协同网络';
  return props.selectedFlow ? `${props.selectedFlow.count} 个剧本` : '待选择';
});

const patternDescription = computed(() => {
  const flow = props.selectedFlow;
  if (viewMode.value === 'detail') return selectedEdgeDetail.value ? selectedEdgeDetail.value.subtitle : '点击线条查看该协同路径对应的剧本名单。';
  if (!flow) return '点击圆环扇区查看代表剧本与闭环路径。';
  return `${flow.relationType} 承载 ${flow.themeCombo}，以 ${flowNarrativeText(flow)} 推进，最终形成“${relationOutcome(flow)}”的关系演化结局。`;
});

async function draw() {
  await nextTick();
  const svg = svgRef.value;
  if (!svg) return;
  const rect = svg.getBoundingClientRect();
  const width = Math.max(680, rect.width || 680);
  const height = Math.max(620, rect.height || 620);
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.innerHTML = '';
  if (!props.flows.length) {
    const text = element('text');
    text.setAttribute('x', String(width / 2));
    text.setAttribute('y', String(height / 2));
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('fill', '#7b6048');
    text.textContent = '导入表格后生成京剧闭环谱系盘';
    svg.appendChild(text);
    return;
  }

  const cx = width / 2;
  const isNarrow = width < 520;
  const cy = isNarrow ? height * 0.54 : height / 2 + 14;
  const maxR = isNarrow ? Math.min(height * 0.32, width * 0.69) : Math.min(width, height) * 0.442;
  const ring = maxR / 5.3;

  if (viewMode.value === 'detail') {
    drawTripartiteNetwork(svg, cx, cy, width, height, ring);
    return;
  }

  const root = buildTwoLayerHierarchy(props.flows);
  layoutAngles(root, -Math.PI / 2, Math.PI * 1.5);

  drawGuides(svg, cx, cy, ring);
  drawNarrativeGlyphTrack(svg, cx, cy, ring * 3.56, ring * 4.72);
  drawOuterBars(svg, cx, cy, ring * 4.92, ring * 5.72);
  drawMainRings(svg, root, cx, cy, ring);
  drawCenter(svg, cx, cy, ring);
}

function drawMainRings(svg: SVGSVGElement, root: NodeDatum, cx: number, cy: number, ring: number) {
  const nodes = flatten(root).filter((node) => node.depth > 0);
  nodes.forEach((node) => {
      const inner = node.depth === 1 ? ring * 1.12 : ring * 2.05;
      const outer = node.depth === 1 ? ring * 1.9 : ring * 3.34;
      const path = element('path');
      const active = isActive(node);
      path.setAttribute('d', arcPath(cx, cy, inner, outer, node.start!, node.end!));
      path.setAttribute('class', `arc ${active ? 'active zoomed' : ''}`);
      path.setAttribute('fill', nodeColor(node));
      path.setAttribute('opacity', props.selectedFlow ? (active ? '1' : '0.2') : '0.88');
      path.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(node.name)}</strong>层级：${node.depth === 1 ? '角色关系' : '主题组合'}`));
      path.addEventListener('mouseleave', hideTooltip);
      path.addEventListener('click', () => selectNode(node));
      svg.appendChild(path);
    });

  nodes.forEach((node) => {
    const span = (node.end || 0) - (node.start || 0);
    const minSpan = node.depth === 1 ? 0.18 : 0.24;
    if (span < minSpan) return;
    const inner = node.depth === 1 ? ring * 1.12 : ring * 2.05;
    const outer = node.depth === 1 ? ring * 1.9 : ring * 3.34;
    const labelText = node.depth === 1 ? truncate(node.name, 5) : compactThemeCombo(node.name);
    const labelAngle = ((node.start || 0) + (node.end || 0)) / 2;
    const labelRadius = (inner + outer) / 2;
    const label =
      node.depth === 1
        ? tangentialLabel(labelText, cx, cy, labelRadius, labelAngle, 'arc-label arc-label--inner')
        : verticalLabel(labelText, cx, cy, labelRadius, labelAngle, 'arc-label arc-label--theme');
    svg.appendChild(label);
  });
}

function drawDetailView(svg: SVGSVGElement, cx: number, cy: number, width: number, height: number, ring: number) {
  const flows = scopedFlows();
  const total = flows.reduce((sum, flow) => sum + flow.count, 0) || 1;
  const left = Math.max(94, cx - ring * 4.25);
  const right = Math.min(width - 94, cx + ring * 4.25);
  const top = Math.max(166, cy - ring * 2.45);
  const selectedScripts = detailScripts(flows);
  const representative = selectedScripts[0];
  const detailCurve = aggregateScriptCurve(selectedScripts, 'narrativeCurve') || aggregateFlowCurve(flows, 'narrativeCurve');
  const relationCurve = aggregateScriptCurve(selectedScripts, 'evolutionCurve') || aggregateFlowCurve(flows, 'evolutionCurve');
  const contentTop = top + 16;
  const kind = detailKind();
  drawDetailKindBadge(svg, left, top - 78, kind);

  const title = element('text');
  title.setAttribute('class', 'detail-title');
  title.setAttribute('x', String(cx));
  title.setAttribute('y', String(top - 58));
  title.setAttribute('text-anchor', 'middle');
  title.textContent = detailShortTitle(kind);
  svg.appendChild(title);

  const subtitle = element('text');
  subtitle.setAttribute('class', 'detail-subtitle');
  subtitle.setAttribute('x', String(cx));
  subtitle.setAttribute('y', String(top - 30));
  subtitle.setAttribute('text-anchor', 'middle');
  subtitle.textContent = detailSubtitle(kind, total, selectedScripts.length);
  subtitle.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(scopeLabel())}</strong>${escapeHtml(detailSubtitle(kind, total, selectedScripts.length))}`));
  subtitle.addEventListener('mouseleave', hideTooltip);
  svg.appendChild(subtitle);

  const leftPanel = detailLeftPanel(kind, flows, selectedScripts);
  drawDetailPanel(svg, left, contentTop, ring * 2.12, ring * 2.18, leftPanel.title, leftPanel.rows);

  drawCurvePanel(svg, cx - ring * 1.15, contentTop, ring * 2.3, ring * 2.18, detailCurve, relationCurve, detailCurveTitle(kind));

  const rightPanel = detailRightPanel(kind, flows, selectedScripts);
  drawDetailPanel(svg, right - ring * 2.12, contentTop, ring * 2.12, ring * 2.18, rightPanel.title, rightPanel.rows);

  const rows = [
    { name: '阶段事件', values: evidenceDetail(selectedScripts, 'stage'), color: '#8f1516' },
    { name: '角色证据', values: evidenceDetail(selectedScripts, 'relation'), color: '#c7922e' },
    { name: '主题证据', values: evidenceDetail(selectedScripts, 'theme'), color: '#2b7fa3' },
  ];
  rows.forEach((row, rowIndex) => {
    const y = contentTop + ring * 2.72 + rowIndex * Math.max(46, ring * 0.46);
    const rowHeight = Math.max(18, ring * 0.2);
    const rowTotal = row.values.reduce((sum, item) => sum + item.count, 0) || 1;
    const label = element('text');
    label.setAttribute('class', 'detail-row-label');
    label.setAttribute('x', String(left));
    label.setAttribute('y', String(y - 10));
    label.textContent = row.name;
    svg.appendChild(label);

    let cursor = left;
    row.values.forEach((item, index) => {
      const widthRatio = item.count / rowTotal;
      const itemWidth = Math.max(30, (right - left) * widthRatio);
      const rect = element('rect');
      rect.setAttribute('class', 'detail-segment');
      rect.setAttribute('x', String(cursor));
      rect.setAttribute('y', String(y));
      rect.setAttribute('width', String(Math.max(0, itemWidth - 5)));
      rect.setAttribute('height', String(rowHeight));
      rect.setAttribute('rx', '10');
      rect.setAttribute('fill', lighten(row.color, index * 0.055));
      rect.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(item.name)}</strong>${row.name}<br>${escapeHtml(item.note)}`));
      rect.addEventListener('mouseleave', hideTooltip);
      svg.appendChild(rect);

      if (itemWidth > 190) {
        const text = element('text');
        text.setAttribute('class', 'detail-segment-label');
        text.setAttribute('x', String(cursor + 12));
        text.setAttribute('y', String(y + rowHeight / 2 + 4));
        text.textContent = truncate(shortEvidenceLabel(item.name), 6);
        svg.appendChild(text);
      }
      cursor += itemWidth;
    });
  });

  if (!representative) return;
  drawRepresentativeBadge(svg, cx, contentTop + ring * 4.08, representative);
}

function drawStageView(svg: SVGSVGElement, cx: number, cy: number, width: number, height: number, ring: number) {
  const left = Math.max(86, cx - ring * 3.45);
  const right = Math.min(width - 86, cx + ring * 3.45);
  const top = Math.max(138, cy - ring * 2.8);
  const bottom = Math.min(height - 76, cy + ring * 2.72);
  const stages = ['开端', '发展', '高潮', '转折', '收束'];
  const stagePoints = stages.map((stage, index) => ({
    stage,
    x: left + ((right - left) * index) / (stages.length - 1),
  }));

  stagePoints.forEach((point) => {
    const line = element('line');
    line.setAttribute('class', 'stage-axis');
    line.setAttribute('x1', String(point.x));
    line.setAttribute('x2', String(point.x));
    line.setAttribute('y1', String(top));
    line.setAttribute('y2', String(bottom));
    svg.appendChild(line);

    const label = element('text');
    label.setAttribute('class', 'stage-axis-label');
    label.setAttribute('x', String(point.x));
    label.setAttribute('y', String(bottom + 30));
    label.setAttribute('text-anchor', 'middle');
    label.textContent = point.stage;
    svg.appendChild(label);
  });

  for (let i = 0; i <= 4; i += 1) {
    const y = bottom - ((bottom - top) * i) / 4;
    const guide = element('line');
    guide.setAttribute('class', 'stage-guide');
    guide.setAttribute('x1', String(left));
    guide.setAttribute('x2', String(right));
    guide.setAttribute('y1', String(y));
    guide.setAttribute('y2', String(y));
    svg.appendChild(guide);
  }

  const summaries = [...groupByNarrative(props.flows).values()].sort((a, b) => b.count - a.count);
  const maxCount = Math.max(...summaries.map((item) => item.count), 1);
  summaries.forEach((summary, index) => {
    const color = narrativeColors[summary.narrativeType] || '#2b7fa3';
    const active = props.selectedFlow?.narrativeType === summary.narrativeType;
    const offset = (index - (summaries.length - 1) / 2) * 8;
    const points = summary.profile.map((value, stageIndex) => ({
      x: stagePoints[stageIndex].x,
      y: bottom - value * (bottom - top) * 0.84 - offset,
    }));
    const path = element('path');
    path.setAttribute('class', `stage-curve ${active ? 'active' : ''}`);
    path.setAttribute('d', smoothPath(points));
    path.setAttribute('stroke', color);
    path.setAttribute('stroke-width', String(active ? 5 : 1.6 + Math.sqrt(summary.count / maxCount) * 4));
    path.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(summary.narrativeType)}</strong>五阶段剧情张力曲线<br>代表模式：${escapeHtml(summary.representative.relationType)} -> ${escapeHtml(summary.representative.themeCombo)} -> ${escapeHtml(relationOutcome(summary.representative))}`));
    path.addEventListener('mouseleave', hideTooltip);
    path.addEventListener('click', () => selectAndPopup(summary.representative));
    svg.appendChild(path);

    points.forEach((point, stageIndex) => {
      const dot = element('circle');
      dot.setAttribute('class', `stage-dot ${active ? 'active' : ''}`);
      dot.setAttribute('cx', String(point.x));
      dot.setAttribute('cy', String(point.y));
      dot.setAttribute('r', String(active ? 5.6 : 3.5));
      dot.setAttribute('fill', color);
      dot.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(summary.narrativeType)}</strong>${stageName(stageIndex, summary.profile.length)}张力：${Math.round(summary.profile[stageIndex] * 100)}%`));
      dot.addEventListener('mouseleave', hideTooltip);
      dot.addEventListener('click', () => selectAndPopup(summary.representative));
      svg.appendChild(dot);
    });

    const label = element('text');
    label.setAttribute('class', `stage-curve-label ${active ? 'active' : ''}`);
    label.setAttribute('x', String(points[points.length - 1].x + 12));
    label.setAttribute('y', String(points[points.length - 1].y + 4));
    label.textContent = summary.narrativeType;
    svg.appendChild(label);
  });

  drawStageExplanation(svg, left, top, ring);
}

function drawDetailPanel(svg: SVGSVGElement, x: number, y: number, w: number, h: number, titleText: string, rows: string[][]) {
  const group = element('g');
  group.setAttribute('class', 'detail-card');
  const rect = element('rect');
  rect.setAttribute('x', String(x));
  rect.setAttribute('y', String(y));
  rect.setAttribute('width', String(w));
  rect.setAttribute('height', String(h));
  rect.setAttribute('rx', '14');
  group.appendChild(rect);

  const title = element('text');
  title.setAttribute('class', 'detail-card-title');
  title.setAttribute('x', String(x + 18));
  title.setAttribute('y', String(y + 30));
  title.textContent = titleText;
  group.appendChild(title);

  rows.slice(0, 4).forEach((row, index) => {
    const baseY = y + 60 + index * 34;
    const bullet = element('circle');
    bullet.setAttribute('class', 'detail-card-bullet');
    bullet.setAttribute('cx', String(x + 20));
    bullet.setAttribute('cy', String(baseY - 4));
    bullet.setAttribute('r', '4');
    group.appendChild(bullet);

    const main = element('text');
    main.setAttribute('class', 'detail-card-main');
    main.setAttribute('x', String(x + 32));
    main.setAttribute('y', String(baseY));
    main.textContent = truncate(shortEvidenceLabel(row[0]), 10);
    group.appendChild(main);
    main.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(row[0])}</strong>${escapeHtml(row[1] || '')}`));
    main.addEventListener('mouseleave', hideTooltip);
    bullet.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(row[0])}</strong>${escapeHtml(row[1] || '')}`));
    bullet.addEventListener('mouseleave', hideTooltip);
  });

  svg.appendChild(group);
}

function drawDetailKindBadge(svg: SVGSVGElement, x: number, y: number, kind: string) {
  const labels: Record<string, string> = {
    relation: '关系层：看一个角色关系如何分化',
    theme: '主题层：看一个主题分支如何组织',
    flow: '路径层：看一条闭环路径的剧本证据',
  };
  const colors: Record<string, string> = {
    relation: '#8f1516',
    theme: '#c7922e',
    flow: '#245f80',
  };
  const group = element('g');
  group.setAttribute('class', 'detail-kind');
  const rect = element('rect');
  rect.setAttribute('x', String(x));
  rect.setAttribute('y', String(y));
  rect.setAttribute('width', '238');
  rect.setAttribute('height', '34');
  rect.setAttribute('rx', '17');
  rect.setAttribute('fill', colors[kind] || '#8f1516');
  group.appendChild(rect);

  const text = element('text');
  text.setAttribute('x', String(x + 16));
  text.setAttribute('y', String(y + 22));
  text.textContent = labels[kind] || labels.flow;
  group.appendChild(text);
  svg.appendChild(group);
}

function drawRepresentativeBadge(svg: SVGSVGElement, cx: number, y: number, script: ScriptRecord) {
  const group = element('g');
  group.setAttribute('class', 'representative-badge');
  const rect = element('rect');
  rect.setAttribute('x', String(cx - 170));
  rect.setAttribute('y', String(y - 18));
  rect.setAttribute('width', '340');
  rect.setAttribute('height', '36');
  rect.setAttribute('rx', '18');
  group.appendChild(rect);

  const text = element('text');
  text.setAttribute('x', String(cx));
  text.setAttribute('y', String(y + 5));
  text.setAttribute('text-anchor', 'middle');
  text.textContent = `当前代表：${truncate(script.title || script.id, 10)}`;
  group.appendChild(text);
  group.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(script.title || script.id)}</strong>中心角色：${escapeHtml(script.centerRole || '未标注')}`));
  group.addEventListener('mouseleave', hideTooltip);
  svg.appendChild(group);
}

function drawCurvePanel(svg: SVGSVGElement, x: number, y: number, w: number, h: number, narrativeCurve?: number[], relationCurve?: number[], titleText = '叙事起伏与关系强度') {
  const group = element('g');
  group.setAttribute('class', 'detail-card');
  const rect = element('rect');
  rect.setAttribute('x', String(x));
  rect.setAttribute('y', String(y));
  rect.setAttribute('width', String(w));
  rect.setAttribute('height', String(h));
  rect.setAttribute('rx', '14');
  group.appendChild(rect);

  const title = element('text');
  title.setAttribute('class', 'detail-card-title');
  title.setAttribute('x', String(x + 18));
  title.setAttribute('y', String(y + 30));
  title.textContent = titleText;
  group.appendChild(title);

  drawMiniCurve(group, normalizeProfile(narrativeCurve || []), x + 22, y + 58, w - 44, h - 92, '#8f1516', '叙事起伏');
  drawMiniCurve(group, normalizeProfile(relationCurve || []), x + 22, y + 58, w - 44, h - 92, '#245f80', '关系强度');
  svg.appendChild(group);
}

function drawMiniCurve(group: SVGElement, values: number[], x: number, y: number, w: number, h: number, color: string, label: string) {
  if (!values.length) return;
  const points = values.map((value, index) => ({
    x: x + (w * index) / Math.max(1, values.length - 1),
    y: y + h - value * h,
  }));
  const path = element('path');
  path.setAttribute('class', 'detail-curve');
  path.setAttribute('d', smoothPath(points));
  path.setAttribute('stroke', color);
  group.appendChild(path);

  points.forEach((point) => {
    const dot = element('circle');
    dot.setAttribute('class', 'detail-curve-dot');
    dot.setAttribute('cx', String(point.x));
    dot.setAttribute('cy', String(point.y));
    dot.setAttribute('r', '3.2');
    dot.setAttribute('fill', color);
    group.appendChild(dot);
  });

  const text = element('text');
  text.setAttribute('class', 'detail-card-sub');
  text.setAttribute('x', String(x + w));
  text.setAttribute('y', String(points[points.length - 1].y - 8));
  text.setAttribute('text-anchor', 'end');
  text.textContent = label;
  group.appendChild(text);
}

function groupByNarrative(flows: LoopFlow[]) {
  const map = new Map<string, { narrativeType: string; count: number; profile: number[]; representative: LoopFlow }>();
  flows.forEach((flow) => {
    const profile = narrativeProfile(flow);
    const existing = map.get(flow.narrativeType);
    if (!existing) {
      map.set(flow.narrativeType, {
        narrativeType: flow.narrativeType,
        count: flow.count,
        profile: profile.map((value) => value * flow.count),
        representative: flow,
      });
      return;
    }
    existing.count += flow.count;
    existing.profile = existing.profile.map((value, index) => value + profile[index] * flow.count);
    if (flow.count > existing.representative.count) existing.representative = flow;
  });
  map.forEach((summary) => {
    summary.profile = summary.profile.map((value) => value / summary.count);
  });
  return map;
}

function drawStageExplanation(svg: SVGSVGElement, left: number, top: number, ring: number) {
  const group = element('g');
  group.setAttribute('class', 'stage-explain');
  group.setAttribute('transform', `translate(${left} ${top - 70})`);

  const bg = element('rect');
  bg.setAttribute('x', '0');
  bg.setAttribute('y', '0');
  bg.setAttribute('width', String(ring * 4.7));
  bg.setAttribute('height', '52');
  bg.setAttribute('rx', '8');
  group.appendChild(bg);

  const title = element('text');
  title.setAttribute('x', '16');
  title.setAttribute('y', '21');
  title.setAttribute('class', 'stage-explain-title');
  title.textContent = '区别：环图看“类别结构”，阶段图看“剧情时间走势”';
  group.appendChild(title);

  const desc = element('text');
  desc.setAttribute('x', '16');
  desc.setAttribute('y', '39');
  desc.setAttribute('class', 'stage-explain-text');
  desc.textContent = '曲线越高表示该阶段戏剧张力越强，曲线越粗表示该叙事结构对应模式越多。';
  group.appendChild(desc);

  svg.appendChild(group);
}

function drawNarrativeGlyphTrack(svg: SVGSVGElement, cx: number, cy: number, innerR: number, outerR: number) {
  const span = (Math.PI * 2) / Math.max(1, props.flows.length);
  const hasSelection = Boolean(props.selectedFlow || selectionScope.value);
  let angle = -Math.PI / 2;
  props.flows.forEach((flow) => {
    const profile = narrativeProfile(flow);
    const color = narrativeVariantColor(flow, narrativeColors[flow.narrativeType] || '#c7b894');
    const gap = Math.min(0.018, span * 0.18);
    const usableStart = angle + gap;
    const usableEnd = angle + span - gap;
    const range = outerR - innerR;
    const baseR = innerR + range * 0.2;
    const samples = Math.max(5, Math.min(10, Math.round(span * 10)));
    const outerPoints = Array.from({ length: samples }, (_, index) => {
      const t = samples === 1 ? 0.5 : index / (samples - 1);
      const a = usableStart + (usableEnd - usableStart) * t;
      const value = sampleProfile(profile, t);
      return polar(cx, cy, baseR + range * (0.14 + value * 0.62), a);
    });
    const innerPoints = Array.from({ length: samples }, (_, index) => {
      const t = samples === 1 ? 0.5 : index / (samples - 1);
      const a = usableEnd - (usableEnd - usableStart) * t;
      return polar(cx, cy, baseR, a);
    });
    const ribbon = element('path');
    const active = isFlowRelated(flow);
    ribbon.setAttribute('class', `narrative-ribbon ${active ? 'active' : hasSelection ? 'muted' : ''}`);
    ribbon.setAttribute('d', [...outerPoints, ...innerPoints].map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ') + ' Z');
    ribbon.setAttribute('fill', color);
    if (hasSelection) {
      ribbon.setAttribute('opacity', active ? '0.9' : '0.2');
      ribbon.setAttribute('stroke', active ? 'rgba(255, 250, 235, 0.96)' : 'transparent');
      ribbon.setAttribute('stroke-width', active ? '1.6' : '0');
    }
    ribbon.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(flow.narrativeType)}</strong>剧情张力波带<br>开端-发展-高潮-转折-收束<br>${escapeHtml(flow.relationType)} -> ${escapeHtml(flow.themeCombo)}`));
    ribbon.addEventListener('mouseleave', hideTooltip);
    ribbon.addEventListener('click', () => selectAndPopup(flow));
    svg.appendChild(ribbon);

    narrativeDotPoints(profile).forEach(({ value, sourceIndex, t }) => {
      const index = sourceIndex;
      const a = usableStart + (usableEnd - usableStart) * t;
      const point = polar(cx, cy, baseR + range * (0.14 + value * 0.62), a);
      const dot = element('circle');
      dot.setAttribute('class', `narrative-dot ${active ? 'active' : hasSelection ? 'muted' : ''}`);
      dot.setAttribute('cx', String(point.x));
      dot.setAttribute('cy', String(point.y));
      const baseDotRadius = Math.max(2.4, Math.min(4.8, span * 18));
      dot.setAttribute('r', String(active && hasSelection ? baseDotRadius * 1.12 : baseDotRadius));
      dot.setAttribute('fill', color);
      if (hasSelection) {
        dot.setAttribute('opacity', active ? '1' : '0.26');
        dot.setAttribute('stroke', active ? 'rgba(255, 250, 235, 0.98)' : 'transparent');
        dot.setAttribute('stroke-width', active ? '1.6' : '0');
      }
      dot.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(flow.narrativeType)}</strong>${stageName(index, profile.length)}张力：${Math.round(value * 100)}%<br>${escapeHtml(flow.relationType)} -> ${escapeHtml(flow.themeCombo)}`));
      dot.addEventListener('mouseleave', hideTooltip);
      dot.addEventListener('click', () => selectAndPopup(flow));
      svg.appendChild(dot);
    });
    if (span > 0.12) {
      const labelAngle = usableStart + (usableEnd - usableStart) * 0.62;
      const labelRadius = innerR + range * 0.62;
      const label = tangentialLabel(truncate(flow.narrativeType, 6), cx, cy, labelRadius, labelAngle, 'narrative-label');
      if (hasSelection && !active) label.setAttribute('opacity', '0.22');
      svg.appendChild(label);
    }
    angle += span;
  });
}

function narrativeProfile(flow: LoopFlow) {
  if (flow.narrativeCurve?.length) return normalizeProfile(flow.narrativeCurve);
  return fallbackProfile(flow);
}

function narrativeDotPoints(profile: number[]) {
  const maxDots = 5;
  if (profile.length <= maxDots) {
    return profile.map((value, index) => ({
      value,
      sourceIndex: index,
      t: profile.length === 1 ? 0.5 : index / (profile.length - 1),
    }));
  }

  return Array.from({ length: maxDots }, (_, index) => {
    const t = maxDots === 1 ? 0.5 : index / (maxDots - 1);
    return {
      value: sampleProfile(profile, t),
      sourceIndex: Math.round(t * (profile.length - 1)),
      t,
    };
  });
}

function normalizeProfile(curve: number[]) {
  const values = curve.map(Number).filter((value) => Number.isFinite(value));
  if (!values.length) return [0.35, 0.55, 0.7, 0.55, 0.35];
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (max === min) return values.map(() => 0.5);
  return values.map((value) => 0.12 + ((value - min) / (max - min)) * 0.88);
}

function fallbackProfile(flow: LoopFlow) {
  const seed = hashText(`${flow.relationType}${flow.themeCombo}${flow.evolutionType}${flow.count}`);
  const length = 6;
  return Array.from({ length }, (_, index) => {
    const wave = Math.sin(seed * 0.017 + index * 1.37) * 0.22;
    const trend = index / (length - 1);
    const relationLift = relationOutcome(flow).includes('强化') ? trend * 0.24 : (1 - Math.abs(trend - 0.55)) * 0.16;
    return clamp(0.22 + wave + relationLift + Math.sqrt(flow.count) * 0.018, 0.12, 1);
  });
}

function stageName(index: number, total: number) {
  if (total === 5) return ['开端', '发展', '高潮', '转折', '收束'][index] || `第${index + 1}段`;
  if (total === 6) return ['开端', '承接', '发展', '高潮', '转折', '收束'][index] || `第${index + 1}段`;
  return `第${index + 1}段`;
}

function tangentialLabel(text: string, cx: number, cy: number, radius: number, angle: number, className: string) {
  const point = polar(cx, cy, radius, angle);
  const label = element('text');
  const normalized = ((angle % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
  const flip = normalized > Math.PI / 2 && normalized < Math.PI * 1.5;
  const rotation = (angle * 180) / Math.PI + 90 + (flip ? 180 : 0);
  label.setAttribute('class', className);
  label.setAttribute('x', String(point.x));
  label.setAttribute('y', String(point.y));
  label.setAttribute('text-anchor', 'middle');
  label.setAttribute('dominant-baseline', 'middle');
  label.setAttribute('transform', `rotate(${rotation} ${point.x} ${point.y})`);
  label.textContent = text;
  return label;
}

function verticalLabel(text: string, cx: number, cy: number, radius: number, angle: number, className: string) {
  const point = polar(cx, cy, radius, angle);
  const label = element('text');
  const chars = Array.from(text);
  const lineHeight = className.includes('arc-label--theme') ? 12 : 14;
  const startDy = -((chars.length - 1) * lineHeight) / 2;
  const normalized = ((angle % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
  const flip = normalized > Math.PI / 2 && normalized < Math.PI * 1.5;
  const rotation = (angle * 180) / Math.PI - 90 + (flip ? 180 : 0);

  label.setAttribute('class', `${className} arc-label--vertical`);
  label.setAttribute('x', String(point.x));
  label.setAttribute('y', String(point.y));
  label.setAttribute('text-anchor', 'middle');
  label.setAttribute('dominant-baseline', 'middle');
  label.setAttribute('transform', `rotate(${rotation} ${point.x} ${point.y})`);

  chars.forEach((char, index) => {
    const tspan = element('tspan');
    tspan.setAttribute('x', String(point.x));
    tspan.setAttribute('dy', index === 0 ? String(startDy) : String(lineHeight));
    tspan.textContent = char;
    label.appendChild(tspan);
  });

  return label;
}

function outcomeLabelText(value: string) {
  return value
    .replace(/^关系/, '')
    .replace(/^中段/, '')
    .replace(/持续强化/, '持续强化')
    .replace(/强弱震荡/, '强弱震荡')
    .replace(/稳定推进/, '稳定推进')
    .replace(/线索不足/, '线索不足')
    .replace(/回落$/, '回落')
    .slice(0, 6);
}

function hashText(text: string) {
  return [...text].reduce((sum, char, index) => sum + char.charCodeAt(0) * (index + 3), 0);
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function sampleProfile(profile: number[], t: number) {
  const x = t * (profile.length - 1);
  const left = Math.floor(x);
  const right = Math.min(profile.length - 1, left + 1);
  const ratio = x - left;
  return profile[left] * (1 - ratio) + profile[right] * ratio;
}

function relationOutcome(flow: LoopFlow) {
  const text = flow.evolutionType || '';
  if (text.includes('持续强化')) return '关系持续强化';
  if (text.includes('强弱震荡')) return '关系强弱震荡';
  if (text.includes('中段强化后回落')) return '中段强化后回落';
  if (text.includes('冲突消解')) return '冲突消解回落';
  if (text.includes('稳定推进')) return '关系稳定推进';
  if (text.includes('线索不足')) return '关系线索不足';
  return text || '关系演化未明';
}

function flowNarrativeText(flow: LoopFlow) {
  return flow.waveType ? `${flow.narrativeType}/${flow.waveType}` : flow.narrativeType;
}

function narrativeVariantColor(flow: LoopFlow, baseColor: string) {
  const seed = hashText(`${flow.id}${flow.themeCombo}${flow.waveType || ''}`);
  const amount = ((seed % 7) - 3) * 0.045;
  return shadeColor(baseColor, amount);
}

function drawOuterBars(svg: SVGSVGElement, cx: number, cy: number, innerR: number, outerR: number) {
  const maxCount = Math.max(...props.flows.map((flow) => flow.count), 1);
  const span = (Math.PI * 2) / Math.max(1, props.flows.length);
  let angle = -Math.PI / 2;
  props.flows.forEach((flow, index) => {
    const gap = Math.min(0.024, span * 0.18);
    const heightJitter = 0.18 + 0.16 * Math.sin(index * 1.7);
    const height = (outerR - innerR) * (0.38 + 0.46 * Math.sqrt(flow.count / maxCount) + heightJitter);
    const bar = element('path');
    const active = isFlowRelated(flow);
    bar.setAttribute('class', `outer-bar ${active ? 'active zoomed' : ''}`);
    bar.setAttribute('d', arcPath(cx, cy, innerR, Math.min(outerR + 8, innerR + height), angle + gap, angle + span - gap));
    const outcome = relationOutcome(flow);
    bar.setAttribute('fill', outcomeColors[outcome] || relationColors[flow.relationType] || '#c7b894');
    if (props.selectedFlow) bar.setAttribute('opacity', active ? '1' : '0.18');
    bar.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(outcome)}</strong>关系演化结局外柱<br>${escapeHtml(flow.relationType)} -> ${escapeHtml(flow.themeCombo)}`));
    bar.addEventListener('mouseleave', hideTooltip);
    bar.addEventListener('click', () => selectAndPopup(flow));
    svg.appendChild(bar);
    angle += span;
  });
}

function selectAndPopup(flow: LoopFlow) {
  selectionScope.value = {
    type: 'flow',
    flowId: flow.id,
    narrativeTypes: [flow.narrativeType].filter(Boolean),
  };
  setLoopFilter(selectionScope.value, flow);
  emit('select', flow);
}

function selectNode(node: NodeDatum) {
  const representative = representativeFlow(node);
  const narrativeTypes = Array.from(new Set(node.flows.map((flow) => flow.narrativeType).filter(Boolean)));
  if (node.depth === 1) {
    selectionScope.value = {
      type: 'relation',
      relationType: representative.relationType,
      narrativeTypes,
    };
  } else {
    selectionScope.value = {
      type: 'theme',
      relationType: representative.relationType,
      themeCombo: representative.themeCombo,
      narrativeTypes,
    };
  }
  setLoopFilter(selectionScope.value, representative);
  emit('select', representative);
}

function drawGuides(svg: SVGSVGElement, cx: number, cy: number, ring: number) {
  for (let i = 1; i <= 5; i += 1) {
    const circle = element('circle');
    circle.setAttribute('class', 'ring-guide');
    circle.setAttribute('cx', String(cx));
    circle.setAttribute('cy', String(cy));
    circle.setAttribute('r', String(ring * i));
    svg.appendChild(circle);
  }
}

function drawCenter(svg: SVGSVGElement, cx: number, cy: number, ring: number) {
  const radius = ring * 1.05;
  const activeFlow = props.selectedFlow;
  const activeColor = activeFlow ? outcomeColors[relationOutcome(activeFlow)] || '#d2b274' : '#d2b274';
  const imageRadius = radius - (activeFlow ? 5 : 8);
  const clipId = 'center-opera-image-clip';

  if (activeFlow) {
    const aura = element('circle');
    aura.setAttribute('class', 'center-aura');
    aura.setAttribute('cx', String(cx));
    aura.setAttribute('cy', String(cy));
    aura.setAttribute('r', String(radius + 8));
    aura.setAttribute('stroke', activeColor);
    svg.appendChild(aura);

    const orbit = element('circle');
    orbit.setAttribute('class', 'center-orbit');
    orbit.setAttribute('cx', String(cx));
    orbit.setAttribute('cy', String(cy));
    orbit.setAttribute('r', String(radius + 15));
    orbit.setAttribute('stroke', activeColor);
    svg.appendChild(orbit);
  }

  const base = element('circle');
  base.setAttribute('cx', String(cx));
  base.setAttribute('cy', String(cy));
  base.setAttribute('r', String(radius));
  base.setAttribute('fill', '#fff8e7');
  svg.appendChild(base);

  const defs = element('defs');
  const clip = element('clipPath');
  clip.setAttribute('id', clipId);
  const clipCircle = element('circle');
  clipCircle.setAttribute('cx', String(cx));
  clipCircle.setAttribute('cy', String(cy));
  clipCircle.setAttribute('r', String(imageRadius));
  clip.appendChild(clipCircle);
  defs.appendChild(clip);
  svg.appendChild(defs);

  const center = element('circle');
  center.setAttribute('cx', String(cx));
  center.setAttribute('cy', String(cy));
  center.setAttribute('r', String(radius));
  center.setAttribute('fill', 'none');
  center.setAttribute('stroke', activeColor);
  center.setAttribute('stroke-width', activeFlow ? '4' : '3');
  svg.appendChild(center);

  const image = element('image');
  image.setAttribute('class', `center-image ${activeFlow ? 'active' : ''}`);
  image.setAttribute('href', CENTER_OPERA_SRC);
  image.setAttribute('x', String(cx - imageRadius));
  image.setAttribute('y', String(cy - imageRadius));
  image.setAttribute('width', String(imageRadius * 2));
  image.setAttribute('height', String(imageRadius * 2));
  image.setAttribute('preserveAspectRatio', 'xMidYMid slice');
  image.setAttribute('clip-path', `url(#${clipId})`);
  svg.appendChild(image);

  const hit = element('circle');
  hit.setAttribute('class', 'center-hit');
  hit.setAttribute('cx', String(cx));
  hit.setAttribute('cy', String(cy));
  hit.setAttribute('r', String(radius + 18));
  hit.addEventListener('mousemove', (event) => {
    const prompt = props.selectedFlow ? `点击中心展开：${escapeHtml(scopeLabel())}` : '点击中心进入全局协同网络';
    showTooltip(event, `<strong>${viewMode.value === 'loop' ? '对象详情入口' : '返回闭环环图'}</strong>${prompt}`);
  });
  hit.addEventListener('mouseleave', hideTooltip);
  hit.addEventListener('click', toggleViewMode);
  svg.appendChild(hit);
}

function toggleViewMode() {
  if (viewMode.value === 'loop') {
    selectedEdgeDetail.value = props.selectedFlow ? scriptDetailForFlow(props.selectedFlow) : null;
    viewMode.value = 'detail';
  } else {
    viewMode.value = 'loop';
    selectedEdgeDetail.value = null;
  }
  if (viewMode.value === 'loop') selectionScope.value = null;
  hideTooltip();
  draw();
}

type NetworkLayer = 'relation' | 'theme' | 'narrative';

interface NetworkNode {
  id: string;
  name: string;
  layer: NetworkLayer;
  value: number;
  flows: LoopFlow[];
  x: number;
  y: number;
  active?: boolean;
}

interface NetworkEdge {
  id: string;
  source: NetworkNode;
  target: NetworkNode;
  kind: 'drive' | 'organize' | 'reshape';
  title: string;
  subtitle: string;
  value: number;
  flows: LoopFlow[];
  active?: boolean;
}

function drawTripartiteNetwork(svg: SVGSVGElement, cx: number, cy: number, width: number, height: number, ring: number) {
  drawNetworkClearLayer(svg, width, height);
  const network = buildTripartiteNetwork(props.flows, cx, cy + ring * 0.1, ring);
  drawNetworkGuides(svg, cx, cy + ring * 0.1, ring);
  drawNetworkEdges(svg, network.edges);
  drawNetworkNodes(svg, network.nodes, ring);
  drawNetworkEdgeHotspots(svg, network.edges);
  drawNetworkStoryPanel(svg, width, height);
}

function drawNetworkClearLayer(svg: SVGSVGElement, width: number, height: number) {
  const layer = element('rect');
  layer.setAttribute('class', 'network-clear-layer');
  layer.setAttribute('x', '0');
  layer.setAttribute('y', '0');
  layer.setAttribute('width', String(width));
  layer.setAttribute('height', String(height));
  layer.addEventListener('click', () => {
    if (!selectedEdgeDetail.value) return;
    selectedEdgeDetail.value = null;
    draw();
  });
  svg.appendChild(layer);
}

function buildTripartiteNetwork(flows: LoopFlow[], cx: number, cy: number, ring: number) {
  const relationNames = topNames(flows, (flow) => flow.relationType, 6);
  const themeNames = topNames(flows, (flow) => flow.themeCombo, 7);
  const narrativeNames = topNames(flows, (flow) => flow.narrativeType, 5);

  const relationNodes = placeNodes(relationNames, flows, (flow) => flow.relationType, 'relation', cx, cy, ring * 1.35, -Math.PI / 2);
  const themeNodes = placeNodes(themeNames, flows, (flow) => flow.themeCombo, 'theme', cx, cy, ring * 2.35, -Math.PI / 2 + Math.PI / 9);
  const narrativeNodes = placeNodes(narrativeNames, flows, (flow) => flow.narrativeType, 'narrative', cx, cy, ring * 3.35, -Math.PI / 2 + Math.PI / 18);
  const nodes = [...relationNodes, ...themeNodes, ...narrativeNodes];
  const byId = new Map(nodes.map((node) => [node.id, node]));

  const edges = [
    ...buildNetworkEdges(flows, byId, 'relation', 'theme', 'drive'),
    ...buildNetworkEdges(flows, byId, 'theme', 'narrative', 'organize'),
    ...buildNetworkEdges(flows, byId, 'narrative', 'relation', 'reshape'),
  ];

  const selected = selectedEdgeDetail.value;
  if (selected) {
    const selectedIds = new Set(selected.flows.map((flow) => flow.id));
    edges.forEach((edge) => {
      edge.active = edge.flows.some((flow) => selectedIds.has(flow.id));
      if (edge.active) {
        edge.source.active = true;
        edge.target.active = true;
      }
    });
  }

  return { nodes, edges };
}

function topNames(flows: LoopFlow[], getter: (flow: LoopFlow) => string, limit: number) {
  return groupDetail(flows, getter)
    .slice(0, limit)
    .map((item) => item.name);
}

function placeNodes(
  names: string[],
  flows: LoopFlow[],
  getter: (flow: LoopFlow) => string,
  layer: NetworkLayer,
  cx: number,
  cy: number,
  radius: number,
  offset = -Math.PI / 2,
) {
  return names.map((name, index) => {
    const angle = offset + (Math.PI * 2 * index) / Math.max(1, names.length);
    const nodeFlows = flows.filter((flow) => getter(flow) === name);
    return {
      id: `${layer}:${name}`,
      name,
      layer,
      value: nodeFlows.reduce((sum, flow) => sum + flow.count, 0),
      flows: nodeFlows,
      ...polar(cx, cy, radius, angle),
    };
  });
}

function buildNetworkEdges(
  flows: LoopFlow[],
  byId: Map<string, NetworkNode>,
  sourceLayer: NetworkLayer,
  targetLayer: NetworkLayer,
  kind: NetworkEdge['kind'],
) {
  const edgeMap = new Map<string, LoopFlow[]>();
  flows.forEach((flow) => {
    const sourceName = networkNodeName(flow, sourceLayer);
    const targetName = networkNodeName(flow, targetLayer);
    const source = byId.get(`${sourceLayer}:${sourceName}`);
    const target = byId.get(`${targetLayer}:${targetName}`);
    if (!source || !target) return;
    const id = `${kind}:${source.id}->${target.id}`;
    const existing = edgeMap.get(id) || [];
    existing.push(flow);
    edgeMap.set(id, existing);
  });

  return [...edgeMap.entries()].map(([id, edgeFlows]) => {
    const [sourceId, targetId] = id.replace(`${kind}:`, '').split('->');
    const source = byId.get(sourceId)!;
    const target = byId.get(targetId)!;
    const value = edgeFlows.reduce((sum, flow) => sum + flow.count, 0);
    const title = kind === 'drive' ? '骨架：角色关系' : kind === 'organize' ? '灵魂：主题组合' : '血肉：叙事节奏';
    const subtitle = kind === 'drive'
      ? `${source.name} -> ${target.name}`
      : kind === 'organize'
        ? `${source.name} -> ${target.name}`
        : `${source.name} 回塑 ${target.name}`;
    return { id, source, target, kind, title, subtitle, value, flows: edgeFlows };
  });
}

function networkNodeName(flow: LoopFlow, layer: NetworkLayer) {
  if (layer === 'relation') return flow.relationType;
  if (layer === 'theme') return flow.themeCombo;
  return flow.narrativeType;
}

function drawNetworkGuides(svg: SVGSVGElement, cx: number, cy: number, ring: number) {
  [ring * 1.35, ring * 2.35, ring * 3.35].forEach((radius, index) => {
    const circle = element('circle');
    circle.setAttribute('class', `network-guide network-guide--${index}`);
    circle.setAttribute('cx', String(cx));
    circle.setAttribute('cy', String(cy));
    circle.setAttribute('r', String(radius));
    svg.appendChild(circle);
  });

  [
    ['角色关系', cx + ring * 1.35 + 16, cy - 6],
    ['主题组合', cx + ring * 2.35 + 16, cy - 6],
    ['叙事结构', cx + ring * 3.35 + 16, cy - 6],
  ].forEach(([label, x, y]) => {
    const text = element('text');
    text.setAttribute('class', 'network-layer-label');
    text.setAttribute('x', String(x));
    text.setAttribute('y', String(y));
    text.textContent = String(label);
    svg.appendChild(text);
  });
}

function drawNetworkEdges(svg: SVGSVGElement, edges: NetworkEdge[]) {
  const max = Math.max(...edges.map((edge) => edge.value), 1);
  edges.forEach((edge) => {
    const bend = edge.kind === 'reshape' ? 0.42 : 0.22;
    const mx = (edge.source.x + edge.target.x) / 2;
    const my = (edge.source.y + edge.target.y) / 2;
    const cx = mx + (edge.target.y - edge.source.y) * bend;
    const cy = my - (edge.target.x - edge.source.x) * bend;
    const d = `M ${edge.source.x} ${edge.source.y} Q ${cx} ${cy} ${edge.target.x} ${edge.target.y}`;
    const selectEdge = () => {
      selectedEdgeDetail.value = { title: edge.title, subtitle: edge.subtitle, flows: edge.flows };
      draw();
    };
    const path = element('path');
    path.setAttribute('class', `network-edge network-edge--${edge.kind} ${edge.active ? 'active' : ''}`);
    path.setAttribute('d', d);
    path.setAttribute('stroke-width', String(1.4 + (edge.value / max) * 5.2));
    path.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(edge.title)}</strong>${escapeHtml(edge.subtitle)}<br>${detailScripts(edge.flows).length} 个关联剧本`));
    path.addEventListener('mouseleave', hideTooltip);
    path.addEventListener('click', selectEdge);
    svg.appendChild(path);

    const hit = element('path');
    hit.setAttribute('class', 'network-edge-hit');
    hit.setAttribute('d', d);
    hit.setAttribute('stroke-width', '18');
    hit.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(edge.title)}</strong>${escapeHtml(edge.subtitle)}<br>${detailScripts(edge.flows).length} 个关联剧本`));
    hit.addEventListener('mouseleave', hideTooltip);
    hit.addEventListener('click', selectEdge);
    svg.appendChild(hit);

    const hotPoint = element('circle');
    hotPoint.setAttribute('class', 'network-edge-point');
    hotPoint.setAttribute('cx', String(edge.source.x * 0.25 + cx * 0.5 + edge.target.x * 0.25));
    hotPoint.setAttribute('cy', String(edge.source.y * 0.25 + cy * 0.5 + edge.target.y * 0.25));
    hotPoint.setAttribute('r', '14');
    hotPoint.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(edge.title)}</strong>${escapeHtml(edge.subtitle)}<br>${detailScripts(edge.flows).length} 个关联剧本`));
    hotPoint.addEventListener('mouseleave', hideTooltip);
    hotPoint.addEventListener('click', selectEdge);
    svg.appendChild(hotPoint);
  });
}

function drawNetworkNodes(svg: SVGSVGElement, nodes: NetworkNode[], ring: number) {
  const max = Math.max(...nodes.map((node) => node.value), 1);
  nodes.forEach((node) => {
    const group = element('g');
    group.setAttribute('class', `network-node ${node.active ? 'active' : ''}`);
    group.setAttribute('transform', `translate(${node.x} ${node.y})`);
    const size = 17 + Math.sqrt(node.value / max) * 13;
    const fill = node.layer === 'relation' ? relationColors[node.name] || '#9a7347' : node.layer === 'theme' ? '#e9bd64' : narrativeColors[node.name] || '#2b7fa3';
    const shape = node.layer === 'theme' ? element('polygon') : node.layer === 'narrative' ? element('rect') : element('circle');
    shape.setAttribute('class', `network-node-shape network-node-shape--${node.layer}`);
    shape.setAttribute('fill', fill);
    if (node.layer === 'theme') {
      const points = Array.from({ length: 6 }, (_, i) => {
        const angle = -Math.PI / 2 + (Math.PI * 2 * i) / 6;
        return `${Math.cos(angle) * size},${Math.sin(angle) * size}`;
      }).join(' ');
      shape.setAttribute('points', points);
    } else if (node.layer === 'narrative') {
      shape.setAttribute('x', String(-size * 0.72));
      shape.setAttribute('y', String(-size * 0.72));
      shape.setAttribute('width', String(size * 1.44));
      shape.setAttribute('height', String(size * 1.44));
      shape.setAttribute('rx', String(size * 0.22));
      shape.setAttribute('transform', 'rotate(45)');
    } else {
      shape.setAttribute('r', String(size));
    }
    group.appendChild(shape);

    const label = element('text');
    label.setAttribute('class', 'network-node-label');
    label.setAttribute('x', '0');
    label.setAttribute('y', String(size + 18));
    label.setAttribute('text-anchor', 'middle');
    label.textContent = truncate(node.name, 7);
    group.appendChild(label);
    svg.appendChild(group);
  });
}

function drawNetworkEdgeHotspots(svg: SVGSVGElement, edges: NetworkEdge[]) {
  edges.forEach((edge) => {
    const bend = edge.kind === 'reshape' ? 0.42 : 0.22;
    const mx = (edge.source.x + edge.target.x) / 2;
    const my = (edge.source.y + edge.target.y) / 2;
    const cx = mx + (edge.target.y - edge.source.y) * bend;
    const cy = my - (edge.target.x - edge.source.x) * bend;
    const hotPoint = element('circle');
    hotPoint.setAttribute('class', 'network-edge-point');
    hotPoint.setAttribute('cx', String(edge.source.x * 0.25 + cx * 0.5 + edge.target.x * 0.25));
    hotPoint.setAttribute('cy', String(edge.source.y * 0.25 + cy * 0.5 + edge.target.y * 0.25));
    hotPoint.setAttribute('r', '16');
    hotPoint.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(edge.title)}</strong>${escapeHtml(edge.subtitle)}<br>${detailScripts(edge.flows).length} 个关联剧本`));
    hotPoint.addEventListener('mouseleave', hideTooltip);
    hotPoint.addEventListener('click', () => {
      selectedEdgeDetail.value = { title: edge.title, subtitle: edge.subtitle, flows: edge.flows };
      draw();
    });
    svg.appendChild(hotPoint);
  });
}

function drawNetworkStoryPanel(svg: SVGSVGElement, width: number, height: number) {
  const edgeDetail = selectedEdgeDetail.value;
  if (!edgeDetail) return;
  const panelW = Math.min(430, Math.max(360, width * 0.36));
  const panelH = Math.min(300, Math.max(250, height * 0.38));
  const panelX = Math.max(28, width - panelW - 54);
  const panelY = Math.max(130, height - panelH - 48);
  const foreignObject = element('foreignObject');
  foreignObject.setAttribute('class', 'network-story-foreign');
  foreignObject.setAttribute('x', String(panelX));
  foreignObject.setAttribute('y', String(panelY));
  foreignObject.setAttribute('width', String(panelW));
  foreignObject.setAttribute('height', String(panelH));

  const card = document.createElement('div');
  card.className = 'network-story-card';

  const list = document.createElement('ol');
  list.className = 'network-story-script-list';
  detailScripts(edgeDetail.flows).forEach((script) => {
    const item = document.createElement('li');
    item.title = `${script.id}${script.path ? `\n${script.path}` : ''}`;
    item.textContent = script.title || script.id;
    list.appendChild(item);
  });
  card.appendChild(list);
  foreignObject.appendChild(card);
  svg.appendChild(foreignObject);
}

function scriptDetailForFlow(flow: LoopFlow): EdgeDetail {
  return {
    title: '当前对象的协同串联',
    subtitle: `${flow.relationType} -> ${flow.themeCombo} -> ${flow.narrativeType}`,
    flows: [flow],
  };
}

function buildTwoLayerHierarchy(flows: LoopFlow[]) {
  const root: NodeDatum = { name: 'root', depth: 0, value: 0, children: [], flows: [] };
  flows.forEach((flow) => {
    root.value += flow.count;
    root.flows.push(flow);
    let relation = root.children.find((item) => item.name === flow.relationType);
    if (!relation) {
      relation = { name: flow.relationType, key: 'relationType', depth: 1, value: 0, children: [], parent: root, flows: [] };
      root.children.push(relation);
    }
    relation.value += flow.count;
    relation.flows.push(flow);
    const themeId = `${flow.relationType}::${flow.themeCombo}`;
    let theme = relation.children.find((item) => item.id === themeId);
    if (!theme) {
      theme = { id: themeId, name: flow.themeCombo, key: 'themeCombo', depth: 2, value: 0, children: [], parent: relation, flows: [] };
      relation.children.push(theme);
    }
    theme.value += flow.count;
    theme.flows.push(flow);
  });
  sortHierarchy(root);
  return root;
}

function layoutAngles(node: NodeDatum, start: number, end: number) {
  node.start = start;
  node.end = end;
  let cursor = start;
  const childCount = Math.max(1, node.children.length);
  node.children.forEach((child) => {
    const span = (end - start) / childCount;
    layoutAngles(child, cursor, cursor + span);
    cursor += span;
  });
}

function sortHierarchy(node: NodeDatum) {
  node.children.sort((a, b) => b.value - a.value);
  node.children.forEach(sortHierarchy);
}

function flatten(node: NodeDatum): NodeDatum[] {
  return [node, ...node.children.flatMap(flatten)];
}

function representativeFlow(node: NodeDatum) {
  return [...node.flows].sort((a, b) => b.count - a.count)[0];
}

function scopedFlows() {
  const scope = selectionScope.value;
  const selected = props.selectedFlow;
  if (!scope && !selected) return props.flows;
  if (scope?.type === 'relation') return props.flows.filter((flow) => flow.relationType === scope.relationType);
  if (scope?.type === 'theme') return props.flows.filter((flow) => flow.relationType === scope.relationType && flow.themeCombo === scope.themeCombo);
  const flowId = scope?.type === 'flow' ? scope.flowId : selected?.id;
  return props.flows.filter((flow) => flow.id === flowId);
}

function detailScripts(flows: LoopFlow[]) {
  const ids = new Set(flows.flatMap((flow) => flow.scripts));
  return props.scripts
    .filter((script) => ids.has(script.id))
    .sort((a, b) => Number(b.sceneCount || 0) - Number(a.sceneCount || 0));
}

function detailKind() {
  if (selectionScope.value?.type === 'relation') return 'relation';
  if (selectionScope.value?.type === 'theme') return 'theme';
  return 'flow';
}

function detailSubtitle(kind: string, total: number, scriptCount: number) {
  if (kind === 'relation') return `关系层详情：${scriptCount} 个剧本，展开该角色关系下的主题、叙事和关系演化分支`;
  if (kind === 'theme') return `主题层详情：${scriptCount} 个剧本，观察该主题分支如何组织叙事与角色关系`;
  return `路径层详情：${total} 个剧本/记录，直接展示该闭环路径背后的剧本证据`;
}

function detailShortTitle(kind: string) {
  const scope = selectionScope.value;
  if (kind === 'relation' && scope?.type === 'relation') return `角色关系详情：${scope.relationType}`;
  if (kind === 'theme' && scope?.type === 'theme') return `主题分支详情：${truncate(scope.themeCombo, 14)}`;
  const flow = props.selectedFlow;
  return flow ? `闭环路径详情：${flow.relationType} / ${flow.narrativeType}` : '闭环路径详情';
}

function detailCurveTitle(kind: string) {
  if (kind === 'relation') return '该关系类型的平均起伏';
  if (kind === 'theme') return '该主题分支的平均起伏';
  return '该路径剧本的平均起伏';
}

function detailLeftPanel(kind: string, flows: LoopFlow[], scripts: ScriptRecord[]) {
  if (kind === 'relation') {
    return {
      title: '高张力阶段事件',
      rows: stageEventRows(scripts)
        .slice(0, 6)
        .map((item) => [item.name, item.note]),
    };
  }
  if (kind === 'theme') {
    return {
      title: '主题证据句',
      rows: themeEvidenceRows(scripts).slice(0, 6).map((item) => [item.name, item.note]),
    };
  }
  return {
    title: '路径阶段事件',
    rows: stageEventRows(scripts).slice(0, 6).map((item) => [item.name, item.note]),
  };
}

function detailRightPanel(kind: string, flows: LoopFlow[], scripts: ScriptRecord[]) {
  if (kind === 'relation') {
    return {
      title: '高强度角色证据',
      rows: relationEvidenceRows(scripts)
        .slice(0, 6)
        .map((item) => [item.name, item.note]),
    };
  }
  if (kind === 'theme') {
    return {
      title: '主题中的角色证据',
      rows: relationEvidenceRows(scripts).slice(0, 6).map((item) => [item.name, item.note]),
    };
  }
  return {
    title: '核心角色对证据',
    rows: relationEvidenceRows(scripts).slice(0, 7).map((item) => [item.name, item.note]),
  };
}

function stageEventRows(scripts: ScriptRecord[]) {
  return scripts
    .flatMap((script) =>
      (script.stageEvents || []).map((event) => ({
        name: `${script.title}｜${event.stage}`,
        note: `${Math.round(event.tension * 100)}%｜${event.event}`,
        count: event.tension,
      })),
    )
    .sort((a, b) => b.count - a.count);
}

function relationEvidenceRows(scripts: ScriptRecord[]) {
  return scripts
    .flatMap((script) =>
      (script.relationEvidence || []).map((item) => ({
        name: `${script.title}｜${item.pair}`,
        note: `${item.stage}｜${item.evidence}`,
        count: item.strength,
      })),
    )
    .sort((a, b) => b.count - a.count);
}

function themeEvidenceRows(scripts: ScriptRecord[]) {
  return scripts
    .flatMap((script) =>
      (script.themeEvidence || []).map((item) => ({
        name: `${script.title}｜${item.theme}`,
        note: item.evidence,
        count: item.weight,
      })),
    )
    .sort((a, b) => b.count - a.count);
}

function evidenceDetail(scripts: ScriptRecord[], kind: 'stage' | 'relation' | 'theme') {
  if (kind === 'stage') {
    const rows = stageEventRows(scripts).slice(0, 8);
    return rows.map((row) => ({ name: row.name, count: Math.max(1, Math.round(row.count * 10)), note: row.note }));
  }
  if (kind === 'relation') {
    const rows = relationEvidenceRows(scripts).slice(0, 8);
    return rows.map((row) => ({ name: row.name, count: Math.max(1, row.count), note: row.note }));
  }
  const rows = themeEvidenceRows(scripts).slice(0, 8);
  return rows.map((row) => ({ name: row.name, count: Math.max(1, row.count), note: row.note }));
}

function aggregateScriptCurve(scripts: ScriptRecord[], key: 'narrativeCurve' | 'evolutionCurve') {
  const curves = scripts.map((script) => script[key]).filter((curve): curve is number[] => Boolean(curve?.length));
  return averageVariableCurves(curves);
}

function aggregateFlowCurve(flows: LoopFlow[], key: 'narrativeCurve' | 'evolutionCurve') {
  return averageVariableCurves(flows.map((flow) => flow[key]).filter((curve): curve is number[] => Boolean(curve?.length)));
}

function averageVariableCurves(curves: number[][]) {
  if (!curves.length) return undefined;
  const samples = 7;
  return Array.from({ length: samples }, (_, index) => {
    const t = index / (samples - 1);
    const value = curves.reduce((sum, curve) => sum + sampleProfile(normalizeProfile(curve), t), 0) / curves.length;
    return Number(value.toFixed(3));
  });
}

function topRelationItems(scripts: ScriptRecord[]) {
  const map = new Map<string, { a: string; b: string; strength: number; type: string }>();
  scripts.forEach((script) => {
    script.topRelations?.forEach((relation) => {
      const key = [relation.a, relation.b, relation.type].sort().join('|');
      const existing = map.get(key);
      if (existing) {
        existing.strength += Number(relation.strength || 0);
      } else {
        map.set(key, { ...relation, strength: Number(relation.strength || 0) });
      }
    });
  });
  return [...map.values()].sort((a, b) => b.strength - a.strength);
}

function themeItemsFromScripts(scripts: ScriptRecord[], flows: LoopFlow[]) {
  const map = new Map<string, number>();
  scripts.forEach((script) => {
    if (script.mainTheme) map.set(script.mainTheme, (map.get(script.mainTheme) || 0) + 2);
    script.subThemes?.forEach((theme) => map.set(theme, (map.get(theme) || 0) + 1));
  });
  if (!map.size) {
    flows.forEach((flow) => flow.themeCombo.split('+').forEach((theme) => map.set(theme, (map.get(theme) || 0) + flow.count)));
  }
  return [...map.entries()].map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count);
}

function scopeLabel() {
  const scope = selectionScope.value;
  const selected = props.selectedFlow;
  if (scope?.type === 'relation') return `角色关系详情：${scope.relationType}`;
  if (scope?.type === 'theme') return `主题分支详情：${scope.relationType} / ${scope.themeCombo}`;
  if (selected) return `闭环路径详情：${selected.relationType} / ${selected.themeCombo} / ${selected.narrativeType}`;
  return '全局详情';
}

function groupDetail(flows: LoopFlow[], getter: (flow: LoopFlow) => string) {
  const map = new Map<string, { name: string; count: number; representative: LoopFlow }>();
  flows.forEach((flow) => {
    const name = getter(flow) || '未标注';
    const existing = map.get(name);
    if (!existing) {
      map.set(name, { name, count: flow.count, representative: flow });
      return;
    }
    existing.count += flow.count;
    if (flow.count > existing.representative.count) existing.representative = flow;
  });
  return [...map.values()].sort((a, b) => b.count - a.count);
}

function isActive(node: NodeDatum) {
  return node.flows.some(isFlowRelated);
}

function isFlowRelated(flow: LoopFlow) {
  const selected = props.selectedFlow;
  if (!selected) return false;
  const scope = selectionScope.value || { type: 'flow' as const, flowId: selected.id };
  if (scope.type === 'relation') return flow.relationType === scope.relationType;
  if (scope.type === 'theme') return flow.relationType === scope.relationType && flow.themeCombo === scope.themeCombo;
  return flow.id === scope.flowId;
}

function nodeColor(node: NodeDatum) {
  if (node.depth === 1) return relationColors[node.name] || '#8a7963';
  const relation = ancestorAtDepth(node, 1)?.name;
  return lighten(relationColors[relation ?? ''] || '#8a7963', 0.14);
}

function ancestorAtDepth(node: NodeDatum, depth: number) {
  let current: NodeDatum | undefined = node;
  while (current && current.depth > depth) current = current.parent;
  return current?.depth === depth ? current : null;
}

function showTooltip(event: MouseEvent, html: string) {
  const tooltip = tooltipRef.value;
  if (!tooltip) return;
  tooltip.innerHTML = html;
  const parent = (event.currentTarget as SVGElement).closest('.view')?.getBoundingClientRect();
  if (!parent) return;
  tooltip.style.left = `${event.clientX - parent.left + 14}px`;
  tooltip.style.top = `${event.clientY - parent.top + 14}px`;
  tooltip.classList.add('visible');
}

function hideTooltip() {
  tooltipRef.value?.classList.remove('visible');
}

function element(name: string) {
  return document.createElementNS('http://www.w3.org/2000/svg', name);
}

function arcPath(cx: number, cy: number, innerR: number, outerR: number, start: number, end: number) {
  const large = end - start > Math.PI ? 1 : 0;
  const p1 = polar(cx, cy, outerR, start);
  const p2 = polar(cx, cy, outerR, end);
  const p3 = polar(cx, cy, innerR, end);
  const p4 = polar(cx, cy, innerR, start);
  return [`M ${p1.x} ${p1.y}`, `A ${outerR} ${outerR} 0 ${large} 1 ${p2.x} ${p2.y}`, `L ${p3.x} ${p3.y}`, `A ${innerR} ${innerR} 0 ${large} 0 ${p4.x} ${p4.y}`, 'Z'].join(' ');
}

function smoothPath(points: { x: number; y: number }[]) {
  if (!points.length) return '';
  return points
    .map((point, index) => {
      if (index === 0) return `M ${point.x} ${point.y}`;
      const previous = points[index - 1];
      const midX = (previous.x + point.x) / 2;
      return `C ${midX} ${previous.y}, ${midX} ${point.y}, ${point.x} ${point.y}`;
    })
    .join(' ');
}

function polar(cx: number, cy: number, r: number, angle: number) {
  return { x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r };
}

function lighten(hex: string, amount: number) {
  const value = hex.replace('#', '');
  const n = parseInt(value, 16);
  const r = Math.min(255, Math.round(((n >> 16) & 255) + 255 * amount));
  const g = Math.min(255, Math.round(((n >> 8) & 255) + 255 * amount));
  const b = Math.min(255, Math.round((n & 255) + 255 * amount));
  return `rgb(${r}, ${g}, ${b})`;
}

function shadeColor(hex: string, amount: number) {
  const value = hex.replace('#', '');
  if (!/^[0-9a-f]{6}$/i.test(value)) return hex;

  const n = parseInt(value, 16);
  const mix = amount >= 0 ? 255 : 0;
  const ratio = Math.min(0.28, Math.abs(amount));
  const r = Math.round(((n >> 16) & 255) * (1 - ratio) + mix * ratio);
  const g = Math.round(((n >> 8) & 255) * (1 - ratio) + mix * ratio);
  const b = Math.round((n & 255) * (1 - ratio) + mix * ratio);

  return `rgb(${r}, ${g}, ${b})`;
}

function truncate(value: string, length: number) {
  return value.length > length ? `${value.slice(0, length)}...` : value;
}

function shortEvidenceLabel(value: string) {
  const parts = value.split('｜');
  return parts.length > 1 ? parts.slice(-2).join('｜') : value;
}

function compactThemeCombo(value: string) {
  const parts = value.split(/[+＋]/).map((item) => item.trim()).filter(Boolean);
  if (parts.length <= 1) return truncate(value, 5);
  return truncate(parts.slice(0, 2).join('+'), 8);
}

function escapeHtml(value: string) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

interface Message {
  id: number;
  role: 'assistant' | 'user';
  text: string;
}

const isOpen = ref(false);
const input = ref('');
const position = ref({ x: Math.max(window.innerWidth - 128, 24), y: Math.max(window.innerHeight - 128, 24) });
const isDragging = ref(false);
const movedDuringDrag = ref(false);
const dragOffset = ref({ x: 0, y: 0 });
const messages = ref<Message[]>([
  {
    id: 1,
    role: 'assistant',
    text: '我可以帮你解释这张图：角色关系如何承载主题、组织叙事，并在结局中转化为新的关系状态。',
  },
]);

const prompts = computed(() => [
  '当前路径说明什么？',
  '最多的角色关系是什么？',
  '有哪些叙事结构？',
  '主题和关系结果怎么联系？',
]);

const petStyle = computed(() => ({
  left: `${position.value.x}px`,
  top: `${position.value.y}px`,
}));

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onDrag);
  window.removeEventListener('pointerup', stopDrag);
});

function togglePanel() {
  if (movedDuringDrag.value) {
    movedDuringDrag.value = false;
    return;
  }
  isOpen.value = !isOpen.value;
}

function startDrag(event: PointerEvent) {
  const target = event.currentTarget as HTMLElement;
  target.setPointerCapture?.(event.pointerId);
  isDragging.value = true;
  movedDuringDrag.value = false;
  dragOffset.value = {
    x: event.clientX - position.value.x,
    y: event.clientY - position.value.y,
  };
  window.addEventListener('pointermove', onDrag);
  window.addEventListener('pointerup', stopDrag);
}

function onDrag(event: PointerEvent) {
  if (!isDragging.value) return;
  movedDuringDrag.value = true;
  const maxX = Math.max(window.innerWidth - 98, 8);
  const maxY = Math.max(window.innerHeight - 98, 8);
  position.value = {
    x: clamp(event.clientX - dragOffset.value.x, 8, maxX),
    y: clamp(event.clientY - dragOffset.value.y, 8, maxY),
  };
}

function stopDrag() {
  isDragging.value = false;
  window.removeEventListener('pointermove', onDrag);
  window.removeEventListener('pointerup', stopDrag);
}

function ask(rawQuestion: string) {
  const question = rawQuestion.trim();
  if (!question) return;
  messages.value.push({ id: Date.now(), role: 'user', text: question });
  messages.value.push({ id: Date.now() + 1, role: 'assistant', text: answer(question) });
  input.value = '';
}

function answer(question: string) {
  const normalized = question.toLowerCase();
  if (!props.flows.length) return '当前还没有读取到剧本数据。请先确认 CSV 表格已经加载。';

  if (question.includes('当前') || question.includes('路径') || question.includes('选中')) {
    return describeActiveFlow();
  }

  if (question.includes('最多') || question.includes('主要') || question.includes('关系')) {
    return describeTopRelations();
  }

  if (question.includes('叙事') || question.includes('结构') || normalized.includes('narrative')) {
    return describeNarratives();
  }

  if (question.includes('主题') || question.includes('结局') || question.includes('结果')) {
    return describeThemeOutcome();
  }

  if (question.includes('剧本') || question.includes('多少') || question.includes('数据')) {
    return `当前可视化读取到 ${props.scripts.length || totalCount()} 条剧本/记录，形成 ${props.flows.length} 种“关系-主题-叙事-结果”闭环模式。`;
  }

  return '可以从三个角度问我：1. 当前路径说明什么；2. 哪类角色关系最多；3. 某种叙事结构如何影响关系结果。';
}

function describeActiveFlow() {
  const flow = activeFlow.value || topFlow();
  if (!flow) return '当前还没有选中路径。你可以先点击图中的某个扇区、波带或外柱。';
  return `当前代表路径是“${flow.relationType} -> ${flow.themeCombo} -> ${flow.narrativeType} -> ${flow.evolutionType}”。它表示：这类剧本以“${flow.relationType}”作为关系起点，通过“${flow.themeCombo}”组织主题，并采用“${flow.narrativeType}”推进剧情，最后形成“${flow.evolutionType}”的关系变化。`;
}

function describeTopRelations() {
  const top = aggregate('relationType').slice(0, 3);
  return `当前数据中较突出的角色关系是：${top.map((item) => `${item.name}（${item.count}）`).join('、')}。这些关系可以被理解为京剧组织冲突和情感秩序的入口。`;
}

function describeNarratives() {
  const top = aggregate('narrativeType').slice(0, 4);
  return `当前主要叙事结构包括：${top.map((item) => `${item.name}（${item.count}）`).join('、')}。它们不是主题本身，而是剧情的组织方式，例如渐强、反转、多峰或平缓推进。`;
}

function describeThemeOutcome() {
  const flow = activeFlow.value || topFlow();
  if (!flow) return '主题和关系结果的联系需要先有路径数据。';
  return `以当前路径为例，“${flow.themeCombo}”把“${flow.relationType}”放入特定价值语境中；经过“${flow.narrativeType}”的剧情组织后，关系最终表现为“${flow.evolutionType}”。也就是说，主题解释关系为何重要，叙事解释关系如何变化。`;
}

function aggregate(key: 'relationType' | 'narrativeType') {
  const map = new Map<string, number>();
  props.flows.forEach((flow) => {
    map.set(flow[key], (map.get(flow[key]) || 0) + flow.count);
  });
  return [...map.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);
}

function topFlow() {
  return [...props.flows].sort((a, b) => b.count - a.count)[0] || null;
}

function totalCount() {
  return props.flows.reduce((sum, flow) => sum + flow.count, 0);
}


</script>
