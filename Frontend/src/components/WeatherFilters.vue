<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount, computed } from 'vue'
import { MapPin, Calendar, Search, RefreshCw, Plus, Trash2, X, Settings, Map, ChevronDown, Compass } from '@lucide/vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix default marker icon path issue in Vite
import markerIconUrl from 'leaflet/dist/images/marker-icon.png'
import markerIconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadowUrl from 'leaflet/dist/images/marker-shadow.png'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIconRetinaUrl,
  iconUrl: markerIconUrl,
  shadowUrl: markerShadowUrl
})

const props = defineProps({
  initialLatitude: {
    type: [Number, String],
    default: 48.1351
  },
  initialLongitude: {
    type: [Number, String],
    default: 11.582
  },
  initialYear: {
    type: [Number, String],
    default: 1980
  },
  initialTime: {
    type: String,
    default: '12:00'
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  cities: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['submit-filters', 'add-city', 'delete-city'])

const latitude = ref(props.initialLatitude)
const longitude = ref(props.initialLongitude)
const year = ref(props.initialYear)
const time = ref(props.initialTime || '12:00')

const hoursList = computed(() => {
  return Array.from({ length: 24 }, (_, i) => {
    const hh = String(i).padStart(2, '0')
    return `${hh}:00`
  })
})

// Tabs State: false = Saved Cities, true = Custom Coordinates
const isCustomMode = ref(false)

// Custom dropdown state
const isDropdownOpen = ref(false)
const dropdownRef = ref(null)
const selectedCity = ref(null)

const errors = ref({
  latitude: '',
  longitude: '',
  year: ''
})

// Map state (Main view)
const isMapVisible = ref(false)
let mapInstance = null
let markerInstance = null

// Modal & Modal Map state
const isModalOpen = ref(false)
let modalMapInstance = null
let modalMarkerInstance = null

const newCity = ref({
  name: '',
  latitude: '',
  longitude: ''
})
const modalErrors = ref({
  name: '',
  latitude: '',
  longitude: ''
})
const isSubmittingCity = ref(false)

// Sync with cities from parent
watch(() => props.cities, (newCities) => {
  // Try to find if current coordinates match a saved city
  const match = newCities.find(c => 
    Math.abs(parseFloat(c.latitude) - parseFloat(latitude.value)) < 0.001 &&
    Math.abs(parseFloat(c.longitude) - parseFloat(longitude.value)) < 0.001
  )
  if (match) {
    selectedCity.value = match
    isCustomMode.value = false
  } else {
    selectedCity.value = null
    isCustomMode.value = true
  }
}, { immediate: true })

// Handle city selection
const selectCity = (city) => {
  selectedCity.value = city
  latitude.value = parseFloat(city.latitude)
  longitude.value = parseFloat(city.longitude)
  isDropdownOpen.value = false
}

// Watch coords in custom mode
watch([latitude, longitude], ([newLat, newLon]) => {
  if (isCustomMode.value) {
    // If user changes coords in custom mode, see if it matches a city anyway
    const match = props.cities.find(c => 
      Math.abs(parseFloat(c.latitude) - parseFloat(newLat)) < 0.001 &&
      Math.abs(parseFloat(c.longitude) - parseFloat(newLon)) < 0.001
    )
    selectedCity.value = match || null
  }
})

const validate = () => {
  let isValid = true
  errors.value = { latitude: '', longitude: '', year: '' }

  const latNum = parseFloat(latitude.value)
  if (isNaN(latNum)) {
    errors.value.latitude = 'Breitengrad muss eine Zahl sein.'
    isValid = false
  } else if (latNum < -90 || latNum > 90) {
    errors.value.latitude = 'Breitengrad muss zwischen -90 und 90 liegen.'
    isValid = false
  }

  const lonNum = parseFloat(longitude.value)
  if (isNaN(lonNum)) {
    errors.value.longitude = 'Längengrad muss eine Zahl sein.'
    isValid = false
  } else if (lonNum < -180 || lonNum > 180) {
    errors.value.longitude = 'Längengrad muss zwischen -180 und 180 liegen.'
    isValid = false
  }

  const yearNum = parseInt(year.value)
  const currentYear = new Date().getFullYear()
  if (isNaN(yearNum)) {
    errors.value.year = 'Jahr muss eine Zahl sein.'
    isValid = false
  } else if (yearNum < 1940 || yearNum > currentYear) {
    errors.value.year = `Jahr muss zwischen 1940 und ${currentYear} liegen.`
    isValid = false
  }

  return isValid
}

const handleSubmit = () => {
  if (validate()) {
    emit('submit-filters', {
      latitude: parseFloat(latitude.value),
      longitude: parseFloat(longitude.value),
      year: parseInt(year.value),
      time: time.value
    })
  }
}

// Map toggle and initialization (Main View Map)
const toggleMap = () => {
  isMapVisible.value = !isMapVisible.value
  if (isMapVisible.value) {
    nextTick(() => {
      initMap()
    })
  } else {
    destroyMap()
  }
}

const initMap = () => {
  if (mapInstance) return

  const initialLat = parseFloat(latitude.value) || 48.1351
  const initialLon = parseFloat(longitude.value) || 11.5820

  mapInstance = L.map('map-container').setView([initialLat, initialLon], 9)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(mapInstance)

  // Add marker
  markerInstance = L.marker([initialLat, initialLon], { draggable: true }).addTo(mapInstance)

  // Update coords when marker is dragged
  markerInstance.on('dragend', () => {
    const position = markerInstance.getLatLng()
    latitude.value = parseFloat(position.lat.toFixed(4))
    longitude.value = parseFloat(position.lng.toFixed(4))
  })

  // Update coords when map is clicked
  mapInstance.on('click', (e) => {
    const lat = parseFloat(e.latlng.lat.toFixed(4))
    const lng = parseFloat(e.latlng.lng.toFixed(4))
    latitude.value = lat
    longitude.value = lng
    markerInstance.setLatLng([lat, lng])
  })

  setTimeout(() => {
    if (mapInstance) mapInstance.invalidateSize()
  }, 100)
}

const destroyMap = () => {
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
    markerInstance = null
  }
}

// Watch latitude/longitude values to update map marker dynamically
watch([latitude, longitude], ([newLat, newLon]) => {
  const latNum = parseFloat(newLat)
  const lonNum = parseFloat(newLon)
  if (!isNaN(latNum) && !isNaN(lonNum) && mapInstance && markerInstance) {
    markerInstance.setLatLng([latNum, lonNum])
    mapInstance.setView([latNum, lonNum], mapInstance.getZoom())
  }
})

// Manage Cities Modal & Map Logic
const openModal = () => {
  isModalOpen.value = true
  newCity.value = { 
    name: '', 
    latitude: latitude.value.toString(), 
    longitude: longitude.value.toString() 
  }
  modalErrors.value = { name: '', latitude: '', longitude: '' }
  
  nextTick(() => {
    initModalMap()
  })
}

const closeModal = () => {
  destroyModalMap()
  isModalOpen.value = false
}

const initModalMap = () => {
  if (modalMapInstance) return

  const initialLat = parseFloat(newCity.value.latitude) || 48.1351
  const initialLon = parseFloat(newCity.value.longitude) || 11.5820

  modalMapInstance = L.map('modal-map-container').setView([initialLat, initialLon], 7)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap'
  }).addTo(modalMapInstance)

  modalMarkerInstance = L.marker([initialLat, initialLon], { draggable: true }).addTo(modalMapInstance)

  // Update new city coords when marker is dragged
  modalMarkerInstance.on('dragend', () => {
    const position = modalMarkerInstance.getLatLng()
    newCity.value.latitude = position.lat.toFixed(4)
    newCity.value.longitude = position.lng.toFixed(4)
  })

  // Update new city coords when map is clicked
  modalMapInstance.on('click', (e) => {
    const lat = e.latlng.lat.toFixed(4)
    const lng = e.latlng.lng.toFixed(4)
    newCity.value.latitude = lat
    newCity.value.longitude = lng
    modalMarkerInstance.setLatLng([lat, lng])
  })

  setTimeout(() => {
    if (modalMapInstance) modalMapInstance.invalidateSize()
  }, 200)
}

