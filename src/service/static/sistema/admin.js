"use strict";
/* Pantallas de administración: técnicos, usuarios, modelos de IA y panel de métricas (fases 7 y 8). */

/* ------------------------------------------------------------------ técnicos (HU15) */
VISTAS["tecnicos"] = async (cont) => {
  const lista = await GET("/api/admin/tecnicos");
  const msg = el("div", { class: "mensaje", role: "status" });
  const filas = lista.map((t) => {
    const limite = el("input", { type: "number", min: 1, max: 100, value: t.limite_carga, "aria-label": "Límite de " + t.nombre });
    const disp = el("input", { type: "checkbox", checked: t.disponible, "aria-label": "Disponible: " + t.nombre, style: "width:auto" });
    const apt = CATEGORIAS.map((c) => el("input", { type: "number", min: 1, max: 5, value: t.aptitudes[c], "data-cat": c, "aria-label": `${t.nombre}: aptitud en ${c}` }));
    const guardar = async () => {
      const aptitudes = {};
      apt.forEach((i) => { aptitudes[i.dataset.cat] = parseInt(i.value, 10); });
      try {
        await PUT("/api/admin/tecnicos/" + t.id, { limite_carga: parseInt(limite.value, 10), disponible: disp.checked, aptitudes });
        mensaje(msg, `Cambios de ${t.nombre} guardados. La IA los usará en la próxima asignación.`, "ok");
        VISTAS["tecnicos"](cont);
      } catch (e) { mensaje(msg, e.message, "error"); }
    };
    return el("tr", {}, el("td", {}, el("b", { texto: t.nombre }), el("div", { class: "suave pequeno", texto: `${t.id} · ${t.area}` })),
      el("td", {}, el("div", { class: "hbarra carga", style: "grid-template-columns:1fr;margin:0" },
        el("div", { class: "pista" }, el("div", { class: "relleno" + (t.carga >= t.limite_carga ? " lleno" : t.carga >= 0.8 * t.limite_carga ? " alto" : ""), style: `width:${Math.min(100, 100 * t.carga / t.limite_carga)}%` })),
        el("span", { class: "suave pequeno", texto: `${t.carga} abiertos` }))),
      el("td", {}, limite), el("td", {}, disp), ...apt.map((i) => el("td", {}, i)), el("td", {}, el("button", { class: "primario", texto: "Guardar", onclick: guardar })));
  });
  cont.replaceChildren(el("div", { class: "cabecera" }, el("div", {}, el("h1", { texto: "Técnicos" }),
      el("p", { class: "suave", texto: "El límite de carga, la disponibilidad y las aptitudes (1 a 5) los usa la IA para asignar. Un técnico no disponible se trata como saturado." }))),
    el("div", { class: "tarjeta tabla-ancha" }, el("table", { class: "tabla" },
      el("thead", {}, el("tr", {}, el("th", { texto: "Técnico" }), el("th", { texto: "Carga actual" }), el("th", { texto: "Límite" }), el("th", { texto: "Disponible" }),
        ...CATEGORIAS.map((c) => el("th", { texto: c })), el("th"))), el("tbody", {}, filas)), msg));
};

