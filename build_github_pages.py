"""Gera o pacote estático 24/7 para GitHub Pages (site_dist/) a partir das rotas
Flask e dos ativos estáticos (CSS + áudios neurais PT-BR da Academia), mantendo
integração com o backend Python 24/7 e suporte client-side para cadastro,
exame quantitativo e emissão de certificado na Academia estática.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import tempfile

import academy_data
import config

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "site_dist"
DEFAULT_BACKEND_URL = os.getenv(
    "GITHUB_PAGES_BACKEND_URL",
    "https://heuristika-web-production.up.railway.app",
).rstrip("/")


def _extract_exam_panel(authed_html: str) -> str:
    """Extrai o bloco <div class="panel" id="prova">...</div> da página autenticada."""
    marker = '<div class="panel" id="prova">'
    start = authed_html.find(marker)
    if start == -1:
        return ""
    end = authed_html.find("</section>", start)
    if end == -1:
        return ""
    return authed_html[start:end].strip()


def _build_static_runtime_script(backend_url: str, is_academy: bool = False) -> str:
    """Gera o runtime JS leve para filtros estáticos e Academia interativa no GitHub Pages."""
    questions_payload = [
        {
            "id": q["id"],
            "enunciado": q["enunciado"],
            "correta": q["correta"],
            "explicacao": q["explicacao"],
            "opcoes": q["opcoes"],
        }
        for q in academy_data.PROVA_QUESTOES
    ]
    questions_json = json.dumps(questions_payload, ensure_ascii=False)

    return f"""
