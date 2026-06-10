<template>
  <main class="app">
    <section class="workspace">
      <section class="view">
          <div class="view-head">
            <div>
              <h2>{{ viewTitle }}</h2>
              <p>{{ chartSubtitle }}</p>
            </div>
            <div class="mode-badge">{{ badgeText }}</div>
          </div>
      
          <div class="sunburst-legend">
            <span><b></b>内圈：角色关系</span>
            <span><b></b>主环：主题组合</span>
            <span><b></b>剧情起伏环带：叙事结构</span>
            <span><b></b>外柱：关系演化结局/规模</span>
          </div>
      
          <button v-if="viewMode === 'detail'" class="view-toggle" type="button" @click="toggleViewMode">
            返回闭环环图
          </button>
          <svg ref="svgRef" role="img" aria-label="京剧闭环复合环图"></svg>
          <div class="chart-caption top-left">
            <strong>{{ viewMode === 'loop' ? '读图方式' : '详情方式' }}</strong>
            <p>{{ viewMode === 'loop' ? '由内向外依次读取：角色关系 -> 主题组合 -> 叙事结构 -> 关系演化结局。' : '这里只展开刚才点击的那一块，不再展示全局占比。' }}</p>
            <p>{{ viewMode === 'loop' ? '外柱高度表示该闭环模式对应的剧本/记录数量。' : '色块宽度表示该对象内部各细分项的剧本/记录数量。' }}</p>
          </div>
          <div class="chart-caption top-right">
            <strong>{{ viewMode === 'loop' ? '剧情起伏环带' : '对象细分' }}</strong>
            <p>{{ viewMode === 'loop' ? '每段波带表示开端、发展、高潮、转折、收束的剧情张力走势。' : '详情页按主题、叙事结构、关系演化结局拆解选中对象。' }}</p>
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
          <div v-if="popupFlow" class="mode-popup">
            <button class="popup-close" type="button" @click="popupFlow = null">×</button>
            <strong>{{ popupFlow.relationType }}</strong>
            <h3>{{ popupFlow.themeCombo }}</h3>
            <p>{{ popupFlow.narrativeType }} -> {{ relationOutcome(popupFlow) }}｜{{ popupFlow.count }} 个剧本/记录</p>
            <svg ref="popupSvgRef" class="popup-mini-svg"></svg>
            <div class="popup-tags">
              <span>关系</span>
              <span>主题</span>
              <span>叙事</span>
              <span>演化</span>
            </div>
          </div>
          <div ref="tooltipRef" class="tooltip"></div>
        </section>
    </section>
    <aside class="pet-assistant" :class="{ open: isOpen, dragging: isDragging }" :style="petStyle">
        <button
          class="pet-avatar"
          type="button"
          aria-label="打开京剧问答助手"
          @pointerdown="startDrag"
          @click="togglePanel"
        >
          <img class="pet-image" src="/数据表合集/5/pet-assistant.png" alt="" draggable="false" />
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
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, reactive, ref, watch, watchEffect } from 'vue';
import { loadDemoDataset } from '../services/tableImport';
import { narrativeColors, outcomeColors, relationColors } from '../services/colorScales';
import type { LoopFilters, LoopFlow, ScriptRecord } from '../types/loop';

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
  | { type: 'relation'; relationType: string }
  | { type: 'theme'; relationType: string; themeCombo: string }
  | { type: 'flow'; flowId: string };

const svgRef = ref<SVGSVGElement | null>(null);
const tooltipRef = ref<HTMLDivElement | null>(null);
const popupSvgRef = ref<SVGSVGElement | null>(null);
const popupFlow = ref<LoopFlow | null>(null);
const viewMode = ref<'loop' | 'detail'>('loop');
const selectionScope = ref<SelectionScope | null>(null);

const narrativeLegend = Object.entries(narrativeColors).map(([name, color]) => ({ name, color }));
const outcomeLegend = Object.entries(outcomeColors).map(([name, color]) => ({ name, color }));

const viewTitle = computed(() => (viewMode.value === 'loop' ? '关系-主题-叙事闭环机制图' : '选中对象细分图'));

watch(
  () => [props.flows, props.selectedFlow],
  () => {
    if (popupFlow.value && !props.flows.some((flow) => flow.id === popupFlow.value?.id)) {
      popupFlow.value = null;
    }
    if (selectionScope.value && !props.selectedFlow) {
      selectionScope.value = null;
    }
    draw();
    drawPopupMini();
  },
  { deep: true },
);

watch(popupFlow, () => drawPopupMini());

onMounted(() => {
  draw();
  window.addEventListener('resize', draw);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', draw);
});

