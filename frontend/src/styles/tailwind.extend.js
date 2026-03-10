module.exports = {
  // 菜单颜色
  colors: {
    menu: {
      active: {
        bg: '#E6F0FF',
        text: '#2B6CB0',
      },
      hover: {
        bg: '#F7FAFC',
        text: '#2D3748',
      },
      section: {
        text: '#A0AEC0',
      },
    },
    // Theme variables as actual Tailwind colors
    background: 'var(--background)',
    foreground: 'var(--foreground)',
    card: 'var(--card)',
    'card-foreground': 'var(--card-foreground)',
    popover: 'var(--popover)',
    'popover-foreground': 'var(--popover-foreground)',
    primary: {
      DEFAULT: 'var(--primary)',
      50: 'var(--primary)',
      100: 'var(--primary)',
      200: 'var(--primary)',
      300: 'var(--primary)',
      400: 'var(--primary)',
      500: 'var(--primary)',
      600: 'var(--primary)',
      700: 'var(--primary)',
      800: 'var(--primary)',
      900: 'var(--primary)',
    },
    'primary-foreground': 'var(--primary-foreground)',
    secondary: {
      DEFAULT: 'var(--secondary)',
      50: 'var(--secondary)',
      100: 'var(--secondary)',
      200: 'var(--secondary)',
      300: 'var(--secondary)',
      400: 'var(--secondary)',
      500: 'var(--secondary)',
      600: 'var(--secondary)',
      700: 'var(--secondary)',
      800: 'var(--secondary)',
      900: 'var(--secondary)',
    },
    'secondary-foreground': 'var(--secondary-foreground)',
    muted: 'var(--muted)',
    'muted-foreground': 'var(--muted-foreground)',
    accent: 'var(--accent)',
    'accent-foreground': 'var(--accent-foreground)',
    destructive: 'var(--destructive)',
    'destructive-foreground': 'var(--destructive-foreground)',
    border: 'var(--border)',
    input: 'var(--input)',
    ring: 'var(--ring)',
    success: 'var(--success)',
    'success-foreground': 'var(--success-foreground)',
    warning: 'var(--warning)',
    'warning-foreground': 'var(--warning-foreground)',
    info: 'var(--info)',
    'info-foreground': 'var(--info-foreground)',
  },

  // 卡片阴影
  boxShadow: {
    card: '0 1px 4px 0 rgb(0 0 0 / 4%)',
    'card-hover': '0 4px 12px -2px rgb(0 0 0 / 8%), 0 2px 4px -1px rgb(0 0 0 / 4%)',
  },
}
