<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import axios from 'axios'
import WeatherFilters from './WeatherFilters.vue'
import WeatherChart from './WeatherChart.vue'
import WeatherStats from './WeatherStats.vue'
import DatabaseStats from './DatabaseStats.vue'
import { CalendarDays, AlertTriangle, CheckCircle, ArrowUpDown, ChevronLeft, ChevronRight, FileSpreadsheet } from '@lucide/vue'

const latitude = ref(48.1351) // Munich default
const longitude = ref(11.582) // Munich default
const year = ref(1980)
const time = ref('12:00')

const weatherData = ref([])
const isLoading = ref(false)
const progress = ref(0)
const totalDays = ref(365)
const errors = ref([])
const cacheStats = ref({ hits: 0, misses: 0 })

// Cities state
const cities = ref([])
const isLoadingCities = ref(false)

// DB Stats state
const dbStats = ref(null)

// Fetch DB stats from backend
const loadDbStats = async () => {
  try {
    const response = await axios.get('/api/weather/stats/')
    dbStats.value = response.data
  } catch (err) {
    console.error('Fehler beim Laden der DB-Statistiken:', err)
  }
}

// Search and pagination for the table
const searchQuery = ref('')
const sortKey = ref('date')
const sortOrder = ref('asc')
const currentPage = ref(1)
const itemsPerPage = ref(10)

let abortController = null

// Fetch cities from backend
const loadCities = async () => {
  isLoadingCities.value = true
  try {
    const response = await axios.get('/api/cities/')
    cities.value = response.data
    
    // Seed default cities if list is empty
    if (cities.value.length === 0) {
      await seedDefaultCities()
    }
  } catch (err) {
    console.error('Fehler beim Laden der Städte:', err)
    errors.value.push(`Städte konnten nicht geladen werden: ${err.message}`)
  } finally {
    isLoadingCities.value = false
  }
}

// Seed helper for initial setup
const seedDefaultCities = async () => {
  const defaultCities = [
    { name: 'München', latitude: 48.1351, longitude: 11.5820 },
    { name: 'Berlin', latitude: 52.5200, longitude: 13.4050 },
    { name: 'Hamburg', latitude: 53.5511, longitude: 9.9937 },
    { name: 'Köln', latitude: 50.9375, longitude: 6.9603 },
    { name: 'Frankfurt am Main', latitude: 50.1109, longitude: 8.6821 }
  ]
  
  for (const city of defaultCities) {
    try {
      await axios.post('/api/cities/', city)
    } catch (err) {
      console.error(`Fehler beim Seeden der Stadt ${city.name}:`, err)
    }
  }
  
  // Reload cities after seeding
  const response = await axios.get('/api/cities/')
  cities.value = response.data
}

// Add a city
const handleAddCity = async (cityData) => {
  try {
    const response = await axios.post('/api/cities/', cityData)
    // Add to list and sort
    cities.value.push(response.data)
    cities.value.sort((a, b) => a.name.localeCompare(b.name))
    loadDbStats() // update stats
  } catch (err) {
    console.error('Fehler beim Hinzufügen der Stadt:', err)
    const serverErr = err.response?.data
    let msg = err.message
    if (serverErr) {
      msg = Object.entries(serverErr).map(([key, val]) => `${key}: ${val}`).join(', ')
    }
    alert(`Fehler beim Hinzufügen der Stadt: ${msg}`)
  }
}

// Delete a city
const handleDeleteCity = async (id) => {
  try {
    await axios.delete(`/api/cities/${id}/`)
    cities.value = cities.value.filter(c => c.id !== id)
    loadDbStats() // update stats
  } catch (err) {
    console.error('Fehler beim Löschen der Stadt:', err)
    alert(`Fehler beim Löschen der Stadt: ${err.message}`)
  }
}

