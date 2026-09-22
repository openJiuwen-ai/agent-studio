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
 * 时，以下任一条件不满足即拒绝消费——不写 Cookie，但仍从 URL 清理 Auth
 * 凭证，防其驻留地址栏/历史栈或被 reArrangeSearchParam 搬移进 hash）：
 * 1. 仅当页面处于 iframe 嵌入中（window.self !== window.top）才消费；
 * 2. 父页面来源可信：document.referrer 的 origin 在 TRUSTED_PARENT_ORIGINS
 *    白名单内（精确 origin 匹配，含协议与端口）。不做任何隐式放行——
 *    同源也不例外（同源页面上若存在攻击者可影响的内容，同样构成注入
 *    面；且同源脚本本可直接写 Cookie，隐式放行不增加安全只增加模糊性）。
 *    **部署要求：必须将父平台完整 origin（含协议与端口）配置进
 *    TRUSTED_PARENT_ORIGINS（支持 index.html 运行期注入免构建，见其
 *    注释），否则 SSO 不生效**；
 * 3. referrer 缺失按不可信处理（fail-closed）。父页面不得设置
 *    Referrer-Policy: no-referrer（浏览器默认策略不受影响）。
 *
 * token 编码契约：token 须以 URL 原样（未 percent-encoding）拼入 src，
 * 且不得包含 '&'（URL 按 & 切分查询串，token 会被截断）。Auth 段后紧跟
 * 无 '=' 的裸段时输出疑似截断告警并仍消费首段——该特征与合法的布尔型
 * 参数（如 &flag）不可区分，为不破坏契约合规的 URL 只能告警不强拦；
 * 截断值会在后端校验失败，以告警为排障入口。若父平台对 token 做了
 * percent-encoding（如 + → %2B、= → %3D），写入 Cookie 的值与后端原始
 * token 不一致将导致认证失败——检测到疑似编码值时输出告警（无法安全
 * 自动解码：无法区分编码值与本身含 % 的原始 token）。
 *
 * CSRF 要求：SameSite=None 会使凭据 Cookie 随跨站请求自动携带，而后端
 * 安全链当前禁用了 CSRF 且无 Origin/Referer 校验（OAuth2SecurityConfig
 * csrf.disable）。为避免本前端单独合入即引入跨站请求伪造暴露面：
 * 1. https 且父页面与 console 同站点时不写 SameSite（Lax 默认即可携带，
 *    不扩大跨站暴露面）；
 * 2. 仅 https 且跨站点父页面（真正需要 None 的拓扑）才写
 *    SameSite=None; Secure; Partitioned，且必须先由部署方在后端 Origin
 *    校验上线后设置 window.__SSO_CSRF_PROTECTION_CONFIRMED__ = true
 *    （index.html 注入），否则拒绝写入该 Cookie。
 * 站点关系按 SameSite 语义近似判定（scheme 一致 + 注册域相同，公共后缀
 * 表非全量）：误判只影响可用性不影响安全性——同站误判为跨站会多要求
 * 一次 CSRF 确认，跨站误判为同站写入的 Lax Cookie 不会被跨站携带。
 *
 * 顺序保证：先写入并回读校验 Cookie 值，校验通过后才剥除 URL。写入失败
 * 时保留 Auth 供重试，失败计数经 sessionStorage 跨 reload 累计（存储
 * 被禁用的环境回退会话内计数），达到上限（含首次共
 * MAX_WRITE_FAILURES_BEFORE_CLEANUP 次）后强制清理 URL，防止凭据在
 * 持续被拦截的环境（Safari/ITP、三方 Cookie 策略、HttpOnly 冲突）中
 * 无限期驻留地址栏与历史记录。
 */

/** 与后端 auth.sso.header 默认配置（application-manager.yml）对齐的 Cookie 名 */
export const SSO_COOKIE_NAME = 'Access-Token';

/** iframe src 中传递 token 的参数名（契约约定，大小写敏感） */
export const AUTH_PARAM_NAME = 'Auth';

/** 运行期配置注入键：index.html 内联脚本可免构建配置白名单 */
const RUNTIME_ORIGINS_KEY = '__SSO_TRUSTED_PARENT_ORIGINS__';

/** CSRF 确认注入键：后端 Origin 校验上线后由部署方置 true，方启用跨站 Cookie */
const CSRF_ACK_KEY = '__SSO_CSRF_PROTECTION_CONFIRMED__';

/** 写入失败计数的持久化键（跨 reload 累计；存储不可用时回退会话内计数） */
const WRITE_FAILURE_STORAGE_KEY = '__SSO_WRITE_FAILURE__';

