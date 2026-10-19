"use strict";
/* Pantallas de tickets: nuevo ticket, listas, bandeja de Soporte y detalle con el panel "Análisis de la IA". */

/* ------------------------------------------------------------------ nuevo ticket (HU16, HU21, HU22) */
VISTAS["nuevo"] = async (cont) => {
  const titulo = el("input", { required: true, minlength: 3, maxlength: 200, placeholder: "Ej.: No puedo conectarme a la VPN" });
  const descripcion = el("textarea", { rows: 5, required: true, minlength: 3, maxlength: 5000, placeholder: "Describe el problema con tus palabras" });
  const impacto = el("select", {}, ["Bajo", "Medio", "Alto"].map((x) => el("option", { value: x, texto: x, selected: x === "Medio" })));
  const urgencia = el("select", {}, ["Baja", "Media", "Alta"].map((x) => el("option", { value: x, texto: x, selected: x === "Media" })));
  const usuarios = el("input", { type: "number", min: 1, max: 100000, value: 1 });
  const msg = el("div", { class: "mensaje", role: "status" });
  const resultado = el("div");
  const datos = () => ({ titulo: titulo.value.trim(), descripcion: descripcion.value.trim(), impacto: impacto.value, urgencia: urgencia.value,
                         usuarios_afectados: parseInt(usuarios.value || "1", 10) });

  async function registrar(conRapida) {
    try {
      const t = await POST("/api/tickets", { ...datos(), resuelto_con_solucion_rapida: conRapida });
      resultado.replaceChildren();
      mensaje(msg, "");
      const enlace = el("a", { href: "#/ticket/" + t.id, texto: t.codigo });
      cont.replaceChildren(el("div", { class: "cabecera" }, el("div", {}, el("h1", { texto: "Ticket registrado" }))),
        el("div", { class: "exito" }, conRapida
          ? el("div", {}, enlace, " cerrado con la solución rápida. ¡Gracias! Si el problema vuelve, registra un ticket nuevo.")
          : el("div", {}, enlace, " — Clasificado como ", el("b", { texto: t.categoria }), ", prioridad ", el("b", { texto: t.prioridad }), t.tecnico ? [", asignado a ", el("b", { texto: t.tecnico.nombre }), "."] : ". Aún sin técnico disponible.")),
        el("div", { class: "acciones" }, el("button", { class: "primario", texto: "Registrar otro ticket", onclick: () => VISTAS["nuevo"](cont) }),
          el("button", { texto: "Ver el ticket", onclick: () => { location.hash = "#/ticket/" + t.id; } })));
    } catch (e) { mensaje(msg, e.message, "error"); }
  }

  async function analizar(ev) {
    ev.preventDefault();
    mensaje(msg, "Analizando…");
    try {
      const a = await POST("/api/tickets/analizar", datos());
      mensaje(msg, "");
      const sr = a.solucion_rapida;
      resultado.replaceChildren(el("div", { class: "tarjeta" },
        el("h2", { texto: "Análisis de la IA" }),
        el("p", {}, "Parece un problema de ", el("b", { texto: a.clasificacion.categoria }), " (", pct(a.clasificacion.probabilidades[a.clasificacion.categoria]), " de confianza) con prioridad ",
          etqPrioridad(a.prioridad.prioridad), "."),
        sr ? el("div", { class: "solucion-rapida" }, el("strong", { texto: "Prueba esto antes de registrar el ticket: " + sr.problema }),
              el("ol", {}, sr.pasos.map((p) => el("li", { texto: p }))),
              el("p", { class: "suave pequeno", texto: "¿Esto resolvió tu problema?" }),
              el("div", { class: "acciones" }, el("button", { class: "primario", texto: "Sí, se resolvió", onclick: () => registrar(true) }),
                el("button", { texto: "No, registrar el ticket", onclick: () => registrar(false) })))
           : el("div", {}, el("p", { class: "suave", texto: "No hay una solución rápida para este problema. Registra el ticket y un técnico lo atenderá." }),
               el("div", { class: "acciones" }, el("button", { class: "primario", texto: "Registrar ticket", onclick: () => registrar(false) })))));
    } catch (e) { mensaje(msg, e.message, "error"); resultado.replaceChildren(); }
  }

  cont.replaceChildren(el("div", { class: "cabecera" }, el("div", {}, el("h1", { texto: "Nuevo ticket" }), el("p", { class: "suave", texto: "Cuéntanos qué pasa; la IA lo analiza antes de registrarlo." }))),
    el("div", { class: "rejilla" },
      el("form", { class: "tarjeta", onsubmit: analizar }, el("label", {}, "Título", titulo), el("label", {}, "Descripción", descripcion),
        el("div", { class: "fila" }, el("label", {}, "Impacto", impacto), el("label", {}, "Urgencia", urgencia), el("label", {}, "Usuarios afectados", usuarios)),
        el("div", { class: "acciones" }, el("button", { class: "primario", type: "submit", texto: "Analizar" })), msg),
      resultado));
};

