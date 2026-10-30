"use strict";
/* Página de prueba de los modelos (Sprint 1). JavaScript sin framework; todo el texto dinámico se inserta con textContent. */

const CATEGORIAS = ["Hardware", "Software", "Red", "Accesos", "Correo", "Seguridad"];
const PRIORIDADES = ["Baja", "Media", "Alta", "Crítica"];
const EJEMPLOS = [
  { n: "VPN no conecta", t: "No puedo conectarme a la VPN", d: "Desde esta mañana el cliente VPN da error al conectar desde casa y no puedo trabajar.", i: "Medio", u: "Alta", us: 1 },
  { n: "Sin internet (solución rápida)", t: "mi equipo no tiene internet", d: "mi equipo no tiene internet", i: "Bajo", u: "Media", us: 1 },
  { n: "Contraseña olvidada", t: "Olvidé mi contraseña", d: "No recuerdo la contraseña de mi cuenta y no puedo iniciar sesión en el sistema.", i: "Bajo", u: "Media", us: 1 },
  { n: "Virus / malware", t: "Posible virus en mi computadora", d: "Mi computadora tiene un virus, aparece publicidad por todos lados y el antivirus detectó malware.", i: "Medio", u: "Alta", us: 3 },
  { n: "Outlook no sincroniza", t: "Outlook no sincroniza el correo", d: "Outlook no sincroniza mis correos en el celular desde ayer y no me llegan los mensajes nuevos.", i: "Bajo", u: "Media", us: 1 },
  { n: "Monitor parpadea", t: "El monitor parpadea", d: "La pantalla de mi monitor parpadea y a veces se apaga sola, el cable parece bien conectado.", i: "Bajo", u: "Baja", us: 1 },
  { n: "Caída de plataforma", t: "Caída total del sistema de producción", d: "El sistema de producción está caído por completo para toda la empresa; nadie puede trabajar desde hace una hora.", i: "Alto", u: "Alta", us: 300 },
];

/* ------------------------------------------------------------------ utilidades */
const $ = (id) => document.getElementById(id);
function el(tag, props, ...hijos) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (k === "class") e.className = v;
    else if (k === "texto") e.textContent = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v !== false && v !== null && v !== undefined) e.setAttribute(k, v === true ? "" : v);
  }
  for (const h of hijos.flat()) if (h !== null && h !== undefined && h !== false) e.append(h.nodeType ? h : document.createTextNode(String(h)));
  return e;
}
const pct = (x, d = 1) => (x * 100).toFixed(d).replace(".", ",") + " %";
const num = (x, d = 3) => Number(x).toFixed(d).replace(".", ",");
/* Sesión: la misma que usa el sistema de tickets (sessionStorage "sesion-tickets"). Las operaciones que cambian cargas,
   correcciones o modelos exigen un Administrador; la lectura y el análisis no. */
const CLAVE_SESION = "sesion-tickets";
function sesion() { try { return JSON.parse(sessionStorage.getItem(CLAVE_SESION) || "null"); } catch (e) { return null; } }
function pintarSesion() {
  const s = sesion(), nodo = $("sesion-lab");
  nodo.replaceChildren(s ? el("span", { texto: `${s.usuario.nombre} · ${s.usuario.rol}` }) : el("span", { texto: "Sin sesión (solo lectura)" }),
    el("button", { class: "secundario", texto: s ? "Salir" : "Entrar como Administrador", onclick: () => {
      if (s) { sessionStorage.removeItem(CLAVE_SESION); pintarSesion(); } else { $("dlg-login").showModal(); } } }));
}
async function api(ruta, opciones) {
  opciones = opciones || {};
  const s = sesion();
  if (s && s.token) opciones.headers = { ...(opciones.headers || {}), Authorization: `Bearer ${s.token}` };
  const r = await fetch(ruta, opciones);
  let cuerpo = null;
  try { cuerpo = await r.json(); } catch (e) { /* sin cuerpo */ }
  if (!r.ok) {
    const det = cuerpo && cuerpo.detail;
    if (r.status === 401 || r.status === 403) {
      if (r.status === 401) { sessionStorage.removeItem(CLAVE_SESION); pintarSesion(); $("dlg-login").showModal(); }
      throw new Error((typeof det === "string" ? det : "Sin permiso.") + " Esta acción requiere iniciar sesión como Administrador.");
    }
    throw new Error(typeof det === "string" ? det : (Array.isArray(det) ? det.map((x) => x.msg).join("; ") : `Error ${r.status}`));
  }
  return cuerpo;
}
const post = (ruta, datos) => api(ruta, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(datos) });
const put = (ruta, datos) => api(ruta, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(datos) });
function mensaje(nodo, texto, tipo) { nodo.textContent = texto; nodo.className = "mensaje " + (tipo || ""); }

