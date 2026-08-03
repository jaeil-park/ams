<template>
  <span :class="['inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold', badgeClasses]">
    <span :class="['h-1.5 w-1.5 rounded-full shrink-0', dotClasses]"></span>
    <slot>{{ label || statusLabel }}</slot>
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
  | 'PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | string

interface Props {
  status?: StatusType
  label?: string
}

const props = defineProps<Props>()

const STATUS_LABELS: Record<string, string> = {
  IN_STOCK: '재고',
  RESERVED: '예약',
  SCHEDULED: '납품예정',
  IN_PROGRESS: '진행중',
  DELIVERED: '납품완료',
  WAITING: '대기',
  RMA: 'RMA',
  COMPLETED: '완료',
  ACTIVE: '활성',
  INACTIVE: '비활성',
  PENDING: '대기중',
  APPROVED: '승인됨',
  REJECTED: '반려됨',
}

const statusLabel = computed(() => STATUS_LABELS[props.status ?? ''] ?? props.status ?? '-')

const badgeClasses = computed(() => {
  switch (props.status) {
    case 'IN_STOCK':
    case 'ACTIVE':
    case 'COMPLETED':
    case 'APPROVED':
      return 'bg-emerald-100 text-emerald-800'
    case 'RESERVED':
    case 'PENDING':
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
    case 'REJECTED':
      return 'bg-rose-100 text-rose-800'
    case 'INACTIVE':
      return 'bg-slate-100 text-slate-800'
    default:
      return 'bg-slate-100 text-slate-800'
  }
})

const dotClasses = computed(() => {
  switch (props.status) {
    case 'IN_STOCK':
    case 'ACTIVE':
    case 'COMPLETED':
    case 'APPROVED':
      return 'bg-emerald-500'
    case 'RESERVED':
    case 'PENDING':
      return 'bg-amber-500'
    case 'SCHEDULED':
      return 'bg-blue-500'
    case 'IN_PROGRESS':
      return 'bg-cyan-500'
    case 'DELIVERED':
      return 'bg-blue-500'
    case 'WAITING':
      return 'bg-orange-500'
    case 'RMA':
    case 'REJECTED':
      return 'bg-rose-500'
    case 'INACTIVE':
      return 'bg-slate-400'
    default:
      return 'bg-slate-400'
  }
})
</script>
