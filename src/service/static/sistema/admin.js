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

  function pintarEstado(e) {
    if (e.estado === "ejecutando") {
      zonaProgreso.replaceChildren(el("div", { class: "aviso" }, "Reentrenando… ", el("b", { texto: e.mensajes[e.mensajes.length - 1] || "iniciando" })));
      btn.disabled = true;
      temporizadorModelos = setTimeout(async () => { if (location.hash === "#/modelos") pintarEstado(await GET("/api/reentrenar/estado")); }, 3000);
      return;
    }
    btn.disabled = false;
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

/* Panel de métricas: se completa en la fase 8 */
VISTAS["panel"] = async (cont) => { cont.replaceChildren(el("p", { class: "suave", texto: "Panel de métricas: en construcción." })); };