/* ------------------------------------------------------------------ usuarios (HU14) */
VISTAS["usuarios"] = async (cont) => {
  const lista = await GET("/api/usuarios");
  const msg = el("div", { class: "mensaje", role: "status" });
  const nombre = el("input", { required: true, minlength: 2 });
  const correo = el("input", { type: "email", required: true });
  const clave = el("input", { type: "text", required: true, minlength: 6, placeholder: "mínimo 6 caracteres" });
  const rol = el("select", {}, ["Usuario", "Soporte", "Administrador"].map((r) => el("option", { value: r, texto: r })));
  const crear = async (ev) => {
    ev.preventDefault();
    try { await POST("/api/usuarios", { nombre: nombre.value, correo: correo.value, contrasena: clave.value, rol: rol.value }); VISTAS["usuarios"](cont); }
    catch (e) { mensaje(msg, e.message, "error"); }
  };
  const filas = lista.map((u) => {
    const r = el("select", {}, ["Usuario", "Soporte", "Administrador"].map((x) => el("option", { value: x, texto: x, selected: x === u.rol })));
    const act = el("input", { type: "checkbox", checked: u.activo, style: "width:auto", "aria-label": "Activo: " + u.nombre });
    const nueva = el("input", { type: "text", placeholder: "nueva contraseña", "aria-label": "Nueva contraseña de " + u.nombre });
    const guardar = async () => {
      const cambios = { rol: r.value, activo: act.checked };
      if (nueva.value) cambios.contrasena = nueva.value;
      try { await PUT("/api/usuarios/" + u.id, cambios); mensaje(msg, `Usuario ${u.nombre} actualizado.`, "ok"); VISTAS["usuarios"](cont); }
      catch (e) { mensaje(msg, e.message, "error"); }
    };
    return el("tr", {}, el("td", {}, el("b", { texto: u.nombre }), u.tecnico_id ? el("span", { class: "suave pequeno", texto: " · técnico " + u.tecnico_id }) : null), el("td", { texto: u.correo }),
      el("td", {}, r), el("td", {}, act), el("td", {}, nueva), el("td", {}, el("button", { texto: "Guardar", onclick: guardar })));
  });
  cont.replaceChildren(el("div", { class: "cabecera" }, el("div", {}, el("h1", { texto: "Usuarios" }), el("p", { class: "suave", texto: "Crea usuarios, cambia su rol, desactívalos o restablece su contraseña." }))),
    el("form", { class: "tarjeta", onsubmit: crear }, el("h2", { texto: "Nuevo usuario" }),
      el("div", { class: "fila" }, el("label", {}, "Nombre", nombre), el("label", {}, "Correo", correo), el("label", {}, "Contraseña", clave), el("label", {}, "Rol", rol)),
      el("button", { class: "primario", type: "submit", texto: "Crear usuario" })),
    el("div", { class: "tarjeta tabla-ancha" }, el("table", { class: "tabla" }, el("thead", {}, el("tr", {}, ["Nombre", "Correo", "Rol", "Activo", "Contraseña", ""].map((h) => el("th", { texto: h })))), el("tbody", {}, filas)), msg));
};

