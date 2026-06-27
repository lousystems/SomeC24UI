<script setup>
import { computed } from 'vue'
import { Database, HardDrive, ThermometerSun, ThermometerSnowflake, History, Calendar, MapPin, Server } from '@lucide/vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
  LogarithmicScale
} from 'chart.js'

// Register ChartJS modules for Bar chart (including LogarithmicScale)
ChartJS.register(
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
  LogarithmicScale
)

const props = defineProps({
  stats: {
    type: Object,
    default: null
  }
})

const formatDate = (timestampStr) => {
  if (!timestampStr) return '-'
  const d = new Date(timestampStr)
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

const formatTime = (timestampStr) => {
  if (!timestampStr) return '-'
  const d = new Date(timestampStr)
  return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }) + ' Uhr'
}

// Compute Bar Chart Data for Yearly Distribution
const yearlyChartData = computed(() => {
  const dist = props.stats?.yearly_distribution || {}
  const years = Object.keys(dist).sort()
  const counts = years.map(yr => dist[yr])

  return {
    labels: years,
    datasets: [
      {
        label: 'Datensätze',
        data: counts,
        backgroundColor: '#002e97', // Check24 Deep Blue
        hoverBackgroundColor: '#ff9900', // Check24 Gold Accent on Hover
        borderRadius: 6,
        maxBarThickness: 40
      }
    ]
  }
})

// Bar Chart Options with Logarithmic Y-Axis
const yearlyChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false // Hide legend as there's only one dataset
    },
    tooltip: {
      backgroundColor: '#1e293b',
      titleFont: {
        family: 'Inter',
        size: 12,
        weight: 'bold'
      },
      bodyFont: {
        family: 'Inter',
        size: 11
      },
      padding: 10,
      cornerRadius: 8,
      callbacks: {
        label: (context) => ` ${context.parsed.y} Datensätze`
      }
    }
  },
  scales: {
    x: {
      grid: {
        display: false
      },
      ticks: {
        color: '#6b7280',
        font: {
          family: 'Inter',
          size: 10,
          weight: '600'
        }
      }
    },
    y: {
      type: 'logarithmic',
      grid: {
        color: '#f3f4f6'
      },
      ticks: {
        color: '#6b7280',
        font: {
          family: 'Inter',
          size: 10
        },
        // Custom callback to prevent overlapping tick numbers on logarithmic scale
        callback: function(value) {
          const log = Math.log10(value);
          return Math.floor(log) === log ? value : null;
        }
      }
    }
  }
}

// Robust fallback for unique coordinates count (handles: count key, number, or array length)
const uniqueCoordsCount = computed(() => {
  if (!props.stats) return 0
  
  // 1. If unique_locations_count is a number, return it
  if (typeof props.stats.unique_locations_count === 'number') {
    return props.stats.unique_locations_count
  }
  
  // 2. If unique_locations is directly a number (common count value), return it
  if (typeof props.stats.unique_locations === 'number') {
    return props.stats.unique_locations
  }
  
  // 3. If unique_locations is an array, return its length
  if (Array.isArray(props.stats.unique_locations)) {
    return props.stats.unique_locations.length
  }
  
  return 0
})
</script>

