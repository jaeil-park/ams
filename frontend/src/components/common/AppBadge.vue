<template>
  <span :class="['inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold', badgeClasses]">
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type StatusType = 
  | 'IN_STOCK' 
  | 'RESERVED' 
  | 'SCHEDULED' 
  | 'IN_PROGRESS' 
  | 'DELIVERED' 
  | 'WAITING' 
  | 'RMA' 
  | 'COMPLETED' 
  | 'ACTIVE' 
  | 'INACTIVE'
  | string

interface Props {
  status?: StatusType
  label?: string
}

const props = defineProps<Props>()

const badgeClasses = computed(() => {
  switch (props.status) {
    case 'IN_STOCK':
    case 'ACTIVE':
    case 'COMPLETED':
      return 'bg-emerald-100 text-emerald-800'
    case 'RESERVED':
      return 'bg-amber-100 text-amber-800'
    case 'SCHEDULED':
      return 'bg-blue-100 text-blue-800'
    case 'IN_PROGRESS':
      return 'bg-cyan-100 text-cyan-800'
    case 'DELIVERED':
      return 'bg-blue-100 text-blue-800'
    case 'WAITING':
      return 'bg-orange-100 text-orange-800'
    case 'RMA':
      return 'bg-rose-100 text-rose-800'
    case 'INACTIVE':
      return 'bg-slate-100 text-slate-800'
    default:
      return 'bg-slate-100 text-slate-800'
  }
})
</script>