/* ------------------------------------------------------------------ pestañas */
const PESTANAS = ["analizar", "balanceo", "metricas", "continuo"];
function mostrar(nombre) {
  for (const p of PESTANAS) {
    const activa = p === nombre;
    $("t-" + p).classList.toggle("activa", activa);
    $("t-" + p).setAttribute("aria-selected", activa);
    $("p-" + p).hidden = !activa;
  }
  if (nombre === "balanceo") cargarTecnicos();
  if (nombre === "metricas") cargarMetricas();
  if (nombre === "continuo") cargarContinuo();
}
PESTANAS.forEach((p) => $("t-" + p).addEventListener("click", () => mostrar(p)));

/* ------------------------------------------------------------------ 1 · analizar */
let ultimoAnalisis = null;
function barrasProb(probs, orden, claseExtra) {
  const top = Object.entries(probs).sort((a, b) => b[1] - a[1])[0][0];
  return el("div", { class: "barras" }, orden.map((c) =>
    el("div", { class: "barra-p" + (c === top ? " top" : "") },
      el("span", { texto: c, class: claseExtra ? claseExtra + c : "" }),
      el("div", { class: "pista" }, el("div", { class: "relleno", style: `width:${(probs[c] * 100).toFixed(1)}%` })),
      el("span", { texto: pct(probs[c]), style: "text-align:right" }))));
}
function filaTecnico(t, i) {
  const ocup = t.carga / t.limite_carga;
  return el("div", { class: "tecnico" + (t.recomendado ? " reco" : "") },
    el("div", { class: "pos", texto: i + 1 }),
    el("div", {},
      el("span", { class: "nombre", texto: `${t.nombre} ` }), el("span", { class: "insignia", texto: t.id_tecnico }),
      t.saturado ? el("span", { class: "insignia mal", texto: "saturado", style: "margin-left:6px" }) : null,
      t.recomendado ? el("span", { class: "insignia ok", texto: "recomendado", style: "margin-left:6px" }) : null,
      el("small", { texto: `${t.area} · aptitud ${t.aptitud}/5 · adecuación ${pct(t.adecuacion, 0)}` }),
      t.nota ? el("div", { class: "nota", texto: t.nota }) : null),
    el("div", { class: "carga" }, el("small", { texto: `carga ${t.carga} / ${t.limite_carga}` }),
      el("div", { class: "pista" }, el("div", { class: "relleno" + (ocup >= 1 ? " lleno" : ocup >= 0.8 ? " alto" : ""), style: `width:${Math.min(100, ocup * 100)}%` }))));
}
function pintarResultado(r) {
  const cont = $("resultado");
  cont.className = "tarjeta";
  const cls = r.clasificacion, pri = r.prioridad;
  cont.replaceChildren(
    el("h2", { texto: "Resultado" }),
    el("p", { class: "ayuda", texto: `Respuesta en ${r.tiempo_ms.toFixed(0)} ms · modelos ${r.version_modelos}` }),
    el("p", { class: "sub", texto: "Categoría" }),
    el("p", { class: "grande", texto: `${cls.categoria} (${pct(cls.probabilidades[cls.categoria], 0)})` }),
    barrasProb(cls.probabilidades, CATEGORIAS),
    el("p", { class: "sub", texto: "Prioridad" }),
    el("p", { class: "grande prio-" + pri.prioridad, texto: `${pri.prioridad} (${pct(pri.probabilidades[pri.prioridad], 0)})` }),
    barrasProb(pri.probabilidades, PRIORIDADES, "prio-"),
    el("p", { class: "sub", texto: "Técnicos ordenados por adecuación" }),
    el("div", {}, r.tecnicos.map(filaTecnico)),
    el("p", { class: "sub", texto: "Solución rápida sugerida" }),
    r.solucion_rapida
      ? el("div", { class: "solucion" }, el("strong", { texto: r.solucion_rapida.problema }), el("span", { class: "insignia", texto: `similitud ${num(r.solucion_rapida.similitud, 2)}`, style: "margin-left:8px" }),
          el("ol", {}, r.solucion_rapida.pasos.map((p) => el("li", { texto: p }))))
      : el("p", { class: "ayuda", texto: "Ninguna solución rápida supera el umbral de similitud para este ticket." }),
    el("p", { class: "sub", texto: "5 casos similares" }),
    el("div", {}, r.similares.map((s) => el("div", { class: "similar" },
      el("strong", { texto: s.titulo }), " ", el("span", { class: "insignia", texto: s.categoria }), " ", el("span", { class: "insignia prio-" + s.prioridad, texto: s.prioridad }),
      el("span", { class: "ayuda", texto: `  similitud ${num(s.similitud, 2)} · ${s.fuente}` }),
      s.solucion ? el("details", {}, el("summary", { texto: "Solución del caso" }), s.solucion) : el("div", { class: "ayuda", texto: "Sin solución registrada." })))),
    el("div", { class: "botones" }, el("button", { texto: "Corregir este resultado →", onclick: () => prepararCorreccion() })));
}
$("form-analizar").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const btn = $("btn-analizar");
  btn.disabled = true; btn.textContent = "Analizando…";
  try {
    ultimoAnalisis = { entrada: leerTicket(), salida: null };
    ultimoAnalisis.salida = await post("/api/analizar", ultimoAnalisis.entrada);
    pintarResultado(ultimoAnalisis.salida);
  } catch (e) {
    $("resultado").className = "tarjeta";
    $("resultado").replaceChildren(el("h2", { texto: "Resultado" }), el("p", { class: "mensaje error", texto: e.message }));
  } finally { btn.disabled = false; btn.textContent = "Analizar ticket"; }
});
function leerTicket() {
  return { titulo: $("titulo").value.trim(), descripcion: $("descripcion").value.trim(), impacto: $("impacto").value, urgencia: $("urgencia").value, usuarios_afectados: parseInt($("usuarios").value || "1", 10) };
}
function cargarEjemplo(e) {
  $("titulo").value = e.t; $("descripcion").value = e.d; $("impacto").value = e.i; $("urgencia").value = e.u; $("usuarios").value = e.us;
}
$("ejemplos").replaceChildren(...EJEMPLOS.map((e) => el("button", { type: "button", texto: e.n, onclick: () => { cargarEjemplo(e); $("form-analizar").requestSubmit(); } })));