<script id="hkStaticPagesRuntime">
(function() {{
  window.HK_STATIC_PAGES = true;
  window.HK_BACKEND_URL = {json.dumps(backend_url)};
  const IS_ACADEMY = {"true" if is_academy else "false"};
  const QUESTIONS = {questions_json if is_academy else "[]"};
  const STUDENT_KEY = "hk_static_student_v1";
  const CERTS_KEY = "hk_static_certs_v1";

  // Filtro client-side de categorias na Vitrine estática
  document.querySelectorAll('a[href^="/?categoria="], a[href*="?categoria="]').forEach(link => {{
    link.addEventListener("click", (e) => {{
      const href = link.getAttribute("href") || "";
      const m = href.match(/categoria=([^&#]+)/);
      if (!m) return;
      e.preventDefault();
      const cat = decodeURIComponent(m[1].replace(/\\+/g, " "));
      document.querySelectorAll('a[href*="?categoria="]').forEach(a => {{
        a.classList.toggle("active", a === link);
      }});
      document.querySelectorAll("#operacoes .signal-card").forEach(card => {{
        const badge = card.querySelector(".badge-cat");
        const cardCat = badge ? badge.textContent.trim() : "";
        card.style.display = (cat === "Todos" || !cardCat || cardCat === cat) ? "" : "none";
      }});
      document.querySelectorAll("#histTable tbody tr").forEach(row => {{
        const firstTd = row.querySelector("td");
        const rowCat = firstTd ? firstTd.textContent.trim() : "";
        row.style.display = (cat === "Todos" || !rowCat || rowCat === cat) ? "" : "none";
      }});
    }});
  }});

  if (!IS_ACADEMY) return;

  function esc(s) {{
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }}

  function maskId(doc, email) {{
    const d = String(doc || "").trim();
    if (d) {{
      const digits = d.replace(/\\D/g, "");
      if (digits.length === 11) return `***.${{digits.slice(3, 6)}}.${{digits.slice(6, 9)}}-**`;
      if (d.length > 4) return `${{d.slice(0, 2)}}***${{d.slice(-2)}}`;
      return "***";
    }}
    const mail = String(email || "").trim();
    if (mail.includes("@")) {{
      const [local, domain] = mail.split("@");
      return `${{local.slice(0, 2)}}***@${{domain}}`;
    }}
    return "Verificado";
  }}

  function loadStudent() {{
    try {{ return JSON.parse(localStorage.getItem(STUDENT_KEY) || "null"); }}
    catch (e) {{ return null; }}
  }}
  function saveStudent(st) {{
    try {{ localStorage.setItem(STUDENT_KEY, JSON.stringify(st)); }} catch (e) {{}}
  }}
  function loadCerts() {{
    try {{ return JSON.parse(localStorage.getItem(CERTS_KEY) || "[]"); }}
    catch (e) {{ return []; }}
  }}
  function saveCerts(list) {{
    try {{ localStorage.setItem(CERTS_KEY, JSON.stringify(list)); }} catch (e) {{}}
  }}

  const cadastroEl = document.getElementById("cadastro");
  const staticArea = document.getElementById("staticStudentArea");
  const studentNameBadge = document.getElementById("staticStudentBadge");
  const logoutBtn = document.getElementById("staticLogoutBtn");
  const certsHost = document.getElementById("staticCertsHost");
  const resultHost = document.getElementById("staticResultHost");
  const certModal = document.getElementById("staticCertModal");

  function openCertificateView(cert, student) {{
    if (!certModal) return;
    const masked = maskId(student?.documento, student?.email);
    certModal.innerHTML = `
      <div class="panel cert-print-card" style="padding:36px; border:2px solid rgba(16, 185, 129, 0.55); background:radial-gradient(circle at top right, rgba(16,185,129,0.12), var(--surface) 60%); margin-bottom:28px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:22px; padding-bottom:16px; border-bottom:1px solid var(--border);">
          <strong style="font-size:1.18rem;">Heurístika Academia Quantitativa</strong>
          <span class="badge badge-buy">AUTENTICIDADE VERIFICADA</span>
        </div>
        <div class="mono" style="font-size:0.78rem; color:#34d399; letter-spacing:0.12em;">CERTIFICADO DE CONCLUSÃO &amp; PROFICIÊNCIA QUANTITATIVA</div>
        <h2 style="margin:10px 0 16px; font-size:clamp(1.6rem, 3vw, 2.3rem);">${{esc(student?.nome || "Aluno Heurístika")}}</h2>
        <p style="font-size:0.96rem; color:var(--text-soft); line-height:1.7; margin-bottom:22px;">
          Concluiu com êxito a trilha educacional e foi aprovado(a) no <strong>Exame Avançado de Heurística Financeira, Gestão de Risco Quantitativa, Alocação Multi-Horizonte e Derivativos</strong>, obtendo aproveitamento de <strong class="text-green">${{Math.round(cert.nota_pct)}}% (${{cert.acertos}}/${{cert.total}} questões)</strong>.
        </p>
        <div class="kpi-grid" style="margin-bottom:22px;">
          <div class="kpi-card"><div class="kpi-label">Código Verificador</div><div class="kpi-value" style="font-size:1.05rem; color:#34d399;">${{esc(cert.codigo)}}</div></div>
          <div class="kpi-card"><div class="kpi-label">Data de Emissão</div><div class="kpi-value" style="font-size:1.05rem;">${{esc(cert.emitido_em)}}</div></div>
          <div class="kpi-card"><div class="kpi-label">Identificação</div><div class="kpi-value" style="font-size:1.02rem;">${{esc(masked)}}</div></div>
        </div>
        <div class="no-print" style="display:flex; justify-content:flex-end; gap:10px; flex-wrap:wrap;">
          <button type="button" class="btn btn-sm btn-electric" onclick="window.print()">Imprimir / Salvar PDF</button>
          <button type="button" class="btn btn-sm btn-outline" id="closeStaticCertBtn">Fechar Visualização</button>
        </div>
      </div>
    `;
    certModal.style.display = "block";
    certModal.scrollIntoView({{ behavior: "smooth", block: "center" }});
    document.getElementById("closeStaticCertBtn")?.addEventListener("click", () => {{
      certModal.style.display = "none";
    }});
  }}

  function renderCertsList(student) {{
    if (!certsHost) return;
    const certs = loadCerts().filter(c => c.email === student?.email);
    if (!certs.length) {{
      certsHost.innerHTML = "";
      return;
    }}
    certsHost.innerHTML = `
      <div class="panel" style="margin-bottom:24px; border-color:rgba(16,185,129,0.4);">
        <h2 style="margin:0 0 12px; font-size:1.15rem;">Seus Certificados Emitidos</h2>
        <div style="display:flex; flex-direction:column; gap:10px;">
          ${{certs.map((c, idx) => `
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; background:var(--surface-2); padding:12px 14px; border-radius:10px; border:1px solid var(--border);">
              <div>
                <strong class="mono text-green">${{esc(c.codigo)}}</strong>
                <span style="color:var(--muted); font-size:0.84rem; margin-left:8px;">Nota: ${{Math.round(c.nota_pct)}}% (${{c.acertos}}/${{c.total}}) • Emitido em ${{esc(c.emitido_em)}}</span>
              </div>
              <button type="button" class="btn btn-sm btn-electric open-static-cert-btn" data-cert-idx="${{idx}}">Abrir Certificado ↗</button>
            </div>
          `).join("")}}
        </div>
      </div>
    `;
    certsHost.querySelectorAll(".open-static-cert-btn").forEach(btn => {{
      btn.addEventListener("click", () => {{
        const c = certs[Number(btn.dataset.certIdx || 0)];
        if (c) openCertificateView(c, student);
      }});
    }});
  }}

  function syncAuthUi() {{
    const st = loadStudent();
    const goExamBtns = document.querySelectorAll('a[href="#cadastro"], a[href="#prova"]');
    if (st && st.nome && st.email) {{
      if (cadastroEl) cadastroEl.style.display = "none";
      if (staticArea) staticArea.style.display = "block";
      if (studentNameBadge) studentNameBadge.textContent = "ALUNO: " + String(st.nome).toUpperCase();
      goExamBtns.forEach(a => a.setAttribute("href", "#prova"));
      renderCertsList(st);
    }} else {{
      if (cadastroEl) cadastroEl.style.display = "";
      if (staticArea) staticArea.style.display = "none";
      goExamBtns.forEach(a => a.setAttribute("href", "#cadastro"));
    }}
  }}

  // Intercepta cadastro e login no modo GitHub Pages
  document.querySelectorAll('form[action$="/academia/cadastro"]').forEach(form => {{
    form.addEventListener("submit", (e) => {{
      e.preventDefault();
      const nome = (form.querySelector('[name="nome"]')?.value || "").trim();
      const email = (form.querySelector('[name="email"]')?.value || "").trim().toLowerCase();
      const documento = (form.querySelector('[name="documento"]')?.value || "").trim();
      const pin = (form.querySelector('[name="pin"]')?.value || "").trim();
      if (nome.length < 3 || !/^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$/.test(email) || pin.length < 4) {{
        if (window.hkToast) window.hkToast("Preencha nome completo, e-mail válido e PIN de 4+ dígitos.", "warning");
        return;
      }}
      saveStudent({{ nome, email, documento, pin }});
      syncAuthUi();
      if (window.hkToast) window.hkToast(`Cadastro concluído, ${{nome}}! Prova liberada.`, "success");
      document.getElementById("prova")?.scrollIntoView({{ behavior: "smooth", block: "start" }});
    }});
  }});

  document.querySelectorAll('form[action$="/academia/login"]').forEach(form => {{
    form.addEventListener("submit", (e) => {{
      e.preventDefault();
      const email = (form.querySelector('[name="email"]')?.value || "").trim().toLowerCase();
      const pin = (form.querySelector('[name="pin"]')?.value || "").trim();
      const existing = loadStudent();
      if (existing && existing.email === email && existing.pin === pin) {{
        syncAuthUi();
        if (window.hkToast) window.hkToast(`Bem-vindo(a) de volta, ${{existing.nome}}!`, "success");
        document.getElementById("prova")?.scrollIntoView({{ behavior: "smooth", block: "start" }});
      }} else if (email.includes("@") && pin.length >= 4) {{
        const guessedName = existing?.nome || email.split("@")[0];
        saveStudent({{ nome: guessedName, email, documento: existing?.documento || "", pin }});
        syncAuthUi();
        if (window.hkToast) window.hkToast(`Acesso liberado para ${{guessedName}}!`, "success");
        document.getElementById("prova")?.scrollIntoView({{ behavior: "smooth", block: "start" }});
      }} else {{
        if (window.hkToast) window.hkToast("Informe um e-mail válido e seu PIN de 4+ dígitos.", "warning");
      }}
    }});
  }});

  logoutBtn?.addEventListener("click", () => {{
    try {{ localStorage.removeItem(STUDENT_KEY); }} catch (e) {{}}
    if (resultHost) resultHost.innerHTML = "";
    if (certModal) certModal.style.display = "none";
    syncAuthUi();
    if (window.hkToast) window.hkToast("Você saiu da conta de aluno.", "success");
  }});

  // Intercepta correção da prova no modo GitHub Pages
  const examForm = document.getElementById("examForm");
  if (examForm) {{
    examForm.addEventListener("submit", (e) => {{
      e.preventDefault();
      const st = loadStudent();
      if (!st) {{
        if (window.hkToast) window.hkToast("Cadastre-se antes de enviar a prova.", "warning");
        return;
      }}
      let acertos = 0;
      const revisao = [];
      for (const q of QUESTIONS) {{
        const checked = examForm.querySelector(`input[name="${{q.id}}"]:checked`);
        if (!checked) return;
        const val = checked.value.toLowerCase();
        const ok = val === q.correta;
        if (ok) acertos++;
        revisao.push({{
          enunciado: q.enunciado,
          acertou: ok,
          resposta_usuario: val.toUpperCase(),
          correta: q.correta.toUpperCase(),
          explicacao: q.explicacao,
        }});
      }}
      const total = QUESTIONS.length || 10;
      const nota_pct = Math.round((acertos / total) * 1000) / 10;
      const aprovado = nota_pct >= 70;
      let certObj = null;
      if (aprovado) {{
        const hex1 = Math.floor(1000 + Math.random() * 9000).toString(16).toUpperCase();
        const hex2 = Math.floor(1000 + Math.random() * 9000).toString(16).toUpperCase();
        const now = new Date();
        const dtStr = now.toLocaleDateString("pt-BR") + " " + now.toLocaleTimeString("pt-BR", {{ hour: "2-digit", minute: "2-digit" }});
        certObj = {{
          codigo: `CERT-HRK-${{hex1}}-${{hex2}}`,
          nota_pct,
          acertos,
          total,
          emitido_em: dtStr,
          email: st.email,
        }};
        const allCerts = loadCerts();
        allCerts.unshift(certObj);
        saveCerts(allCerts);
        renderCertsList(st);
      }}

      if (resultHost) {{
        resultHost.innerHTML = `
          <div class="panel" style="margin-bottom:28px; border-color:${{aprovado ? 'rgba(16,185,129,0.5)' : 'rgba(255,71,87,0.45)'}};" id="resultado-prova">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:14px;">
              <div>
                <span class="badge ${{aprovado ? 'badge-buy' : 'badge-loss'}}">
                  ${{aprovado ? 'APROVADO NA CERTIFICAÇÃO' : 'NÃO APROVADO (MÍNIMO 70%)'}}
                </span>
                <h2 style="margin:8px 0 0;">Nota Final: ${{Math.round(nota_pct)}}% (${{acertos}}/${{total}})</h2>
              </div>
              ${{certObj ? `<button type="button" class="btn btn-electric" id="viewLatestStaticCertBtn">Visualizar Certificado (${{esc(certObj.codigo)}})</button>` : ''}}
            </div>
            <div style="display:flex; flex-direction:column; gap:8px;">
              ${{revisao.map(r => `
                <div style="background:var(--surface-2); padding:10px 12px; border-radius:8px; font-size:0.84rem;">
                  <strong class="${{r.acertou ? 'text-green' : 'text-red'}}">${{r.acertou ? '✓ CORRETA' : '✕ INCORRETA'}}</strong> — ${{esc(r.enunciado)}}
                  <div class="mono" style="font-size:0.76rem; color:var(--text-soft); margin-top:4px;">
                    Sua resposta: <strong>${{esc(r.resposta_usuario)}}</strong>${{!r.acertou ? ` • Correta: <strong class="text-green">${{esc(r.correta)}}</strong>` : ''}}
                  </div>
                  <div style="color:var(--muted); margin-top:4px;">${{esc(r.explicacao)}}</div>
                </div>
              `).join("")}}
            </div>
          </div>
        `;
        document.getElementById("viewLatestStaticCertBtn")?.addEventListener("click", () => {{
          if (certObj) openCertificateView(certObj, st);
        }});
        document.getElementById("resultado-prova")?.scrollIntoView({{ behavior: "smooth", block: "start" }});
      }}
      if (window.hkToast) {{
        window.hkToast(
          aprovado
            ? `Parabéns! Aprovado com ${{Math.round(nota_pct)}}%. Certificado emitido!`
            : `Nota: ${{Math.round(nota_pct)}}%. Atingir 70% (7/10) para emitir certificado.`,
          aprovado ? "success" : "warning"
        );
      }}
    }});
  }}

  syncAuthUi();
}})();
</script>
"""


def _rewrite_links(html: str, depth: int, backend_url: str) -> str:
    """Converte URLs absolutas do Flask em caminhos relativos compatíveis com GitHub Pages."""
    prefix = "." if depth == 0 else ".."
    out = html
    out = out.replace('href="/static/', f'href="{prefix}/static/')
    out = out.replace('src="/static/', f'src="{prefix}/static/')
    out = out.replace('"/static/audio/', f'"{prefix}/static/audio/')

    out = out.replace('href="/"', f'href="{prefix}/index.html"')
    out = out.replace('href="/#', f'href="{prefix}/index.html#')
    out = re.sub(r'href="/\?categoria=([^"]+)"', rf'href="{prefix}/index.html?categoria=\1"', out)
    out = out.replace('href="/carteiras"', f'href="{prefix}/carteiras/"')
    out = out.replace('href="/academia"', f'href="{prefix}/academia/"')
    out = out.replace('href="/login"', f'href="{backend_url}/login"')
    out = out.replace('href="/vip"', f'href="{backend_url}/vip"')
    out = out.replace('href="/admin"', f'href="{backend_url}/admin"')
    out = out.replace('href="/lang/pt"', 'href="#pt" data-static-lang="pt"')
    out = out.replace('href="/lang/en"', 'href="#en" data-static-lang="en"')
    return out


def build_static_site(
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    backend_url: str = DEFAULT_BACKEND_URL,
) -> dict[str, int]:
    """Renderiza e empacota o site estático completo em output_dir."""
    out_path = Path(output_dir).resolve()
    backend = (backend_url or DEFAULT_BACKEND_URL).rstrip("/")

    orig_db_path = config.DB_PATH
    tmp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp_db.close()

    try:
        config.DB_PATH = tmp_db.name
        import app as flask_app
        import database

        database.init_db()
        database.seed_initial_data(force=True)
        client = flask_app.app.test_client()

        home_html = client.get("/").data.decode("utf-8")
        carteiras_html = client.get("/carteiras").data.decode("utf-8")
        academia_guest_html = client.get("/academia").data.decode("utf-8")

        demo_student = database.register_student(
            "Aluno Certificação",
            "demo_static@heuristika.com",
            "000.000.000-00",
            "1234",
        )
        with client.session_transaction() as sess:
            sess["academy_student_id"] = demo_student["id"]
        academia_authed_html = client.get("/academia").data.decode("utf-8")
    finally:
        config.DB_PATH = orig_db_path
        try:
            os.remove(tmp_db.name)
        except OSError:
            pass

    exam_panel_html = _extract_exam_panel(academia_authed_html)
    static_student_wrapper = f"""
  <div id="staticStudentArea" style="display:none; margin-bottom:32px;">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:18px; padding:12px 16px; background:var(--surface); border:1px solid rgba(16,185,129,0.35); border-radius:10px;">
      <span class="badge badge-buy" id="staticStudentBadge">ALUNO HABILITADO</span>
      <button type="button" class="btn btn-sm btn-outline" id="staticLogoutBtn">Trocar Aluno / Sair</button>
    </div>
    <div id="staticCertModal" style="display:none;"></div>
    <div id="staticCertsHost"></div>
    <div id="staticResultHost"></div>
    {exam_panel_html}
  </div>
"""

    if "</section>" in academia_guest_html:
        last_sec = academia_guest_html.rfind("</section>")
        academia_combined_html = (
            academia_guest_html[:last_sec]
            + static_student_wrapper
            + academia_guest_html[last_sec:]
        )
    else:
        academia_combined_html = academia_guest_html + static_student_wrapper

    if out_path.exists():
        shutil.rmtree(out_path)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / ".nojekyll").write_text("", encoding="utf-8")

    # Copia static/ (CSS + MP3s + manifesto)
    shutil.copytree(BASE_DIR / "static", out_path / "static")

    # 1. Vitrine (raiz)
    home_final = _rewrite_links(home_html, depth=0, backend_url=backend).replace(
        "</body>",
        _build_static_runtime_script(backend, is_academy=False) + "\n</body>",
    )
    (out_path / "index.html").write_text(home_final, encoding="utf-8")
    (out_path / "404.html").write_text(home_final, encoding="utf-8")

    # 2. Carteiras (/carteiras/index.html e /carteiras.html)
    (out_path / "carteiras").mkdir(parents=True, exist_ok=True)
    cart_sub = _rewrite_links(carteiras_html, depth=1, backend_url=backend).replace(
        "</body>",
        _build_static_runtime_script(backend, is_academy=False) + "\n</body>",
    )
    cart_root = _rewrite_links(carteiras_html, depth=0, backend_url=backend).replace(
        "</body>",
        _build_static_runtime_script(backend, is_academy=False) + "\n</body>",
    )
    (out_path / "carteiras" / "index.html").write_text(cart_sub, encoding="utf-8")
    (out_path / "carteiras.html").write_text(cart_root, encoding="utf-8")

    # 3. Academia (/academia/index.html e /academia.html)
    (out_path / "academia").mkdir(parents=True, exist_ok=True)
    acad_runtime = _build_static_runtime_script(backend, is_academy=True)
    acad_sub = _rewrite_links(academia_combined_html, depth=1, backend_url=backend).replace(
        "</body>",
        acad_runtime + "\n</body>",
    )
    acad_root = _rewrite_links(academia_combined_html, depth=0, backend_url=backend).replace(
        "</body>",
        acad_runtime + "\n</body>",
    )
    (out_path / "academia" / "index.html").write_text(acad_sub, encoding="utf-8")
    (out_path / "academia.html").write_text(acad_root, encoding="utf-8")

    files_count = sum(1 for p in out_path.rglob("*") if p.is_file())
    return {"files_count": files_count, "output_dir": str(out_path)}


if __name__ == "__main__":
    info = build_static_site()
    print(f"Pacote GitHub Pages gerado em {info['output_dir']} ({info['files_count']} arquivos).")
