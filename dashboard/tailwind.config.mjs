/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        brand: {
          space: '#020617',     // Base backdrop slate-950
          cosmic: '#0b0f19',    // Cards backdrop
          glow: '#06b6d4',      // Cyan glow
          nebula: '#3b82f6',    // Bluefin Blue
        },
        status: {
          pass: '#10b981',      // Emerald-500
          fail: '#f43f5e',      // Rose-500
          warn: '#f59e0b',      // Amber-500
          info: '#3b82f6',      // Blue-500
        }
      },
      boxShadow: {
        'glow-cyan': '0 0 15px -3px rgba(6, 182, 212, 0.4)',
        'glow-blue': '0 0 15px -3px rgba(59, 130, 246, 0.4)',
      }
    },
  },
  plugins: [],
}