<template>
  <div class="border border-slate-200 rounded-md overflow-hidden bg-slate-50 mt-2 p-4 text-xs space-y-4">
    <!-- Server Inventory Subpanel -->
    <div>
      <h4 class="font-bold text-slate-700 flex items-center gap-1.5 mb-2 select-none">
        <svg class="h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
        </svg>
        납품 서버 재고 리스트
      </h4>
      <div v-if="servers.length === 0" class="text-slate-400 py-3 text-center border border-dashed border-slate-200 rounded bg-white">
        납품된 서버 장비가 없습니다.
      </div>
      <div v-else class="overflow-x-auto border border-slate-200 rounded bg-white">
        <table class="min-w-full divide-y divide-slate-100">
          <thead class="bg-slate-50">
            <tr>
              <th class="px-4 py-2 text-left font-bold text-slate-500">시리얼 태그 (S/N)</th>
              <th class="px-4 py-2 text-left font-bold text-slate-500">장비 모델</th>
              <th class="px-4 py-2 text-left font-bold text-slate-500">상태</th>
              <th class="px-4 py-2 text-left font-bold text-slate-500">IP (서비스/MGMT)</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="srv in servers" :key="srv.id" class="hover:bg-slate-50">
              <td class="px-4 py-2 font-mono font-semibold text-blue-600 cursor-pointer" @click="goToInventory(srv.serial_tag)">
                {{ srv.serial_tag }}
              </td>
              <td class="px-4 py-2 text-slate-700">{{ srv.model }}</td>
              <td class="px-4 py-2"><AppBadge :status="srv.status" /></td>
              <td class="px-4 py-2 text-slate-500 font-mono">
                {{ srv.service_ip || '-' }} / {{ srv.mgmt_ip || '-' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Part Inventory Subpanel -->
    <div>
      <h4 class="font-bold text-slate-700 flex items-center gap-1.5 mb-2 select-none">
        <svg class="h-4 w-4 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
        </svg>
        프로젝트 할당 부품 목록
      </h4>
      <div v-if="parts.length === 0" class="text-slate-400 py-3 text-center border border-dashed border-slate-200 rounded bg-white">
        할당된 부품 재고가 없습니다.
      </div>
      <div v-else class="overflow-x-auto border border-slate-200 rounded bg-white">
        <table class="min-w-full divide-y divide-slate-100">
          <thead class="bg-slate-50">
            <tr>
              <th class="px-4 py-2 text-left font-bold text-slate-500">부품 모델명</th>
              <th class="px-4 py-2 text-left font-bold text-slate-500">보유 수량</th>
              <th class="px-4 py-2 text-left font-bold text-slate-500">재고 위치</th>
              <th class="px-4 py-2 text-left font-bold text-slate-500">보증 만료일</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="part in parts" :key="part.id" class="hover:bg-slate-50">
              <td class="px-4 py-2 font-semibold text-violet-600 cursor-pointer" @click="goToParts(part.model)">
                {{ part.model }}
              </td>
              <td class="px-4 py-2 text-slate-700 font-bold">{{ part.qty }} 개</td>
              <td class="px-4 py-2 text-slate-500">{{ part.location || '-' }}</td>
              <td class="px-4 py-2 text-slate-500 font-mono">{{ part.warranty_end || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/utils/api'
import AppBadge from '@/components/common/AppBadge.vue'

interface Props {
  projectId: number
}

const props = defineProps<Props>()
const router = useRouter()

const servers = ref<any[]>([])
const parts = ref<any[]>([])

onMounted(() => {
  fetchLinkedItems()
})

async function fetchLinkedItems() {
  try {
    // 1. 서버 재고 필터링 조회
    const srvRes = await api.get(`/inventory?project_id=${props.projectId}&limit=100`)
    servers.value = srvRes.data.data
    
    // 2. 파트 재고 조회 (API 필터에 맞추어 프로젝트 ID로 파트 목록을 가져옵니다)
    const partRes = await api.get(`/parts?limit=100`)
    // 이 프로젝트에 매핑된 파트 필터링
    parts.value = partRes.data.data.filter((p: any) => p.project_id === props.projectId)
  } catch (error) {
    console.error('Linked items fetch failed:', error)
  }
}

function goToInventory(serialTag: string) {
  router.push({ name: 'inventory', query: { search: serialTag } })
}

function goToParts(model: string) {
  router.push({ name: 'parts', query: { search: model } })
}
</script>
