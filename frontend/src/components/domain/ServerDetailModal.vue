<template>
  <AppModal :is-open="isOpen" title="서버 상세 자산 정보" size="lg" @close="emit('close')">
    <div class="space-y-6 font-sans text-xs" v-if="server">
      <!-- 1. Top Linked Info Area -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-50 p-4 rounded-lg border border-slate-200">
        <div>
          <span class="block text-4xs font-bold text-slate-400 uppercase tracking-wider">소속 프로젝트</span>
          <span class="block font-semibold text-slate-700 text-xs mt-0.5 truncate" :title="projectName">
            {{ projectName }}
          </span>
        </div>
        <div>
          <span class="block text-4xs font-bold text-slate-400 uppercase tracking-wider">담당자 / 연락처</span>
          <span class="block font-semibold text-slate-700 text-xs mt-0.5">
            {{ server.host_name || '-' }} / {{ server.service_ip || '-' }}
          </span>
        </div>
        <div>
          <span class="block text-4xs font-bold text-slate-400 uppercase tracking-wider">장비 관리상태</span>
          <div class="mt-0.5">
            <AppBadge :status="server.status" />
          </div>
        </div>
      </div>

      <!-- 2. Warranty 수기 등록 -->
      <div
        class="border rounded-lg p-4 flex flex-col gap-3"
        :class="warrantyBorderClass"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div
              class="h-8 w-8 rounded-full flex items-center justify-center"
              :class="warrantyIconBg"
            >
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <h4 class="font-bold text-sm" :class="warrantyTitleClass">보증기간 (Warranty)</h4>
              <p class="text-slate-500 font-medium text-xs mt-0.5">{{ warrantyStatusText }}</p>
            </div>
          </div>
          <!-- 만료 임박 / 만료 배지 -->
          <span
            v-if="warrantyBadge"
            class="px-2 py-0.5 rounded-full text-3xs font-bold uppercase tracking-wider"
            :class="warrantyBadge.cls"
          >
            {{ warrantyBadge.label }}
          </span>
        </div>

        <!-- 수기 입력 폼 -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
          <div>
            <label class="block text-3xs font-bold text-slate-400 uppercase tracking-wider mb-1">시작일</label>
            <input
              v-model="warrantyForm.start_date"
              type="date"
              class="w-full border border-slate-300 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
          <div>
            <label class="block text-3xs font-bold text-slate-400 uppercase tracking-wider mb-1">종료일</label>
            <input
              v-model="warrantyForm.end_date"
              type="date"
              class="w-full border border-slate-300 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
          <div class="flex items-end gap-2">
            <AppButton
              variant="primary"
              class="text-3xs px-4 py-1.5 shrink-0 w-full"
              :loading="warrantyLoading"
              @click="saveWarranty"
            >
              저장
            </AppButton>
            <AppButton
              v-if="warrantyInfo"
              variant="ghost"
              class="text-3xs px-2 py-1.5 shrink-0 text-red-400 hover:text-red-600"
              :loading="warrantyLoading"
              @click="deleteWarranty"
              title="워런티 삭제"
            >
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </AppButton>
          </div>
        </div>
      </div>


      <!-- 3. Specifications details Grid -->
      <div>
        <h4 class="font-bold text-slate-800 mb-2 pb-1 border-b border-slate-100">하드웨어 상세 사양</h4>
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-3 text-slate-600">
          <div>
            <span class="text-slate-400 font-semibold">장비 모델명:</span>
            <span class="ml-1 text-slate-800 font-bold">{{ server.model }}</span>
          </div>
          <div>
            <span class="text-slate-400 font-semibold">시리얼 태그(S/N):</span>
            <span class="ml-1 text-slate-800 font-mono font-bold">{{ server.serial_tag }}</span>
          </div>
          <div>
            <span class="text-slate-400 font-semibold">제조사(Vendor):</span>
            <span class="ml-1 text-slate-800 font-medium">{{ server.vendor || '-' }}</span>
          </div>
          <div>
            <span class="text-slate-400 font-semibold">CPU 모델:</span>
            <span class="ml-1 text-slate-800 font-medium">{{ server.cpu_model || '-' }}</span>
          </div>
          <div>
            <span class="text-slate-400 font-semibold">CPU 코어수:</span>
            <span class="ml-1 text-slate-800 font-medium">{{ server.cpu_core ? server.cpu_core + ' Cores' : '-' }}</span>
          </div>
          <div>
            <span class="text-slate-400 font-semibold">메모리 사양:</span>
            <span class="ml-1 text-slate-800 font-medium">
              {{ server.mem_capacity ? server.mem_capacity + 'GB' : '' }} 
              {{ server.mem_gen }} 
              {{ server.mem_qty ? `(${server.mem_qty}개)` : '' }}
            </span>
          </div>
          <div class="sm:col-span-2">
            <span class="text-slate-400 font-semibold">DISK 1:</span>
            <span class="ml-1 text-slate-800 font-medium">
              {{ server.disk1_spec }} {{ server.disk1_qty ? `x ${server.disk1_qty}개` : '' }} 
              {{ server.disk1_raid ? `(RAID ${server.disk1_raid})` : '' }}
            </span>
          </div>
          <div class="sm:col-span-2" v-if="server.disk2_spec">
            <span class="text-slate-400 font-semibold">DISK 2:</span>
            <span class="ml-1 text-slate-800 font-medium">
              {{ server.disk2_spec }} {{ server.disk2_qty ? `x ${server.disk2_qty}개` : '' }} 
              {{ server.disk2_raid ? `(RAID ${server.disk2_raid})` : '' }}
            </span>
          </div>
          <div>
            <span class="text-slate-400 font-semibold">NIC 1:</span>
            <span class="ml-1 text-slate-800 font-medium">{{ server.nic1 || '-' }}</span>
          </div>
          <div>
            <span class="text-slate-400 font-semibold">NIC 2:</span>
            <span class="ml-1 text-slate-800 font-medium">{{ server.nic2 || '-' }}</span>
          </div>
        </div>
      </div>

      <!-- 4. Firmware Details -->
      <div>
        <h4 class="font-bold text-slate-800 mb-2 pb-1 border-b border-slate-100">펌웨어 버전 정보</h4>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-slate-600 font-mono">
          <div>
            <span class="text-slate-400 font-semibold font-sans">BIOS Ver:</span>
            <span class="ml-1 text-slate-800 font-semibold">{{ server.bios_ver || '-' }}</span>
          </div>
          <div>
            <span class="text-slate-400 font-semibold font-sans">iDRAC Ver:</span>
            <span class="ml-1 text-slate-800 font-semibold">{{ server.idrac_ver || '-' }}</span>
          </div>
          <div>
            <span class="text-slate-400 font-semibold font-sans">RAID Controller:</span>
            <span class="ml-1 text-slate-800 font-semibold">{{ server.raid_ver || '-' }}</span>
          </div>
        </div>
      </div>

      <!-- 5. History / Logs Section -->
      <div>
        <h4 class="font-bold text-slate-800 mb-2 pb-1 border-b border-slate-100">장비 실측 히스토리 기록</h4>
        <div v-if="server.history && Object.keys(server.history).length > 0" class="bg-slate-50 p-3 rounded border border-slate-200 font-mono text-slate-600 max-h-[120px] overflow-y-auto">
          <pre class="whitespace-pre-wrap">{{ JSON.stringify(server.history, null, 2) }}</pre>
        </div>
        <div v-else class="text-slate-400 font-medium text-center py-4 bg-slate-50 rounded border border-dashed border-slate-200">
          기록된 히스토리가 없습니다.
        </div>
      </div>
    </div>
  </AppModal>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import api from '@/utils/api'