const destroyModalMap = () => {
  if (modalMapInstance) {
    modalMapInstance.remove()
    modalMapInstance = null
    modalMarkerInstance = null
  }
}

// Watch modal coords to update marker
watch([() => newCity.value.latitude, () => newCity.value.longitude], ([newLat, newLon]) => {
  const latNum = parseFloat(newLat)
  const lonNum = parseFloat(newLon)
  if (!isNaN(latNum) && !isNaN(lonNum) && modalMapInstance && modalMarkerInstance) {
    modalMarkerInstance.setLatLng([latNum, lonNum])
    modalMapInstance.setView([latNum, lonNum], modalMapInstance.getZoom())
  }
})

const validateNewCity = () => {
  let isValid = true
  modalErrors.value = { name: '', latitude: '', longitude: '' }

  if (!newCity.value.name.trim()) {
    modalErrors.value.name = 'Name ist erforderlich.'
    isValid = false
  }

  const latNum = parseFloat(newCity.value.latitude)
  if (isNaN(latNum)) {
    modalErrors.value.latitude = 'Muss eine Zahl sein.'
    isValid = false
  } else if (latNum < -90 || latNum > 90) {
    modalErrors.value.latitude = 'Muss zwischen -90 und 90 liegen.'
    isValid = false
  }

  const lonNum = parseFloat(newCity.value.longitude)
  if (isNaN(lonNum)) {
    modalErrors.value.longitude = 'Muss eine Zahl sein.'
    isValid = false
  } else if (lonNum < -180 || lonNum > 180) {
    modalErrors.value.longitude = 'Muss zwischen -180 und 180 liegen.'
    isValid = false
  }

  return isValid
}

