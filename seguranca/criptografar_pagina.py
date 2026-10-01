"""Protege uma página estática (GitHub Pages) com senha de verdade: o HTML inteiro é criptografado com AES-256-GCM,
com chave derivada da senha por PBKDF2-SHA256 (600 mil rodadas). O arquivo publicado só contém a tela de senha e o
conteúdo embaralhado; sem a senha, ler o código-fonte não revela nada. A página abre no próprio navegador do visitante.

uso:
  SENHA='...' python3 criptografar_pagina.py criptografar original.html publicada.html --titulo "Cliente · Social Listening" [--liberar chave=valor]
  SENHA='...' python3 criptografar_pagina.py decriptografar publicada.html original.html
  python3 criptografar_pagina.py gerar-senha

--liberar grava chave=valor no sessionStorage antes de abrir a página, para desligar uma tela de senha antiga que
exista dentro do HTML original. A senha nunca vai para o repositório: guarde-a fora dele e passe pela variável SENHA.
"""
import sys, os, json, base64, secrets, hashlib, argparse, html as htmlmod, re
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITER = 600_000
ALFABETO = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789'

def chave(senha, sal, it=ITER):
    return hashlib.pbkdf2_hmac('sha256', senha.encode('utf-8'), sal, it, dklen=32)

def criptografar(texto, senha):
    sal, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    ct = AESGCM(chave(senha, sal)).encrypt(iv, texto.encode('utf-8'), None)
    b = lambda x: base64.b64encode(x).decode()
    return {'v': 1, 'iter': ITER, 'salt': b(sal), 'iv': b(iv), 'ct': b(ct)}

def decriptografar(p, senha):
    d = lambda x: base64.b64decode(x)
    return AESGCM(chave(senha, d(p['salt']), p['iter'])).decrypt(d(p['iv']), d(p['ct']), None).decode('utf-8')

