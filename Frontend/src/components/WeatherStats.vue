<script setup>
import { computed } from 'vue'
import { TrendingDown, TrendingUp, Sun } from '@lucide/vue'

const props = defineProps({
  weatherData: {
    type: Array,
    required: true
  },
  latitude: {
    type: Number,
    required: true
  },
  longitude: {
    type: Number,
    required: true
  }
})

// Calculate temperature statistics
const stats = computed(() => {
  if (!props.weatherData || props.weatherData.length === 0) {
    return { min: null, max: null, avg: null }
  }

  let minItem = props.weatherData[0]
  let maxItem = props.weatherData[0]
  let sum = 0

  props.weatherData.forEach(item => {
    if (item.temperature < minItem.temperature) minItem = item
    if (item.temperature > maxItem.temperature) maxItem = item
    sum += item.temperature
  })

  const avg = sum / props.weatherData.length

  const formatDate = (dateStr) => {
    const d = new Date(dateStr)
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
  }

  return {
    min: minItem.temperature,
    minDate: formatDate(minItem.date),
    max: maxItem.temperature,
    maxDate: formatDate(maxItem.date),
    avg: avg
  }
})
</script>

<template>
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    <!-- Min Temperature -->
    <div class="bg-white rounded-xl shadow-md border border-gray-100 p-5 flex items-center gap-4">
      <div class="p-3 rounded-lg bg-blue-50 text-blue-600">
        <TrendingDown class="w-6 h-6" />
      </div>
      <div>
        <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider block">Tiefsttemperatur</span>
        <span class="text-2xl font-bold text-gray-800 block" v-if="stats.min !== null">
          {{ stats.min.toFixed(1) }} °C
        </span>
        <span class="text-xs text-gray-400 block" v-if="stats.min !== null">
          am {{ stats.minDate }}
        </span>
        <span class="text-gray-400" v-else>-</span>
      </div>
    </div>

    <!-- Max Temperature -->
    <div class="bg-white rounded-xl shadow-md border border-gray-100 p-5 flex items-center gap-4">
      <div class="p-3 rounded-lg bg-red-50 text-red-600">
        <TrendingUp class="w-6 h-6" />
      </div>
      <div>
        <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider block">Höchsttemperatur</span>
        <span class="text-2xl font-bold text-gray-800 block" v-if="stats.max !== null">
          {{ stats.max.toFixed(1) }} °C
        </span>
        <span class="text-xs text-gray-400 block" v-if="stats.max !== null">
          am {{ stats.maxDate }}
        </span>
        <span class="text-gray-400" v-else>-</span>
      </div>
    </div>

    <!-- Avg Temperature -->
    <div class="bg-white rounded-xl shadow-md border border-gray-100 p-5 flex items-center gap-4">
      <div class="p-3 rounded-lg bg-yellow-50 text-yellow-600">
        <Sun class="w-6 h-6" />
      </div>
      <div>
        <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider block">Durchschnitt</span>
        <span class="text-2xl font-bold text-gray-800 block" v-if="stats.avg !== null">
          {{ stats.avg.toFixed(1) }} °C
        </span>
        <span class="text-xs text-gray-400 block" v-if="stats.avg !== null">
          über {{ weatherData.length }} Tage
        </span>
        <span class="text-gray-400" v-else>-</span>
      </div>
    </div>
  </div>
</template>
