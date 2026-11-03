import { defineConfig } from 'vite';

// 静态演示包：产物放在 /RetireNest/ 子路径下，只打首页。
// 与默认配置分开，`npm run build` 不受影响。
export default defineConfig({
  base: '/RetireNest/',
  define: {
    'import.meta.env.VITE_DEMO': JSON.stringify('true'),
  },
  build: {
    outDir: 'dist-demo',
    emptyOutDir: true,
    rollupOptions: {
      input: { index: 'index.html' },
    },
  },
});