MODELO = r'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>__TITULO__</title>
<style>
  :root{color-scheme:dark}
  *{box-sizing:border-box}
  body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0f1418;
       font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:#f2f2f2;padding:16px}
  .cartao{width:100%;max-width:380px;background:#182027;border:1px solid #2a343c;border-radius:18px;padding:32px 28px}
  h1{font-size:20px;margin:0 0 6px}
  p{margin:0 0 22px;color:#a9b4bb;font-size:14px}
  label{display:block;font-size:13px;color:#a9b4bb;margin-bottom:6px}
  input{width:100%;padding:12px 14px;border-radius:10px;border:1px solid #33404a;background:#0f1418;color:#f2f2f2;font-size:16px}
  button{width:100%;margin-top:16px;padding:12px;border:0;border-radius:10px;background:#f2f2f2;color:#0f1418;font-size:15px;font-weight:600;cursor:pointer}
  button:disabled{opacity:.6;cursor:wait}
  .erro{min-height:20px;margin-top:12px;color:#ff8a80;font-size:14px}
</style>
</head>
<body>
<form class="cartao" id="f" autocomplete="on">
  <h1>__TITULO__</h1>
  <p>Acesso restrito. Digite a senha para abrir.</p>
  <input type="text" name="username" autocomplete="username" value="acesso" hidden>
  <label for="s">Senha</label>
  <input type="password" id="s" autocomplete="current-password" required autofocus>
  <button id="b" type="submit">Entrar</button>
  <div class="erro" id="e" role="alert"></div>
</form>
<script>
(function(){
  var P = __PAYLOAD__, LIB = __LIBERAR__, CH = 'pagina_protegida_' + P.salt.slice(0, 8);
  function b64(s){ return Uint8Array.from(atob(s), function(c){ return c.charCodeAt(0); }); }
  function txt(u){ var s = ''; for (var i = 0; i < u.length; i += 32768) s += String.fromCharCode.apply(null, u.subarray(i, i + 32768)); return btoa(s); }
  function derivar(senha){
    return crypto.subtle.importKey('raw', new TextEncoder().encode(senha), 'PBKDF2', false, ['deriveKey']).then(function(base){
      return crypto.subtle.deriveKey({name:'PBKDF2', salt:b64(P.salt), iterations:P.iter, hash:'SHA-256'}, base, {name:'AES-GCM', length:256}, true, ['decrypt']);
    });
  }
  function abrir(k){
    return crypto.subtle.decrypt({name:'AES-GCM', iv:b64(P.iv)}, k, b64(P.ct)).then(function(pt){
      try { Object.keys(LIB).forEach(function(c){ sessionStorage.setItem(c, LIB[c]); }); } catch(e){}
      var html = new TextDecoder().decode(pt);
      document.open(); document.write(html); document.close();
    });
  }
  var f = document.getElementById('f'), s = document.getElementById('s'), b = document.getElementById('b'), e = document.getElementById('e');
  // mesma aba, senha já digitada: reabre sem pedir de novo, depois que a tela terminar de carregar
  // (document.open() durante o carregamento é ignorado pelo navegador)
  try {
    var guardada = sessionStorage.getItem(CH);
    if (guardada) {
      f.style.visibility = 'hidden';
      var reabrir = function(){
        crypto.subtle.importKey('raw', b64(guardada), {name:'AES-GCM'}, true, ['decrypt']).then(abrir)
          .catch(function(){ sessionStorage.removeItem(CH); f.style.visibility = ''; });
      };
      if (document.readyState === 'complete') setTimeout(reabrir, 0); else window.addEventListener('load', function(){ setTimeout(reabrir, 0); });
    }
  } catch(err){}
  f.addEventListener('submit', function(ev){
    ev.preventDefault(); e.textContent = ''; b.disabled = true; b.textContent = 'Abrindo';
    var chave;
    derivar(s.value).then(function(k){ chave = k; return crypto.subtle.exportKey('raw', k); })
      .then(function(raw){
        // guarda a chave antes de trocar o documento: depois do document.open() a continuação não é garantida
        try { sessionStorage.setItem(CH, txt(new Uint8Array(raw))); } catch(err){}
        return abrir(chave);
      })
      .catch(function(){ try { sessionStorage.removeItem(CH); } catch(err){} e.textContent = 'Senha incorreta. Tente novamente.'; s.value = ''; s.focus(); b.disabled = false; b.textContent = 'Entrar'; });
  });
})();
</script>
</body>
</html>
'''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('acao', choices=['criptografar', 'decriptografar', 'gerar-senha'])
    ap.add_argument('entrada', nargs='?'); ap.add_argument('saida', nargs='?')
    ap.add_argument('--titulo', default='Acesso restrito')
    ap.add_argument('--liberar', action='append', default=[])
    a = ap.parse_args()
    if a.acao == 'gerar-senha':
        print('-'.join(''.join(secrets.choice(ALFABETO) for _ in range(4)) for _ in range(4))); return
    senha = os.environ.get('SENHA')
    if not senha:
        import getpass; senha = getpass.getpass('Senha: ')
    if a.acao == 'criptografar':
        texto = open(a.entrada, encoding='utf-8').read()
        p = criptografar(texto, senha)
        assert decriptografar(p, senha) == texto
        lib = dict(x.split('=', 1) for x in a.liberar)
        out = (MODELO.replace('__TITULO__', htmlmod.escape(a.titulo))
               .replace('__PAYLOAD__', json.dumps(p)).replace('__LIBERAR__', json.dumps(lib)))
        open(a.saida, 'w', encoding='utf-8').write(out)
        print(f'criptografada: {a.saida} ({len(out) // 1024} KB)')
    else:
        m = re.search(r'var P = (\{.*?\}), LIB', open(a.entrada, encoding='utf-8').read(), re.S)
        open(a.saida, 'w', encoding='utf-8').write(decriptografar(json.loads(m.group(1)), senha))
        print(f'decriptografada: {a.saida}')

if __name__ == '__main__':
    main()