/* ------------------------------------------------------------------ soluciones rápidas (HU26) */
VISTAS["soluciones"] = async (cont) => {
  const lista = await GET("/api/soluciones");
  const msg = el("div", { class: "mensaje", role: "status" });
  const filtro = el("input", { type: "search", placeholder: "Buscar por problema, frase o categoría", "aria-label": "Buscar soluciones" });
  const cuerpo = el("tbody");
  const guardar = async (s, cambios) => {
    try { await PUT("/api/soluciones/" + s.id, cambios); VISTAS["soluciones"](cont); }
    catch (e) { mensaje(msg, e.message, "error"); }
  };
  const editor = (s, fila) => {
    if (fila.nextSibling && fila.nextSibling.classList.contains("editor")) { fila.nextSibling.remove(); return; }
    const problema = el("input", { value: s.problema, maxlength: 200 });
    const categoria = el("select", {}, CATEGORIAS.map((c) => el("option", { value: c, texto: c, selected: c === s.categoria })));
    const frases = el("textarea", { rows: 4 }); frases.value = s.frases_ejemplo.join("\n");
    const pasos = el("textarea", { rows: 5 }); pasos.value = s.pasos.join("\n");
    const lineas = (t) => t.value.split("\n").map((x) => x.trim()).filter(Boolean);
    const ed = el("tr", { class: "editor" }, el("td", { colspan: 5 },
      el("div", { class: "fila" }, el("label", {}, "Problema", problema), el("label", {}, "Categoría", categoria)),
      el("label", {}, "Frases de ejemplo (una por línea)", frases), el("label", {}, "Pasos (uno por línea)", pasos),
      el("div", { class: "acciones" }, el("button", { class: "primario", texto: "Guardar cambios", onclick: () => guardar(s, { problema: problema.value, categoria: categoria.value, frases_ejemplo: lineas(frases), pasos: lineas(pasos) }) }),
        el("button", { texto: "Cancelar", onclick: () => ed.remove() }))));
    fila.after(ed);
  };
  const pintar = () => {
    const q = filtro.value.trim().toLowerCase();
    cuerpo.replaceChildren(...lista.slice().reverse().filter((s) => !q || [s.id, s.problema, s.categoria, ...s.frases_ejemplo].join(" ").toLowerCase().includes(q)).map((s) => {
      const fila = el("tr", { class: s.activa ? "" : "inactiva" },
        el("td", {}, el("b", { texto: s.id }), s.origen === "ticket" ? el("div", { class: "suave pequeno", texto: `de ${s.ticket_origen} · ${s.creada_por}` }) : null),
        el("td", {}, el("div", { texto: s.problema }), el("div", { class: "suave pequeno", texto: `${s.frases_ejemplo.length} frases · ${s.pasos.length} pasos` })),
        el("td", {}, etq(s.categoria, "neutra")), el("td", {}, etq(s.activa ? "activa" : "inactiva", s.activa ? "ok" : "mal")),
        el("td", {}, el("div", { class: "acciones" }, el("button", { texto: "Editar", onclick: () => editor(s, fila) }),
          el("button", { texto: s.activa ? "Desactivar" : "Activar", onclick: () => guardar(s, { activa: !s.activa }) }))));
      return fila;
    }));
  };
  filtro.addEventListener("input", pintar);
  pintar();
  const activas = lista.filter((s) => s.activa).length, deTickets = lista.filter((s) => s.origen === "ticket").length;
  cont.replaceChildren(el("div", { class: "cabecera" }, el("div", {}, el("h1", { texto: "Soluciones rápidas" }),
      el("p", { class: "suave", texto: `${activas} activas de ${lista.length} (${deTickets} agregadas desde tickets). La IA sugiere una solución activa cuando el ticket se parece a sus frases de ejemplo. Para agregar una, abre un ticket Resuelto o Cerrado y pulsa «Guardar como solución rápida». Los cambios se aplican al instante.` }))),
    el("div", { class: "tarjeta tabla-ancha" }, filtro, el("table", { class: "tabla" },
      el("thead", {}, el("tr", {}, ["Id", "Problema", "Categoría", "Estado", ""].map((h) => el("th", { texto: h })))), cuerpo), msg));
};

