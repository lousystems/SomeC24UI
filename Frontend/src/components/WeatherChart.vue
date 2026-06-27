<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  CategoryScale,
  Filler
} from 'chart.js'

// Register ChartJS modules
ChartJS.register(
  Title,
  Tooltip,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  CategoryScale,
  Filler
)

const props = defineProps({
  weatherData: {
    type: Array,
    required: true
  },
  year: {
    type: [Number, String],
    default: 1980
  },
  time: {
    type: String,
    default: '12:00'
  }
})

// Prepare chart data format
const chartData = computed(() => {
  // Sort data by date just in case it came in out of order due to parallel fetching
  const sorted = [...props.weatherData].sort((a, b) => new Date(a.date) - new Date(b.date))
  
  const labels = sorted.map(item => {
    // Format date beautifully (e.g., "01. Jan")
    const d = new Date(item.date)
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: 'short' })
  })
  
  const temperatures = sorted.map(item => item.temperature)

  return {
    labels,
    datasets: [
      {
        label: `Temperatur um ${props.time} Uhr (°C)`,
        data: temperatures,
        borderColor: '#002e97', // Check24 Deep Royal Blue
        backgroundColor: (context) => {
          const chart = context.chart
          const { ctx, chartArea } = chart
          if (!chartArea) return null
          
          // Create gradient for filled chart background
          const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
          gradient.addColorStop(0, 'rgba(0, 46, 151, 0.25)')
          gradient.addColorStop(1, 'rgba(0, 46, 151, 0.0)')
          return gradient
        },
        borderWidth: 2,
        pointBackgroundColor: '#ff9900', // Check24 Accent Gold/Yellow
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: '#002e97',
        pointRadius: (context) => {
          // Keep points small unless hovered, or show them on smaller datasets
          return props.weatherData.length < 40 ? 4 : 0
        },
        pointHoverRadius: 6,
        fill: true,
        tension: 0.3 // Smooth curves
      }
    ]
  }
})

const chartOptions = computed(() => {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top',
        labels: {
          color: '#374151', // Dark text
          font: {
            family: 'Inter',
            size: 13,
            weight: '500'
          }
        }
      },
      tooltip: {
        backgroundColor: '#1e293b', // Dark slate tooltip
        titleFont: {
          family: 'Inter',
          size: 14,
          weight: 'bold'
        },
        bodyFont: {
          family: 'Inter',
          size: 13
        },
        padding: 12,
        cornerRadius: 8,
        displayColors: false,
        callbacks: {
          label: (context) => {
            return ` ${context.parsed.y.toFixed(1)} °C (${props.time} Uhr)`
          }
        }
      }
    },
    scales: {
      x: {
        grid: {
          display: false
        },
        ticks: {
          color: '#6b7280', // Slate ticks
          font: {
            family: 'Inter',
            size: 11
          },
          // Limit ticks shown to prevent overlapping
          maxTicksLimit: 12
        }
      },
      y: {
        grid: {
          color: '#e5e7eb' // Light gray grid lines
        },
        ticks: {
          color: '#6b7280',
          font: {
            family: 'Inter',
            size: 11
          },
          callback: (value) => `${value}°C`
        }
      }
    }
  }
})
</script>

<template>
  <div class="relative h-96 w-full">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>
