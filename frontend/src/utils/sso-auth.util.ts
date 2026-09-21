/**
 * SSO iframe 嵌入场景的 Access-Token 接入工具。
 *
 * 三方平台前端以 iframe 嵌入 console，并把认证 token 以 `Auth` 参数拼在
 * iframe src 的 hash 查询串里（如 `#/home/.../flow/?id=xx&Auth=<token>`）。
 * 本工具在应用启动最早期（resetUserData 顶部、首个 HTTP 请求 getHealth 之前）
 * 执行：解析 Auth → 写入 Access-Token Cookie（后端 SsoAuthenticationFilter 按
 * auth.sso.header 配置从同名 Cookie 提取，默认名即 Access-Token）→ 写入校验
 * 通过后从 URL 中剥除该参数（凭证不得留在地址栏与历史栈）。
 *
 * 安全门控（防登录 CSRF / 会话固定：诱导用户打开携带攻击者 token 的链接
 * 时，以下任一条件不满足即拒绝消费，且对 URL 零改动）：
 * 1. 仅当页面处于 iframe 嵌入中（window.self !== window.top）才消费；
 * 2. 父页面来源可信：document.referrer 与 console 完全同源（origin 精确
 *    一致，含协议与端口），或其 origin 在 TRUSTED_PARENT_ORIGINS 白名单内。
 *    同主机不同端口/协议不构成可信边界（Cookie 按域名而非端口共享）。
 *    **部署要求：父平台与 console 非同源时，必须将其完整 origin（含协议
 *    与端口）配置进 TRUSTED_PARENT_ORIGINS，否则 SSO 不生效**；
 * 3. referrer 缺失按不可信处理（fail-closed）。父页面不得设置
 *    Referrer-Policy: no-referrer（浏览器默认策略不受影响）。
 *
 * token 编码契约：token 须以 URL 原样（未 percent-encoding）拼入 src。
 * 若父平台对 token 做了 percent-encoding（如 + → %2B、= → %3D），写入
 * Cookie 的值与后端原始 token 不一致将导致认证失败——检测到疑似编码值
 * 时输出告警（无法安全自动解码：无法区分编码值与本身含 % 的原始 token）。
 *
 * 顺序保证：先写入并回读校验 Cookie 值，校验通过后才剥除 URL——写入被
 * 浏览器拦截（三方 Cookie 策略 / 同名 HttpOnly Cookie 冲突 / 非法字符）
 * 时保留 Auth 供 reload 重试，避免"地址栏已清但认证未落盘"的不可重试状态。
 */

/** 与后端 auth.sso.header 默认配置（application-manager.yml）对齐的 Cookie 名 */
export const SSO_COOKIE_NAME = 'Access-Token';

/** iframe src 中传递 token 的参数名（契约约定，大小写敏感） */
export const AUTH_PARAM_NAME = 'Auth';

/**
 * 可信父平台 origin 白名单（完整 origin，含协议+主机+端口，如
 * http://122.219.72.238:8081）。默认仅隐式放行与 console 完全同源的父页面；
 * 其余来源（含同主机不同端口/协议、子域、跨域）必须在此按 origin 精确配置。
 */
export const TRUSTED_PARENT_ORIGINS: string[] = [];

