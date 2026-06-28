import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

// https://astro.build/config
export default defineConfig({
  outDir: './dist',
  site: 'https://projectbluefin.github.io',
  base: '/testsuite/',
  integrations: [tailwind()],
});