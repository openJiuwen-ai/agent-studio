export function generateLetterAvatar(name?: string, size: number = 150): string {
  const initial = (name || '').trim().charAt(0).toUpperCase() || 'U'
  const colors = ['#5f81ff', '#6ea6ff', '#73b3ff', '#8ff4ff', '#56b0e4', '#509ae6']
  let hash = 0
  for (let i = 0; i < initial.length; i++) hash = initial.charCodeAt(i) + ((hash << 5) - hash)
  const bg = colors[Math.abs(hash) % colors.length]
  const svg = `<?xml version="1.0" encoding="UTF-8"?><svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"><rect width="100%" height="100%" rx="${size / 2}" fill="${bg}"/><text x="50%" y="50%" dy=".36em" text-anchor="middle" fill="#fff" font-family="-apple-system,system-ui,Segoe UI,Roboto,Arial" font-size="${Math.floor(size * 0.48)}" font-weight="700">${initial}</text></svg>`
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}


export function resolveAvatar(avatar: string | undefined, name?: string, size: number = 150): string {
  const isDefaultUnsplash = !!avatar && /unsplash\.com\/photo-1472099645785-5658abf4ff4e/.test(avatar)
  if (!avatar || isDefaultUnsplash) {
    return generateLetterAvatar(name, size)
  }
  return avatar
}