/* ------------------------------------------------------------------ 2 · balanceo */
let tecnicos = [];
async function cargarTecnicos() {
  tecnicos = await api("/api/tecnicos");
  const tb = $("tabla-cargas").querySelector("tbody");
  tb.replaceChildren(...tecnicos.map((t) => el("tr", {},
    el("td", {}, el("strong", { texto: t.nombre }), el("div", { class: "ayuda", texto: t.id_tecnico, style: "margin:0" })),
    el("td", { texto: t.area }), el("td", { class: "num", texto: t.limite_carga }),
    el("td", {}, el("input", { type: "number", min: 0, value: t.carga, "data-id": t.id_tecnico, "aria-label": `Carga de ${t.nombre}` })),
    el("td", { class: "num", texto: pct(t.carga / t.limite_carga, 0) }))));
  const sel = $("sel-ejemplo-balanceo");
  if (!sel.options.length) sel.replaceChildren(...EJEMPLOS.map((e, i) => el("option", { value: i, texto: e.n })));
}
function cargasEditadas() {
  const o = {};
  $("tabla-cargas").querySelectorAll("input[data-id]").forEach((i) => { o[i.dataset.id] = Math.max(0, parseInt(i.value || "0", 10)); });
  return o;
}
$("btn-aplicar-cargas").addEventListener("click", async () => {
  try { await put("/api/tecnicos", { cargas: cargasEditadas() }); mensaje($("msg-cargas"), "Cargas aplicadas.", "ok"); await cargarTecnicos(); }
  catch (e) { mensaje($("msg-cargas"), e.message, "error"); }
});
$("btn-reset-cargas").addEventListener("click", async () => {
  const o = {}; tecnicos.forEach((t) => { o[t.id_tecnico] = Math.round(0.4 * t.limite_carga); });
  await put("/api/tecnicos", { cargas: o }); mensaje($("msg-cargas"), "Cargas restablecidas al 40 % del límite.", "ok"); await cargarTecnicos();
});
async function asignarEjemplo() {
  const e = EJEMPLOS[parseInt($("sel-ejemplo-balanceo").value || "0", 10)];
  const r = await post("/api/analizar", { titulo: e.t, descripcion: e.d, impacto: e.i, urgencia: e.u, usuarios_afectados: e.us });
  $("resultado-balanceo").replaceChildren(
    el("p", { texto: `Categoría ${r.clasificacion.categoria} · prioridad ${r.prioridad.prioridad}` }), el("div", {}, r.tecnicos.map(filaTecnico)));
  return r;
}
$("btn-asignar").addEventListener("click", () => asignarEjemplo().catch((e) => mensaje($("msg-cargas"), e.message, "error")));
$("btn-saturar").addEventListener("click", async () => {
  try {
    const r = await asignarEjemplo();
    const t = r.tecnicos.find((x) => x.recomendado);
    await put("/api/tecnicos", { cargas: { [t.id_tecnico]: t.limite_carga } });
    mensaje($("msg-cargas"), `${t.nombre} saturado (${t.limite_carga}/${t.limite_carga}). Nueva asignación abajo.`, "ok");
    await cargarTecnicos(); await asignarEjemplo();
  } catch (e) { mensaje($("msg-cargas"), e.message, "error"); }
});

