# Weather Frontend Application

This is the frontend for the Check24 Weather Application. It is built using **Vue 3**, **Vite**, **Tailwind CSS v4**, and **Chart.js** for visualizing historical weather data.

## Features
- **Interactive Weather Chart:** Visualizes temperature trends over time.
- **City Selection:** Allows users to select or manage different cities.
- **Fast and Responsive:** Powered by Vite for fast HMR and optimized builds.
- **Modern Styling:** Utilizes Tailwind CSS for a clean and responsive UI.

## Setup Instructions

### 1. Prerequisites
- **Node.js** (v18+)
- **npm** (Node Package Manager)

### 2. Installation
Navigate to the `Frontend` directory and install the dependencies:
```bash
npm install
```

### 3. Environment Configuration
Ensure your backend is running. If you are running locally without Docker, the frontend communicates with the backend API.

### 4. Running the Development Server
Start the Vite development server:
```bash
npm run dev
```
The application will be accessible at `http://localhost:5173` (or the port specified by Vite in your console).

### 5. Building for Production
To build the application for production, run:
```bash
npm run build
```
This generates optimized static files in the `dist/` directory, which are served by Nginx in the Docker production setup.
