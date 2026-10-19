"use strict";
/* Núcleo de la interfaz: utilidades, API, sesión, inicio de sesión, menú por rol y rutas por #hash.
   Todo el texto que viene del servidor se inserta con textContent (nunca como HTML). */

const CATEGORIAS = ["Hardware", "Software", "Red", "Accesos", "Correo", "Seguridad"];
const PRIORIDADES = ["Baja", "Media", "Alta", "Crítica"];
const ESTADOS = ["Abierto", "En progreso", "Resuelto", "Cerrado"];
const VISTAS = {};            // nombre de ruta -> función(contenedor, parámetro)
const sesion = { token: null, usuario: null };

/* ------------------------------------------------------------------ utilidades */
function el(tag, props, ...hijos) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (k === "class") e.className = v;
    else if (k === "texto") e.textContent = v;
    else if (k === "value") e.value = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v !== false && v !== null && v !== undefined) e.setAttribute(k, v === true ? "" : v);
  }
  for (const h of hijos.flat(2)) if (h !== null && h !== undefined && h !== false) e.append(h.nodeType ? h : document.createTextNode(String(h)));
  return e;
}
const pct = (x, d = 0) => (x * 100).toFixed(d).replace(".", ",") + " %";
const num = (x, d = 2) => Number(x).toFixed(d).replace(".", ",");
function fecha(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
function etq(texto, clase) { return el("span", { class: "etq " + (clase || ""), texto }); }
const etqPrioridad = (p) => etq(p, "p-" + p);
const etqEstado = (e) => etq(e, "e-" + e.replace(" ", "-"));
function mensaje(nodo, texto, tipo) { nodo.textContent = texto || ""; nodo.className = "mensaje " + (tipo || ""); }
function horas(h) { return h === null || h === undefined ? "—" : h < 1 ? Math.round(h * 60) + " min" : h < 48 ? num(h, 1) + " h" : num(h / 24, 1) + " días"; }

/* ------------------------------------------------------------------ sesión y API */
function guardarSesion() {
  try { sessionStorage.setItem("sesion-tickets", JSON.stringify(sesion)); } catch (e) { /* sin almacenamiento: se pedirá iniciar sesión al recargar */ }
}
function leerSesion() {
  try { const s = JSON.parse(sessionStorage.getItem("sesion-tickets") || "null"); if (s && s.token) Object.assign(sesion, s); } catch (e) { /* ignorar */ }
}
function cerrarSesion() {
  sesion.token = null; sesion.usuario = null;
  try { sessionStorage.removeItem("sesion-tickets"); } catch (e) { /* ignorar */ }
  location.hash = "";
  pintarLogin();
}
async function api(ruta, opciones = {}) {
  const cabeceras = { "Content-Type": "application/json" };
  if (sesion.token) cabeceras.Authorization = "Bearer " + sesion.token;
  const r = await fetch(ruta, { ...opciones, headers: cabeceras, body: opciones.body ? JSON.stringify(opciones.body) : undefined });
  let cuerpo = null;
  try { cuerpo = await r.json(); } catch (e) { /* sin cuerpo */ }
  if (r.status === 401 && sesion.token) { cerrarSesion(); throw new Error("Tu sesión terminó. Inicia sesión de nuevo."); }
  if (!r.ok) {
    const d = cuerpo && cuerpo.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => `${(x.loc || []).slice(-1)[0]}: ${x.msg}`).join("; ") : `Error ${r.status}`);
  }
  return cuerpo;
}
const GET = (ruta) => api(ruta);
const POST = (ruta, body) => api(ruta, { method: "POST", body: body || {} });
const PUT = (ruta, body) => api(ruta, { method: "PUT", body });

/* ------------------------------------------------------------------ inicio de sesión */
const DEMO = [["Administrador", "admin@soporte.local", "Admin123"], ["Usuario (Ana)", "ana.torres@empresa.local", "Usuario123"],
              ["Soporte (Marcela, redes)", "marcela.vega@soporte.local", "Soporte123"], ["Soporte (Mateo)", "mateo.quispe@soporte.local", "Soporte123"]];
function pintarLogin() {
  const app = document.getElementById("app");
  const correo = el("input", { type: "email", required: true, autocomplete: "username", placeholder: "correo@empresa.local" });
  const clave = el("input", { type: "password", required: true, autocomplete: "current-password" });
  const msg = el("div", { class: "mensaje", role: "alert" });
  const entrar = async (ev) => {
    ev && ev.preventDefault();
    try {
      const r = await POST("/api/auth/login", { correo: correo.value.trim(), contrasena: clave.value });
      sesion.token = r.token; sesion.usuario = r.usuario; guardarSesion();
      location.hash = r.usuario.rol === "Administrador" ? "#/panel" : r.usuario.rol === "Soporte" ? "#/bandeja" : "#/nuevo";
      pintarEstructura();
    } catch (e) { mensaje(msg, e.message, "error"); }
  };
  app.replaceChildren(el("div", { class: "login" }, el("div", { class: "caja" },
    el("h1", { texto: "Mesa de ayuda TI" }), el("p", { class: "suave", texto: "Inicia sesión para continuar" }),
    el("form", { onsubmit: entrar }, el("label", {}, "Correo", correo), el("label", {}, "Contraseña", clave),
      el("button", { class: "primario", type: "submit", style: "width:100%", texto: "Entrar" }), msg),
    el("div", { class: "demo" }, el("div", { texto: "Cuentas de demostración (clic para rellenar):" }),
      DEMO.map(([n, c, p]) => el("button", { type: "button", texto: n, onclick: () => { correo.value = c; clave.value = p; entrar(); } }))))));
}