/** 读取 index.html 注入的运行期可信 origin（非数组/非字符串项忽略） */
function readRuntimeOrigins(): string[] {
  const injected = (window as any)[RUNTIME_ORIGINS_KEY];
  if (!Array.isArray(injected)) {
    return [];
  }
  return injected.filter((origin): origin is string => typeof origin === 'string');
}

/**
 * 可信父平台 origin 白名单（完整 origin，含协议+主机+端口，如
 * http://122.219.72.238:8081）。**唯一放行依据，无任何隐式信任**——
 * 同源/同主机/子域/跨域一律须显式配置。
 *
 * 配置入口（二选一）：
 * 1. 运行期注入（免构建）：index.html 内联脚本
 *    `window.__SSO_TRUSTED_PARENT_ORIGINS__ = ['http://父平台:端口'];`
 *    （须置于 bundle 脚本之前，本模块加载时读取）
 * 2. 构建期配置：直接修改本数组后重新构建
 */
export const TRUSTED_PARENT_ORIGINS: string[] = [...readRuntimeOrigins()];

/**
 * 同一会话内写入失败的保留上限（含首次）：达到后不再保留 URL 中的 Auth
 * 供重试，而是强制清理以限制凭据暴露面。
 */
const MAX_WRITE_FAILURES_BEFORE_CLEANUP = 2;

/** 同一会话内的写入失败计数（写入成功后归零；token 变更时对新 token 重新计数） */
let writeFailureCount = 0;

/** 上一次写入失败的 token：父平台换发新 token 时重置计数，给予完整重试预算 */
let lastFailedToken: string | null = null;

/** 跨 reload 的失败计数持久化状态 */
interface PersistedWriteFailure {
  token: string;
  count: number;
}