/* ------------------------------------------------------------------ listas */
async function listaTickets(cont, { titulo, subtitulo, columnas, filtros }) {
  const selEstado = el("select", {}, el("option", { value: "", texto: "Todos los estados" }), ESTADOS.map((e) => el("option", { value: e, texto: e })));
  const selCat = el("select", {}, el("option", { value: "", texto: "Todas las categorías" }), CATEGORIAS.map((e) => el("option", { value: e, texto: e })));
  const selPri = el("select", {}, el("option", { value: "", texto: "Todas las prioridades" }), PRIORIDADES.map((e) => el("option", { value: e, texto: e })));
  const zona = el("div", { class: "tarjeta" });
  async function cargar() {
    const q = new URLSearchParams();
    if (selEstado.value) q.set("estado", selEstado.value);
    if (filtros && selCat.value) q.set("categoria", selCat.value);
    if (filtros && selPri.value) q.set("prioridad", selPri.value);
    const lista = await GET("/api/tickets?" + q);
    zona.replaceChildren(el("p", { class: "suave pequeno", texto: `${lista.length} ticket${lista.length === 1 ? "" : "s"}` }), tablaTickets(lista, columnas));
  }
  [selEstado, selCat, selPri].forEach((s) => s.addEventListener("change", cargar));
  cont.replaceChildren(el("div", { class: "cabecera" }, el("div", {}, el("h1", { texto: titulo }), el("p", { class: "suave", texto: subtitulo }))),
    el("div", { class: "fila", style: "max-width:720px;margin-bottom:12px" }, selEstado, filtros ? selCat : null, filtros ? selPri : null), zona);
  await cargar();
}
VISTAS["mis-tickets"] = (c) => listaTickets(c, { titulo: "Mis tickets", subtitulo: "Los tickets que has registrado.", columnas: ["tecnico"], filtros: false });
VISTAS["bandeja"] = (c) => listaTickets(c, { titulo: "Bandeja de tickets", subtitulo: "Tus tickets asignados: lo abierto primero, Crítica primero y, dentro de cada prioridad, lo más antiguo.",
                                            columnas: ["solicitante"], filtros: false });
VISTAS["tickets"] = (c) => listaTickets(c, { titulo: "Todos los tickets", subtitulo: "Vista de administración con filtros.", columnas: ["solicitante", "tecnico"], filtros: true });

