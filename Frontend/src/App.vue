<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import Dashboard from './components/Dashboard.vue'
import { CloudSun } from 'lucide-vue-next'

const apiStatus = ref('loading') // 'online' | 'offline' | 'unhealthy' | 'loading'
const dbStatus = ref('offline')
const cacheStatus = ref('offline')

const checkHealth = async () => {
  try {
    const response = await axios.get('/api/health/')
    if (response.data && response.data.status === 'healthy') {
      apiStatus.value = 'online'
      dbStatus.value = response.data.database
      cacheStatus.value = response.data.cache
    } else {
      apiStatus.value = 'unhealthy'
      dbStatus.value = response.data?.database || 'offline'
      cacheStatus.value = response.data?.cache || 'offline'
    }
  } catch (err) {
    if (err.response && err.response.data) {
      apiStatus.value = 'unhealthy'
      dbStatus.value = err.response.data.database || 'offline'
      cacheStatus.value = err.response.data.cache || 'offline'
    } else {
      apiStatus.value = 'offline'
      dbStatus.value = 'offline'
      cacheStatus.value = 'offline'
    }
  }
}

let intervalId = null

onMounted(() => {
  checkHealth()
  intervalId = setInterval(checkHealth, 5000)
})

onUnmounted(() => {
  if (intervalId) {
    clearInterval(intervalId)
  }
})
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex flex-col font-sans antialiased">
    <!-- Check24 Brand Header -->
    <header class="bg-[#002e97] text-white shadow-lg sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <!-- Logo Section -->
          <div class="flex items-center gap-3">
            <div class="bg-white p-2 rounded-lg text-[#002e97] shadow-inner flex items-center justify-center">
              <CloudSun class="w-6 h-6 stroke-[2.5]" />
            </div>
            <div>
              <div class="flex items-center gap-1.5">
                <span class="font-black text-xl tracking-tight text-white">CHECK<span class="text-[#ff9900]">24</span></span>
                <span class="text-xs px-2 py-0.5 bg-blue-800 text-blue-200 rounded font-semibold tracking-wide uppercase">Wetter</span>
              </div>
              <p class="text-[10px] text-blue-200 font-medium tracking-wider uppercase">Coding Challenge Frontend</p>
            </div>
          </div>

          <!-- Quick Navigation Links (Check24 style) -->
          <nav class="hidden md:flex items-center gap-6 text-sm font-semibold">
            <a href="#" class="text-white border-b-2 border-[#ff9900] pb-1 hover:text-gray-150 transition-colors">Wetter-Historie</a>
            <a 
              href="/api/schema/swagger-ui/" 
              target="_blank" 
              class="text-blue-200 hover:text-white transition-colors"
            >
              Swagger API-Docs
            </a>
            <a 
              href="https://open-meteo.com/" 
              target="_blank" 
              class="text-blue-200 hover:text-white transition-colors flex items-center gap-1"
            >
              Open-Meteo API
            </a>
            <a 
              href="https://check24.de" 
              target="_blank" 
              class="text-blue-200 hover:text-white transition-colors"
            >
              check24.de
            </a>
          </nav>
        </div>
      </div>
    </header>

    <!-- Main Container -->
    <main class="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Title Area -->
      <div class="mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 tracking-tight">Historisches Wetter-Dashboard</h1>
          <p class="text-sm text-gray-500 mt-1">
            Analysieren Sie historische Wetteraufzeichnungen der Open-Meteo API mit dualer Kachelung (PostgreSQL &amp; Redis).
          </p>
        </div>
        
        <!-- API Status Indicator -->
        <div 
          class="flex items-center gap-2 px-3 py-1.5 bg-white border rounded-lg shadow-sm transition-all"
          :class="{
            'border-green-200 bg-green-50/5': apiStatus === 'online',
            'border-amber-200 bg-amber-50/5': apiStatus === 'unhealthy',
            'border-red-200 bg-red-50/5': apiStatus === 'offline',
            'border-gray-250': apiStatus === 'loading'
          }"
          :title="apiStatus === 'online' ? `Datenbank: ${dbStatus} | Cache: ${cacheStatus}` : 
                  apiStatus === 'unhealthy' ? `Datenbank: ${dbStatus} | Cache: ${cacheStatus} (Dienst eingeschränkt)` : 
                  apiStatus === 'offline' ? 'Verbindung zum Backend-Server fehlgeschlagen.' : 'Prüfe Verbindung...'"
        >
          <!-- Online status -->
          <span v-if="apiStatus === 'online'" class="relative flex h-2 w-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
          </span>
          <!-- Unhealthy status -->
          <span v-else-if="apiStatus === 'unhealthy'" class="relative flex h-2 w-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-450 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
          </span>
          <!-- Offline status -->
          <span v-else-if="apiStatus === 'offline'" class="relative flex h-2 w-2">
            <span class="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
          </span>
          <!-- Loading status -->
          <span v-else class="relative flex h-2 w-2">
            <span class="animate-pulse relative inline-flex rounded-full h-2 w-2 bg-gray-400"></span>
          </span>

          <span class="text-xs font-semibold text-gray-600">
            Backend API: 
            <span v-if="apiStatus === 'online'" class="text-green-600">Online</span>
            <span v-else-if="apiStatus === 'unhealthy'" class="text-amber-600 font-bold">Eingeschränkt</span>
            <span v-else-if="apiStatus === 'offline'" class="text-red-600 font-bold">Offline</span>
            <span v-else class="text-gray-450">Prüfe...</span>
          </span>
        </div>
      </div>

      <!-- Main Dashboard Component -->
      <Dashboard />
    </main>

    <!-- Check24 Footer -->
    <footer class="bg-gray-800 text-gray-400 py-6 border-t border-gray-700 mt-auto text-xs">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex flex-col sm:flex-row justify-between items-center gap-4">
          <p>&copy; 2026 CHECK24 Vergleichsportal GmbH. Alle Rechte vorbehalten.</p>
          <div class="flex gap-4">
            <a href="#" class="hover:text-white transition-colors">Impressum</a>
            <a href="#" class="hover:text-white transition-colors">Datenschutz</a>
            <a href="#" class="hover:text-white transition-colors">Hilfe</a>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<style>
/* Any global resets if needed */
</style>
