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
/* Iconos de línea (constantes propias, no contenido del servidor) */
const ICONOS = {
  panel: '<path d="M3 3v18h18"/><path d="M7 16v-5"/><path d="M12 16V8"/><path d="M17 16V6"/>',
  bandeja: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
  documento: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>',
  nuevo: '<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>',
  tecnicos: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
  usuarios: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  rayo: '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>',
  modelos: '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>',
  laboratorio: '<path d="M9 3h6M10 3v6.5L4.5 19a1.5 1.5 0 0 0 1.3 2.25h12.4A1.5 1.5 0 0 0 19.5 19L14 9.5V3"/><path d="M7.5 15h9"/>',
  salir: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  marca: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="m4.93 4.93 4.24 4.24M14.83 14.83l4.24 4.24M14.83 9.17l4.24-4.24M4.93 19.07l4.24-4.24"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
};
function icono(nombre) {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  s.setAttribute("viewBox", "0 0 24 24"); s.setAttribute("class", "icono"); s.setAttribute("aria-hidden", "true");
  s.innerHTML = ICONOS[nombre] || "";
  return s;
}
const logo = () => el("span", { class: "logo" }, icono("marca"));
const marca = (sub) => el("div", { class: "marca" }, logo(), el("div", {}, "Mesa de ayuda TI", el("small", { texto: sub || "Soporte con inteligencia artificial" })));
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
  const ventajas = [["Clasificación y prioridad automáticas", "Una red GRU y un perceptrón multicapa analizan cada ticket en milisegundos."],
                    ["Asignación equilibrada", "El técnico más apto con capacidad disponible, sin saturar a nadie."],
                    ["Soluciones rápidas", "Los problemas comunes se resuelven al momento, sin esperar a Soporte."],
                    ["Aprende de las correcciones", "Cada corrección mejora la siguiente versión de los modelos."]];
  app.replaceChildren(el("div", { class: "login" },
    el("section", { class: "portada", "aria-hidden": "true" },
      el("div", { class: "logo-grande" }, logo(), "Mesa de ayuda TI"),
      el("div", {}, el("h2", { texto: "Tickets de TI atendidos más rápido, con ayuda de la IA" }),
        el("p", { texto: "Registra un problema con tus palabras: el sistema lo clasifica, lo prioriza y lo asigna al técnico adecuado." }),
        el("ul", {}, ventajas.map(([t, d]) => el("li", {}, icono("check"), el("div", {}, el("b", { texto: t }), el("div", { texto: d })))))),
      el("div", { class: "pie", texto: "Instalación local · los datos no salen de tu servidor" })),
    el("div", { class: "lado-form" }, el("div", { class: "caja" },
      el("div", { class: "movil-marca" }, marca()),
      el("h1", { texto: "Inicia sesión" }), el("p", { class: "suave", texto: "Usa tu correo de la empresa." }),
      el("form", { onsubmit: entrar }, el("label", {}, "Correo", correo), el("label", {}, "Contraseña", clave),
        el("button", { class: "primario", type: "submit", texto: "Entrar" }), msg),
      el("div", { class: "demo" }, el("div", { texto: "Cuentas de demostración (clic para entrar):" }),
        el("div", { class: "botones" }, DEMO.map(([n, c, p]) => el("button", { type: "button", texto: n, onclick: () => { correo.value = c; clave.value = p; entrar(); } }))))))));
}

/* ------------------------------------------------------------------ estructura, menú y rutas */
function menuPorRol(rol) {
  if (rol === "Administrador") return [["panel", "Panel de métricas"], ["tickets", "Todos los tickets"], ["nuevo", "Nuevo ticket"], ["tecnicos", "Técnicos"],
                                      ["usuarios", "Usuarios"], ["soluciones", "Soluciones rápidas"], ["modelos", "Modelos de IA"]];
  if (rol === "Soporte") return [["bandeja", "Bandeja de tickets"], ["panel", "Mi resumen"]];
  return [["nuevo", "Nuevo ticket"], ["mis-tickets", "Mis tickets"]];
}
const ICONO_RUTA = { panel: "panel", tickets: "bandeja", bandeja: "bandeja", "mis-tickets": "documento", nuevo: "nuevo", tecnicos: "tecnicos",
                     usuarios: "usuarios", soluciones: "rayo", modelos: "modelos" };
