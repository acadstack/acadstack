import { fileURLToPath, URL } from 'url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  // Load env variables from .env files and process.env
  const env = loadEnv(mode, process.cwd(), '')
  console.log('Loaded OAUTH_CLIENT_ID from loadEnv:', env.OAUTH_CLIENT_ID);
  console.log('Raw process.env.OAUTH_CLIENT_ID:', process.env.OAUTH_CLIENT_ID);
  
  // Check if required env variable is set
  if (!env.OAUTH_CLIENT_ID) {
    throw new Error('❌ Environment variable OAUTH_CLIENT_ID is required but not defined.')
  }

  return {
    base: "/acadstack/",
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    build: {
      emptyOutDir: true,
    },
  }
})