/* ------------------------------------------------------------------ modelos de IA (HU27) */
let temporizadorModelos = null;
VISTAS["modelos"] = async (cont) => {
  clearTimeout(temporizadorModelos);
  const [reg, met, corr, est] = await Promise.all([GET("/api/modelos"), GET("/api/metricas"), GET("/api/correcciones"), GET("/api/reentrenar/estado")]);
  const msg = el("div", { class: "mensaje", role: "status" });
  const zonaProgreso = el("div");
  const r = met.resumen, cat = met.categoria, pri = met.prioridad, asi = met.asignacion;
  const kpi = (v, t) => el("div", { class: "kpi" }, el("b", { texto: v }), el("span", { texto: t }));
  const epocas = el("input", { type: "number", min: 1, max: 30, value: 3, style: "width:90px" });
  const btn = el("button", { class: "primario", texto: "Reentrenar con las correcciones" });
  const faltan = Math.max(0, (est.minimo_correcciones || 0) - (est.correcciones_validas || 0));

  function pintarEstado(e) {
    if (e.estado === "ejecutando") {
      zonaProgreso.replaceChildren(el("div", { class: "aviso" }, "Reentrenando… ", el("b", { texto: e.mensajes[e.mensajes.length - 1] || "iniciando" })));
      btn.disabled = true;
      temporizadorModelos = setTimeout(async () => { if (location.hash === "#/modelos") pintarEstado(await GET("/api/reentrenar/estado")); }, 3000);
      return;
    }
    btn.disabled = faltan > 0;
    if (e.estado === "terminado" || e.estado === "error") {
      const x = e.resultado || {};
      zonaProgreso.replaceChildren(el("div", { class: x.publicada ? "exito" : "aviso" },
        el("b", { texto: x.publicada ? "Versión publicada" : "Versión no publicada" }), el("div", { texto: x.motivo || "" }),
        x.vigente ? el("div", { class: "pequeno", texto: `F1 macro de categoría en el conjunto de referencia: vigente ${x.vigente.version} ${num(x.vigente.f1_macro, 4)} → nueva ${x.nueva.version} ${num(x.nueva.f1_macro, 4)} (diferencia ${x.diferencia >= 0 ? "+" : ""}${num(x.diferencia, 4)}). Correcciones usadas: ${x.n_correcciones}.` }) : null));
    }
  }
  btn.addEventListener("click", async () => {
    try { await POST("/api/reentrenar", { epocas: parseInt(epocas.value || "3", 10) }); pintarEstado({ estado: "ejecutando", mensajes: ["iniciando"] }); }
    catch (e) { mensaje(msg, e.message, "error"); }
  });
  const activar = async (v) => {
    try { await POST("/api/modelos/activar", { version: v }); VISTAS["modelos"](cont); } catch (e) { mensaje(msg, e.message, "error"); }
  };

  cont.replaceChildren(el("div", { class: "cabecera" }, el("div", {}, el("h1", { texto: "Modelos de IA" }),
      el("p", { class: "suave", texto: `Versión activa: ${met.version}. Los tickets nuevos usan esta versión (se ve en el análisis de cada ticket).` })),
      el("a", { href: "/laboratorio", target: "_blank", rel: "noopener", texto: "Abrir el laboratorio de modelos ↗" })),
    el("div", { class: "kpis" }, kpi(num(r.f1_macro_categoria_gru, 3), "F1 macro GRU (categoría)"), kpi(num(r.f1_macro_categoria_base, 3), "F1 macro modelo base"),
      kpi(num(r.f1_macro_prioridad, 3), "F1 macro MLP prioridad"), kpi(num(r.recall_critica, 3), "Recall de Crítica"), kpi(pct(r.top1_asignacion, 1), "Técnico esperado primero"),
      kpi(pct(r.similares_3_de_5, 1), "≥ 3 de 5 similares de la misma categoría")),
    el("div", { class: "rejilla" },
      el("div", { class: "tarjeta" }, el("h2", { texto: "Versiones" }), el("table", { class: "tabla" },
        el("thead", {}, el("tr", {}, ["Versión", "Estado", "F1 GRU", "Correcciones", ""].map((h) => el("th", { texto: h })))),
        el("tbody", {}, reg.versiones.slice().reverse().map((v) => el("tr", {}, el("td", {}, el("b", { texto: v.version }), v.version === reg.activa ? [" ", etq("activa", "ok")] : null,
          el("div", { class: "suave pequeno", texto: v.nota || "" })), el("td", {}, etq(v.estado, v.estado === "publicada" ? "neutra" : "mal")),
          el("td", { texto: v.metricas.f1_macro_categoria_gru === undefined ? "—" : num(v.metricas.f1_macro_categoria_gru, 4) }), el("td", { texto: v.n_correcciones }),
          el("td", {}, v.estado === "publicada" && v.version !== reg.activa ? el("button", { texto: "Activar", onclick: () => activar(v.version) }) : null))))), msg),
      el("div", { class: "tarjeta" }, el("h2", { texto: "Reentrenamiento" }),
        el("p", { class: "suave pequeno", texto: "Reentrena desde la versión activa con las correcciones y la compara en un conjunto de referencia fijo. Solo se publica si su F1 macro iguala o supera al de la vigente. Tarda unos minutos." }),
        el("p", { class: faltan ? "aviso pequeno" : "suave pequeno", texto: faltan
          ? `Se necesitan al menos ${est.minimo_correcciones} correcciones válidas para reentrenar (hay ${est.correcciones_validas}). Con pocas correcciones el modelo no cambia de forma medible.`
          : `Correcciones válidas: ${est.correcciones_validas} (mínimo ${est.minimo_correcciones}).` }),
        el("div", { class: "acciones" }, el("label", { style: "margin:0" }, "Épocas máximas ", epocas), btn), zonaProgreso,
        el("h3", {}, "Correcciones guardadas ", etq(corr.length, "neutra")),
        corr.length ? el("table", { class: "tabla" }, el("thead", {}, el("tr", {}, ["Ticket", "Categoría", "Prioridad", "Fecha"].map((h) => el("th", { texto: h })))),
          el("tbody", {}, corr.slice(-8).reverse().map((c) => el("tr", {}, el("td", { texto: c.titulo }), el("td", { texto: c.categoria_corregida }), el("td", { texto: c.prioridad_corregida }), el("td", { texto: c.fecha })))))
          : el("p", { class: "suave", texto: "Aún no hay correcciones. Corrígelas desde el detalle de un ticket." }))),
    el("div", { class: "tarjeta" }, el("h2", { texto: "Criterios de aceptación (conjunto de prueba, tickets reales)" }), el("table", { class: "tabla" }, el("tbody", {},
      [[cat.gru.reales.f1_macro >= 0.85, `GRU: F1 macro ≥ 0,85 (${num(cat.gru.reales.f1_macro, 3)})`],
       [cat.gru.reales.f1_macro > cat.base.reales.f1_macro, `GRU mejor que el modelo base (${num(cat.gru.reales.f1_macro, 3)} frente a ${num(cat.base.reales.f1_macro, 3)}: empate estadístico)`],
       [pri["mlp completo"].reales.f1_macro >= 0.8 && pri["mlp completo"].reales.por_clase["Crítica"].recall >= 0.85, `MLP de prioridad: F1 ≥ 0,80 y recall de Crítica ≥ 0,85 (${num(pri["mlp completo"].reales.f1_macro, 3)}; ${num(pri["mlp completo"].reales.por_clase["Crítica"].recall, 3)})`],
       [asi.top1 >= 0.8, `Asignación: técnico esperado primero ≥ 80 % (${pct(asi.top1, 1)})`],
       [asi.violaciones_de_limite_con_balanceo === 0, `Balanceo: ${asi.violaciones_de_limite_con_balanceo} violaciones del límite de carga`]]
        .map(([ok, t]) => el("tr", {}, el("td", {}, etq(ok ? "cumple" : "no cumple", ok ? "ok" : "mal")), el("td", { texto: t }))))),
      el("p", { class: "suave pequeno", texto: "Nota: el MLP de prioridad depende casi por completo de impacto y urgencia; la categoría tiene un techo por ruido de etiqueta (≈ 85 % de acierto estimado en la auditoría)." })),
    met.figuras.length ? el("div", { class: "tarjeta" }, el("h2", { texto: "Figuras" }), el("div", { class: "rejilla" },
      met.figuras.filter((f) => /cm_|metricas_|curvas/.test(f)).map((f) => el("a", { href: f, target: "_blank", rel: "noopener" }, el("img", { src: f, alt: f.split("/").pop(), style: "max-width:100%;border:1px solid var(--borde);border-radius:8px", loading: "lazy" }))))) : null);
  pintarEstado(est);
};