/* ------------------------------------------------------------------ 3 · métricas */
function mapaConfusion(matriz, clases, titulo) {
  const maxFila = matriz.map((f) => f.reduce((a, b) => a + b, 0));
  return el("div", {}, el("h3", { texto: titulo }),
    el("table", { class: "mapa" },
      el("thead", {}, el("tr", {}, el("th", { texto: "real ↓ / predicho →" }), clases.map((c) => el("th", { texto: c })))),
      el("tbody", {}, matriz.map((fila, i) => el("tr", {}, el("th", { texto: clases[i] }),
        fila.map((v, j) => {
          const frac = maxFila[i] ? v / maxFila[i] : 0;
          return el("td", { texto: v, style: `background: color-mix(in srgb, ${i === j ? "var(--ok)" : "var(--mal)"} ${Math.round(frac * 70)}%, transparent)` });
        }))))));
}
function tablaClases(titulo, filas, clases) {
  return el("div", {}, el("h3", { texto: titulo }),
    el("table", { class: "tabla" },
      el("thead", {}, el("tr", {}, el("th", { texto: "Clase" }), filas.map((f) => [el("th", { class: "num", texto: `F1 ${f.nombre}` }), el("th", { class: "num", texto: `P ${f.nombre}` }), el("th", { class: "num", texto: `R ${f.nombre}` })]).flat(), el("th", { class: "num", texto: "n" }))),
      el("tbody", {},
        clases.map((c) => el("tr", {}, el("td", { texto: c }), filas.map((f) => { const v = f.datos.por_clase[c]; return [el("td", { class: "num", texto: num(v.f1) }), el("td", { class: "num", texto: num(v.precision) }), el("td", { class: "num", texto: num(v.recall) })]; }).flat(), el("td", { class: "num", texto: filas[0].datos.por_clase[c].soporte }))),
        el("tr", {}, el("td", {}, el("strong", { texto: "F1 macro" })), filas.map((f) => [el("td", { class: "num" }, el("strong", { texto: num(f.datos.f1_macro) })), el("td"), el("td")]).flat(), el("td")))));
}
function criterio(ok, texto) {
  return el("div", { class: "criterio" }, el("span", { class: "insignia " + (ok ? "ok" : "mal"), texto: ok ? "cumple" : "no cumple" }), el("span", { texto }));
}
async function cargarMetricas() {
  const cont = $("contenido-metricas");
  let m;
  try { m = await api("/api/metricas"); } catch (e) { cont.replaceChildren(el("p", { class: "mensaje error", texto: e.message })); return; }
  const cat = m.categoria, pri = m.prioridad, asi = m.asignacion, sim = m.similitud;
  const gru = cat.gru.reales, base = cat.base.reales;
  const mlp = pri["mlp completo"].reales, regla = pri["regla: matriz impacto × urgencia"].reales, txt = pri["base: TF-IDF + LR (solo texto)"].reales, sinIU = pri["mlp sin impacto/urgencia (texto)"].reales;
  const sr = sim.soluciones_rapidas;
  cont.replaceChildren(
    el("h2", { texto: `Métricas de la versión ${m.version}` }),
    el("p", { class: "ayuda", texto: "Evaluadas sobre el conjunto de prueba (tickets reales, sin variantes aumentadas). Criterios de aceptación del plan del Sprint 1." }),
    el("div", { class: "kpis" },
      el("div", { class: "kpi" }, el("b", { texto: num(gru.f1_macro) }), el("span", { texto: "F1 macro GRU (categoría)" })),
      el("div", { class: "kpi" }, el("b", { texto: num(base.f1_macro) }), el("span", { texto: "F1 macro modelo base" })),
      el("div", { class: "kpi" }, el("b", { texto: num(mlp.f1_macro) }), el("span", { texto: "F1 macro MLP prioridad" })),
      el("div", { class: "kpi" }, el("b", { texto: num(mlp.por_clase["Crítica"].recall) }), el("span", { texto: "Recall de Crítica" })),
      el("div", { class: "kpi" }, el("b", { texto: pct(asi.top1, 1) }), el("span", { texto: "Técnico esperado primero" })),
      el("div", { class: "kpi" }, el("b", { texto: pct(sim.casos_similares.criterio_3_de_5_misma_categoria, 1) }), el("span", { texto: "≥ 3 de 5 similares de la misma categoría" }))),
    criterio(gru.f1_macro >= 0.85, `GRU: F1 macro ≥ 0,85 (${num(gru.f1_macro)})`),
    criterio(gru.f1_macro > base.f1_macro, `GRU mejor que el modelo base (${num(gru.f1_macro)} frente a ${num(base.f1_macro)})`),
    criterio(mlp.f1_macro >= 0.80 && mlp.por_clase["Crítica"].recall >= 0.85, `MLP de prioridad: F1 macro ≥ 0,80 y recall de Crítica ≥ 0,85 (${num(mlp.f1_macro)}; ${num(mlp.por_clase["Crítica"].recall)})`),
    criterio(asi.top1 >= 0.80, `Asignación: técnico esperado en primer lugar ≥ 80 % (${pct(asi.top1)})`),
    criterio(asi.violaciones_de_limite_con_balanceo === 0, `Balanceo: ningún técnico supera su límite si hay otro disponible (${asi.violaciones_de_limite_con_balanceo} violaciones)`),
    criterio(sim.casos_similares.muestra_30.criterio_3_de_5 >= 0.6, `Similitud: ≥ 3 de 5 de la misma categoría; muestra de 30: ${pct(sim.casos_similares.muestra_30.criterio_3_de_5, 0)}, validación completa: ${pct(sim.casos_similares.criterio_3_de_5_misma_categoria)}`),
    el("p", { class: "ayuda", texto: "Nota: la prioridad se explica casi por completo con impacto × urgencia (el MLP iguala a la regla de la matriz); sin esas dos variables el F1 cae a " + num(sinIU.f1_macro) + ". La categoría tiene un techo por ruido de etiqueta (≈ 85 % de acierto estimado en la auditoría)." }),
    el("div", { class: "dos-col" },
      el("div", {}, tablaClases("Categoría: GRU frente al modelo base (test)", [{ nombre: "GRU", datos: gru }, { nombre: "base", datos: base }], CATEGORIAS)),
      el("div", {}, tablaClases("Prioridad: MLP frente a la regla de la matriz", [{ nombre: "MLP", datos: mlp }, { nombre: "matriz", datos: regla }], PRIORIDADES))),
    el("h3", { texto: "Prioridad: variantes y referencias" }),
    el("table", { class: "tabla" }, el("thead", {}, el("tr", {}, el("th", { texto: "Modelo" }), el("th", { class: "num", texto: "F1 macro" }), el("th", { class: "num", texto: "Exactitud" }), el("th", { class: "num", texto: "Recall Crítica" }))),
      el("tbody", {}, Object.entries(pri).filter(([k]) => k !== "historial_mlp_completo").map(([k, v]) => el("tr", {}, el("td", { texto: k }), el("td", { class: "num", texto: num(v.reales.f1_macro) }), el("td", { class: "num", texto: num(v.reales.exactitud) }), el("td", { class: "num", texto: num(v.reales.por_clase["Crítica"].recall) }))))),
    el("div", { class: "dos-col" },
      mapaConfusion(gru.matriz_confusion, CATEGORIAS, "Matriz de confusión · GRU (categoría)"),
      mapaConfusion(base.matriz_confusion, CATEGORIAS, "Matriz de confusión · modelo base"),
      mapaConfusion(mlp.matriz_confusion, PRIORIDADES, "Matriz de confusión · MLP de prioridad")),
    el("h3", { texto: "Acierto de la GRU por fuente de datos" }),
    el("table", { class: "tabla" }, el("thead", {}, el("tr", {}, el("th", { texto: "Fuente" }), el("th", { class: "num", texto: "Tickets" }), el("th", { class: "num", texto: "Exactitud GRU" }), el("th", { class: "num", texto: "Exactitud base" }))),
      el("tbody", {}, Object.entries(cat.gru.por_fuente).map(([f, v]) => el("tr", {}, el("td", { texto: f }), el("td", { class: "num", texto: v.n }), el("td", { class: "num", texto: pct(v.exactitud) }), el("td", { class: "num", texto: pct((cat.base.por_fuente[f] || {}).exactitud || 0) }))))),
    el("h3", { texto: "Asignación y similitud" }),
    el("ul", {}, [
      `Asignación: top-1 ${pct(asi.top1)}, top-3 ${pct(asi.top3)}; con balanceo ${pct(asi.top1_con_balanceo)}; referencia «el más apto sin mirar la carga»: ${pct(asi.referencia_mas_apto_sin_carga)}.`,
      `Violaciones del límite de carga: ${asi.violaciones_de_limite_con_balanceo} con balanceo frente a ${asi.violaciones_de_limite_sin_balanceo} sin balanceo (sobre ${asi.n_test} tickets de prueba).`,
      `Casos similares: precisión@5 ${num(sim.casos_similares.precision_en_5)}; referencia TF-IDF: ≥ 3 de 5 en ${pct(sim.casos_similares.referencia_tfidf.criterio_3_de_5)}.`,
      `Soluciones rápidas: umbral ${sr.umbral}; acierto entre frases de una misma entrada (leave-one-out) ${pct(sr.leave_one_phrase_out.exactitud_top1)}. Es un detector conservador: dispara en ${pct(sr.val.fraccion_que_dispara)} de los tickets largos de validación, y en ${sr.val.categoria_coincide_cuando_dispara === null ? "—" : pct(sr.val.categoria_coincide_cuando_dispara, 0)} de esos casos la categoría coincide.`,
    ].map((t) => el("li", { texto: t }))),
    m.figuras.length ? el("div", {}, el("h3", { texto: "Figuras" }), el("div", { class: "dos-col" }, m.figuras.map((f) => el("a", { href: f, target: "_blank", rel: "noopener" }, el("img", { src: f, alt: f.split("/").pop(), style: "max-width:100%;border:1px solid var(--borde);border-radius:8px", loading: "lazy" }))))) : null);
}