<template>
  <div v-if="stats" class="bg-white rounded-xl shadow-md border border-gray-100 p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center gap-2 border-b border-gray-155 pb-4">
      <Database class="w-5 h-5 text-[#002e97]" />
      <div>
        <h3 class="text-base font-bold text-gray-800">System- &amp; Datenbankstatistiken</h3>
        <p class="text-xs text-gray-500">Live-Metriken aus der PostgreSQL-Datenbank</p>
      </div>
    </div>

    <!-- Stats Content Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Box 1: Storage & Records & Locations -->
      <div class="space-y-4">
        <h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider">Datenbank-Speicher</h4>
        
        <div class="grid grid-cols-2 gap-3">
          <!-- Total records -->
          <div class="bg-gray-50 rounded-lg p-3 border border-gray-150/50">
            <span class="text-[10px] font-semibold text-gray-500 uppercase block">Einträge gesamt</span>
            <span class="text-lg font-black text-gray-850">{{ stats.total_records }}</span>
          </div>
          <!-- Unique locations count -->
          <div class="bg-gray-50 rounded-lg p-3 border border-gray-150/50">
            <span class="text-[10px] font-semibold text-gray-500 uppercase block">Einzigartige Koordinaten</span>
            <span class="text-lg font-black text-gray-850">{{ uniqueCoordsCount }}</span>
          </div>
        </div>

        <!-- Storage size details -->
        <div class="bg-gray-50 rounded-lg p-4 border border-gray-150/50 space-y-2.5">
          <div class="flex items-center gap-2 mb-1">
            <HardDrive class="w-4 h-4 text-[#002e97]" />
            <span class="text-xs font-bold text-gray-700">Tabellengröße (PostgreSQL)</span>
          </div>
          
          <div class="flex justify-between text-xs border-b border-gray-150/30 pb-1.5">
            <span class="text-gray-500">Daten:</span>
            <span class="font-semibold text-gray-800">{{ stats.table_storage?.data_size || '-' }}</span>
          </div>
          <div class="flex justify-between text-xs border-b border-gray-150/30 pb-1.5">
            <span class="text-gray-500">Indizes:</span>
            <span class="font-semibold text-gray-800">{{ stats.table_storage?.index_size || '-' }}</span>
          </div>
          <div class="flex justify-between text-xs pt-0.5">
            <span class="font-bold text-gray-600">Gesamtspeicher:</span>
            <span class="font-extrabold text-[#002e97]">{{ stats.table_storage?.total_size || '-' }}</span>
          </div>
        </div>
      </div>

      <!-- Box 2: All-time records -->
      <div class="space-y-4">
        <h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider">Allzeit-Rekorde in DB</h4>
        
        <div class="space-y-3">
          <!-- Hottest Record -->
          <div v-if="stats.hottest_record" class="bg-red-50/30 border border-red-100 rounded-lg p-3 flex items-start gap-3">
            <div class="p-2 bg-red-100/50 rounded-md text-red-600 shrink-0">
              <ThermometerSun class="w-4.5 h-4.5" />
            </div>
            <div class="text-xs">
              <span class="font-bold text-red-800 block">Höchste Temperatur</span>
              <span class="text-lg font-black text-red-700">{{ stats.hottest_record.temperature.toFixed(1) }} °C</span>
              <span class="text-[10px] text-gray-555 block mt-0.5 flex items-center gap-1">
                <Calendar class="w-3 h-3 text-gray-400" />
                am {{ formatDate(stats.hottest_record.timestamp) }} ({{ formatTime(stats.hottest_record.timestamp) }})
              </span>
              <span class="text-[10px] text-gray-555 block mt-0.5 flex items-center gap-1">
                <MapPin class="w-3 h-3 text-gray-400" />
                Lat: {{ parseFloat(stats.hottest_record.latitude).toFixed(3) }}°, Lon: {{ parseFloat(stats.hottest_record.longitude).toFixed(3) }}°
              </span>
            </div>
          </div>

          <!-- Coldest Record -->
          <div v-if="stats.coldest_record" class="bg-blue-50/30 border border-blue-100 rounded-lg p-3 flex items-start gap-3">
            <div class="p-2 bg-blue-100/50 rounded-md text-blue-600 shrink-0">
              <ThermometerSnowflake class="w-4.5 h-4.5" />
            </div>
            <div class="text-xs">
              <span class="font-bold text-blue-800 block">Tiefste Temperatur</span>
              <span class="text-lg font-black text-blue-700">{{ stats.coldest_record.temperature.toFixed(1) }} °C</span>
              <span class="text-[10px] text-gray-555 block mt-0.5 flex items-center gap-1">
                <Calendar class="w-3 h-3 text-gray-400" />
                am {{ formatDate(stats.coldest_record.timestamp) }} ({{ formatTime(stats.coldest_record.timestamp) }})
              </span>
              <span class="text-[10px] text-gray-555 block mt-0.5 flex items-center gap-1">
                <MapPin class="w-3 h-3 text-gray-400" />
                Lat: {{ parseFloat(stats.coldest_record.latitude).toFixed(3) }}°, Lon: {{ parseFloat(stats.coldest_record.longitude).toFixed(3) }}°
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Box 3: Yearly distribution chart (Logarithmic Scale) -->
      <div class="space-y-4 flex flex-col">
        <h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1">
          <span>Verteilung nach Jahren</span>
          <span class="text-[9px] px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded font-semibold tracking-wide uppercase">logarithmisch</span>
        </h4>
        
        <div class="flex-grow min-h-[160px] relative mt-2">
          <Bar 
            v-if="stats.yearly_distribution && Object.keys(stats.yearly_distribution).length > 0"
            :data="yearlyChartData" 
            :options="yearlyChartOptions" 
          />
          <div v-else class="absolute inset-0 flex items-center justify-center text-xs text-gray-450">
            Keine Verteilungsdaten vorhanden.
          </div>
        </div>
      </div>

    </div>
  </div>
</template>