/** RFC 6265 cookie-value 非法字符（空白、双引号、逗号、分号、反斜杠） */
const ILLEGAL_COOKIE_CHARS = /[\s;,"\\]/;

/**
 * 从 query 串（不含前导 '?'）中提取 Auth 参数的原始值，并返回剥除后的剩余串。
 *
 * 使用纯字符串切分而非 URLSearchParams：token 是不透明字符串，
 * URLSearchParams 会把 '+' 解码为空格、'%xx' 解码，静默损坏凭证；
 * 其余参数段按字节原样保留（顺序与空段均不变，如 'a&&b' 剥除 Auth 后
 * 仍是 'a&&b'），避免影响对 URL 做裸正则匹配的消费方（如 http.service
 * 的 peekWorkspaceId），也保证"无 Auth 时 query 串逐字节不变"。
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
    } else {
      // 含空段在内的其余段逐段保留，保证剥除 Auth 之外零改动
      kept.push(seg);
    }
  }
  return { token, query: kept.join('&') };
}

/**
 * 判断 referrer 是否为可信父页面：与 console 完全同源（origin 精确一致，
 * 含协议与端口），或 origin 在 TRUSTED_PARENT_ORIGINS 白名单内（精确
 * 匹配）。referrer 缺失/非法按不可信处理。
 * 同主机不同端口/协议不放行：Cookie 按域名而非端口共享，同主机上的其他
 * 服务不是可信边界。
 */
function isTrustedReferrer(referrer: string): boolean {
  if (!referrer) {
    return false;
  }
  let refOrigin = '';
  try {
    refOrigin = new URL(referrer).origin;
  } catch (e) {
    return false;
  }
  return refOrigin === location.origin || TRUSTED_PARENT_ORIGINS.includes(refOrigin);
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

/** 回读本工具写入的 Cookie 原值（不存在返回 null） */
function readSsoCookieValue(): string | null {
  const prefix = `${SSO_COOKIE_NAME}=`;
  for (const item of document.cookie.split('; ')) {
    if (item.startsWith(prefix)) {
      return item.slice(prefix.length);
    }
  }
  return null;
}

/**
 * 将 token 原样写入 Access-Token Cookie，并回读校验值一致才算成功。
 *
 * - 不做 encodeURIComponent：后端 cookie.getValue() 不做 URL 解码，
 *   编码会导致含 '+'/'/' 的 token 校验失败
 * - 会话级（不设 expires）：iframe 每次挂载都会重带 Auth，且应用内
 *   reload 不丢失认证
 * - https 下补 SameSite=None; Secure; Partitioned（CHIPS）：跨站 iframe
 *   必需，Partitioned 是 Chrome 三方 Cookie 封禁下的回退；http 下不加
 *   SameSite（浏览器在非安全上下文会拒绝 SameSite=None，也无法设置
 *   需 Secure 的 Partitioned）
 * - 含非法 Cookie 字符的 token 直接拒绝写入（写入也会在分号处截断，
 *   残缺 token 只会导致后端校验失败）
 * - 已知限制：JS 无法设置 HttpOnly，本 Cookie 可被页面脚本读取——XSS
 *   暴露面是 URL 传 token 设计的固有代价（token 本就在 URL 中出现过），
 *   缓解为立即剥除 URL + 会话级生命周期；若后端曾下发同名 HttpOnly
 *   Cookie，浏览器会静默拒绝本次 JS 写入，由回读值校验检出并告警
 * - 残余限制：Safari 不支持 CHIPS 且会拦截 iframe 内 Cookie 写入，回读
 *   校验同样会检出并告警（此类环境需 Storage Access API，超出本工具范围）
 *
 * @returns 写入并回读校验通过返回 true；被拒绝/拦截/校验不一致返回 false
 */
export function writeSsoCookie(token: string): boolean {
  if (ILLEGAL_COOKIE_CHARS.test(token)) {
    console.warn('[SSO] Access-Token contains illegal cookie characters, reject writing');
    return false;
  }
  const attrs = ['path=/'];
  if (location.protocol === 'https:') {
    attrs.push('SameSite=None', 'Secure', 'Partitioned');
  }
  document.cookie = `${SSO_COOKIE_NAME}=${token}; ${attrs.join('; ')}`;
  // 回读值校验：检出三方 Cookie 策略静默拦截、同名 HttpOnly Cookie 拒绝
  // 覆盖、值截断/损坏等所有"写入了但不可用"的情形
  if (readSsoCookieValue() !== token) {
    console.warn(
      '[SSO] Access-Token cookie verification failed after write, possibly blocked by cookie policy'
    );
    return false;
  }
  return true;
}

/**
 * 组合入口：解析 Auth（hash 主通道 + search 防御）→ 安全门控 → 写入并校验
 * Cookie → 校验通过后剥除 URL。
 *
 * 失败语义：写入被拒绝/拦截时保留 URL 中的 Auth（页面 reload 可整体重试），
 * 不写 Cookie、不剥除 URL；门控拒绝时对 URL 零改动。
 *
 * @returns 成功消费（Cookie 已落盘校验一致）返回 token；URL 无 Auth 参数、
 *          安全门控拒绝或写入失败时返回 null
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

    // ---- 剥除动作（仅在校验通过的写入之后执行；自身异常不外抛）----
    const stripAuthFromUrl = () => {
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
    };

    // ---- 写入阶段：空值属垃圾参数，直接剥除；非空值须写入校验通过才剥除 ----
    if (!token) {
      try {
        stripAuthFromUrl();
      } catch (e) {
        console.warn('[SSO] failed to strip Auth param from url', e);
      }
      return null;
    }

    // 编码契约检查：疑似 percent-encoding 的 token 与后端原始值不一致会导致
    // 认证失败，此处仅告警不自动解码（无法区分编码值与本身含 % 的原始 token）
    if (/%[0-9A-Fa-f]{2}/.test(token)) {
      console.warn(
        '[SSO] Access-Token appears to be percent-encoded; the contract requires the raw token, authentication may fail'
      );
    }

    let writeOk = false;
    try {
      writeOk = writeSsoCookie(token);
    } catch (e) {
      console.warn('[SSO] failed to write Access-Token cookie', e);
    }
    if (!writeOk) {
      // 保留 URL 中的 Auth：reload 可整体重试，避免"地址栏已清但认证未落盘"
      console.warn(
        '[SSO] Access-Token cookie not landed, keep Auth in url for reload retry'
      );
      return null;
    }

    try {
      stripAuthFromUrl();
    } catch (e) {
      console.warn('[SSO] failed to strip Auth param from url', e);
    }
    return token;
  } catch (e) {
    console.warn('[SSO] failed to consume Auth param from url', e);
    return null;
  }
}
