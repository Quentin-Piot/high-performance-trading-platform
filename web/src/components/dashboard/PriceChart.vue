<script setup lang="ts">
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, DataZoomComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { computed } from 'vue'
import { useSimulationStore } from '@/stores/simulation'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, DataZoomComponent, LegendComponent])

const store = useSimulationStore()

const option = computed(() => {
  const data = store.priceSeries.map(pt => [pt.time, pt.price])
  const latest = data[data.length - 1]
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 16, right: 16, top: 24, bottom: 40 },
    xAxis: { type: 'time', boundaryGap: false },
    yAxis: { type: 'value', scale: true },
    dataZoom: [
      { type: 'inside', throttle: 50 },
      { type: 'slider', height: 18 }
    ],
    series: [
      {
        name: store.params.symbol,
        type: 'line',
        showSymbol: false,
        smooth: true,
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.05 },
        data,
        markPoint: latest ? {
          symbol: 'circle',
          symbolSize: 8,
          data: [{ coord: latest, value: latest[1] }],
          itemStyle: { color: '#10b981' },
          label: { formatter: (p: { value?: number | string }) => String(p?.value ?? ''), color: '#10b981' }
        } : undefined,
      }
    ]
  }
})
</script>

<template>
  <VChart :option="option" autoresize class="h-64 w-full" />
</template>