const handleFilterSubmit = (newFilters) => {
  latitude.value = newFilters.latitude
  longitude.value = newFilters.longitude
  year.value = newFilters.year
  time.value = newFilters.time
  loadWeatherData()
}

// Load weather data utilizing the new range endpoints in backend
const loadWeatherData = async () => {
  // Cancel any ongoing fetches
  if (abortController) {
    abortController.abort()
  }
  
  abortController = new AbortController()
  const signal = abortController.signal

  isLoading.value = true
  progress.value = 0
  weatherData.value = []
  errors.value = []
  cacheStats.value = { hits: 0, misses: 0 }
  currentPage.value = 1

  const today = new Date()
  const currentYear = today.getFullYear()

  let start_date = `${year.value}-01-01`
  let end_date = `${year.value}-12-31`
  
  // Limit query to today's date if the user requests the current year,
  // preventing "Date cannot be in the future" validation errors in the backend.
  if (year.value === currentYear) {
    const y = today.getFullYear()
    const m = String(today.getMonth() + 1).padStart(2, '0')
    const d = String(today.getDate()).padStart(2, '0')
    end_date = `${y}-${m}-${d}`
  }
  
  try {
    // Single request for the range
    const response = await axios.get('/api/weather/', {
      params: {
        latitude: latitude.value,
        longitude: longitude.value,
        start_date: start_date,
        end_date: end_date,
        time: time.value
      },
      signal
    })

    const results = response.data.results
    if (results && results.length > 0) {
      // Map results
      const loadedResults = results.map(item => {
        // Extract date YYYY-MM-DD from timestamp e.g. "1980-01-01T12:00:00Z"
        const dateStr = item.timestamp.split('T')[0]
        return {
          date: dateStr,
          temperature: parseFloat(item.temperature)
        }
      })

      // Read cache header
      const cacheHeader = response.headers['x-cache']
      if (cacheHeader === 'HIT') {
        cacheStats.value.hits = 1
        cacheStats.value.misses = 0
      } else {
        cacheStats.value.hits = 0
        cacheStats.value.misses = 1
      }

      weatherData.value = loadedResults
      progress.value = loadedResults.length
      totalDays.value = loadedResults.length
    } else {
      errors.value.push("Keine Wetterdaten für diesen Zeitraum gefunden.")
    }
  } catch (err) {
    if (axios.isCancel(err)) {
      console.log('Abfrage abgebrochen.')
      return
    }
    
    // Extract exact validation messages from backend if available
    const serverErr = err.response?.data
    let errorMsg = err.message
    if (serverErr) {
      if (typeof serverErr === 'object') {
        errorMsg = Object.entries(serverErr)
          .map(([key, val]) => `${key}: ${val}`)
          .join(' | ')
      } else if (typeof serverErr === 'string') {
        errorMsg = serverErr
      }
    }
    errors.value.push(`Backend-Fehler: ${errorMsg}`)
  } finally {
    if (!signal.aborted) {
      isLoading.value = false
      loadDbStats() // update DB stats
    }
  }
}

// Sorting logic for Table
const toggleSort = (key) => {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortOrder.value = 'asc'
  }
}

// Computed property for filtered and sorted table data
const filteredAndSortedData = computed(() => {
  let result = [...weatherData.value]

  // Apply search query filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(item => {
      const dObj = new Date(item.date)
      const formattedDate = dObj.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
      return formattedDate.includes(query) || item.date.includes(query) || item.temperature.toString().includes(query)
    })
  }

  // Sort
  result.sort((a, b) => {
    let aVal = a[sortKey.value]
    let bVal = b[sortKey.value]

    if (sortKey.value === 'date') {
      aVal = new Date(aVal)
      bVal = new Date(bVal)
    }

    if (aVal < bVal) return sortOrder.value === 'asc' ? -1 : 1
    if (aVal > bVal) return sortOrder.value === 'asc' ? 1 : -1
    return 0
  })

  return result
})

