import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

const apiTarget = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000';

const apiProxy = {
  '/api': {
    target: apiTarget,
    changeOrigin: true,
  },
};

const root = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
  build: {
    rollupOptions: {
      input: {
        main: resolve(root, 'index.html'),
        commands: resolve(root, 'commands.html'),
        agent: resolve(root, 'agent.html'),
      },
    },
  },
});
