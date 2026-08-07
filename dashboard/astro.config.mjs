import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  outDir: './dist',
  site: 'https://projectbluefin.github.io',
  base: '/testsuite/',
  vite: {
    plugins: [tailwindcss()],
  },
});