/* ------------------------------------------------------------------ 4 · aprendizaje continuo */
let temporizador = null;
function inicializarCorreccion() {
  $("c-categoria").replaceChildren(...CATEGORIAS.map((c) => el("option", { texto: c })));
  $("c-prioridad").replaceChildren(...PRIORIDADES.map((c) => el("option", { texto: c })));
}
inicializarCorreccion();
function prepararCorreccion() {
  if (!ultimoAnalisis) return;
  mostrar("continuo");
  $("c-titulo").value = ultimoAnalisis.entrada.titulo; $("c-descripcion").value = ultimoAnalisis.entrada.descripcion;
  $("c-categoria").value = ultimoAnalisis.salida.clasificacion.categoria; $("c-prioridad").value = ultimoAnalisis.salida.prioridad.prioridad;
  const rec = ultimoAnalisis.salida.tecnicos.find((t) => t.recomendado);
  if (rec) $("c-tecnico").value = rec.id_tecnico;
}
async function cargarContinuo() {
  const ts = await api("/api/tecnicos");
  const sel = $("c-tecnico"), actual = sel.value;
  sel.replaceChildren(el("option", { value: "", texto: "(sin cambio)" }), ...ts.map((t) => el("option", { value: t.id_tecnico, texto: `${t.id_tecnico} · ${t.nombre}` })));
  sel.value = actual;
  await Promise.all([listarCorrecciones(), listarVersiones(), estadoReentrenamiento()]);
}
async function listarCorrecciones() {
  const lista = await api("/api/correcciones");
  $("n-correcciones").textContent = lista.length;
  $("lista-correcciones").replaceChildren(...(lista.length ? lista.slice(-5).reverse().map((c) => el("div", { texto: `• ${c.titulo} → ${c.categoria_corregida} / ${c.prioridad_corregida}${c.tecnico_reasignado ? " / " + c.tecnico_reasignado : ""}` })) : [el("span", { texto: "Todavía no hay correcciones." })]));
}
$("form-correccion").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const cuerpo = { titulo: $("c-titulo").value.trim(), descripcion: $("c-descripcion").value.trim(), categoria_corregida: $("c-categoria").value, prioridad_corregida: $("c-prioridad").value };
  if ($("c-tecnico").value) cuerpo.tecnico_reasignado = $("c-tecnico").value;
  if (ultimoAnalisis && ultimoAnalisis.entrada.titulo === cuerpo.titulo) { Object.assign(cuerpo, { impacto: ultimoAnalisis.entrada.impacto, urgencia: ultimoAnalisis.entrada.urgencia, usuarios_afectados: ultimoAnalisis.entrada.usuarios_afectados }); }
  try { const r = await post("/api/correcciones", cuerpo); mensaje($("msg-correccion"), `Corrección guardada (${r.total_correcciones} en total).`, "ok"); await listarCorrecciones(); }
  catch (e) { mensaje($("msg-correccion"), e.message, "error"); }
});
async function listarVersiones() {
  const reg = await api("/api/modelos");
  $("estado-modelo").textContent = `Modelos ${reg.activa}`; $("estado-modelo").classList.add("ok");
  const tb = $("tabla-versiones").querySelector("tbody");
  tb.replaceChildren(...reg.versiones.slice().reverse().map((v) => {
    const activa = v.version === reg.activa;
    const f1 = v.metricas.f1_macro_categoria_gru;
    return el("tr", {},
      el("td", {}, el("strong", { texto: v.version }), activa ? el("span", { class: "insignia ok", texto: "activa", style: "margin-left:6px" }) : null),
      el("td", {}, el("span", { class: "insignia " + (v.estado === "publicada" ? "" : "mal"), texto: v.estado })),
      el("td", { class: "num", texto: f1 === undefined ? "—" : num(f1, 4) }), el("td", { class: "num", texto: v.n_correcciones }),
      el("td", { texto: v.nota || "", style: "font-size:12px;color:var(--suave)" }),
      el("td", {}, v.estado === "publicada" && !activa ? el("button", { texto: "Restaurar", onclick: () => activarVersion(v.version) }) : null));
  }));
}
async function activarVersion(v) {
  try { await post("/api/modelos/activar", { version: v }); mensaje($("estado-reentrenamiento"), `Versión ${v} activada.`, "ok"); await listarVersiones(); }
  catch (e) { mensaje($("estado-reentrenamiento"), e.message, "error"); }
}
function pintarComparacion(r) {
  const c = $("comparacion");
  if (!r) { c.replaceChildren(); return; }
  if (!r.vigente) { c.replaceChildren(el("p", { class: "mensaje error", texto: r.motivo || "No se pudo reentrenar." })); return; }
  c.replaceChildren(
    el("h3", { texto: "Comparación de versiones (conjunto de referencia: test, tickets reales)" }),
    el("table", { class: "tabla" }, el("thead", {}, el("tr", {}, el("th", { texto: "" }), el("th", { class: "num", texto: "F1 macro" }), el("th", { texto: "Resultado" }))),
      el("tbody", {},
        el("tr", {}, el("td", { texto: `Vigente ${r.vigente.version}` }), el("td", { class: "num", texto: num(r.vigente.f1_macro, 4) }), el("td", { texto: r.publicada ? "reemplazada" : "se mantiene activa" })),
        el("tr", {}, el("td", { texto: `Nueva ${r.nueva.version}` }), el("td", { class: "num", texto: num(r.nueva.f1_macro, 4) }), el("td", {}, el("span", { class: "insignia " + (r.publicada ? "ok" : "mal"), texto: r.publicada ? "publicada" : "descartada" }))))),
    el("p", { class: "ayuda", texto: `${r.motivo} Correcciones usadas: ${r.n_correcciones}. Diferencia: ${r.diferencia >= 0 ? "+" : ""}${num(r.diferencia, 4)}.` }));
}
async function estadoReentrenamiento() {
  const e = await api("/api/reentrenar/estado");
  const nodo = $("estado-reentrenamiento");
  if (e.estado === "ejecutando") {
    mensaje(nodo, "Reentrenando… " + (e.mensajes[e.mensajes.length - 1] || ""), "");
    $("btn-reentrenar").disabled = true;
    clearTimeout(temporizador); temporizador = setTimeout(estadoReentrenamiento, 3000);
  } else {
    $("btn-reentrenar").disabled = false;
    if (e.estado === "terminado") { mensaje(nodo, e.resultado.publicada ? "Reentrenamiento terminado: versión publicada." : "Reentrenamiento terminado: la versión nueva se descartó.", e.resultado.publicada ? "ok" : ""); pintarComparacion(e.resultado); listarVersiones(); }
    else if (e.estado === "error") { mensaje(nodo, e.resultado.motivo, "error"); }
  }
}
$("btn-reentrenar").addEventListener("click", async () => {
  try {
    await post("/api/reentrenar", { epocas: parseInt($("r-epocas").value || "3", 10) });
    mensaje($("estado-reentrenamiento"), "Reentrenamiento iniciado…", ""); $("btn-reentrenar").disabled = true;
    clearTimeout(temporizador); temporizador = setTimeout(estadoReentrenamiento, 2000);
  } catch (e) { mensaje($("estado-reentrenamiento"), e.message, "error"); }
});

/* ------------------------------------------------------------------ inicio */
(async () => {
  try {
    const s = await api("/api/salud");
    $("estado-modelo").textContent = `Modelos ${s.version_modelos}`; $("estado-modelo").classList.add("ok");
  } catch (e) { $("estado-modelo").textContent = "Sin modelos: " + e.message; }
  cargarEjemplo(EJEMPLOS[0]);
})();

/* ------------------------------------------------------------------ inicio de sesión del Administrador */
$("form-login").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  try {
    const r = await post("/api/auth/login", { correo: $("l-correo").value.trim(), contrasena: $("l-contrasena").value });
    if (r.usuario.rol !== "Administrador") { mensaje($("msg-login"), "Ese usuario no es Administrador.", "error"); return; }
    sessionStorage.setItem(CLAVE_SESION, JSON.stringify({ token: r.token, usuario: r.usuario }));
    $("l-contrasena").value = ""; mensaje($("msg-login"), "", ""); $("dlg-login").close(); pintarSesion();
  } catch (e) { mensaje($("msg-login"), e.message, "error"); }
});
$("btn-cancelar-login").addEventListener("click", () => $("dlg-login").close());
pintarSesion();