/* ------------------------------------------------------------------ panel de métricas (HU28, HU29, HU30) */
VISTAS["panel"] = async (cont) => {
  const d = await GET("/api/panel/resumen");
  const propio = d.alcance === "propios";
  const kpi = (v, t) => el("div", { class: "kpi" }, el("b", { texto: v }), el("span", { texto: t }));
  const barras = (titulo, datos, color) => {
    const max = Math.max(1, ...Object.values(datos));
    return el("div", { class: "tarjeta" }, el("h2", { texto: titulo }), Object.entries(datos).map(([k, v]) =>
      el("div", { class: "hbarra" }, el("span", { texto: k }), el("div", { class: "pista" }, el("div", { class: "relleno", style: `width:${(100 * v / max).toFixed(0)}%` + (color ? `;background:${color(k)}` : "") })), el("span", { class: "derecha", texto: v }))));
  };
  const colorPrio = { Baja: "#6aa985", Media: "#d9b43c", Alta: "#e08a3c", "Crítica": "#c0392b" };
  const ia = d.sugerencias_ia;
  const maxDia = Math.max(1, ...d.por_dia.map((x) => x.tickets));
  cont.replaceChildren(
    el("div", { class: "cabecera" }, el("div", {}, el("h1", { texto: propio ? "Mi resumen" : "Panel de métricas" }),
      el("p", { class: "suave", texto: propio ? "Resumen de los tickets que tienes asignados." : "Resumen de todos los tickets del sistema." }))),
    el("div", { class: "kpis" }, kpi(d.total, "Tickets en total"), kpi(d.abiertos, "Abiertos o en progreso"), kpi(horas(d.tiempo_resolucion.promedio_horas), "Tiempo promedio de resolución"),
      kpi(d.resueltos_con_solucion_rapida, "Resueltos con solución rápida"), kpi(ia.categoria_aceptada === null ? "—" : pct(ia.categoria_aceptada), "Categorías de la IA aceptadas"),
      kpi(ia.prioridad_aceptada === null ? "—" : pct(ia.prioridad_aceptada), "Prioridades de la IA aceptadas")),
    el("div", { class: "rejilla tres" }, barras("Por estado", d.por_estado), barras("Por categoría", d.por_categoria), barras("Por prioridad", d.por_prioridad, (k) => colorPrio[k]), barras("Por área del técnico", d.por_area)),
    el("div", { class: "tarjeta" }, el("h2", { texto: "Tickets por día (últimos 14 días)" }),
      el("div", { class: "dias" }, d.por_dia.map((x) => el("div", { class: "col", title: `${x.fecha}: ${x.tickets}` }, el("span", { texto: x.tickets || "" }),
        el("div", { class: "barra", style: `height:${(100 * x.tickets / maxDia * 0.8).toFixed(0)}%` }), el("span", { texto: x.fecha.slice(8) }))))),
    el("div", { class: "rejilla" },
      el("div", { class: "tarjeta" }, el("h2", { texto: "Carga actual frente al límite" }), d.carga_tecnicos.map((t) =>
        el("div", { class: "hbarra carga" }, el("span", { texto: t.nombre.split(" ")[0] + (t.disponible ? "" : " (no disp.)") }),
          el("div", { class: "pista" }, el("div", { class: "relleno" + (t.carga >= t.limite ? " lleno" : t.carga >= 0.8 * t.limite ? " alto" : ""), style: `width:${Math.min(100, 100 * t.carga / t.limite)}%` })),
          el("span", { class: "derecha", texto: `${t.carga}/${t.limite}` })))),
      el("div", { class: "tarjeta" }, el("h2", { texto: "Tiempo de resolución por técnico" }),
        el("p", { class: "suave pequeno", texto: `${d.tiempo_resolucion.resueltos} tickets resueltos por técnicos (sin contar los resueltos con solución rápida).` }),
        el("table", { class: "tabla" }, el("thead", {}, el("tr", {}, el("th", { texto: "Técnico" }), el("th", { class: "num", texto: "Resueltos" }), el("th", { class: "num", texto: "Promedio" }))),
          el("tbody", {}, d.tiempo_resolucion.por_tecnico.map((t) => el("tr", {}, el("td", { texto: t.nombre }), el("td", { class: "num", texto: t.resueltos }), el("td", { class: "num", texto: horas(t.promedio_horas) })))))),
      el("div", { class: "tarjeta" }, el("h2", { texto: "Calidad de las sugerencias de la IA" }),
        el("p", { texto: ia.analizados ? `De ${ia.analizados} tickets analizados, ${ia.corregidos} tuvieron la categoría corregida por Soporte.` : "Todavía no hay tickets analizados." }),
        el("p", { class: "suave pequeno", texto: "Una sugerencia se considera aceptada si el ticket conserva la categoría o prioridad que propuso el modelo." }))));
};