const handleAddCity = async () => {
  if (!validateNewCity()) return
  
  isSubmittingCity.value = true
  try {
    emit('add-city', {
      name: newCity.value.name,
      latitude: parseFloat(newCity.value.latitude),
      longitude: parseFloat(newCity.value.longitude)
    })
    
    newCity.value.name = ''
  } catch (err) {
    console.error(err)
  } finally {
    isSubmittingCity.value = false
  }
}

const handleDeleteCity = (id) => {
  if (confirm('Möchten Sie diese Stadt wirklich löschen?')) {
    emit('delete-city', id)
  }
}

// Close dropdown on click outside
const handleClickOutside = (event) => {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target)) {
    isDropdownOpen.value = false
  }
}

onMounted(() => {
  window.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', handleClickOutside)
  destroyMap()
  destroyModalMap()
})
</script>

<template>
  <div class="bg-white rounded-xl shadow-md border border-gray-100 p-6 space-y-5">
    <!-- Header with Toggle Buttons -->
    <div class="flex flex-col sm:flex-row justify-between sm:items-center gap-4 border-b border-gray-100 pb-4">
      <!-- Mode Tabs -->
      <div class="flex bg-gray-100 p-1 rounded-lg self-start">
        <button
          type="button"
          @click="isCustomMode = false"
          class="px-4 py-1.5 text-xs font-bold rounded-md transition-all cursor-pointer"
          :class="!isCustomMode ? 'bg-white text-[#002e97] shadow-sm' : 'text-gray-500 hover:text-gray-700'"
        >
          📍 Gespeicherte Stadt
        </button>
        <button
          type="button"
          @click="isCustomMode = true"
          class="px-4 py-1.5 text-xs font-bold rounded-md transition-all cursor-pointer"
          :class="isCustomMode ? 'bg-white text-[#002e97] shadow-sm' : 'text-gray-500 hover:text-gray-700'"
        >
          ✏️ Eigene Koordinaten
        </button>
      </div>

      <!-- Manage cities button -->
      <button
        type="button"
        @click="openModal"
        class="text-xs font-semibold text-[#002e97] hover:text-[#002578] flex items-center gap-1.5 py-1.5 px-3 rounded-lg border border-blue-150 hover:bg-blue-50 transition-all cursor-pointer self-end sm:self-auto"
      >
        <Settings class="w-3.5 h-3.5" />
        Städte verwalten
      </button>
    </div>

    <!-- Filter Form -->
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Row 1: Location Inputs -->
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
        
        <!-- SAVED CITIES MODE -->
        <template v-if="!isCustomMode">
          <!-- Styled Dynamic City Selector -->
          <div ref="dropdownRef" class="relative md:col-span-2">
            <label class="block text-sm font-medium text-gray-600 mb-1">Ausgewählter Ort</label>
            <button
              type="button"
              @click="isDropdownOpen = !isDropdownOpen"
              :disabled="isLoading"
              class="w-full px-3 py-2.5 border border-gray-300 rounded-lg bg-white text-left focus:outline-none focus:ring-2 focus:ring-[#002e97]/30 focus:border-[#002e97] transition-all flex items-center justify-between text-sm cursor-pointer disabled:bg-gray-100 disabled:text-gray-400"
            >
              <span class="truncate font-bold text-gray-800">
                {{ selectedCity ? selectedCity.name : 'Bitte Stadt auswählen...' }}
              </span>
              <ChevronDown class="w-4 h-4 text-gray-400 transition-transform duration-200" :class="{ 'rotate-180': isDropdownOpen }" />
            </button>

            <!-- Custom Dropdown Menu -->
            <div
              v-if="isDropdownOpen"
              class="absolute left-0 z-50 mt-1 w-full bg-white border border-gray-150 rounded-lg shadow-lg max-h-60 overflow-y-auto divide-y divide-gray-100 animate-fade-in"
            >
              <button
                v-for="city in cities"
                :key="city.id"
                type="button"
                @click="selectCity(city)"
                class="w-full text-left px-4 py-3 hover:bg-gray-50 flex justify-between items-center cursor-pointer transition-colors"
                :class="{ 'bg-blue-50/50': selectedCity?.id === city.id }"
              >
                <div class="flex flex-col gap-0.5">
                  <span class="text-xs font-bold text-gray-800">{{ city.name }}</span>
                  <span class="text-[10px] text-gray-400">
                    {{ parseFloat(city.latitude).toFixed(4) }}° Lat, {{ parseFloat(city.longitude).toFixed(4) }}° Lon
                  </span>
                </div>
                <Compass v-if="selectedCity?.id === city.id" class="w-4 h-4 text-[#002e97]" />
              </button>
            </div>
          </div>

          <!-- Read-only Location Info Card -->
          <div class="bg-blue-50/30 border border-blue-100 rounded-lg px-4 py-2.5 flex items-center justify-between md:col-span-1 h-[42px] mb-[1px]">
            <span class="text-xs font-semibold text-gray-500">Koordinaten:</span>
            <span class="text-xs font-bold text-[#002e97]">
              {{ parseFloat(latitude).toFixed(3) }}° / {{ parseFloat(longitude).toFixed(3) }}°
            </span>
          </div>
        </template>

        <!-- CUSTOM COORDINATES MODE -->
        <template v-else>
          <!-- Latitude input -->
          <div>
            <label class="block text-sm font-medium text-gray-600 mb-1" for="latitude">Breitengrad (Lat)</label>
            <input
              id="latitude"
              v-model="latitude"
              type="text"
              placeholder="z.B. 48.1351"
              :disabled="isLoading"
              class="w-full pl-3 pr-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#002e97]/30 focus:border-[#002e97] transition-all disabled:bg-gray-100 disabled:text-gray-400"
              :class="errors.latitude ? 'border-red-500 ring-1 ring-red-500' : 'border-gray-300'"
            />
            <p v-if="errors.latitude" class="text-xs text-red-500 mt-1">{{ errors.latitude }}</p>
          </div>

          <!-- Longitude input -->
          <div>
            <label class="block text-sm font-medium text-gray-600 mb-1" for="longitude">Längengrad (Lon)</label>
            <input
              id="longitude"
              v-model="longitude"
              type="text"
              placeholder="z.B. 11.582"
              :disabled="isLoading"
              class="w-full pl-3 pr-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#002e97]/30 focus:border-[#002e97] transition-all disabled:bg-gray-100 disabled:text-gray-400"
              :class="errors.longitude ? 'border-red-500 ring-1 ring-red-500' : 'border-gray-300'"
            />
            <p v-if="errors.longitude" class="text-xs text-red-500 mt-1">{{ errors.longitude }}</p>
          </div>

          <!-- Map Toggle Button -->
          <div>
            <button
              type="button"
              @click="toggleMap"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg hover:bg-blue-50/50 hover:border-blue-300 flex items-center justify-center gap-1.5 text-sm font-semibold transition-all text-gray-700 cursor-pointer h-[42px] mb-[1px]"
              :class="{ 'bg-blue-50 border-[#002e97] text-[#002e97]': isMapVisible }"
            >
              <Map class="w-4 h-4" />
              {{ isMapVisible ? 'Karte schließen' : 'Auf Karte wählen' }}
            </button>
          </div>
        </template>

        <!-- Year input (shared) -->
        <div>
          <label class="block text-sm font-medium text-gray-600 mb-1" for="year">Jahr</label>
          <input
            id="year"
            v-model="year"
            type="number"
            min="1940"
            max="2026"
            placeholder="z.B. 1980"
            :disabled="isLoading"
            class="w-full pl-3 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#002e97]/30 focus:border-[#002e97] transition-all disabled:bg-gray-100 disabled:text-gray-400 h-[42px] mb-[1px]"
            :class="errors.year ? 'border-red-500 ring-1 ring-red-500' : 'border-gray-300'"
          />
          <p v-if="errors.year" class="text-xs text-red-500 mt-1">{{ errors.year }}</p>
        </div>

        <!-- Time select (shared) -->
        <div>
          <label class="block text-sm font-medium text-gray-600 mb-1" for="time">Uhrzeit</label>
          <select
            id="time"
            v-model="time"
            :disabled="isLoading"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#002e97]/30 focus:border-[#002e97] transition-all bg-white disabled:bg-gray-100 disabled:text-gray-400 h-[42px] mb-[1px] font-medium text-gray-700 cursor-pointer"
          >
            <option v-for="h in hoursList" :key="h" :value="h">
              {{ h }} Uhr {{ h === '12:00' ? '(Standard)' : '' }}
            </option>
          </select>
        </div>
      </div>

      <!-- Leaflet Map Container (Visible in Custom Mode or if Toggled) -->
      <div 
        v-if="isMapVisible && isCustomMode" 
        class="border border-gray-200 rounded-lg overflow-hidden shadow-inner relative z-10 animate-fade-in"
      >
        <div id="map-container" class="w-full h-80"></div>
        <div class="absolute bottom-2 left-2 z-[999] bg-white/90 backdrop-blur-xs px-2.5 py-1.5 rounded-md border border-gray-250 text-[10px] text-gray-500 font-semibold shadow-xs flex items-center gap-1">
          <MapPin class="w-3 h-3 text-[#ff9900]" />
          Klicken Sie auf die Karte oder ziehen Sie die Nadel, um Koordinaten zu aktualisieren.
        </div>
      </div>

      <!-- Action Button -->
      <div class="flex justify-end pt-2">
        <button
          type="submit"
          :disabled="isLoading || (!isCustomMode && !selectedCity)"
          class="px-5 py-2.5 bg-[#ff9900] hover:bg-[#e68a00] text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed text-sm"
        >
          <component :is="isLoading ? RefreshCw : Search" class="w-4 h-4" :class="{ 'animate-spin': isLoading }" />
          {{ isLoading ? 'Lade Wetterdaten...' : 'Daten abfragen' }}
        </button>
      </div>
    </form>

    <!-- Modal for Managing Cities -->
    <div 
      v-if="isModalOpen" 
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs transition-opacity"
    >
      <div class="bg-white rounded-xl shadow-xl border border-gray-100 max-w-lg w-full overflow-hidden flex flex-col max-h-[90vh]">
        <!-- Modal Header -->
        <div class="px-6 py-4 bg-gray-50 border-b border-gray-150 flex items-center justify-between">
          <h3 class="text-base font-bold text-gray-800 flex items-center gap-2">
            <MapPin class="w-5 h-5 text-[#002e97]" />
            Orte &amp; Städte verwalten
          </h3>
          <button 
            @click="closeModal" 
            class="text-gray-400 hover:text-gray-600 hover:bg-gray-100 p-1.5 rounded-lg transition-all cursor-pointer"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <!-- Modal Body (Scrollable) -->
        <div class="p-6 overflow-y-auto space-y-6 flex-1">
          <!-- Add City Form -->
          <div class="bg-blue-50/50 border border-blue-100 rounded-xl p-4">
            <h4 class="text-sm font-bold text-gray-800 mb-3 flex items-center gap-1.5">
              <Plus class="w-4 h-4 text-[#002e97]" />
              Neuen Ort hinzufügen
            </h4>
            <form @submit.prevent="handleAddCity" class="space-y-3">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <!-- Name -->
                <div class="sm:col-span-2">
                  <label class="block text-xs font-semibold text-gray-500 mb-1">Name</label>
                  <input
                    v-model="newCity.name"
                    type="text"
                    placeholder="z.B. Berlin"
                    class="w-full px-2.5 py-1.5 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-[#002e97] focus:border-[#002e97] bg-white"
                    :class="{ 'border-red-500': modalErrors.name }"
                  />
                  <p v-if="modalErrors.name" class="text-[10px] text-red-500 mt-0.5">{{ modalErrors.name }}</p>
                </div>
                
                <!-- Lat -->
                <div>
                  <label class="block text-xs font-semibold text-gray-500 mb-1">Breite (Lat)</label>
                  <input
                    v-model="newCity.latitude"
                    type="text"
                    placeholder="z.B. 52.5200"
                    class="w-full px-2.5 py-1.5 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-[#002e97] focus:border-[#002e97] bg-white"
                    :class="{ 'border-red-500': modalErrors.latitude }"
                  />
                  <p v-if="modalErrors.latitude" class="text-[10px] text-red-500 mt-0.5">{{ modalErrors.latitude }}</p>
                </div>

                <!-- Lon -->
                <div>
                  <label class="block text-xs font-semibold text-gray-500 mb-1">Länge (Lon)</label>
                  <input
                    v-model="newCity.longitude"
                    type="text"
                    placeholder="z.B. 13.4050"
                    class="w-full px-2.5 py-1.5 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-[#002e97] focus:border-[#002e97] bg-white"
                    :class="{ 'border-red-500': modalErrors.longitude }"
                  />
                  <p v-if="modalErrors.longitude" class="text-[10px] text-red-500 mt-0.5">{{ modalErrors.longitude }}</p>
                </div>

                <!-- Modal Map Selector -->
                <div class="sm:col-span-2">
                  <label class="block text-xs font-semibold text-gray-500 mb-1">Standort auf Karte wählen</label>
                  <div id="modal-map-container" class="w-full h-44 rounded border border-gray-250 shadow-inner relative z-10"></div>
                </div>

                <!-- Submit new city -->
                <div class="sm:col-span-2 pt-2">
                  <button
                    type="submit"
                    :disabled="isSubmittingCity"
                    class="w-full py-2 bg-[#002e97] hover:bg-[#002578] text-white text-xs font-semibold rounded shadow transition-all flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50"
                  >
                    Ort speichern
                  </button>
                </div>
              </div>
            </form>
          </div>

          <!-- Cities List -->
          <div>
            <h4 class="text-sm font-bold text-gray-800 mb-2">Gespeicherte Orte ({{ cities.length }})</h4>
            <div class="border border-gray-150 rounded-lg divide-y divide-gray-100 max-h-40 overflow-y-auto">
              <div 
                v-for="city in cities" 
                :key="city.id" 
                class="px-4 py-2 flex items-center justify-between text-xs hover:bg-gray-50 transition-colors"
              >
                <div>
                  <span class="font-bold text-gray-800">{{ city.name }}</span>
                  <span class="text-gray-400 ml-2">
                    ({{ parseFloat(city.latitude).toFixed(4) }}° Lat, {{ parseFloat(city.longitude).toFixed(4) }}° Lon)
                  </span>
                </div>
                <button
                  type="button"
                  @click="handleDeleteCity(city.id)"
                  class="text-red-500 hover:text-red-700 hover:bg-red-50 p-1.5 rounded transition-all cursor-pointer"
                  title="Stadt löschen"
                >
                  <Trash2 class="w-3.5 h-3.5" />
                </button>
              </div>
              <div v-if="cities.length === 0" class="p-6 text-center text-gray-400">
                Keine gespeicherten Städte vorhanden.
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="px-6 py-3 bg-gray-50 border-t border-gray-150 flex justify-end">
          <button
            type="button"
            @click="closeModal"
            class="px-4 py-2 border border-gray-250 hover:bg-gray-100 text-gray-700 text-xs font-semibold rounded-lg transition-all cursor-pointer"
          >
            Schließen
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