import { useUiStore } from '@/stores/ui'
import AppBadge from '@/components/common/AppBadge.vue'
import AppButton from '@/components/common/AppButton.vue'
import AppModal from '@/components/common/AppModal.vue'

interface Props {
  isOpen: boolean
  serverId: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'updated'): void
}>()

const uiStore = useUiStore()

const server = ref<any>(null)
const projectName = ref('소속 없음')
const warrantyLoading = ref(false)
const warrantyInfo = ref<any>(null)

const warrantyForm = ref({ start_date: '', end_date: '' })

onMounted(() => {
  fetchServerDetail()
})

async function fetchServerDetail() {
  try {
    const res = await api.get(`/inventory/${props.serverId}`)
    server.value = res.data.data

    if (server.value.project_id) {
      fetchProjectName(server.value.project_id)
    }
    await fetchWarrantyRecord()
  } catch (error) {
    console.error('Server detail fetch failed:', error)
  }
}

async function fetchProjectName(projId: number) {
  try {
    const res = await api.get(`/projects/${projId}`)
    projectName.value = res.data.data.name
  } catch (error) {
    console.error(error)
  }
}

async function fetchWarrantyRecord() {
  try {
    const res = await api.get(`/warranty/server/${props.serverId}`)
    warrantyInfo.value = res.data.data
    // 폼에 기존 값 채우기
    warrantyForm.value.start_date = warrantyInfo.value.start_date ?? ''
    warrantyForm.value.end_date = warrantyInfo.value.end_date ?? ''
  } catch {
    warrantyInfo.value = null
    warrantyForm.value = { start_date: '', end_date: '' }
  }
}