const ADMINISTRACION = ["tecnicos", "usuarios", "soluciones", "modelos"];  // rutas que van bajo el título «Administración»
function iniciales(nombre) { return nombre.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join(""); }
function menuMovil(abrir) {
  const e = document.querySelector(".estructura");
  if (!e) return;
  e.classList.toggle("menu-abierto", abrir);
  const b = document.querySelector(".boton-menu");
  if (b) b.setAttribute("aria-expanded", abrir ? "true" : "false");
}
function pintarEstructura() {
  const u = sesion.usuario;
  const menu = menuPorRol(u.rol);
  const enlaces = [];
  menu.forEach(([ruta, texto]) => {
    if (ruta === ADMINISTRACION.find((r) => menu.some((m) => m[0] === r))) enlaces.push(el("div", { class: "seccion", texto: "Administración" }));
    enlaces.push(el("a", { href: "#/" + ruta, "data-ruta": ruta }, icono(ICONO_RUTA[ruta]), el("span", { texto })));
  });
  const lateral = el("nav", { class: "lateral", id: "menu-lateral", "aria-label": "Menú principal" }, marca(),
    el("div", { class: "seccion", texto: u.rol === "Usuario" ? "Mis solicitudes" : "Operación" }), enlaces,
    u.rol === "Administrador" ? [el("div", { class: "seccion", texto: "Herramientas" }),
      el("a", { href: "/laboratorio", target: "_blank", rel: "noopener" }, icono("laboratorio"), el("span", { texto: "Laboratorio de modelos ↗" }))] : null,
    el("div", { class: "sesion" }, el("span", { class: "avatar", "aria-hidden": "true", texto: iniciales(u.nombre) }), el("b", { texto: u.nombre, title: u.correo }),
      el("span", { texto: u.rol + (u.tecnico_id ? " · " + u.tecnico_id : "") }),
      el("button", { onclick: cerrarSesion }, icono("salir"), "Cerrar sesión")));
  const superior = el("header", { class: "barra-superior" },
    el("button", { class: "boton-menu", "aria-label": "Abrir el menú", "aria-controls": "menu-lateral", "aria-expanded": "false", onclick: () => menuMovil(true) }, icono("menu")),
    marca(u.rol));
  const velo = el("div", { class: "velo", onclick: () => menuMovil(false) });
  document.getElementById("app").replaceChildren(el("div", { class: "estructura" }, lateral, velo,
    el("main", {}, superior, el("div", { id: "contenido", tabindex: "-1" }))));
  navegar();
}
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") menuMovil(false); });
async function navegar() {
  if (!sesion.usuario) return;
  const [, ruta, param] = (location.hash || "").match(/^#\/([^/]+)\/?(.*)$/) || [];
  const permitidas = menuPorRol(sesion.usuario.rol).map((m) => m[0]);
  const nombre = ruta === "ticket" ? "ticket" : permitidas.includes(ruta) ? ruta : permitidas[0];
  document.querySelectorAll(".lateral a[data-ruta]").forEach((a) => a.classList.toggle("activo", a.dataset.ruta === nombre ||
    (nombre === "ticket" && a.dataset.ruta === (sesion.usuario.rol === "Usuario" ? "mis-tickets" : sesion.usuario.rol === "Soporte" ? "bandeja" : "tickets"))));
  menuMovil(false);
  window.scrollTo(0, 0);
  // cada navegación pinta en su propio contenedor: si una vista lenta termina después de cambiar de pantalla, no pisa la nueva
  const cont = el("div", { class: "vista" }, el("p", { class: "suave", texto: "Cargando…" }));
  document.getElementById("contenido").replaceChildren(cont);
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
  return el("div", { class: "tabla-ancha" }, el("table", { class: "tabla tabla-tickets" },
    el("thead", {}, el("tr", {}, el("th", { texto: "Código" }), el("th", { texto: "Título" }), el("th", { texto: "Categoría" }), el("th", { texto: "Prioridad" }), el("th", { texto: "Estado" }),
      col("solicitante") ? el("th", { texto: "Solicitante" }) : null, col("tecnico") ? el("th", { texto: "Técnico" }) : null, el("th", { texto: "Creado" }))),
    el("tbody", {}, tickets.map((t) => el("tr", { class: "clic", tabindex: 0, onclick: () => { location.hash = "#/ticket/" + t.id; }, onkeydown: (ev) => { if (ev.key === "Enter") location.hash = "#/ticket/" + t.id; } },
      el("td", { class: "codigo", texto: t.codigo }), el("td", { class: "titulo", texto: t.titulo }), el("td", { "data-et": "Categoría", texto: t.categoria }),
      el("td", { "data-et": "Prioridad" }, etqPrioridad(t.prioridad)), el("td", { "data-et": "Estado" }, etqEstado(t.estado)),
      col("solicitante") ? el("td", { "data-et": "Solicitante", texto: t.solicitante.nombre }) : null,
      col("tecnico") ? el("td", { "data-et": "Técnico", texto: t.tecnico ? t.tecnico.nombre : (t.resuelto_con_solucion_rapida ? "Solución rápida" : "Sin asignar") }) : null,
      el("td", { "data-et": "Creado", texto: fecha(t.creado_en) }))))));
}
