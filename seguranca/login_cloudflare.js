// Login no servidor para sites estáticos na Cloudflare Pages (modo avançado, _worker.js).
// Sem sessão válida, a página com os dados nunca é enviada ao navegador.
// Variáveis do projeto: USERNAME, PASSWORD, SESSION_SECRET (obrigatórias) e TITULO, LIBERAR (opcionais).
// LIBERAR = "chave=valor" é gravado no sessionStorage da página servida, para desligar uma tela de senha antiga
// que exista dentro do HTML original.
const COOKIE = "sessao_protegida";
const MAX_AGE = 60 * 60 * 24 * 30;
const enc = new TextEncoder();

async function hmac(secret, msg) {
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(msg));
  return [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, "0")).join("");
}
function igual(a, b) {
  const x = enc.encode(String(a)), y = enc.encode(String(b));
  let d = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) d |= (x[i] || 0) ^ (y[i] || 0);
  return d === 0;
}
async function criarSessao(user, secret) {
  const payload = `${user}.${Date.now()}`;
  return `${payload}.${await hmac(secret, payload)}`;
}
async function sessaoValida(cookie, secret) {
  if (!cookie) return false;
  const p = cookie.split(".");
  if (p.length < 3) return false;
  const sig = p.pop(), ts = p[p.length - 1];
  if (!igual(sig, await hmac(secret, p.join(".")))) return false;
  return (Date.now() - parseInt(ts, 10)) / 1000 <= MAX_AGE;
}
function cookies(req) {
  const out = {};
  (req.headers.get("cookie") || "").split(";").forEach(c => { const [k, ...v] = c.trim().split("="); if (k) out[k] = v.join("="); });
  return out;
}
const SEG = { "x-robots-tag": "noindex, nofollow", "referrer-policy": "no-referrer", "x-content-type-options": "nosniff", "x-frame-options": "DENY" };
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function telaLogin(titulo, erro) {
  return `<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>${esc(titulo)}</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0f1418;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:#f2f2f2;padding:16px}
form{width:100%;max-width:380px;background:#182027;border:1px solid #2a343c;border-radius:18px;padding:32px 28px}h1{font-size:20px;margin:0 0 6px}p{margin:0 0 22px;color:#a9b4bb;font-size:14px}
label{display:block;font-size:13px;color:#a9b4bb;margin:12px 0 6px}input{width:100%;padding:12px 14px;border-radius:10px;border:1px solid #33404a;background:#0f1418;color:#f2f2f2;font-size:16px}
button{width:100%;margin-top:18px;padding:12px;border:0;border-radius:10px;background:#f2f2f2;color:#0f1418;font-size:15px;font-weight:600;cursor:pointer}.erro{margin-top:12px;color:#ff8a80;font-size:14px}
</style></head><body><form method="post" action="/login"><h1>${esc(titulo)}</h1><p>Acesso restrito.</p>
<label for="u">Usuário</label><input id="u" name="user" autocomplete="username" required autofocus>
<label for="s">Senha</label><input id="s" name="pass" type="password" autocomplete="current-password" required>
<button type="submit">Entrar</button>${erro ? '<div class="erro" role="alert">Usuário ou senha incorretos. Tente novamente.</div>' : ""}</form></body></html>`;
}
function html(body, status) { return new Response(body, { status, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store", ...SEG } }); }

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const { USERNAME, PASSWORD, SESSION_SECRET } = env;
    const titulo = env.TITULO || "Acesso restrito";
    if (url.pathname === "/robots.txt") return new Response("User-agent: *\nDisallow: /\n", { headers: { "content-type": "text/plain; charset=utf-8" } });
    if (!USERNAME || !PASSWORD || !SESSION_SECRET) return new Response("Acesso não configurado.", { status: 503, headers: { "content-type": "text/plain; charset=utf-8", ...SEG } });
    if (url.pathname === "/login" && request.method === "POST") {
      const f = await request.formData();
      const okU = igual((f.get("user") || "").trim().toLowerCase(), USERNAME.toLowerCase());
      const okP = igual(f.get("pass") || "", PASSWORD);
      if (okU && okP) {
        const s = await criarSessao(USERNAME, SESSION_SECRET);
        return new Response(null, { status: 302, headers: { "location": "/", "set-cookie": `${COOKIE}=${s}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=${MAX_AGE}`, ...SEG } });
      }
      return html(telaLogin(titulo, true), 401);
    }
    if (url.pathname === "/logout") return new Response(null, { status: 302, headers: { "location": "/", "set-cookie": `${COOKIE}=; Path=/; Max-Age=0` } });
    if (!(await sessaoValida(cookies(request)[COOKIE], SESSION_SECRET))) return html(telaLogin(titulo, false), 200);
    const resp = await env.ASSETS.fetch(request);
    const tipo = resp.headers.get("content-type") || "";
    if (!tipo.includes("text/html")) return resp;
    let corpo = await resp.text();
    if (env.LIBERAR && env.LIBERAR.includes("=")) {
      const [k, v] = env.LIBERAR.split("=");
      corpo = corpo.replace(/<head[^>]*>/i, m => `${m}<script>try{sessionStorage.setItem(${JSON.stringify(k)},${JSON.stringify(v)})}catch(e){}</script>`);
    }
    const h = new Headers(resp.headers);
    h.set("cache-control", "no-store");
    for (const [k, v] of Object.entries(SEG)) h.set(k, v);
    return new Response(corpo, { status: resp.status, headers: h });
  }
};