/* ------------------------------------------------------------------ detalle del ticket */
function panelIA(d) {
  const a = d.analisis;
  if (!a) return el("div", { class: "tarjeta ia" }, el("h2", { texto: "Análisis de la IA" }), el("p", { class: "suave", texto: "Este ticket no tiene análisis guardado." }));
  const corr = d.correcciones || [];
  const rank = a.tecnicos_sugeridos || [];
  return el("div", { class: "tarjeta ia" }, el("h2", { texto: "Análisis de la IA" }),
    corr.length ? el("div", { class: "aviso" }, corr.map((c) => el("div", { texto: `La IA sugirió ${c.categoria_ia} / ${c.prioridad_ia}; corregido a ${c.categoria_correcta} / ${c.prioridad_correcta} por ${c.usuario}.` }))) : null,
    el("div", { class: "rejilla" },
      el("div", {}, el("h3", { texto: "Clasificación (GRU bidireccional)" }), barrasProb(a.prob_categoria, CATEGORIAS),
        el("p", { class: "pequeno" }, "Categoría sugerida: ", el("b", { texto: a.categoria_sugerida }), d.categoria !== a.categoria_sugerida ? ` (actual: ${d.categoria})` : "")),
      el("div", {}, el("h3", { texto: "Prioridad (MLP)" }), barrasProb(a.prob_prioridad, PRIORIDADES),
        el("p", { class: "pequeno" }, "Entradas: impacto ", el("b", { texto: d.impacto }), ", urgencia ", el("b", { texto: d.urgencia }), ", usuarios afectados ", el("b", { texto: d.usuarios_afectados }),
          ". Prioridad sugerida: ", el("b", { texto: a.prioridad_sugerida }), d.prioridad !== a.prioridad_sugerida ? ` (actual: ${d.prioridad})` : ""))),
    el("h3", { texto: "Asignación (MLP + reglas de balanceo)" }),
    el("p", { class: "suave pequeno", texto: "Ranking de técnicos con la carga que tenían cuando se registró el ticket. Si el más adecuado está saturado, la asignación pasa al siguiente." }),
    el("div", { class: "tabla-ancha" }, el("table", { class: "tabla" },
      el("thead", {}, el("tr", {}, ["#", "Técnico", "Aptitud", "Carga / límite", "Saturado", "Adecuación", "Nota"].map((h) => el("th", { texto: h })))),
      el("tbody", {}, rank.map((t, i) => el("tr", {}, el("td", { texto: i + 1 }), el("td", {}, el("b", { texto: t.nombre }), t.recomendado ? [" ", etq("elegido", "ok")] : null),
        el("td", { texto: t.aptitud + "/5" }), el("td", { texto: `${t.carga} / ${t.limite_carga}` }), el("td", {}, t.saturado ? etq("sí", "mal") : "no"), el("td", { texto: pct(t.adecuacion) }),
        el("td", { class: "nota-balanceo", texto: t.nota || "" })))))),
    el("h3", { texto: "Solución rápida" }),
    a.solucion_rapida ? el("div", { class: "solucion-rapida" }, el("strong", { texto: a.solucion_rapida.problema }), " ", etq("similitud " + num(a.solucion_rapida.similitud), "neutra"),
        el("ol", {}, a.solucion_rapida.pasos.map((p) => el("li", { texto: p }))))
      : el("p", { class: "suave", texto: "Ninguna solución rápida supera el umbral de similitud de 0,7." }),
    d.resuelto_con_solucion_rapida ? el("p", { class: "pequeno" }, etq("Resuelto con solución rápida", "ok")) : null,
    el("h3", { texto: "Casos similares" }),
    el("div", {}, (a.similares || []).map((s) => el("div", { class: "similar" }, el("b", { texto: s.titulo }), " ", etq(s.categoria, "neutra"), " ", etqPrioridad(s.prioridad), " ",
      el("span", { class: "suave pequeno", texto: "similitud " + num(s.similitud) }),
      s.solucion ? el("details", {}, el("summary", { texto: "Ver la solución del caso" }), el("div", { class: "pequeno", texto: s.solucion })) : el("div", { class: "suave pequeno", texto: "Sin solución registrada." })))),
    el("p", { class: "pie-ia", texto: `Modelos ${a.version_modelos} · tiempo de inferencia ${Math.round(a.tiempo_ms)} ms` }));
}

