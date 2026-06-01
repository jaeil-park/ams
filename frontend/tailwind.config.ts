import type { Config } from 'tailwindcss'

export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        sidebar: '#0F172A',
        accent: '#2563EB',
        // Status colors
        'status-stock': '#10B981',     // emerald — 재고
        'status-reserved': '#F59E0B',  // amber — 예약
        'status-delivered': '#3B82F6', // blue — 납품완료
        'status-rma': '#F43F5E',       // rose — RMA
        'status-progress': '#06B6D4',  // cyan — 진행중
        'status-waiting': '#F97316',   // orange — 대기
        'status-part': '#8B5CF6',      // violet — 파트
      },
      fontFamily: {
        sans: ['Inter', 'Pretendard', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
} satisfies Config