/** 读取持久化失败计数（存储被禁用/解析失败时返回 null，回退会话内计数） */
function readPersistedWriteFailure(): PersistedWriteFailure | null {
  try {
    const raw = sessionStorage.getItem(WRITE_FAILURE_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (
      parsed &&
      typeof parsed.token === 'string' &&
      typeof parsed.count === 'number'
    ) {
      return parsed;
    }
    return null;
  } catch (e) {
    // 三方 iframe 内 sessionStorage 可能被分区/禁用，访问即抛错——回退内存计数
    return null;
  }
}

/** 写入/清除持久化失败计数（存储不可用时静默忽略） */
function writePersistedWriteFailure(state: PersistedWriteFailure | null): void {
  try {
    if (state === null) {
      sessionStorage.removeItem(WRITE_FAILURE_STORAGE_KEY);
    } else {
      sessionStorage.setItem(WRITE_FAILURE_STORAGE_KEY, JSON.stringify(state));
    }
  } catch (e) {
    // 存储不可用时忽略，仅影响跨 reload 累计
  }
}

/**
 * 原生 history.replaceState 的模块加载期引用。utils.ts 的
 * initHistoryInterceptor 会在应用初始化时包装 replaceState：对非 '#' 开头
 * 的 URL 执行无 base 的 new URL 解析（相对 URL 会抛 TypeError，导致剥除
 * 静默失败），其参数搬移与重编码也会破坏本工具的字节级 URL 重建。
 * 本模块加载早于拦截器安装，在此绑定原生实现，使启动路径与
 * hashchange（运行期换 token）路径的剥除行为一致。拦截器包装后派发的
 * 自定义事件全工程无监听方，绕过无副作用。
 *
 * 已知取舍（绕过包装器的两方面差异）：
 * 1. search 中剩余的非白名单参数不会被本工具提前搬进 hash——应用侧
 *    既有规则会在下一次经过包装器的 pushState/replaceState 时照常搬移，
 *    本工具只是不做提前归一化，不改变最终行为；
 * 2. 包装器派发的 'replaceState' 自定义事件被跳过——当前无监听方；
 *    未来若有模块依赖该事件同步状态，需重新评估此处绕过。
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
 * @returns token 为 null 表示未找到非空值；query 为剥除 Auth 后的剩余串；
 *          suspectTruncated 为 true 表示 Auth 段后紧跟无 '=' 的裸段，
 *          疑似 token 内含未编码的 & 被切分截断（调用方应放弃消费）
 */
export function extractAuthParam(query: string): {
  token: string | null;
  query: string;
  suspectTruncated: boolean;
} {
  const kept: string[] = [];
  let token: string | null = null;
  let suspectTruncated = false;
  const segs = query.split('&');
  for (let i = 0; i < segs.length; i++) {
    const seg = segs[i];
    if (seg.startsWith(`${AUTH_PARAM_NAME}=`)) {
      const value = seg.slice(AUTH_PARAM_NAME.length + 1);
      // 取第一个非空值；空值 Auth= 同样从 URL 中剥除
      if (value && token === null) {
        token = value;
        // 检测：Auth 段后紧跟无 '=' 的裸段，疑似 token 内含未编码的 &
        // 被切分截断（截断值写入 Cookie 只会在后端静默校验失败）
        const next = segs[i + 1];
        if (next !== undefined && next !== '' && !next.includes('=')) {
          suspectTruncated = true;
        }
      }
    } else {
      // 含空段在内的其余段逐段保留，保证剥除 Auth 之外零改动
      kept.push(seg);
    }
  }
  return { token, query: kept.join('&'), suspectTruncated };
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

/** 常见二级公共后缀（近似 PSL 的非全量子集，覆盖主流部署） */
const TWO_PART_PUBLIC_SUFFIXES = new Set([
  'co.uk', 'org.uk', 'ac.uk', 'gov.uk',
  'com.cn', 'net.cn', 'org.cn', 'gov.cn', 'edu.cn',
  'com.au', 'net.au', 'org.au',
  'co.jp', 'or.jp', 'ne.jp',
  'co.kr', 'co.nz', 'com.br', 'com.mx', 'com.tr',
]);

/**
 * 近似计算注册域（eTLD+1）：IP 地址整串为站点单位；末两段命中二级公共
 * 后缀表时取末三段，否则取末两段。公共后缀表非全量，未知后缀场景的
 * 误差只影响可用性不影响安全性（Lax Cookie 不会跨站携带）。
 */
function registrableDomainOf(hostname: string): string {
  const host = hostname.toLowerCase();
  if (host.includes(':')) {
    return host; // IPv6 整串
  }
  const labels = host.split('.');
  if (labels.every((label) => /^\d+$/.test(label))) {
    return host; // IPv4 整串
  }
  if (labels.length <= 2) {
    return host;
  }
  const lastTwo = labels.slice(-2).join('.');
  if (TWO_PART_PUBLIC_SUFFIXES.has(lastTwo)) {
    return labels.slice(-3).join('.');
  }
  return lastTwo;
}

/**
 * SameSite 语义的近似同站判定：scheme 一致（schemeful same-site，http 与
 * https 互为跨站）且注册域相同。修复此前 hostname 前后缀比较对兄弟子域
 * （a.example.com vs b.example.com，共享注册域属同站）与协议差异的误判。
 */
function isSameSite(refUrl: URL): boolean {
  if (refUrl.protocol !== location.protocol) {
    return false;
  }
  return registrableDomainOf(refUrl.hostname) === registrableDomainOf(location.hostname);
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
 * - https 且跨站点父页面（crossSite=true）时写 SameSite=None; Secure;
 *   Partitioned（CHIPS，Chrome 三方 Cookie 封禁的回退），且须部署方先
 *   置 window.__SSO_CSRF_PROTECTION_CONFIRMED__ = true 确认后端 Origin
 *   校验已上线，否则拒绝写入；https 同站点父页面不写 SameSite（Lax 默认
 *   即可携带，不扩大跨站暴露面）但加 Secure（防同域名 http 明文携带）；
 *   http + 跨站点父页面拒绝写入（Lax Cookie 必然不被携带，走失败路径
 *   保留 Auth 供重试）；http 同站点不加 SameSite（非安全上下文无法设置）
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
export function writeSsoCookie(token: string, crossSite: boolean): boolean {
  if (ILLEGAL_COOKIE_CHARS.test(token)) {
    console.warn('[SSO] Access-Token contains illegal cookie characters, reject writing');
    return false;
  }
  const attrs = ['path=/'];
  if (location.protocol === 'https:') {
    if (crossSite) {
      // 跨站点父页面必须 SameSite=None 才能携带，但 None 会把凭据暴露给
      // 任意跨站请求（后端当前 csrf.disable 无 Origin 校验）——必须由部署方
      // 在后端 Origin 校验上线后显式确认，否则拒绝写入（防本前端单独合入
      // 即引入 CSRF 暴露面）
      if ((window as any)[CSRF_ACK_KEY] !== true) {
        console.warn(
          '[SSO] cross-site https cookie (SameSite=None) refused: backend Origin/CSRF ' +
            'validation not confirmed; set window.__SSO_CSRF_PROTECTION_CONFIRMED__ = true ' +
            'after deploying backend Origin checks'
        );
        return false;
      }
      attrs.push('SameSite=None', 'Secure', 'Partitioned');
    } else {
      // 同站点父页面：Lax 默认即可携带，不写 SameSite（不扩大跨站暴露面）；
      // 仍加 Secure——防止同域名 http 服务把该会话 Cookie 明文携带出去
      attrs.push('Secure');
    }
  } else if (crossSite) {
    // http + 跨站点：默认 Lax 的 Cookie 不会被跨站请求携带，写入了也必然
    // 不可用——拒绝写入并走失败路径（保留 URL 中的 Auth 供拓扑修正后
    // 重试），与拓扑告警语义一致，避免"回读成功即剥除"造成的静默失败
    console.warn(
      '[SSO] http deployment with cross-site iframe: the default-Lax cookie will ' +
        'not be sent on cross-site requests, SSO cannot work; use https or same-site topology'
    );
    return false;
  } else {
    // http 同站点：无法设置 Secure（连同 SameSite=None/Partitioned 一并不可用）。
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
 * 平台变更 hash 触发的再次消费均可整体重试）；失败计数在 sessionStorage
 * 持久化以跨 reload 累计（存储被禁用的环境回退会话内计数），达到上限
 * （MAX_WRITE_FAILURES_BEFORE_CLEANUP）后强制清理 URL 以限制凭据暴露。
 * 门控拒绝时清理 URL 中的 Auth（凭证防驻留）；疑似 token 截断（Auth 段后
 * 跟无 '=' 的裸段，与布尔型参数不可区分）仅告警不强拦。
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

    // ---- 剥除动作（门控拒绝与写入成功两处复用；原生引用 + 自身异常不外抛）----
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

    // ---- 契约观察：Auth 段后紧跟无 '=' 的裸段——可能是 token 含未编码 &
    // 被截断，也可能是合法的布尔型参数（如 &flag），二者不可区分；
    // 为不破坏契约合规的 URL，仅告警不强拦（截断值会在后端校验失败）----
    const suspectTruncated =
      hashRes.suspectTruncated || searchRes.suspectTruncated;
    if (suspectTruncated) {
      console.warn(
        '[SSO] Auth value may be truncated by an unencoded & (or followed by a value-less ' +
          'flag param); consuming and stripping only the first segment (truncated tokens may ' +
          'leave a residual fragment in the url), verify the token on the parent side'
      );
    }

    // ---- 安全门控：非可信 iframe 嵌入时拒绝消费，但仍清理 URL 中的凭证
    // （疑似截断时保持 URL 不变，与截断观察契约一致，不做部分清理）----
    if (!isTrustedEmbedding()) {
      console.warn(
        '[SSO] Auth param ignored: page is not embedded by a trusted parent (login-CSRF protection)'
      );
      if (!suspectTruncated) {
        try {
          stripAuthFromUrl();
        } catch (e) {
          console.warn('[SSO] failed to strip Auth param from url', e);
        }
      }
      return null;
    }

    // ---- 父页面站点关系（供 Cookie 属性决策；按 SameSite 语义近似判定：
    // scheme 一致 + 注册域相同，见 isSameSite；http+跨站的拒绝在 writeSsoCookie）----
    let crossSiteParent = false;
    try {
      crossSiteParent = !isSameSite(new URL(document.referrer));
    } catch (e) {
      // referrer 已在门控校验过，此处不可达；保守视为同站点
    }

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
      writeOk = writeSsoCookie(token, crossSiteParent);
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
      // 跨 reload 累计：主重试路径是页面 reload（模块计数会重置），
      // 取持久化计数（同 token）与内存计数的大者，防止失败预算无限刷新
      const persisted = readPersistedWriteFailure();
      const persistedCount = persisted && persisted.token === token ? persisted.count : 0;
      writeFailureCount = Math.max(writeFailureCount, persistedCount + 1);
      writePersistedWriteFailure({ token, count: writeFailureCount });
      if (writeFailureCount >= MAX_WRITE_FAILURES_BEFORE_CLEANUP) {
        // 持续失败（Safari/ITP、三方 Cookie 策略、HttpOnly 冲突等）：放弃重试
        // 并强制清理，防止凭据无限期驻留地址栏与历史记录（保留持久化计数，
        // 父平台重发同 token 时立即再次清理）
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
    writePersistedWriteFailure(null);

    // 注：疑似截断时成功路径仍剥除 Auth 段——与门控拒绝分支（未消费任何
    // 内容故整体保持不变）的非对称是有意的：布尔参数场景（Auth=token&flag）
    // 不能让有效凭据驻留 URL；真截断场景残段属已失效凭据的碎片，无认证价值。
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
