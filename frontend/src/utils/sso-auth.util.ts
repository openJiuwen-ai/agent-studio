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
 * 2. 父页面来源可信：document.referrer 的 origin 在 TRUSTED_PARENT_ORIGINS
 *    白名单内（精确 origin 匹配，含协议与端口）。不做任何隐式放行——
 *    同源也不例外（同源页面上若存在攻击者可影响的内容，同样构成注入
 *    面；且同源脚本本可直接写 Cookie，隐式放行不增加安全只增加模糊性）。
 *    **部署要求：必须将父平台完整 origin（含协议与端口）配置进
 *    TRUSTED_PARENT_ORIGINS，否则 SSO 不生效**；
 * 3. referrer 缺失按不可信处理（fail-closed）。父页面不得设置
 *    Referrer-Policy: no-referrer（浏览器默认策略不受影响）。
 *
 * token 编码契约：token 须以 URL 原样（未 percent-encoding）拼入 src，
 * 且不得包含 '&'（URL 按 & 切分查询串，token 会被截断——检测到疑似截断
 * 时输出告警）。若父平台对 token 做了 percent-encoding（如 + → %2B、
 * = → %3D），写入 Cookie 的值与后端原始 token 不一致将导致认证失败——
 * 检测到疑似编码值时输出告警（无法安全自动解码：无法区分编码值与本身
 * 含 % 的原始 token）。
 *
 * CSRF 要求：SameSite=None 使该 Cookie 随所有发往 console 源的跨站请求
 * 自动携带，而后端安全链当前禁用了 CSRF 且无 Origin/Referer 校验
 * （OAuth2SecurityConfig csrf.disable）——任何第三方站点可借已登录用户
 * 身份发起 console 请求。后端必须为 SSO 开启场景补充 Origin 白名单校验
 * （建议在 SsoAuthenticationFilter 内实现），本前端无法自愈此风险。
 *
 * 顺序保证：先写入并回读校验 Cookie 值，校验通过后才剥除 URL。写入失败
 * 时保留 Auth 供重试，但同会话内失败达到上限（含首次共
 * MAX_WRITE_FAILURES_BEFORE_CLEANUP 次）后改为强制清理 URL，防止凭据在
 * 持续被拦截的环境（Safari/ITP、三方 Cookie 策略、HttpOnly 冲突）中
 * 无限期驻留地址栏与历史记录。
 */

/** 与后端 auth.sso.header 默认配置（application-manager.yml）对齐的 Cookie 名 */
export const SSO_COOKIE_NAME = 'Access-Token';

/** iframe src 中传递 token 的参数名（契约约定，大小写敏感） */
export const AUTH_PARAM_NAME = 'Auth';

/**
 * 可信父平台 origin 白名单（完整 origin，含协议+主机+端口，如
 * http://122.219.72.238:8081）。**唯一放行依据，无任何隐式信任**——
 * 同源/同主机/子域/跨域一律须在此显式配置。
 */
export const TRUSTED_PARENT_ORIGINS: string[] = [];

/**
 * 同一会话内写入失败的保留上限（含首次）：达到后不再保留 URL 中的 Auth
 * 供重试，而是强制清理以限制凭据暴露面。
 */
const MAX_WRITE_FAILURES_BEFORE_CLEANUP = 2;

/** 同一会话内的写入失败计数（写入成功后归零；token 变更时对新 token 重新计数） */
let writeFailureCount = 0;

/** 上一次写入失败的 token：父平台换发新 token 时重置计数，给予完整重试预算 */
let lastFailedToken: string | null = null;

/**
 * 原生 history.replaceState 的模块加载期引用。utils.ts 的
 * initHistoryInterceptor 会在应用初始化时包装 replaceState：对非 '#' 开头
 * 的 URL 执行无 base 的 new URL 解析（相对 URL 会抛 TypeError，导致剥除
 * 静默失败），其参数搬移与重编码也会破坏本工具的字节级 URL 重建。
 * 本模块加载早于拦截器安装，在此绑定原生实现，使启动路径与
 * hashchange（运行期换 token）路径的剥除行为一致。拦截器包装后派发的
 * 自定义事件全工程无监听方，绕过无副作用。
 */
const nativeReplaceState: typeof history.replaceState = history.replaceState.bind(history);

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
  const segs = query.split('&');
  for (let i = 0; i < segs.length; i++) {
    const seg = segs[i];
    if (seg.startsWith(`${AUTH_PARAM_NAME}=`)) {
      const value = seg.slice(AUTH_PARAM_NAME.length + 1);
      // 取第一个非空值；空值 Auth= 同样从 URL 中剥除
      if (value && token === null) {
        token = value;
        // 启发式检测：Auth 段后紧跟无 '=' 的裸段，疑似 token 内含未编码的 &
        // 被切分截断（截断值会写入 Cookie 并在后端校验失败，无前端信号）
        const next = segs[i + 1];
        if (next !== undefined && next !== '' && !next.includes('=')) {
          console.warn(
            '[SSO] Auth value may be truncated by an unencoded & in the token; the contract requires URL-safe tokens'
          );
        }
      }
    } else {
      // 含空段在内的其余段逐段保留，保证剥除 Auth 之外零改动
      kept.push(seg);
    }
  }
  return { token, query: kept.join('&') };
}

