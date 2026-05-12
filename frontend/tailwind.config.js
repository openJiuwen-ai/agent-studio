/*
 * Copyright (c) 2026 OpenJiuwen Project
 * Licensed under the MIT License
 */

/** @type {import('tailwindcss').Config} */
const tailwindExtend = require('./src/styles/tailwind.extend');

module.exports = {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
    // Only include specific package source files, not entire packages directory
    // to avoid scanning node_modules and other unnecessary files
    './packages/workflow-canvas/src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        secondary: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        },
        // 业务自定义颜色从 tailwind.extend.js 引入
        ...tailwindExtend.colors,
      },
      fontFamily: {
        sans: ['HarmonyOS Sans SC', 'HarmonyOS Sans', 'Inter', 'system-ui', 'sans-serif'],
      },
      fontWeight: {
        normal: '400',
        medium: '500',
        semibold: '600',
        bold: '700',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'loader-circle': 'loaderCircle 5s linear infinite',
        'loader-letter': 'loaderLetter 3s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        loaderCircle: {
          '0%': {
            transform: 'rotate(90deg)',
            boxShadow:
              '0 6px 12px 0 #38bdf8 inset, 0 12px 18px 0 #005dff inset, 0 36px 36px 0 #1e40af inset, 0 0 3px 1.2px rgba(56,189,248,0.3), 0 0 6px 1.8px rgba(0,93,255,0.2)',
          },
          '50%': {
            transform: 'rotate(270deg)',
            boxShadow:
              '0 6px 12px 0 #60a5fa inset, 0 12px 6px 0 #0284c7 inset, 0 24px 36px 0 #005dff inset, 0 0 3px 1.2px rgba(56,189,248,0.3), 0 0 6px 1.8px rgba(0,93,255,0.2)',
          },
          '100%': {
            transform: 'rotate(450deg)',
            boxShadow:
              '0 6px 12px 0 #4dc8fd inset, 0 12px 18px 0 #005dff inset, 0 36px 36px 0 #1e40af inset, 0 0 3px 1.2px rgba(56,189,248,0.3), 0 0 6px 1.8px rgba(0,93,255,0.2)',
          },
        },
        loaderLetter: {
          '0%, 100%': { opacity: '0.4', transform: 'translateY(0)' },
          '20%': { opacity: '1', transform: 'scale(1.15)' },
          '40%': { opacity: '0.7', transform: 'translateY(0)' },
        },
      },
      // 从 tailwind.extend.js 引入其他业务自定义配置（boxShadow 等）
      boxShadow: tailwindExtend.boxShadow,
    },
  },
  plugins: [require('@tailwindcss/typography')],
};