/* ------------------------------------------------------------------ estructura, menú y rutas */
function menuPorRol(rol) {
  if (rol === "Administrador") return [["panel", "Panel de métricas"], ["tickets", "Todos los tickets"], ["nuevo", "Nuevo ticket"], ["tecnicos", "Técnicos"],
                                      ["usuarios", "Usuarios"], ["modelos", "Modelos de IA"]];
  if (rol === "Soporte") return [["bandeja", "Bandeja de tickets"]];
  return [["nuevo", "Nuevo ticket"], ["mis-tickets", "Mis tickets"]];
}
function pintarEstructura() {
  const u = sesion.usuario;
  const menu = menuPorRol(u.rol);
  const lateral = el("nav", { class: "lateral", "aria-label": "Menú principal" }, el("div", { class: "marca", texto: "Mesa de ayuda TI" }),
    menu.map(([ruta, texto]) => el("a", { href: "#/" + ruta, "data-ruta": ruta, texto })),
    u.rol === "Administrador" ? el("a", { href: "/laboratorio", target: "_blank", rel: "noopener", texto: "Laboratorio de modelos ↗" }) : null,
    el("div", { class: "sesion" }, el("b", { texto: u.nombre }), el("span", { texto: u.rol + (u.tecnico_id ? " · " + u.tecnico_id : "") }),
      el("button", { texto: "Cerrar sesión", onclick: cerrarSesion })));
  document.getElementById("app").replaceChildren(el("div", { class: "estructura" }, lateral, el("main", { id: "contenido", tabindex: "-1" })));
  navegar();
}
async function navegar() {
  if (!sesion.usuario) return;
  const [, ruta, param] = (location.hash || "").match(/^#\/([^/]+)\/?(.*)$/) || [];
  const permitidas = menuPorRol(sesion.usuario.rol).map((m) => m[0]);
  const nombre = ruta === "ticket" ? "ticket" : permitidas.includes(ruta) ? ruta : permitidas[0];
  document.querySelectorAll(".lateral a[data-ruta]").forEach((a) => a.classList.toggle("activo", a.dataset.ruta === nombre ||
    (nombre === "ticket" && a.dataset.ruta === (sesion.usuario.rol === "Usuario" ? "mis-tickets" : sesion.usuario.rol === "Soporte" ? "bandeja" : "tickets"))));
  const cont = document.getElementById("contenido");
  cont.replaceChildren(el("p", { class: "suave", texto: "Cargando…" }));
  try { await VISTAS[nombre](cont, param); }
  catch (e) { cont.replaceChildren(el("div", { class: "tarjeta" }, el("h2", { texto: "No se pudo cargar" }), el("p", { class: "mensaje error", texto: e.message }))); }
}
window.addEventListener("hashchange", navegar);

async function iniciar() {
  leerSesion();
  if (sesion.token) {
    try { sesion.usuario = await GET("/api/auth/yo"); guardarSesion(); pintarEstructura(); return; }
    catch (e) { sesion.token = null; sesion.usuario = null; }
  }
  pintarLogin();
}

/* ------------------------------------------------------------------ piezas reutilizables */
function barrasProb(probs, orden) {
  const top = Object.entries(probs).sort((a, b) => b[1] - a[1])[0][0];
  return el("div", { class: "barras" }, orden.map((c) => el("div", { class: "barra-p" + (c === top ? " top" : "") },
    el("span", { texto: c }), el("div", { class: "pista" }, el("div", { class: "relleno", style: `width:${(probs[c] * 100).toFixed(1)}%` })),
    el("span", { class: "derecha", texto: pct(probs[c], 1) }))));
}
function tablaTickets(tickets, mostrar) {
  if (!tickets.length) return el("p", { class: "suave", texto: "No hay tickets para mostrar." });
  const col = (n) => mostrar.includes(n);
  return el("div", { class: "tabla-ancha" }, el("table", { class: "tabla" },
    el("thead", {}, el("tr", {}, el("th", { texto: "Código" }), el("th", { texto: "Título" }), el("th", { texto: "Categoría" }), el("th", { texto: "Prioridad" }), el("th", { texto: "Estado" }),
      col("solicitante") ? el("th", { texto: "Solicitante" }) : null, col("tecnico") ? el("th", { texto: "Técnico" }) : null, el("th", { texto: "Creado" }))),
    el("tbody", {}, tickets.map((t) => el("tr", { class: "clic", tabindex: 0, onclick: () => { location.hash = "#/ticket/" + t.id; }, onkeydown: (ev) => { if (ev.key === "Enter") location.hash = "#/ticket/" + t.id; } },
      el("td", { texto: t.codigo }), el("td", { texto: t.titulo }), el("td", { texto: t.categoria }), el("td", {}, etqPrioridad(t.prioridad)), el("td", {}, etqEstado(t.estado)),
      col("solicitante") ? el("td", { texto: t.solicitante.nombre }) : null,
      col("tecnico") ? el("td", { texto: t.tecnico ? t.tecnico.nombre : (t.resuelto_con_solucion_rapida ? "Solución rápida" : "Sin asignar") }) : null,
      el("td", { texto: fecha(t.creado_en) }))))));
}