/**
 * 判断 referrer 是否为可信父页面：origin 在 TRUSTED_PARENT_ORIGINS 白名单
 * 内（精确匹配，含协议与端口）。referrer 缺失/非法按不可信处理。
 * 不做同源/同主机隐式放行：同源页面上攻击者可影响的内容同样构成注入面，
 * 且同源脚本本可直接写 Cookie，隐式放行只增加规则模糊性。
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
  return TRUSTED_PARENT_ORIGINS.includes(refOrigin);
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
 * 回读校验 Access-Token Cookie 是否为生效值。
 * document.cookie 与请求 Cookie 头均按 path 长度降序列出同名 Cookie
 * （RFC 6265 §5.4）：若存在更具体 path 的同名旧 Cookie，后端优先读到
 * 旧值（遮蔽本工具写入的 path=/ 值）。
 *
 * @returns 'ok' 首条同名 Cookie 即目标值（后端读到正确 token）；
 *          'shadowed' 目标值存在但被更具体 path 的同名旧 Cookie 遮蔽
 *          （后端将读到旧值，需清理旧 Cookie）；
 *          'missing' 无任何同名 Cookie（写入被拦截或值损坏）
 */
function verifySsoCookieValue(token: string): 'ok' | 'shadowed' | 'missing' {
  const prefix = `${SSO_COOKIE_NAME}=`;
  let sawOtherValue = false;
  for (const item of document.cookie.split('; ')) {
    if (!item.startsWith(prefix)) {
      continue;
    }
    if (item.slice(prefix.length) === token) {
      return sawOtherValue ? 'shadowed' : 'ok';
    }
    sawOtherValue = true;
  }
  return 'missing';
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
  } else {
    // 非安全上下文：无法设置 Secure（连同 SameSite=None/Partitioned 一并不可用），
    // 且未显式 SameSite 的 Cookie 默认按 Lax 处理——跨站 iframe 的请求不会
    // 携带，http 部署仅同站点拓扑可用（consume 处会输出拓扑告警）。
    // 凭证将以非 Secure Cookie 明文暴露——但 token 本就以明文 URL 传输，
    // 拒绝写入并不能保护它，故选择强告警而非拒绝；根治手段是 https 部署。
    console.warn(
      '[SSO] Access-Token cookie is being written WITHOUT Secure over insecure http: ' +
        'the credential is exposed in plaintext; deploy console over https'
    );
  }
  document.cookie = `${SSO_COOKIE_NAME}=${token}; ${attrs.join('; ')}`;
  // 回读值校验：检出三方 Cookie 策略静默拦截、同名 HttpOnly Cookie 拒绝
  // 覆盖、被更具体 path 的同名旧 Cookie 遮蔽、值截断/损坏等所有
  // "写入了但不可用"的情形
  const verifyResult = verifySsoCookieValue(token);
  if (verifyResult !== 'ok') {
    console.warn(
      verifyResult === 'shadowed'
        ? '[SSO] Access-Token cookie is shadowed by a stale same-name cookie with a ' +
          'more specific path; clean it before retry'
        : '[SSO] Access-Token cookie verification failed after write, possibly blocked by cookie policy'
    );
    return false;
  }
  return true;
}

/**
 * 组合入口：解析 Auth（hash 主通道 + search 防御）→ 安全门控 → 写入并校验
 * Cookie → 校验通过后剥除 URL。
 *
 * 失败语义：写入被拒绝/拦截时保留 URL 中的 Auth 供重试（页面 reload 或父
 * 平台变更 hash 触发的再次消费均可整体重试）；同会话内失败达到上限
 * （MAX_WRITE_FAILURES_BEFORE_CLEANUP）后强制清理 URL 以限制凭据暴露。
 * 门控拒绝时对 URL 零改动。
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

    // ---- http + 跨站 iframe 拓扑告警：未显式 SameSite 的 Cookie 默认按
    // Lax 处理，跨站子资源请求不会携带——该拓扑下 SSO 必然失败 ----
    if (location.protocol !== 'https:') {
      try {
        const refHost = new URL(document.referrer).hostname;
        const sameSite =
          refHost === location.hostname ||
          refHost.endsWith(`.${location.hostname}`) ||
          location.hostname.endsWith(`.${refHost}`);
        if (!sameSite) {
          console.warn(
            '[SSO] http deployment with cross-site iframe: the default-Lax cookie will ' +
              'not be sent on cross-site requests, SSO cannot work; use https or same-site topology'
          );
        }
      } catch (e) {
        // referrer 已在门控校验过，解析异常不在此处理
      }
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
      nativeReplaceState(
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
      if (token !== lastFailedToken) {
        // 父平台已换发新 token：重置计数，让新 token 获得完整重试预算
        writeFailureCount = 0;
        lastFailedToken = token;
      }
      writeFailureCount++;
      if (writeFailureCount >= MAX_WRITE_FAILURES_BEFORE_CLEANUP) {
        // 持续失败（Safari/ITP、三方 Cookie 策略、HttpOnly 冲突等）：放弃重试
        // 并强制清理，防止凭据无限期驻留地址栏与历史记录
        console.warn(
          '[SSO] Access-Token write failed repeatedly, strip Auth from url to limit credential exposure'
        );
        try {
          stripAuthFromUrl();
        } catch (e) {
          console.warn('[SSO] failed to strip Auth param from url', e);
        }
        return null;
      }
      // 首次失败：保留 URL 中的 Auth，reload 或父平台 hash 变更可整体重试
      console.warn(
        '[SSO] Access-Token cookie not landed, keep Auth in url for reload retry'
      );
      return null;
    }
    writeFailureCount = 0;
    lastFailedToken = null;

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
