import { reactive } from 'vue'

export const loopFilterState = reactive({
  scope: null,
  flow: null,
})

export function setLoopFilter(scope, flow = null) {
  loopFilterState.scope = scope
  loopFilterState.flow = flow
}

export function clearLoopFilter() {
  loopFilterState.scope = null
  loopFilterState.flow = null
}
