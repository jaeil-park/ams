<template>
  <div class="flex items-center gap-1 border-b border-slate-200 select-none overflow-x-auto">
    <button
      v-for="tab in tabs"
      :key="tab.value"
      type="button"
      :class="[
        'relative flex items-center gap-2 px-4 py-2.5 text-xs font-semibold whitespace-nowrap transition-colors border-b-2 -mb-px',
        modelValue === tab.value
          ? 'border-blue-600 text-blue-600'
          : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
      ]"
      @click="emit('update:modelValue', tab.value)"
    >
      <span
        v-if="tab.dotClass"
        class="h-1.5 w-1.5 rounded-full shrink-0"
        :class="tab.dotClass"
      ></span>
      <span>{{ tab.label }}</span>
      <span
        v-if="tab.count !== undefined"
        :class="[
          'px-1.5 py-0.5 rounded-full text-3xs font-bold leading-none tabular-nums',
          modelValue === tab.value ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500'
        ]"
      >
        {{ tab.count }}
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
export interface TabDefinition {
  /** 탭 식별자 — 상위 화면이 필터 값으로 사용 */
  value: string
  label: string
  /** 우측 건수 배지 (미지정 시 배지 숨김) */
  count?: number
  /** 라벨 앞 상태 색상 점 (tailwind 배경 클래스) */
  dotClass?: string
}

defineProps<{
  modelValue: string
  tabs: TabDefinition[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()
</script>
