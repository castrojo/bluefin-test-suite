import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

// https://astro.build/config
export default defineConfig({
  outDir: './dist',
  site: 'https://qa.projectbluefin.io',
  base: '/',
  integrations: [tailwind()],
});