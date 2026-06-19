// ============================================================
// Havanna Brasil · Social Listening Marca Total
// Cloudflare Pages · advanced mode (_worker.js)
// Tela de login com a logo Havanna + sessao assinada (HMAC).
// Credenciais lidas de variaveis de ambiente, com fallback.
// Produto Nuts & Co · 2026
// ============================================================

const COOKIE = "havanna_mt_sess";
const MAX_AGE = 60 * 60 * 24 * 30; // 30 dias

async function hmac(secret, msg) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(msg));
  return [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, "0")).join("");
}
async function makeSession(user, secret) {
  const ts = Date.now();
  const payload = `${user}.${ts}`;
  return `${payload}.${await hmac(secret, payload)}`;
}
async function verifySession(cookie, secret) {
  if (!cookie) return false;
  const parts = cookie.split(".");
  if (parts.length !== 3) return false;
  const [user, ts, sig] = parts;
  const expected = await hmac(secret, `${user}.${ts}`);
  if (sig !== expected) return false;
  if ((Date.now() - parseInt(ts)) / 1000 > MAX_AGE) return false;
  return true;
}
function parseCookies(req) {
  const out = {};
  (req.headers.get("cookie") || "").split(";").forEach(c => {
    const [k, ...v] = c.trim().split("=");
    if (k) out[k] = v.join("=");
  });
  return out;
}

function loginPage(error) {
  return `<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Havanna · Acesso restrito</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700;800&family=Manrope:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{min-height:100vh;display:grid;place-items:center;font-family:'Manrope',system-ui,sans-serif;color:#F5F0EA;
 background:radial-gradient(700px 360px at 12% 0%,rgba(228,0,43,.30),transparent 60%),radial-gradient(640px 360px at 90% 8%,rgba(255,205,0,.22),transparent 58%),radial-gradient(700px 420px at 60% 120%,rgba(215,150,60,.20),transparent 60%),#09080F;padding:24px}
.card{width:100%;max-width:400px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.13);backdrop-filter:blur(18px);border-radius:22px;padding:38px 34px;box-shadow:0 40px 90px -50px rgba(0,0,0,.85)}
.logo{display:flex;align-items:center;gap:13px;margin-bottom:30px}
.logo .nm{font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;letter-spacing:.18em;font-size:21px}
.logo .sub{font-size:9.5px;letter-spacing:.22em;text-transform:uppercase;color:#A8A1B2;margin-top:5px}
h1{font-family:'Plus Jakarta Sans',sans-serif;font-size:18px;font-weight:700;margin-bottom:6px}
p.desc{font-size:13px;color:#A8A1B2;margin-bottom:24px;line-height:1.5}
label{display:block;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#A8A1B2;font-weight:600;margin:0 0 7px}
input{width:100%;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.14);border-radius:11px;color:#F5F0EA;padding:13px 14px;font-size:14px;font-family:inherit;margin-bottom:16px;color-scheme:dark}
input:focus{outline:none;border-color:#FFCD00}
button{width:100%;border:none;border-radius:11px;padding:14px;font-family:'Plus Jakarta Sans',sans-serif;font-weight:700;font-size:14px;color:#fff;cursor:pointer;background:linear-gradient(92deg,#E4002B,#FF7A1A);transition:.18s;margin-top:4px}
button:hover{transform:translateY(-1px);box-shadow:0 12px 30px -10px rgba(228,0,43,.7)}
.err{background:rgba(255,92,138,.13);border:1px solid rgba(255,92,138,.35);color:#FF9DB8;font-size:12.5px;border-radius:10px;padding:11px 13px;margin-bottom:18px}
.foot{margin-top:24px;text-align:center;font-size:11px;color:#7C7689;letter-spacing:.04em}
</style></head><body>
<form class="card" method="POST" action="/login">
  <div class="logo">
    <svg width="38" height="46" viewBox="0 0 40 48" aria-label="Havanna"><path d="M4 5 H36 V29 Q36 40 20 46 Q4 40 4 29 Z" fill="#E4002B"/><rect x="13" y="14" width="3.6" height="20" fill="#FFCD00"/><rect x="23.4" y="14" width="3.6" height="20" fill="#FFCD00"/><rect x="13" y="22.2" width="14" height="3.6" fill="#FFCD00"/></svg>
    <div><div class="nm">HAVANNA</div><div class="sub">Social Listening · Marca Total</div></div>
  </div>
  <h1>Acesso restrito</h1>
  <p class="desc">Material estratégico de acesso restrito. Informe suas credenciais para continuar.</p>
  ${error ? '<div class="err">Usuário ou senha inválidos. Tente novamente.</div>' : ''}
  <label>Usuário</label>
  <input type="text" name="user" autocomplete="username" autofocus required>
  <label>Senha</label>
  <input type="password" name="pass" autocomplete="current-password" required>
  <button type="submit">Entrar</button>
  <div class="foot">Documento confidencial · Um produto Nuts &amp; Co</div>
</form>
</body></html>`;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const USER = env.USERNAME || "nuts.havanna";
    const PASS = env.PASSWORD || "MarcaTotal2026";
    const SECRET = env.SESSION_SECRET || "havanna_nuts_marca_total_2026_chave_secreta_brasil";

    // Login
    if (url.pathname === "/login" && request.method === "POST") {
      const form = await request.formData();
      if (form.get("user") === USER && form.get("pass") === PASS) {
        const sess = await makeSession(USER, SECRET);
        return new Response(null, {
          status: 302,
          headers: {
            "Location": "/",
            "Set-Cookie": `${COOKIE}=${sess}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=${MAX_AGE}`
          }
        });
      }
      return new Response(loginPage(true), { status: 401, headers: { "Content-Type": "text/html; charset=utf-8" } });
    }

    // Logout
    if (url.pathname === "/logout") {
      return new Response(null, { status: 302, headers: { "Location": "/", "Set-Cookie": `${COOKIE}=; Path=/; Max-Age=0` } });
    }

    // Sessao valida -> serve o dashboard
    const cookies = parseCookies(request);
    if (await verifySession(cookies[COOKIE], SECRET)) {
      return env.ASSETS.fetch(request);
    }

    // Sem sessao -> tela de login
    return new Response(loginPage(false), { status: 200, headers: { "Content-Type": "text/html; charset=utf-8" } });
  }
};