const chartSubtitle = computed(() => {
  if (viewMode.value === 'detail') return `当前展开：${scopeLabel()}。`;
  const flow = props.selectedFlow;
  if (!flow) return '中心向外阅读：角色关系承载主题，主题组织叙事，叙事推进后反向塑造关系。';
  return `${flow.relationType} -> ${flow.themeCombo} -> ${flow.narrativeType} -> ${relationOutcome(flow)}`;
});

const badgeText = computed(() => {
  if (viewMode.value === 'detail') return `${scopedFlows().reduce((sum, flow) => sum + flow.count, 0)} 个剧本`;
  return props.selectedFlow ? `${props.selectedFlow.count} 个剧本` : '待选择';
});

const patternDescription = computed(() => {
  const flow = props.selectedFlow;
  if (viewMode.value === 'detail') return `详情页只解释“${scopeLabel()}”内部如何分解为主题、叙事与关系演化结局。`;
  if (!flow) return '点击圆环扇区查看代表剧本与闭环路径。';
  return `${flow.relationType} 承载 ${flow.themeCombo}，以 ${flow.narrativeType} 推进，最终形成“${relationOutcome(flow)}”的关系演化结局。`;
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
  const cy = isNarrow ? height * 0.47 : height / 2 + 22;
  const maxR = isNarrow ? Math.min(height * 0.35, width * 0.72) : Math.min(width, height) * 0.39;
  const ring = maxR / 5.2;

  if (viewMode.value === 'detail') {
    drawDetailView(svg, cx, cy, width, height, ring);
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
  flatten(root)
    .filter((node) => node.depth > 0)
    .forEach((node) => {
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
  const total = props.flows.reduce((sum, flow) => sum + flow.count, 0) || 1;
  let angle = -Math.PI / 2;
  props.flows.forEach((flow) => {
    const span = (Math.PI * 2 * flow.count) / total;
    const profile = narrativeProfile(flow);
    const color = narrativeColors[flow.narrativeType] || '#c7b894';
    const gap = Math.min(0.018, span * 0.18);
    const usableStart = angle + gap;
    const usableEnd = angle + span - gap;
    const range = outerR - innerR;
    const baseR = innerR + range * 0.2;
    const samples = Math.max(8, Math.min(20, Math.round(span * 14)));
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
    ribbon.setAttribute('class', `narrative-ribbon ${active ? 'active zoomed' : ''}`);
    ribbon.setAttribute('d', [...outerPoints, ...innerPoints].map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ') + ' Z');
    ribbon.setAttribute('fill', color);
    if (props.selectedFlow) ribbon.setAttribute('opacity', active ? '0.82' : '0.12');
    ribbon.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(flow.narrativeType)}</strong>剧情张力波带<br>开端-发展-高潮-转折-收束<br>${escapeHtml(flow.relationType)} -> ${escapeHtml(flow.themeCombo)}`));
    ribbon.addEventListener('mouseleave', hideTooltip);
    ribbon.addEventListener('click', () => selectAndPopup(flow));
    svg.appendChild(ribbon);

    profile.forEach((value, index) => {
      const t = profile.length === 1 ? 0.5 : index / (profile.length - 1);
      const a = usableStart + (usableEnd - usableStart) * t;
      const point = polar(cx, cy, baseR + range * (0.14 + value * 0.62), a);
      const dot = element('circle');
      dot.setAttribute('class', `narrative-dot ${active ? 'active zoomed' : ''}`);
      dot.setAttribute('cx', String(point.x));
      dot.setAttribute('cy', String(point.y));
      dot.setAttribute('r', String(Math.max(2.4, Math.min(4.8, span * 18)) * (active ? 1.25 : 1)));
      dot.setAttribute('fill', color);
      if (props.selectedFlow) dot.setAttribute('opacity', active ? '1' : '0.18');
      dot.addEventListener('mousemove', (event) => showTooltip(event, `<strong>${escapeHtml(flow.narrativeType)}</strong>${stageName(index, profile.length)}张力：${Math.round(value * 100)}%<br>${escapeHtml(flow.relationType)} -> ${escapeHtml(flow.themeCombo)}`));
      dot.addEventListener('mouseleave', hideTooltip);
      dot.addEventListener('click', () => selectAndPopup(flow));
      svg.appendChild(dot);
    });
    angle += span;
  });
}

function narrativeProfile(flow: LoopFlow) {
  if (flow.narrativeCurve?.length) return normalizeProfile(flow.narrativeCurve);
  return fallbackProfile(flow);
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

function drawOuterBars(svg: SVGSVGElement, cx: number, cy: number, innerR: number, outerR: number) {
  const total = props.flows.reduce((sum, flow) => sum + flow.count, 0) || 1;
  const maxCount = Math.max(...props.flows.map((flow) => flow.count), 1);
  let angle = -Math.PI / 2;
  props.flows.forEach((flow, index) => {
    const span = (Math.PI * 2 * flow.count) / total;
    const gap = Math.min(0.018, span * 0.22);
    const heightJitter = 0.18 + 0.16 * Math.sin(index * 1.7);
    const height = (outerR - innerR) * (0.28 + 0.64 * Math.sqrt(flow.count / maxCount) + heightJitter);
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
  selectionScope.value = { type: 'flow', flowId: flow.id };
  popupFlow.value = flow;
  emit('select', flow);
  drawPopupMini();
}

function selectNode(node: NodeDatum) {
  const representative = representativeFlow(node);
  if (node.depth === 1) {
    selectionScope.value = { type: 'relation', relationType: representative.relationType };
  } else {
    selectionScope.value = {
      type: 'theme',
      relationType: representative.relationType,
      themeCombo: representative.themeCombo,
    };
  }
  popupFlow.value = representative;
  emit('select', representative);
  drawPopupMini();
}

async function drawPopupMini() {
  await nextTick();
  const flow = popupFlow.value;
  const svg = popupSvgRef.value;
  if (!flow || !svg) return;
  const width = 260;
  const height = 122;
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.innerHTML = '';

  const profile = narrativeProfile(flow);
  const left = 18;
  const top = 16;
  const barW = 22;
  profile.forEach((value, index) => {
    const h = 56 * value;
    const rect = element('rect');
    rect.setAttribute('x', String(left + index * 34));
    rect.setAttribute('y', String(top + 62 - h));
    rect.setAttribute('width', String(barW));
    rect.setAttribute('height', String(h));
    rect.setAttribute('rx', '4');
    rect.setAttribute('fill', narrativeColors[flow.narrativeType] || '#c7b894');
    svg.appendChild(rect);
  });

  profile.forEach((_, index) => {
    const text = element('text');
    text.setAttribute('x', String(left + index * 34 + barW / 2));
    text.setAttribute('y', '94');
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('fill', '#b9a991');
    text.setAttribute('font-size', '11');
    text.textContent = stageName(index, profile.length).slice(0, 1);
    svg.appendChild(text);
  });

  const circle = element('circle');
  circle.setAttribute('cx', '218');
  circle.setAttribute('cy', '50');
  circle.setAttribute('r', '28');
  circle.setAttribute('fill', outcomeColors[relationOutcome(flow)] || '#8c6db0');
  circle.setAttribute('opacity', '0.9');
  svg.appendChild(circle);

  const count = element('text');
  count.setAttribute('x', '218');
  count.setAttribute('y', '56');
  count.setAttribute('text-anchor', 'middle');
  count.setAttribute('fill', '#101419');
  count.setAttribute('font-size', '18');
  count.setAttribute('font-weight', '800');
  count.textContent = String(flow.count);
  svg.appendChild(count);

  const caption = element('text');
  caption.setAttribute('x', '218');
  caption.setAttribute('y', '94');
  caption.setAttribute('text-anchor', 'middle');
  caption.setAttribute('fill', '#b9a991');
  caption.setAttribute('font-size', '11');
  caption.textContent = '规模';
  svg.appendChild(caption);
}

function drawGuides(svg: SVGSVGElement, cx: number, cy: number, ring: number) {
  for (let i = 1; i <= 6; i += 1) {
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
  image.setAttribute('href', '/数据表合集/5/center-opera.jpg');
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
    const prompt = props.selectedFlow ? `点击中心展开：${escapeHtml(scopeLabel())}` : '先点击一个角色关系、主题或外层路径';
    showTooltip(event, `<strong>${viewMode.value === 'loop' ? '对象详情入口' : '返回闭环环图'}</strong>${prompt}`);
  });
  hit.addEventListener('mouseleave', hideTooltip);
  hit.addEventListener('click', toggleViewMode);
  svg.appendChild(hit);
}

function toggleViewMode() {
  if (viewMode.value === 'loop' && !props.selectedFlow) return;
  viewMode.value = viewMode.value === 'loop' ? 'detail' : 'loop';
  popupFlow.value = null;
  if (viewMode.value === 'loop') selectionScope.value = null;
  hideTooltip();
  draw();
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
  node.children.forEach((child) => {
    const span = (end - start) * (child.value / node.value);
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

function truncate(value: string, length: number) {
  return value.length > length ? `${value.slice(0, length)}...` : value;
}

function shortEvidenceLabel(value: string) {
  const parts = value.split('｜');
  return parts.length > 1 ? parts.slice(-2).join('｜') : value;
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
