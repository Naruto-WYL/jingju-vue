<template>
  <div ref="wrapRef" class="vertical-pattern-view">
    <div class="period-tabs" aria-label="时期筛选">
      <button
        v-for="period in periodTabs"
        :key="period.value"
        type="button"
        :class="{ active: activePeriod === period.value }"
        @click="setPeriod(period.value)"
      >
        {{ period.label }}
      </button>
    </div>

    <div class="vertical-pattern-canvas">
      <svg ref="svgRef" class="vertical-pattern-svg" role="img" aria-label="角色行当时期对应模式竖向图" />
      <div class="zoom-controls" aria-label="图形缩放">
        <button type="button" title="放大" @click="zoomBy(1.18)">+</button>
        <button type="button" title="缩小" @click="zoomBy(1 / 1.18)">-</button>
        <button type="button" title="重置" @click="resetZoom">1:1</button>
      </div>
    </div>

    <section class="context-panel">
      <strong>{{ currentContext.title }}</strong>
      <p>{{ currentContext.desc }}</p>
    </section>

    <div
      v-if="tooltip.visible"
      class="pattern-tooltip"
      :style="{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }"
    >
      <strong>{{ tooltip.title }}</strong>
      <span>{{ tooltip.value }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as d3 from 'd3'

const rawNodes = [
        { name: "神话传说", type: "period", sort: 1 }, { name: "春秋战国", type: "period", sort: 2 }, 
        { name: "秦汉", type: "period", sort: 3 }, { name: "三国", type: "period", sort: 4 }, 
        { name: "晋朝", type: "period", sort: 5 }, { name: "隋唐五代", type: "period", sort: 6 }, 
        { name: "宋朝", type: "period", sort: 7 }, { name: "元朝", type: "period", sort: 8 }, 
        { name: "明朝", type: "period", sort: 9 }, { name: "清朝", type: "period", sort: 10 }, 
        
        { name: "皇亲国戚", type: "identity", sort: 20 }, { name: "朝堂文臣", type: "identity", sort: 21 }, 
        { name: "统兵将帅", type: "identity", sort: 22 }, { name: "幕僚军师", type: "identity", sort: 23 }, 
        { name: "内廷宦官", type: "identity", sort: 24 }, { name: "世家女眷", type: "identity", sort: 25 }, 
        { name: "丫鬟侍女", type: "identity", sort: 26 }, { name: "府第家仆", type: "identity", sort: 27 }, 
        { name: "儒生学子", type: "identity", sort: 28 }, { name: "行伍军卒", type: "identity", sort: 29 }, 
        { name: "衙门差役", type: "identity", sort: 30 }, { name: "市井布衣", type: "identity", sort: 31 }, 
        { name: "绿林草莽", type: "identity", sort: 32 }, { name: "释道僧尼", type: "identity", sort: 33 }, 
        { name: "神仙妖魅", type: "identity", sort: 34 },
        
        // 核心：16 大行当完整集结
        { name: "老生", type: "role", sort: 40 }, { name: "生", type: "role", sort: 41 }, 
        { name: "末", type: "role", sort: 42 }, { name: "外", type: "role", sort: 43 },
        { name: "武生", type: "role", sort: 44 }, { name: "红生", type: "role", sort: 45 }, 
        { name: "小生", type: "role", sort: 46 }, 
        { name: "净", type: "role", sort: 47 }, { name: "副净", type: "role", sort: 48 }, 
        { name: "丑", type: "role", sort: 49 }, { name: "杂", type: "role", sort: 50 },
        { name: "正旦", type: "role", sort: 51 }, { name: "青衣", type: "role", sort: 52 }, 
        { name: "旦", type: "role", sort: 53 }, { name: "花旦", type: "role", sort: 54 }, 
        { name: "老旦", type: "role", sort: 55 }, { name: "彩旦", type: "role", sort: 56 }
        // 注意：原列表中包含武旦，但您的16行当列表未提供“武旦”，若需替换可微调，此处严格按您16种列表排布。
    ]
const rawLinks = [
        {
                "source": "神话传说",
                "target": "皇亲国戚",
                "value": 3
        },
        {
                "source": "神话传说",
                "target": "朝堂文臣",
                "value": 3
        },
        {
                "source": "神话传说",
                "target": "世家女眷",
                "value": 1
        },
        {
                "source": "神话传说",
                "target": "衙门差役",
                "value": 1
        },
        {
                "source": "神话传说",
                "target": "释道僧尼",
                "value": 8
        },
        {
                "source": "神话传说",
                "target": "神仙妖魅",
                "value": 49
        },
        {
                "source": "春秋战国",
                "target": "皇亲国戚",
                "value": 2
        },
        {
                "source": "春秋战国",
                "target": "统兵将帅",
                "value": 2
        },
        {
                "source": "春秋战国",
                "target": "世家女眷",
                "value": 2
        },
        {
                "source": "春秋战国",
                "target": "儒生学子",
                "value": 5
        },
        {
                "source": "春秋战国",
                "target": "市井布衣",
                "value": 2
        },
        {
                "source": "春秋战国",
                "target": "释道僧尼",
                "value": 1
        },
        {
                "source": "秦汉",
                "target": "皇亲国戚",
                "value": 19
        },
        {
                "source": "秦汉",
                "target": "朝堂文臣",
                "value": 7
        },
        {
                "source": "秦汉",
                "target": "统兵将帅",
                "value": 1
        },
        {
                "source": "秦汉",
                "target": "幕僚军师",
                "value": 11
        },
        {
                "source": "秦汉",
                "target": "世家女眷",
                "value": 18
        },
        {
                "source": "秦汉",
                "target": "府第家仆",
                "value": 2
        },
        {
                "source": "秦汉",
                "target": "儒生学子",
                "value": 3
        },
        {
                "source": "秦汉",
                "target": "行伍军卒",
                "value": 4
        },
        {
                "source": "秦汉",
                "target": "衙门差役",
                "value": 1
        },
        {
                "source": "秦汉",
                "target": "市井布衣",
                "value": 8
        },
        {
                "source": "秦汉",
                "target": "绿林草莽",
                "value": 2
        },
        {
                "source": "秦汉",
                "target": "释道僧尼",
                "value": 9
        },
        {
                "source": "秦汉",
                "target": "神仙妖魅",
                "value": 7
        },
        {
                "source": "三国",
                "target": "皇亲国戚",
                "value": 10
        },
        {
                "source": "三国",
                "target": "朝堂文臣",
                "value": 80
        },
        {
                "source": "三国",
                "target": "统兵将帅",
                "value": 219
        },
        {
                "source": "三国",
                "target": "幕僚军师",
                "value": 105
        },
        {
                "source": "三国",
                "target": "世家女眷",
                "value": 22
        },
        {
                "source": "三国",
                "target": "丫鬟侍女",
                "value": 1
        },
        {
                "source": "三国",
                "target": "儒生学子",
                "value": 8
        },
        {
                "source": "三国",
                "target": "行伍军卒",
                "value": 2
        },
        {
                "source": "三国",
                "target": "市井布衣",
                "value": 1
        },
        {
                "source": "三国",
                "target": "释道僧尼",
                "value": 2
        },
        {
                "source": "晋朝",
                "target": "皇亲国戚",
                "value": 1
        },
        {
                "source": "晋朝",
                "target": "世家女眷",
                "value": 1
        },
        {
                "source": "晋朝",
                "target": "儒生学子",
                "value": 1
        },
        {
                "source": "晋朝",
                "target": "市井布衣",
                "value": 1
        },
        {
                "source": "晋朝",
                "target": "释道僧尼",
                "value": 5
        },
        {
                "source": "隋唐五代",
                "target": "皇亲国戚",
                "value": 44
        },
        {
                "source": "隋唐五代",
                "target": "朝堂文臣",
                "value": 12
        },
        {
                "source": "隋唐五代",
                "target": "统兵将帅",
                "value": 48
        },
        {
                "source": "隋唐五代",
                "target": "世家女眷",
                "value": 41
        },
        {
                "source": "隋唐五代",
                "target": "儒生学子",
                "value": 3
        },
        {
                "source": "隋唐五代",
                "target": "衙门差役",
                "value": 1
        },
        {
                "source": "隋唐五代",
                "target": "市井布衣",
                "value": 2
        },
        {
                "source": "隋唐五代",
                "target": "释道僧尼",
                "value": 2
        },
        {
                "source": "隋唐五代",
                "target": "神仙妖魅",
                "value": 3
        },
        {
                "source": "宋朝",
                "target": "皇亲国戚",
                "value": 37
        },
        {
                "source": "宋朝",
                "target": "朝堂文臣",
                "value": 27
        },
        {
                "source": "宋朝",
                "target": "统兵将帅",
                "value": 65
        },
        {
                "source": "宋朝",
                "target": "世家女眷",
                "value": 45
        },
        {
                "source": "宋朝",
                "target": "府第家仆",
                "value": 1
        },
        {
                "source": "宋朝",
                "target": "儒生学子",
                "value": 2
        },
        {
                "source": "宋朝",
                "target": "行伍军卒",
                "value": 1
        },
        {
                "source": "宋朝",
                "target": "衙门差役",
                "value": 3
        },
        {
                "source": "宋朝",
                "target": "市井布衣",
                "value": 9
        },
        {
                "source": "宋朝",
                "target": "绿林草莽",
                "value": 1
        },
        {
                "source": "宋朝",
                "target": "释道僧尼",
                "value": 7
        },
        {
                "source": "宋朝",
                "target": "神仙妖魅",
                "value": 8
        },
        {
                "source": "元朝",
                "target": "朝堂文臣",
                "value": 3
        },
        {
                "source": "元朝",
                "target": "统兵将帅",
                "value": 2
        },
        {
                "source": "元朝",
                "target": "幕僚军师",
                "value": 1
        },
        {
                "source": "元朝",
                "target": "世家女眷",
                "value": 15
        },
        {
                "source": "元朝",
                "target": "府第家仆",
                "value": 1
        },
        {
                "source": "元朝",
                "target": "儒生学子",
                "value": 3
        },
        {
                "source": "元朝",
                "target": "行伍军卒",
                "value": 1
        },
        {
                "source": "元朝",
                "target": "衙门差役",
                "value": 1
        },
        {
                "source": "元朝",
                "target": "市井布衣",
                "value": 1
        },
        {
                "source": "元朝",
                "target": "释道僧尼",
                "value": 3
        },
        {
                "source": "元朝",
                "target": "神仙妖魅",
                "value": 3
        },
        {
                "source": "明朝",
                "target": "皇亲国戚",
                "value": 5
        },
        {
                "source": "明朝",
                "target": "朝堂文臣",
                "value": 27
        },
        {
                "source": "明朝",
                "target": "内廷宦官",
                "value": 1
        },
        {
                "source": "明朝",
                "target": "世家女眷",
                "value": 34
        },
        {
                "source": "明朝",
                "target": "丫鬟侍女",
                "value": 3
        },
        {
                "source": "明朝",
                "target": "府第家仆",
                "value": 1
        },
        {
                "source": "明朝",
                "target": "儒生学子",
                "value": 16
        },
        {
                "source": "明朝",
                "target": "行伍军卒",
                "value": 2
        },
        {
                "source": "明朝",
                "target": "衙门差役",
                "value": 4
        },
        {
                "source": "明朝",
                "target": "市井布衣",
                "value": 2
        },
        {
                "source": "明朝",
                "target": "绿林草莽",
                "value": 2
        },
        {
                "source": "明朝",
                "target": "释道僧尼",
                "value": 20
        },
        {
                "source": "明朝",
                "target": "神仙妖魅",
                "value": 7
        },
        {
                "source": "清朝",
                "target": "皇亲国戚",
                "value": 2
        },
        {
                "source": "清朝",
                "target": "朝堂文臣",
                "value": 6
        },
        {
                "source": "清朝",
                "target": "世家女眷",
                "value": 13
        },
        {
                "source": "清朝",
                "target": "丫鬟侍女",
                "value": 1
        },
        {
                "source": "清朝",
                "target": "儒生学子",
                "value": 3
        },
        {
                "source": "清朝",
                "target": "行伍军卒",
                "value": 3
        },
        {
                "source": "清朝",
                "target": "市井布衣",
                "value": 2
        },
        {
                "source": "清朝",
                "target": "绿林草莽",
                "value": 18
        },
        {
                "source": "清朝",
                "target": "释道僧尼",
                "value": 10
        },
        {
                "source": "清朝",
                "target": "神仙妖魅",
                "value": 2
        },
        {
                "source": "皇亲国戚",
                "target": "老生",
                "value": 25
        },
        {
                "source": "皇亲国戚",
                "target": "生",
                "value": 2
        },
        {
                "source": "皇亲国戚",
                "target": "末",
                "value": 3
        },
        {
                "source": "皇亲国戚",
                "target": "外",
                "value": 2
        },
        {
                "source": "皇亲国戚",
                "target": "武生",
                "value": 1
        },
        {
                "source": "皇亲国戚",
                "target": "小生",
                "value": 31
        },
        {
                "source": "皇亲国戚",
                "target": "副净",
                "value": 1
        },
        {
                "source": "皇亲国戚",
                "target": "正旦",
                "value": 1
        },
        {
                "source": "皇亲国戚",
                "target": "旦",
                "value": 44
        },
        {
                "source": "皇亲国戚",
                "target": "花旦",
                "value": 1
        },
        {
                "source": "皇亲国戚",
                "target": "老旦",
                "value": 12
        },
        {
                "source": "朝堂文臣",
                "target": "老生",
                "value": 32
        },
        {
                "source": "朝堂文臣",
                "target": "末",
                "value": 11
        },
        {
                "source": "朝堂文臣",
                "target": "外",
                "value": 2
        },
        {
                "source": "朝堂文臣",
                "target": "净",
                "value": 109
        },
        {
                "source": "朝堂文臣",
                "target": "丑",
                "value": 9
        },
        {
                "source": "朝堂文臣",
                "target": "杂",
                "value": 1
        },
        {
                "source": "朝堂文臣",
                "target": "旦",
                "value": 1
        },
        {
                "source": "统兵将帅",
                "target": "老生",
                "value": 84
        },
        {
                "source": "统兵将帅",
                "target": "生",
                "value": 12
        },
        {
                "source": "统兵将帅",
                "target": "末",
                "value": 2
        },
        {
                "source": "统兵将帅",
                "target": "外",
                "value": 1
        },
        {
                "source": "统兵将帅",
                "target": "武生",
                "value": 62
        },
        {
                "source": "统兵将帅",
                "target": "红生",
                "value": 73
        },
        {
                "source": "统兵将帅",
                "target": "小生",
                "value": 21
        },
        {
                "source": "统兵将帅",
                "target": "净",
                "value": 76
        },
        {
                "source": "统兵将帅",
                "target": "副净",
                "value": 3
        },
        {
                "source": "统兵将帅",
                "target": "丑",
                "value": 3
        },
        {
                "source": "幕僚军师",
                "target": "老生",
                "value": 95
        },
        {
                "source": "幕僚军师",
                "target": "生",
                "value": 4
        },
        {
                "source": "幕僚军师",
                "target": "末",
                "value": 1
        },
        {
                "source": "幕僚军师",
                "target": "外",
                "value": 1
        },
        {
                "source": "幕僚军师",
                "target": "武生",
                "value": 2
        },
        {
                "source": "幕僚军师",
                "target": "净",
                "value": 13
        },
        {
                "source": "幕僚军师",
                "target": "丑",
                "value": 1
        },
        {
                "source": "内廷宦官",
                "target": "外",
                "value": 1
        },
        {
                "source": "世家女眷",
                "target": "正旦",
                "value": 31
        },
        {
                "source": "世家女眷",
                "target": "青衣",
                "value": 5
        },
        {
                "source": "世家女眷",
                "target": "旦",
                "value": 90
        },
        {
                "source": "世家女眷",
                "target": "花旦",
                "value": 3
        },
        {
                "source": "世家女眷",
                "target": "老旦",
                "value": 62
        },
        {
                "source": "世家女眷",
                "target": "彩旦",
                "value": 1
        },
        {
                "source": "丫鬟侍女",
                "target": "旦",
                "value": 5
        },
        {
                "source": "府第家仆",
                "target": "老生",
                "value": 1
        },
        {
                "source": "府第家仆",
                "target": "外",
                "value": 3
        },
        {
                "source": "府第家仆",
                "target": "丑",
                "value": 1
        },
        {
                "source": "儒生学子",
                "target": "老生",
                "value": 11
        },
        {
                "source": "儒生学子",
                "target": "武生",
                "value": 2
        },
        {
                "source": "儒生学子",
                "target": "小生",
                "value": 23
        },
        {
                "source": "儒生学子",
                "target": "丑",
                "value": 8
        },
        {
                "source": "行伍军卒",
                "target": "末",
                "value": 1
        },
        {
                "source": "行伍军卒",
                "target": "武生",
                "value": 1
        },
        {
                "source": "行伍军卒",
                "target": "净",
                "value": 1
        },
        {
                "source": "行伍军卒",
                "target": "丑",
                "value": 7
        },
        {
                "source": "行伍军卒",
                "target": "杂",
                "value": 3
        },
        {
                "source": "衙门差役",
                "target": "生",
                "value": 1
        },
        {
                "source": "衙门差役",
                "target": "净",
                "value": 1
        },
        {
                "source": "衙门差役",
                "target": "丑",
                "value": 9
        },
        {
                "source": "市井布衣",
                "target": "老生",
                "value": 1
        },
        {
                "source": "市井布衣",
                "target": "生",
                "value": 2
        },
        {
                "source": "市井布衣",
                "target": "外",
                "value": 2
        },
        {
                "source": "市井布衣",
                "target": "小生",
                "value": 2
        },
        {
                "source": "市井布衣",
                "target": "丑",
                "value": 15
        },
        {
                "source": "市井布衣",
                "target": "旦",
                "value": 1
        },
        {
                "source": "市井布衣",
                "target": "老旦",
                "value": 1
        },
        {
                "source": "市井布衣",
                "target": "彩旦",
                "value": 4
        },
        {
                "source": "绿林草莽",
                "target": "武生",
                "value": 19
        },
        {
                "source": "绿林草莽",
                "target": "净",
                "value": 2
        },
        {
                "source": "绿林草莽",
                "target": "副净",
                "value": 1
        },
        {
                "source": "绿林草莽",
                "target": "丑",
                "value": 1
        },
        {
                "source": "释道僧尼",
                "target": "老生",
                "value": 6
        },
        {
                "source": "释道僧尼",
                "target": "生",
                "value": 1
        },
        {
                "source": "释道僧尼",
                "target": "末",
                "value": 3
        },
        {
                "source": "释道僧尼",
                "target": "外",
                "value": 5
        },
        {
                "source": "释道僧尼",
                "target": "小生",
                "value": 6
        },
        {
                "source": "释道僧尼",
                "target": "净",
                "value": 14
        },
        {
                "source": "释道僧尼",
                "target": "丑",
                "value": 30
        },
        {
                "source": "释道僧尼",
                "target": "杂",
                "value": 1
        },
        {
                "source": "释道僧尼",
                "target": "花旦",
                "value": 1
        },
        {
                "source": "神仙妖魅",
                "target": "生",
                "value": 3
        },
        {
                "source": "神仙妖魅",
                "target": "末",
                "value": 2
        },
        {
                "source": "神仙妖魅",
                "target": "外",
                "value": 2
        },
        {
                "source": "神仙妖魅",
                "target": "武生",
                "value": 29
        },
        {
                "source": "神仙妖魅",
                "target": "小生",
                "value": 9
        },
        {
                "source": "神仙妖魅",
                "target": "净",
                "value": 12
        },
        {
                "source": "神仙妖魅",
                "target": "丑",
                "value": 6
        },
        {
                "source": "神仙妖魅",
                "target": "旦",
                "value": 16
        }
]
const roleProfiles = {
        "老生": [
                "男",
                "中年",
                "忠义",
                "二黄系",
                "韵白型",
                "程式化",
                "中等"
        ],
        "生": [
                "男",
                "中年",
                "忠义",
                "西皮系",
                "韵白型",
                "程式化",
                "中等"
        ],
        "末": [
                "男",
                "老年",
                "忠义",
                "二黄系",
                "韵白型",
                "程式化",
                "中等"
        ],
        "外": [
                "男",
                "老年",
                "威严",
                "二黄系",
                "韵白型",
                "程式化",
                "少量"
        ],
        "武生": [
                "男",
                "青年",
                "刚烈",
                "西皮系",
                "少念型",
                "程式化",
                "中等"
        ],
        "红生": [
                "男",
                "中年",
                "忠义",
                "西皮系",
                "韵白型",
                "程式化",
                "中等"
        ],
        "小生": [
                "男",
                "青年",
                "机智",
                "西皮系",
                "念白型",
                "身段型",
                "中等"
        ],
        "净": [
                "男",
                "中年",
                "豪放",
                "西皮系",
                "京白型",
                "程式化",
                "中等"
        ],
        "副净": [
                "男",
                "中年",
                "阴险",
                "西皮系",
                "京白型",
                "程式化",
                "中等"
        ],
        "丑": [
                "男",
                "中年",
                "滑稽",
                "其他",
                "京白型",
                "程式化",
                "少量"
        ],
        "杂": [
                "男",
                "青年",
                "机智",
                "其他",
                "少念型",
                "少做功",
                "少量"
        ],
        "正旦": [
                "女",
                "中年",
                "忠义",
                "二黄系",
                "韵白型",
                "身段型",
                "中等"
        ],
        "青衣": [
                "女",
                "中年",
                "忠义",
                "二黄系",
                "韵白型",
                "身段型",
                "无"
        ],
        "旦": [
                "女",
                "少年",
                "机智",
                "西皮系",
                "韵白型",
                "身段型",
                "中等"
        ],
        "花旦": [
                "女",
                "少年",
                "机智",
                "西皮系",
                "京白型",
                "舞蹈型",
                "少量"
        ],
        "老旦": [
                "女",
                "老年",
                "威严",
                "西皮系",
                "京白型",
                "少做功",
                "中等"
        ],
        "彩旦": [
                "女",
                "老年",
                "滑稽",
                "吹腔系",
                "京白型",
                "程式化",
                "少量"
        ]
}

const W = 467
const H = 575
const NODE_H = 9
const PERIOD_Y = 28
const IDENTITY_Y = 200
const ROLE_Y = 352
const MATRIX_TOP = 404
const MATRIX_BOTTOM = 565
const allPeriods = ['神话传说', '春秋战国', '秦汉', '三国', '晋朝', '隋唐五代', '宋朝', '元朝', '明朝', '清朝']
const periodTabs = [
  { value: 'all', label: '全局纵览' },
  ...allPeriods.map((period) => ({ value: period, label: period })),
]
const contextData = {
  all: {
    title: '全景视野：身份与行当的真实映射关系',
    desc: '本图基于角色推断汇总构建：上方为历史时期，中部为十五类身份，下方为行当。线条粗细表示样本数量，悬停可查看映射强度。',
  },
  神话传说: {
    title: '神话传说：神仙妖魅与释道僧尼的舞台想象',
    desc: '该时期样本以神仙妖魅、释道僧尼等身份为主，武生、净、旦等行当共同承担奇幻人物塑造。',
  },
  春秋战国: {
    title: '春秋战国：列国人物与士人叙事',
    desc: '该时期更常见朝堂文臣、统兵将帅、儒生学子与世家女眷，主题集中在忠烈、谋略和伦理冲突。',
  },
  秦汉: {
    title: '秦汉：帝王将相与楚汉人物谱系',
    desc: '秦汉题材中皇亲国戚、统兵将帅、幕僚军师的流向较突出，生、净、老生等行当共同呈现英雄叙事。',
  },
  三国: {
    title: '三国：将帅、军师与红生行当的高密度时期',
    desc: '三国剧目角色规模大，统兵将帅和幕僚军师高度集中，老生、红生、净、武生等行当形成清晰流向。',
  },
  晋朝: {
    title: '晋朝：儒生学子与世家女眷的文戏线索',
    desc: '晋朝样本较少，但人物关系偏文戏和情感叙事，儒生学子、世家女眷与小生、旦类行当关系更明显。',
  },
  隋唐五代: {
    title: '隋唐五代：将帅、皇亲与世家女眷的并行结构',
    desc: '该时期既有统兵将帅，也有世家女眷与皇亲国戚相关人物，武生、老生、旦类行当均有表现。',
  },
  宋朝: {
    title: '宋朝：公案、忠烈与市井人物的集中呈现',
    desc: '宋朝样本包含公案戏和忠烈题材，朝堂文臣、统兵将帅、衙门差役、市井布衣等身份构成较丰富。',
  },
  元朝: {
    title: '元朝：悲剧女性与市井叙事',
    desc: '元朝相关剧目常见世家女眷、市井布衣、衙门差役等身份，青衣、正旦、老旦等行当更突出。',
  },
  明朝: {
    title: '明朝：才子佳人与府第关系',
    desc: '明朝题材中儒生学子、世家女眷、丫鬟侍女、府第家仆等身份较常见，流向偏小生、旦类、花旦和丑角。',
  },
  清朝: {
    title: '清朝：侠义、公案与市井身份',
    desc: '清朝样本强调衙门差役、市井布衣、绿林草莽等身份，短打武生、丑角、杂行等更能体现社会百态。',
  },
}
const traitsMeta = [
  { id: 1, name: '性别', categories: ['男', '女'] },
  { id: 2, name: '年龄', categories: ['少年', '青年', '中年', '老年'] },
  { id: 3, name: '性格', categories: ['忠义', '刚烈', '机智', '威严', '阴险', '豪放', '滑稽'] },
  { id: 4, name: '唱腔', categories: ['西皮系', '二黄系', '昆腔系', '吹腔系', '其他'] },
  { id: 5, name: '念白', categories: ['念白型', '韵白型', '京白型', '少念型'] },
  { id: 6, name: '做工', categories: ['程式化', '身段型', '舞蹈型', '少做功'] },
  { id: 7, name: '武打', categories: ['无', '少量', '中等', '大量'] },
]

const colors = {
  皇亲国戚: '#e67e22', 朝堂文臣: '#1abc9c', 统兵将帅: '#c0392b', 幕僚军师: '#2980b9', 内廷宦官: '#8e44ad',
  世家女眷: '#d2527f', 丫鬟侍女: '#f39c12', 府第家仆: '#d35400', 儒生学子: '#27ae60', 行伍军卒: '#c0392b',
  衙门差役: '#7f8c8d', 市井布衣: '#3498db', 绿林草莽: '#16a085', 释道僧尼: '#f1c40f', 神仙妖魅: '#2c3e50',
  老生: '#8f8a7c', 生: '#8f8a7c', 末: '#8f8a7c', 外: '#8f8a7c', 武生: '#8f8a7c', 红生: '#8f8a7c', 小生: '#8f8a7c',
  净: '#8f8a7c', 副净: '#8f8a7c', 丑: '#8f8a7c', 杂: '#8f8a7c', 正旦: '#8f8a7c', 青衣: '#8f8a7c', 旦: '#8f8a7c', 花旦: '#8f8a7c', 老旦: '#8f8a7c', 彩旦: '#8f8a7c',
}

const svgRef = ref(null)
const wrapRef = ref(null)
const activePeriod = ref('all')
const currentContext = computed(() => contextData[activePeriod.value] || contextData.all)
const tooltip = reactive({ visible: false, x: 0, y: 0, title: '', value: '' })
const zoomTransform = ref(d3.zoomIdentity)
let resizeObserver = null
let zoomBehavior = null

onMounted(async () => {
  await nextTick()
  draw()
  resizeObserver = new ResizeObserver(draw)
  if (wrapRef.value) resizeObserver.observe(wrapRef.value)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  if (svgRef.value) d3.select(svgRef.value).on('.zoom', null)
})

function draw() {
  if (!svgRef.value) return

  const svg = d3.select(svgRef.value)
  svg.selectAll('*').remove()
  svg.attr('viewBox', `0 0 ${W} ${H}`).attr('preserveAspectRatio', 'xMidYMid meet')
  const zoomLayer = svg.append('g').attr('class', 'zoom-layer')

  const nodes = buildNodes()
  const links = rawLinks.map((link, index) => ({ ...link, id: `link-${index}` }))
  const valueScale = d3.scaleSqrt().domain([1, d3.max(links, (d) => d.value) || 1]).range([0.6, 13])

  drawLinks(zoomLayer, links, nodes, valueScale)
  drawNodes(zoomLayer, nodes)
  drawMatrix(zoomLayer)
  setupZoom(svg, zoomLayer)
}

function setPeriod(period) {
  activePeriod.value = period
  nextTick(draw)
}

function setupZoom(svg, zoomLayer) {
  zoomBehavior = d3
    .zoom()
    .scaleExtent([0.65, 4])
    .translateExtent([
      [-90, -80],
      [W + 90, H + 80],
    ])
    .extent([
      [0, 0],
      [W, H],
    ])
    .filter((event) => {
      if (event.type === 'dblclick') return false
      return !event.button
    })
    .on('zoom', (event) => {
      zoomTransform.value = event.transform
      zoomLayer.attr('transform', event.transform)
    })

  svg.call(zoomBehavior)
  svg.call(zoomBehavior.transform, zoomTransform.value)
}

function zoomBy(factor) {
  if (!svgRef.value || !zoomBehavior) return
  d3.select(svgRef.value)
    .transition()
    .duration(160)
    .call(zoomBehavior.scaleBy, factor)
}

function resetZoom() {
  if (!svgRef.value || !zoomBehavior) return
  d3.select(svgRef.value)
    .transition()
    .duration(180)
    .call(zoomBehavior.transform, d3.zoomIdentity)
}

function buildNodes() {
  const periods = rawNodes.filter((node) => node.type === 'period')
  const identities = rawNodes.filter((node) => node.type === 'identity')
  const roles = rawNodes.filter((node) => node.type === 'role')
  const sums = new Map()

  rawLinks.forEach((link) => {
    sums.set(link.source, (sums.get(link.source) || 0) + link.value)
    sums.set(link.target, Math.max(sums.get(link.target) || 0, link.value))
  })

  return new Map([
    ...layoutRow(periods, PERIOD_Y, 3, W - 3, sums),
    ...layoutRow(identities, IDENTITY_Y, 3, W - 3, sums),
    ...layoutRow(roles, ROLE_Y, 3, W - 3, sums),
  ].map((node) => [node.name, node]))
}

function layoutRow(items, y, left, right, sums) {
  const step = (right - left) / Math.max(1, items.length - 1)
  const maxValue = d3.max(items, (item) => sums.get(item.name) || 1) || 1
  const widthScale = d3.scaleSqrt().domain([1, maxValue]).range([5, Math.min(34, step * 0.86)])

  return items.map((item, index) => ({
    ...item,
    x: left + index * step,
    y,
    width: widthScale(sums.get(item.name) || 1),
    color: colors[item.name] || '#7f8c8d',
  }))
}

function drawLinks(svg, links, nodes, valueScale) {
  const linkGroup = svg.append('g').attr('class', 'vertical-links')

  linkGroup.selectAll('path')
    .data(links.filter((link) => nodes.has(link.source) && nodes.has(link.target)))
    .join('path')
    .attr('d', (link) => linkPath(nodes.get(link.source), nodes.get(link.target)))
    .attr('stroke', (link) => linkColor(link))
    .attr('stroke-width', (link) => valueScale(link.value))
    .attr('stroke-opacity', (link) => isLinkVisible(link) ? 0.46 : 0.055)
    .on('mouseenter', function (event, link) {
      d3.select(this).raise().attr('stroke-opacity', 0.86).attr('stroke-width', Math.max(2.4, valueScale(link.value) + 1.2))
      showTooltip(event, `${link.source} → ${link.target}`, `样本数：${link.value}`)
    })
    .on('mousemove', moveTooltip)
    .on('mouseleave', function (event, link) {
      d3.select(this).attr('stroke-opacity', isLinkVisible(link) ? 0.46 : 0.055).attr('stroke-width', valueScale(link.value))
      hideTooltip()
    })
}

function isLinkVisible(link) {
  if (activePeriod.value === 'all') return true
  return getLinkPeriods(link).includes(activePeriod.value)
}

function getLinkPeriods(link) {
  if (allPeriods.includes(link.source)) return [link.source]

  return allPeriods.filter((period) => {
    const periodLinks = rawLinks.filter((item) => item.source === period && item.target === link.source)
    return periodLinks.length && rawLinks.some((item) => item.source === link.source && item.target === link.target)
  })
}

function linkPath(source, target) {
  const y1 = source.y + NODE_H / 2
  const y2 = target.y - NODE_H / 2
  const midY = (y1 + y2) / 2
  return `M${source.x},${y1} C${source.x},${midY} ${target.x},${midY} ${target.x},${y2}`
}

function linkColor(link) {
  const baseName = allPeriods.includes(link.source) ? link.target : link.source
  return d3.interpolateRgb(colors[baseName] || '#8f8a7c', '#fff')(0.18)
}

function drawNodes(svg, nodes) {
  const data = Array.from(nodes.values())
  const nodeGroup = svg.append('g').attr('class', 'vertical-nodes')
  const item = nodeGroup.selectAll('g').data(data).join('g').attr('transform', (d) => `translate(${d.x},${d.y})`)

  item.append('rect')
    .attr('x', (d) => -d.width / 2)
    .attr('y', -NODE_H / 2)
    .attr('width', (d) => d.width)
    .attr('height', NODE_H)
    .attr('rx', 2)
    .attr('fill', (d) => d.color)
    .attr('fill-opacity', (d) => d.type === 'period' ? 0.86 : d.type === 'identity' ? 0.94 : 0.82)

  item.append('text')
    .attr('class', (d) => `node-label node-label--${d.type}`)
    .attr('y', (d) => labelY(d.type))
    .attr('text-anchor', 'middle')
    .selectAll('tspan')
    .data((d) => splitLabel(d.name, d.type))
    .join('tspan')
    .attr('x', 0)
    .attr('dy', (d, i) => i === 0 ? 0 : '1.08em')
    .text((d) => d)
}

function labelY(type) {
  if (type === 'period') return 17
  if (type === 'identity') return -43
  return 17
}

function splitLabel(label, type) {
  if (['period', 'identity', 'role'].includes(type)) return Array.from(label)
  return [label]
}

function matrixTitleAnchor(id) {
  if (id === 1) return 'start'
  if (id === 7) return 'end'
  return 'middle'
}

function matrixTitleX(x, id) {
  if (id === 1) return x + 2
  if (id === 7) return x - 2
  return x
}

function matrixCategoryAnchor(id) {
  return id === 7 ? 'end' : 'start'
}

function matrixCategoryX(x, id) {
  return id === 7 ? x - 5 : x + 5
}

function drawMatrix(svg) {
  const xScale = d3.scaleLinear().domain([1, 7]).range([4, W - 4])
  const profileLine = d3.line().x((d) => d.x).y((d) => d.y).curve(d3.curveMonotoneX)
  const categoryCoords = new Map()
  const matrix = svg.append('g').attr('class', 'trait-matrix')

  traitsMeta.forEach((trait) => {
    const x = xScale(trait.id)
    matrix.append('line').attr('x1', x).attr('x2', x).attr('y1', MATRIX_TOP).attr('y2', MATRIX_BOTTOM).attr('class', 'matrix-axis')
    matrix
      .append('text')
      .attr('class', 'matrix-title')
      .attr('x', matrixTitleX(x, trait.id))
      .attr('y', MATRIX_TOP - 5)
      .attr('text-anchor', matrixTitleAnchor(trait.id))
      .text(`${trait.id} ${trait.name}`)

    trait.categories.forEach((category, index) => {
      const y = MATRIX_TOP + 16 + index * ((MATRIX_BOTTOM - MATRIX_TOP - 26) / Math.max(1, trait.categories.length - 1))
      categoryCoords.set(`${trait.id}:${category}`, { x, y, category, traitId: trait.id })
      matrix.append('circle').attr('cx', x).attr('cy', y).attr('r', 2.6).attr('class', 'matrix-dot')
      matrix
        .append('text')
        .attr('x', matrixCategoryX(x, trait.id))
        .attr('y', y + 3)
        .attr('text-anchor', matrixCategoryAnchor(trait.id))
        .attr('class', 'matrix-category')
        .text(category)
    })
  })

  const profiles = Object.entries(roleProfiles)
    .map(([role, profile]) => ({
      role,
      points: profile.map((category, index) => categoryCoords.get(`${index + 1}:${category}`)).filter(Boolean),
    }))
    .filter((profile) => profile.points.length > 1)

  matrix.append('g').attr('class', 'matrix-profiles')
    .selectAll('path')
    .data(profiles)
    .join('path')
    .attr('d', (d) => profileLine(d.points))
    .on('mouseenter', function (event, d) {
      d3.select(this).raise().attr('stroke-opacity', 0.78).attr('stroke-width', 1.8)
      showTooltip(event, `${d.role}典型特征`, roleProfiles[d.role].join(' / '))
    })
    .on('mousemove', moveTooltip)
    .on('mouseleave', function () {
      d3.select(this).attr('stroke-opacity', 0.34).attr('stroke-width', 1.15)
      hideTooltip()
    })
}

function showTooltip(event, title, value) {
  tooltip.visible = true
  tooltip.title = title
  tooltip.value = value
  moveTooltip(event)
}

function moveTooltip(event) {
  const rect = wrapRef.value?.getBoundingClientRect()
  if (!rect) return
  tooltip.x = event.clientX - rect.left + 12
  tooltip.y = event.clientY - rect.top + 12
}

function hideTooltip() {
  tooltip.visible = false
}
</script>

<style scoped>
.vertical-pattern-view {
  position: relative;
  display: grid;
  grid-template-rows: 28px minmax(0, 1fr) 66px;
  gap: 5px;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  border-radius: 6px;
  color: #3f332b;
  background: transparent;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  animation: chart-two-enter 260ms ease-out both;
}

.period-tabs {
  display: flex;
  gap: 2px;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  min-height: 0;
  padding: 3px;
  overflow-x: hidden;
  overflow-y: hidden;
  border-radius: 999px;
  border: 1px solid rgba(143, 47, 36, 0.12);
  background: #FBF6E9;
  box-shadow: inset 0 0 0 1px rgba(255, 248, 232, 0.64);
  scrollbar-width: none;
  transform: translateY(3px);
}

.period-tabs::-webkit-scrollbar {
  display: none;
}

.period-tabs button {
  flex: 1 1 0;
  min-width: 0;
  height: 21px;
  padding: 0 2px;
  border: 0;
  border-radius: 999px;
  color: #6b5b4d;
  background: transparent;
  font-size: 10px;
  font-weight: 900;
  line-height: 21px;
  text-align: center;
  overflow: hidden;
  text-overflow: clip;
  white-space: nowrap;
  cursor: pointer;
  transition:
    color 0.16s ease,
    background-color 0.16s ease,
    box-shadow 0.16s ease;
}

.period-tabs button:hover {
  color: #8b2a25;
  background: #FBF6E9;
}

.period-tabs button.active {
  color: #8b2a25;
  background: #FBF6E9;
  box-shadow:
    inset 0 0 0 1px rgba(255, 248, 232, 0.26),
    0 2px 7px rgba(143, 47, 36, 0.18);
}

.vertical-pattern-canvas {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border-radius: 6px;
}

.vertical-pattern-svg {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 0;
  border-radius: 6px;
  background: #FBF6E9;
  cursor: grab;
  touch-action: none;
}

.vertical-pattern-svg:active {
  cursor: grabbing;
}

.zoom-controls {
  position: absolute;
  top: 6px;
  right: 7px;
  z-index: 4;
  display: flex;
  gap: 3px;
  padding: 2px;
  border: 1px solid rgba(143, 47, 36, 0.22);
  border-radius: 999px;
  background: #FBF6E9;
  box-shadow: 0 4px 10px rgba(82, 54, 32, 0.12);
}

.zoom-controls button {
  display: grid;
  place-items: center;
  min-width: 21px;
  height: 21px;
  padding: 0 5px;
  border: 0;
  border-radius: 999px;
  color: #7a241d;
  background: transparent;
  font-size: 12px;
  font-weight: 900;
  line-height: 1;
  cursor: pointer;
}

.zoom-controls button:hover {
  color: #7a241d;
  background: #FBF6E9;
}

.vertical-pattern-svg :deep(text) {
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
}

.vertical-pattern-svg :deep(.vertical-links path) {
  fill: none;
  cursor: pointer;
  stroke-linecap: round;
  mix-blend-mode: normal;
  transition:
    stroke-opacity 0.18s ease,
    stroke-width 0.18s ease;
}

.vertical-pattern-svg :deep(.node-label) {
  fill: #261b16;
  font-size: 10.5px;
  font-weight: 900;
  paint-order: stroke;
  stroke: rgba(252, 243, 224, 0.92);
  stroke-width: 2.4px;
  stroke-linejoin: round;
}

.vertical-pattern-svg :deep(.node-label--identity) {
  fill: #2c2019;
  font-size: 9.5px;
}

.vertical-pattern-svg :deep(.node-label--role) {
  fill: #261b16;
  font-size: 10.2px;
}

.vertical-pattern-svg :deep(.matrix-axis) {
  stroke: rgba(87, 65, 48, 0.42);
  stroke-dasharray: 3 4;
}

.vertical-pattern-svg :deep(.matrix-title) {
  fill: #3d2a21;
  font-size: 9.8px;
  font-weight: 900;
}

.vertical-pattern-svg :deep(.matrix-category) {
  fill: rgba(35, 25, 19, 0.96);
  font-size: 8.7px;
  font-weight: 900;
  paint-order: stroke;
  stroke: rgba(252, 243, 224, 0.78);
  stroke-width: 1.2px;
  stroke-linejoin: round;
}

.vertical-pattern-svg :deep(.matrix-dot) {
  fill: rgba(78, 65, 52, 0.56);
}

.vertical-pattern-svg :deep(.matrix-profiles path) {
  fill: none;
  stroke: rgba(54, 47, 42, 0.76);
  stroke-width: 1.15;
  stroke-opacity: 0.34;
  cursor: pointer;
  transition:
    stroke-opacity 0.16s ease,
    stroke-width 0.16s ease;
}

.pattern-tooltip {
  position: absolute;
  z-index: 5;
  display: grid;
  gap: 3px;
  max-width: 210px;
  padding: 7px 9px;
  pointer-events: none;
  border: 1px solid rgba(143, 47, 36, 0.22);
  border-radius: 6px;
  color: #49342b;
  background: #FBF6E9;
  box-shadow: 0 8px 18px rgba(58, 34, 22, 0.16);
  animation: tooltip-in 120ms ease-out both;
}

.pattern-tooltip strong {
  font-size: 12px;
  line-height: 1.15;
}

.pattern-tooltip span {
  font-size: 10px;
  line-height: 1.35;
}

.context-panel {
  min-height: 0;
  padding: 5px 10px;
  overflow: hidden;
  border-left: 3px solid rgba(139, 42, 37, 0.62);
  border-radius: 0;
  color: #4b4945;
  background: #FBF6E9;
  box-shadow: none;
}

.context-panel strong {
  display: block;
  margin-bottom: 2px;
  overflow: hidden;
  color: #7a241d;
  font-size: 14.5px;
  font-weight: 900;
  line-height: 1.15;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.context-panel p {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  font-size: 12.6px;
  font-weight: 700;
  line-height: 1.2;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

@keyframes chart-two-enter {
  from {
    opacity: 0;
    transform: translateY(6px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes tooltip-in {
  from {
    opacity: 0;
    transform: translateY(3px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