// ─── Warranty 저장 ────────────────────────────────────────────────────────────
async function saveWarranty() {
  if (!warrantyForm.value.start_date || !warrantyForm.value.end_date) {
    uiStore.addToast('시작일과 종료일을 모두 입력해주세요.', 'warning')
    return
  }
  warrantyLoading.value = true
  try {
    await api.put(`/warranty/server/${props.serverId}`, {
      start_date: warrantyForm.value.start_date,
      end_date: warrantyForm.value.end_date,
      source: 'MANUAL',
    })
    uiStore.addToast('보증기간이 저장되었습니다.', 'success')
    await fetchWarrantyRecord()
    emit('updated')
  } catch (err: any) {
    uiStore.addToast(err?.response?.data?.detail || '저장 실패', 'error')
  } finally {
    warrantyLoading.value = false
  }
}

// ─── Warranty 삭제 ────────────────────────────────────────────────────────────
async function deleteWarranty() {
  warrantyLoading.value = true
  try {
    await api.delete(`/warranty/server/${props.serverId}`)
    uiStore.addToast('보증기간 정보가 삭제되었습니다.', 'success')
    warrantyInfo.value = null
    warrantyForm.value = { start_date: '', end_date: '' }
    emit('updated')
  } catch {
    uiStore.addToast('삭제 실패', 'error')
  } finally {
    warrantyLoading.value = false
  }
}

// ─── Warranty 상태 computed ────────────────────────────────────────────────────

/** 오늘부터 종료일까지 남은 일수 (없으면 null) */
const daysUntilExpiry = computed<number | null>(() => {
  if (!warrantyInfo.value?.end_date) return null
  const end = new Date(warrantyInfo.value.end_date)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.floor((end.getTime() - today.getTime()) / 86_400_000)
})

const warrantyStatusText = computed(() => {
  if (!warrantyInfo.value) return '보증 정보 없음 — 아래에서 직접 입력하세요'
  return `${warrantyInfo.value.start_date} ~ ${warrantyInfo.value.end_date} (${warrantyInfo.value.source})`
})

/** 배경 border 색상 */
const warrantyBorderClass = computed(() => {
  const d = daysUntilExpiry.value
  if (d === null) return 'border-slate-200 bg-slate-50'
  if (d < 0) return 'border-red-300 bg-red-50'
  if (d <= 30) return 'border-amber-300 bg-amber-50'
  return 'border-emerald-200 bg-emerald-50'
})

const warrantyIconBg = computed(() => {
  const d = daysUntilExpiry.value
  if (d === null) return 'bg-slate-100 text-slate-500'
  if (d < 0) return 'bg-red-100 text-red-600'
  if (d <= 30) return 'bg-amber-100 text-amber-600'
  return 'bg-emerald-100 text-emerald-600'
})

const warrantyTitleClass = computed(() => {
  const d = daysUntilExpiry.value
  if (d === null) return 'text-slate-700'
  if (d < 0) return 'text-red-700'
  if (d <= 30) return 'text-amber-700'
  return 'text-emerald-700'
})

/** 배지 (만료/임박) */
const warrantyBadge = computed<{ label: string; cls: string } | null>(() => {
  const d = daysUntilExpiry.value
  if (d === null) return null
  if (d < 0) return { label: '만료됨', cls: 'bg-red-100 text-red-700' }
  if (d <= 30) return { label: `D-${d} 만료임박`, cls: 'bg-amber-100 text-amber-700' }
  return null
})
</script>

