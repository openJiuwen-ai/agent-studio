/**
 * SSO iframe 嵌入场景的 Access-Token 接入工具。
 *
 * 三方平台前端以 iframe 嵌入 console，并把认证 token 以 `Auth` 参数拼在
 * iframe src 的 hash 查询串里（如 `#/home/.../flow/?id=xx&Auth=<token>`）。
 * 本工具在应用启动最早期（resetUserData 顶部、首个 HTTP 请求 getHealth 之前）
 * 执行：解析 Auth → 写入 Access-Token Cookie（后端 SsoAuthenticationFilter 按
 * auth.sso.header 配置从同名 Cookie 提取，默认名即 Access-Token）→ 从 URL
 * 中剥除该参数（凭证不得留在地址栏与历史栈）。
 *
 * 安全门控（防登录 CSRF / 会话固定：诱导用户打开携带攻击者 token 的链接
 * 时，以下任一条件不满足即拒绝消费，且对 URL 零改动）：
 * 1. 仅当页面处于 iframe 嵌入中（window.self !== window.top）才消费；
 * 2. 父页面来源可信：document.referrer 与 console 同主机（覆盖同 IP 不同
 *    端口的部署形态，忽略协议/端口），或其 origin 在 TRUSTED_PARENT_ORIGINS
 *    白名单内（跨域 https 部署时由部署方补充）；
 * 3. referrer 缺失按不可信处理（fail-closed）。父页面不得设置
 *    Referrer-Policy: no-referrer（浏览器默认策略不受影响）。
 */

/** 与后端 auth.sso.header 默认配置（application-manager.yml）对齐的 Cookie 名 */
export const SSO_COOKIE_NAME = 'Access-Token';

/** iframe src 中传递 token 的参数名（契约约定，大小写敏感） */
export const AUTH_PARAM_NAME = 'Auth';

/**
 * 可信父平台 origin 白名单（完整 origin，形如 https://customer.example.com）。
 * 默认隐式放行与 console 同主机（含父子域）的父页面；跨域部署时在此补充。
 */
export const TRUSTED_PARENT_ORIGINS: string[] = [];

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
 * 判断 referrer 是否为可信父页面：同主机（忽略协议/端口，含父子域），
 * 或 origin 在 TRUSTED_PARENT_ORIGINS 白名单内。referrer 缺失/非法按不可信处理。
 */
function isTrustedReferrer(referrer: string): boolean {
  if (!referrer) {
    return false;
  }
  let refOrigin = '';
  let refHost = '';
  try {
    const refUrl = new URL(referrer);
    refOrigin = refUrl.origin;
    refHost = refUrl.hostname;
  } catch (e) {
    return false;
  }
  if (TRUSTED_PARENT_ORIGINS.includes(refOrigin)) {
    return true;
  }
  const host = location.hostname;
  return (
    refHost === host || refHost.endsWith(`.${host}`) || host.endsWith(`.${refHost}`)
  );
}

/**
 * 仅当页面由可信父平台 iframe 嵌入时才允许消费 Auth。
 * 直接打开带 token 的链接（window.self === window.top）一律拒绝。
 */
function isTrustedEmbedding(): boolean {
  if (window.self === window.top) {
    return false;
  }
  return isTrustedReferrer(document.referrer);
}

/**
 * 将 token 原样写入 Access-Token Cookie。
 *
 * - 不做 encodeURIComponent：后端 cookie.getValue() 不做 URL 解码，
 *   编码会导致含 '+'/'/' 的 token 校验失败
 * - 会话级（不设 expires）：iframe 每次挂载都会重带 Auth，且应用内
 *   reload 不丢失认证
 * - https 下补 SameSite=None; Secure; Partitioned（CHIPS）：跨站 iframe
 *   必需，Partitioned 是 Chrome 三方 Cookie 封禁下的回退；http 下不加
 *   SameSite（浏览器在非安全上下文会拒绝 SameSite=None，也无法设置
 *   需 Secure 的 Partitioned）
 * - 残余限制：Safari 不支持 CHIPS 且会拦截 iframe 内 Cookie 写入，
 *   此时回读校验会输出 warn（此类环境需 Storage Access API，超出本工具范围）
 */
export function writeSsoCookie(token: string): void {
  if (/[\s;,"]/.test(token)) {
    console.warn('[SSO] Access-Token contains illegal cookie characters, write may fail');
  }
  const attrs = ['path=/'];
  if (location.protocol === 'https:') {
    attrs.push('SameSite=None', 'Secure', 'Partitioned');
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
 * 组合入口：解析 Auth（hash 主通道 + search 防御）→ 安全门控 → 剥除 URL →
 * 写 Cookie。
 *
 * 顺序保证：URL 剥除先于 Cookie 写入，且二者各自独立兜底——即使 Cookie
 * 写入抛异常（沙箱 iframe/超长 token），Auth 也已从地址栏与历史栈移除。
 *
 * @returns 提取到的 token；URL 无 Auth 参数或安全门控拒绝时返回 null
 *          （此时不写 Cookie、不改 URL、无任何副作用）
 */
export function consumeSsoAuthFromUrl(): string | null {
  try {
    // ---- 纯解析阶段（无副作用）----
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

    // search 侧防御性检查：若 Auth 残留在 search，后续 pushState 会把它
    // 搬进 hash（reArrangeSearchParam 白名单之外），必须一并清掉
    const search = window.location.search;
    const searchQuery = search.startsWith('?') ? search.slice(1) : '';

    const hashRes = extractAuthParam(hashQuery);
    const searchRes = extractAuthParam(searchQuery);
    const hashChanged = hashRes.query !== hashQuery;
    const searchChanged = searchRes.query !== searchQuery;
    if (!hashChanged && !searchChanged) {
      return null;
    }
    // hash 为主通道，search 兜底
    const token = hashRes.token !== null ? hashRes.token : searchRes.token;

    // ---- 安全门控：非可信 iframe 嵌入时拒绝消费，且对 URL 零改动 ----
    if (!isTrustedEmbedding()) {
      console.warn(
        '[SSO] Auth param ignored: page is not embedded by a trusted parent (login-CSRF protection)'
      );
      return null;
    }

    // ---- 剥除阶段：凭证出地址栏/历史栈，独立兜底，不因后续失败而跳过 ----
    try {
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
    } catch (e) {
      console.warn('[SSO] failed to strip Auth param from url', e);
    }

    // ---- 写入阶段：独立兜底，失败不影响已完成的剥除 ----
    if (token) {
      try {
        writeSsoCookie(token);
      } catch (e) {
        console.warn('[SSO] failed to write Access-Token cookie', e);
      }
    }
    return token;
  } catch (e) {
    console.warn('[SSO] failed to consume Auth param from url', e);
    return null;
  }
}