VISTAS["ticket"] = async (cont, id) => {
  const rol = sesion.usuario.rol;
  async function pintar(d) {
    const esStaff = rol !== "Usuario";
    const miTecnico = sesion.usuario.tecnico_id;
    const gestiona = rol === "Administrador" || (rol === "Soporte" && d.tecnico && d.tecnico.id === miTecnico);
    const abierto = d.estado === "Abierto" || d.estado === "En progreso";
    const aplicar = (promesa, nodoMsg) => promesa.then(pintar).catch((e) => mensaje(nodoMsg, e.message, "error"));

    // --- acciones
    const msgAcc = el("div", { class: "mensaje", role: "status" });
    const acciones = el("div", { class: "tarjeta" }, el("h2", { texto: "Acciones" }));
    let hayAcciones = false;
    if (esStaff && gestiona && d.estado === "Abierto") {
      hayAcciones = true;
      acciones.append(el("button", { class: "primario", texto: "Pasar a En progreso", onclick: () => aplicar(PUT(`/api/tickets/${id}/estado`, { estado: "En progreso" }), msgAcc) }));
    }
    if (esStaff && gestiona && d.estado === "En progreso") {
      hayAcciones = true;
      const sol = el("textarea", { rows: 3, placeholder: "Solución aplicada (obligatoria)" });
      acciones.append(el("label", {}, "Solución aplicada", sol),
        el("button", { class: "primario", texto: "Marcar como resuelto", onclick: () => aplicar(PUT(`/api/tickets/${id}/estado`, { estado: "Resuelto", solucion: sol.value }), msgAcc) }));
    }
    if (d.estado === "Resuelto" && d.solicitante.id === sesion.usuario.id) {
      hayAcciones = true;
      acciones.append(el("p", { class: "pequeno", texto: "El técnico marcó el ticket como resuelto. ¿Quedó solucionado?" }),
        el("div", { class: "acciones" }, el("button", { class: "primario", texto: "Confirmar y cerrar", onclick: () => aplicar(POST(`/api/tickets/${id}/confirmar`), msgAcc) }),
          el("button", { texto: "Reabrir: sigue el problema", onclick: () => aplicar(POST(`/api/tickets/${id}/reabrir`), msgAcc) })));
    }
    if (esStaff && gestiona) {  // corregir la clasificación de la IA (HU24)
      hayAcciones = true;
      const sc = el("select", {}, CATEGORIAS.map((c) => el("option", { value: c, texto: c, selected: c === d.categoria })));
      const sp = el("select", {}, PRIORIDADES.map((c) => el("option", { value: c, texto: c, selected: c === d.prioridad })));
      acciones.append(el("h3", { texto: "Corregir la clasificación de la IA" }),
        el("div", { class: "fila" }, el("label", {}, "Categoría", sc), el("label", {}, "Prioridad", sp)),
        el("button", { texto: "Guardar corrección", onclick: () => aplicar(POST(`/api/tickets/${id}/corregir`, { categoria: sc.value, prioridad: sp.value }), msgAcc) }),
        el("p", { class: "suave pequeno", texto: "La corrección se usa para reentrenar los modelos." }));
    }
    if (esStaff && gestiona && abierto) {  // reasignación (HU23)
      hayAcciones = true;
      acciones.append(el("h3", { texto: "Reasignar" }));
      acciones.append(el("button", { texto: rol === "Administrador" ? "Reasignar automáticamente (IA)" : "Devolver: que la IA elija otro técnico", onclick: () => aplicar(POST(`/api/tickets/${id}/reasignar`, {}), msgAcc) }));
      if (rol === "Administrador") {
        const sel = el("select", {});
        GET("/api/admin/tecnicos").then((ts) => sel.replaceChildren(...ts.filter((t) => !d.tecnico || t.id !== d.tecnico.id).map((t) =>
          el("option", { value: t.id, texto: `${t.nombre} · aptitud ${t.aptitudes[d.categoria]}/5 · carga ${t.carga}/${t.limite_carga}${t.disponible ? "" : " · no disponible"}` }))));
        acciones.append(el("div", { class: "fila", style: "margin-top:8px" }, el("label", {}, "Elegir técnico (manual)", sel),
          el("div", { style: "align-self:end" }, el("button", { texto: "Reasignar manualmente", onclick: () => aplicar(POST(`/api/tickets/${id}/reasignar`, { tecnico_id: sel.value }), msgAcc) }))));
      }
    }
    if (!hayAcciones) acciones.append(el("p", { class: "suave", texto: d.estado === "Cerrado" ? "Este ticket está cerrado." : "No hay acciones disponibles para ti en este momento." }));
    acciones.append(msgAcc);

    // --- comentarios
    const texto = el("textarea", { rows: 2, placeholder: "Escribe un comentario", maxlength: 3000 });
    const msgCom = el("div", { class: "mensaje" });
    const comentarios = el("div", { class: "tarjeta" }, el("h2", { texto: "Comentarios" }),
      d.comentarios.length ? d.comentarios.map((c) => el("div", { class: "comentario" }, el("div", { class: "quien", texto: `${c.autor} (${c.rol}) · ${fecha(c.creado_en)}` }), el("div", { texto: c.texto })))
                           : el("p", { class: "suave", texto: "Aún no hay comentarios." }),
      texto, el("div", { class: "acciones" }, el("button", { texto: "Comentar", onclick: () => { if (texto.value.trim()) aplicar(POST(`/api/tickets/${id}/comentarios`, { texto: texto.value }), msgCom); } })), msgCom);

    // --- datos del ticket
    const fila = (k, v) => el("tr", {}, el("th", { texto: k }), el("td", {}, v));
    const datos = el("div", { class: "tarjeta" }, el("h2", { texto: "Datos" }), el("table", { class: "tabla" }, el("tbody", {},
      fila("Solicitante", d.solicitante.nombre), fila("Técnico", d.tecnico ? `${d.tecnico.nombre} (${d.tecnico.area})` : d.resuelto_con_solucion_rapida ? "No necesario (solución rápida)" : "Sin asignar"),
      fila("Impacto / urgencia", `${d.impacto} / ${d.urgencia} · ${d.usuarios_afectados} usuario(s)`), fila("Creado", fecha(d.creado_en)), fila("Actualizado", fecha(d.actualizado_en)),
      fila("Resuelto", fecha(d.resuelto_en)), fila("Cerrado", fecha(d.cerrado_en)))));
    const historial = el("div", { class: "tarjeta" }, el("h2", { texto: "Historial" }), el("ul", { class: "cronologia" }, d.historial.map((h) =>
      el("li", {}, el("b", { texto: h.accion }), " · ", h.usuario, " · ", el("span", { class: "suave", texto: fecha(h.creado_en) }), h.detalle ? el("div", { class: "suave pequeno", texto: h.detalle }) : null))));

    cont.replaceChildren(
      el("div", { class: "cabecera" }, el("div", {}, el("p", { class: "suave pequeno" }, el("a", { href: "#", onclick: (ev) => { ev.preventDefault(); history.back(); }, texto: "← Volver" })),
        el("h1", { texto: `${d.codigo} · ${d.titulo}` }), el("div", {}, etqEstado(d.estado), " ", etqPrioridad(d.prioridad), " ", etq(d.categoria, "neutra")))),
      el("div", { class: "rejilla" }, el("div", {}, el("div", { class: "tarjeta" }, el("h2", { texto: "Descripción" }), el("p", { style: "white-space:pre-wrap", texto: d.descripcion }),
          d.solucion ? [el("h3", { texto: "Solución" }), el("p", { style: "white-space:pre-wrap", texto: d.solucion })] : null), acciones, comentarios),
        el("div", {}, datos, historial)),
      esStaff ? panelIA(d) : null);
  }
  await pintar(await GET("/api/tickets/" + id));
};