// Pagination
const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  return filteredAndSortedData.value.slice(start, start + itemsPerPage.value)
})

const totalPages = computed(() => {
  return Math.ceil(filteredAndSortedData.value.length / itemsPerPage.value) || 1
})

const changePage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
  }
}

onMounted(() => {
  loadCities().then(() => {
    loadWeatherData()
  })
  loadDbStats()
})

onUnmounted(() => {
  if (abortController) {
    abortController.abort()
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Top Filter Section -->
    <WeatherFilters
      :initial-latitude="latitude"
      :initial-longitude="longitude"
      :initial-year="year"
      :initial-time="time"
      :is-loading="isLoading"
      :cities="cities"
      @submit-filters="handleFilterSubmit"
      @add-city="handleAddCity"
      @delete-city="handleDeleteCity"
    />

    <!-- Global Loading State -->
    <div v-if="isLoading" class="bg-white rounded-xl shadow-md border border-gray-100 p-8 text-center flex flex-col items-center justify-center min-h-[250px]">
      <svg class="animate-spin h-10 w-10 text-[#002e97] mb-4" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <span class="text-sm font-semibold text-gray-600">Lade Jahresdaten aus dem Backend...</span>
      <p class="text-xs text-gray-400 mt-1">
        Frage Zeitraum vom 01.01.{{ year }} bis 31.12.{{ year }} ab.
      </p>
    </div>

    <!-- Error Alert panel -->
    <div v-if="errors.length > 0" class="bg-red-50 border-l-4 border-red-500 rounded-lg p-4">
      <div class="flex items-start gap-3">
        <AlertTriangle class="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
        <div class="flex-1">
          <h3 class="text-sm font-semibold text-red-800">Ein Problem ist aufgetreten:</h3>
          <div class="text-xs text-red-700 mt-1 space-y-1">
            <p v-for="(err, idx) in errors" :key="idx">• {{ err }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Data Section -->
    <div v-if="weatherData.length > 0" class="space-y-6">
      <!-- Stats Row -->
      <WeatherStats
        :weather-data="weatherData"
        :latitude="latitude"
        :longitude="longitude"
      />

      <!-- Line Chart Container -->
      <div class="bg-white rounded-xl shadow-md border border-gray-100 p-6">
        <div class="flex justify-between items-center mb-6">
          <div>
            <h2 class="text-lg font-bold text-gray-800 flex items-center gap-2">
              <CalendarDays class="w-5 h-5 text-[#002e97]" />
              Temperaturentwicklung im Jahr {{ year }} um {{ time }} Uhr
            </h2>
            <p class="text-xs text-gray-500 mt-0.5">
              Standort: {{ latitude.toFixed(4) }}° Lat, {{ longitude.toFixed(4) }}° Lon (Temperaturen um {{ time }} Uhr)
            </p>
          </div>
          <span 
            v-if="!isLoading" 
            class="px-2.5 py-1 bg-green-50 text-green-700 text-xs font-bold rounded-full border border-green-200 flex items-center gap-1"
          >
            <CheckCircle class="w-3.5 h-3.5" />
            Vollständig geladen
          </span>
        </div>
        
        <WeatherChart :weather-data="weatherData" :year="year" :time="time" />
      </div>

      <!-- Detailed Data Table Section -->
      <div class="bg-white rounded-xl shadow-md border border-gray-100 p-6">
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
          <div>
            <h3 class="text-base font-bold text-gray-800 flex items-center gap-2">
              <FileSpreadsheet class="w-4 h-4 text-[#002e97]" />
              Detailtabelle
            </h3>
            <p class="text-xs text-gray-500">Alle aufgezeichneten Daten des ausgewählten Jahres</p>
          </div>
          
          <!-- Search input -->
          <div class="w-full md:w-64">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Suchen... (z.B. 12.05. oder 12.4)"
              class="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#002e97]/30 focus:border-[#002e97]"
            />
          </div>
        </div>

        <!-- Table element -->
        <div class="overflow-x-auto rounded-lg border border-gray-100">
          <table class="w-full text-sm text-left text-gray-600">
            <thead class="text-xs uppercase bg-gray-50 text-gray-500 border-b border-gray-150">
              <tr>
                <th scope="col" class="px-6 py-3 cursor-pointer select-none hover:bg-gray-100" @click="toggleSort('date')">
                  <div class="flex items-center gap-1.5">
                    Datum
                    <ArrowUpDown class="w-3.5 h-3.5 text-gray-400" />
                  </div>
                </th>
                <th scope="col" class="px-6 py-3">Zeitpunkt</th>
                <th scope="col" class="px-6 py-3 cursor-pointer select-none hover:bg-gray-100" @click="toggleSort('temperature')">
                  <div class="flex items-center gap-1.5">
                    Temperatur (°C)
                    <ArrowUpDown class="w-3.5 h-3.5 text-gray-400" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="item in paginatedData" 
                :key="item.date" 
                class="bg-white border-b border-gray-50 hover:bg-blue-50/20 transition-colors"
              >
                <td class="px-6 py-3.5 font-medium text-gray-900">
                  {{ new Date(item.date).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }) }}
                </td>
                <td class="px-6 py-3.5 text-gray-500">{{ time }} Uhr</td>
                <td class="px-6 py-3.5 font-bold" :class="item.temperature < 0 ? 'text-blue-500' : item.temperature > 20 ? 'text-red-500' : 'text-gray-700'">
                  {{ item.temperature.toFixed(1) }} °C
                </td>
              </tr>
              <tr v-if="filteredAndSortedData.length === 0">
                <td colspan="3" class="px-6 py-10 text-center text-gray-400">
                  Keine Einträge gefunden.
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Table Pagination controls -->
        <div class="flex flex-col sm:flex-row justify-between items-center gap-4 mt-4 text-xs font-medium text-gray-500">
          <span>
            Zeige {{ Math.min((currentPage - 1) * itemsPerPage + 1, filteredAndSortedData.length) }} bis 
            {{ Math.min(currentPage * itemsPerPage, filteredAndSortedData.length) }} von 
            {{ filteredAndSortedData.length }} Einträgen
          </span>
          
          <div class="flex items-center gap-2">
            <button
              @click="changePage(currentPage - 1)"
              :disabled="currentPage === 1"
              class="p-1.5 border border-gray-250 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              <ChevronLeft class="w-4 h-4" />
            </button>
            <span class="px-2 font-bold text-gray-700">Seite {{ currentPage }} von {{ totalPages }}</span>
            <button
              @click="changePage(currentPage + 1)"
              :disabled="currentPage === totalPages"
              class="p-1.5 border border-gray-250 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              <ChevronRight class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty/Backend Offline state -->
    <div v-else-if="!isLoading && weatherData.length === 0" class="bg-white rounded-xl shadow-md border border-gray-100 p-12 text-center">
      <AlertTriangle class="w-12 h-12 text-[#ff9900] mx-auto mb-4" />
      <h3 class="text-lg font-bold text-gray-800 mb-2">Keine Wetterdaten geladen</h3>
      <p class="text-sm text-gray-500 max-w-md mx-auto mb-6">
        Das Backend ist entweder nicht erreichbar oder hat keine Daten geliefert. Bitte stellen Sie sicher, dass der Django-Server läuft.
      </p>
      <button 
        @click="loadWeatherData" 
        class="px-5 py-2.5 bg-[#002e97] hover:bg-[#002578] text-white text-sm font-semibold rounded-lg shadow cursor-pointer transition-all inline-flex items-center gap-2"
      >
        <RefreshCw class="w-4 h-4" />
        Erneut versuchen
      </button>
    </div>

    <!-- Database Stats Card -->
    <DatabaseStats :stats="dbStats" class="mt-6" />
  </div>
</template>
