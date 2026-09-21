/**
 * SSO iframe 嵌入场景的 Access-Token 接入工具。
 *
 * 客户平台前端以 iframe 嵌入 console，并把认证 token 以 `Auth` 参数拼在
 * iframe src 的 hash 查询串里（如 `#/home/.../flow/?id=xx&Auth=<token>`）。
 * 本工具在应用启动最早期（resetUserData 顶部、首个 HTTP 请求 getHealth 之前）
 * 执行：解析 Auth → 写入 Access-Token Cookie（后端 SsoAuthenticationFilter 按
 * auth.sso.header 配置从同名 Cookie 提取，默认名即 Access-Token）→ 从 URL
 * 中剥除该参数（凭证不得留在地址栏与历史栈）。
 */

/** 与后端 auth.sso.header 默认配置（application-manager.yml）对齐的 Cookie 名 */
export const SSO_COOKIE_NAME = 'Access-Token';

/** iframe src 中传递 token 的参数名（契约约定，大小写敏感） */
export const AUTH_PARAM_NAME = 'Auth';

/**
 * 从 query 串（不含前导 '?'）中提取 Auth 参数的原始值，并返回剥除后的剩余串。
 *
 * 使用纯字符串切分而非 URLSearchParams：token 是不透明字符串，
 * URLSearchParams 会把 '+' 解码为空格、'%xx' 解码，静默损坏凭证；
 * 其余参数段按字节原样保留（顺序不变），避免影响对 URL 做裸正则
 * 匹配的消费方（如 http.service 的 peekWorkspaceId）。
 *
 * @returns token 为 null 表示未找到非空值；query 为剥除 Auth 后的剩余串
 */
export function extractAuthParam(query: string): { token: string | null; query: string } {
  const kept: string[] = [];
  let token: string | null = null;
  for (const seg of query.split('&')) {
    if (seg.startsWith(`${AUTH_PARAM_NAME}=`)) {
      const value = seg.slice(AUTH_PARAM_NAME.length + 1);
      // 取第一个非空值；空值 Auth= 同样从 URL 中剥除
      if (value && token === null) {
        token = value;
      }
    } else if (seg !== '') {
      kept.push(seg);
    }
  }
  return { token, query: kept.join('&') };
}

/**
 * 将 token 原样写入 Access-Token Cookie。
 *
 * - 不做 encodeURIComponent：后端 cookie.getValue() 不做 URL 解码，
 *   编码会导致含 '+'/'/' 的 token 校验失败
 * - 会话级（不设 expires）：iframe 每次挂载都会重带 Auth，且应用内
 *   reload 不丢失认证
 * - https 下补 SameSite=None; Secure（跨站 iframe 必需）；http 下不加
 *   SameSite（浏览器在非安全上下文会拒绝 SameSite=None）
 */
export function writeSsoCookie(token: string): void {
  if (/[\s;,"]/.test(token)) {
    console.warn('[SSO] Access-Token contains illegal cookie characters, write may fail');
  }
  const attrs = ['path=/'];
  if (location.protocol === 'https:') {
    attrs.push('SameSite=None', 'Secure');
  }
  document.cookie = `${SSO_COOKIE_NAME}=${token}; ${attrs.join('; ')}`;
  // 回读校验：跨站 iframe 里浏览器可能静默拦截 Cookie 写入，此处给出可观测信号
  const existed = document.cookie
    .split('; ')
    .some((item) => item.startsWith(`${SSO_COOKIE_NAME}=`));
  if (!existed) {
    console.warn(
      '[SSO] Access-Token cookie not detected after write, possibly blocked by third-party cookie policy'
    );
  }
}

/**
 * 组合入口：从 hash（主通道）与 search（防御性）解析 Auth → 写 Cookie →
 * 用 replaceState 将 Auth 从 URL 剥除（带 token 的 URL 不进历史栈）。
 *
 * @returns 提取到的 token；URL 中无 Auth 参数时返回 null（不写 Cookie、不改 URL）
 */
export function consumeSsoAuthFromUrl(): string | null {
  try {
    // ---- hash 侧：'#<路由路径>?<query>' ----
    let route = '';
    let hashQuery = '';
    const hash = window.location.hash;
    if (hash.startsWith('#')) {
      const hashBody = hash.slice(1);
      const qIndex = hashBody.indexOf('?');
      if (qIndex >= 0) {
        route = hashBody.slice(0, qIndex);
        hashQuery = hashBody.slice(qIndex + 1);
      } else {
        route = hashBody;
      }
    }

    // ---- search 侧防御性检查：若 Auth 残留在 search，后续 pushState 会把它
    // 搬进 hash（reArrangeSearchParam 白名单之外），必须一并清掉 ----
    const search = window.location.search;
    const searchQuery = search.startsWith('?') ? search.slice(1) : '';

    const hashRes = extractAuthParam(hashQuery);
    const searchRes = extractAuthParam(searchQuery);
    // hash 为主通道，search 兜底
    const token = hashRes.token !== null ? hashRes.token : searchRes.token;

    const hashChanged = hashRes.query !== hashQuery;
    const searchChanged = searchRes.query !== searchQuery;
    if (!hashChanged && !searchChanged) {
      return null;
    }

    if (token) {
      writeSsoCookie(token);
    }

    const newHash = hashChanged
      ? `#${route}${hashRes.query ? `?${hashRes.query}` : ''}`
      : hash;
    const newSearch = searchChanged
      ? searchRes.query
        ? `?${searchRes.query}`
        : ''
      : search;
    history.replaceState(
      history.state,
      '',
      window.location.pathname + newSearch + newHash
    );
    return token;
  } catch (e) {
    console.warn('[SSO] failed to consume Auth param from url', e);
    return null;
  }
}
