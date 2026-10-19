"use strict";
/* Pantallas de administración: panel de métricas, técnicos, usuarios y modelos de IA (fases 7 y 8). */
VISTAS["panel"] = async (cont) => { cont.replaceChildren(el("p", { class: "suave", texto: "Panel de métricas: en construcción." })); };
VISTAS["tecnicos"] = async (cont) => { cont.replaceChildren(el("p", { class: "suave", texto: "Técnicos: en construcción." })); };
VISTAS["usuarios"] = async (cont) => { cont.replaceChildren(el("p", { class: "suave", texto: "Usuarios: en construcción." })); };
VISTAS["modelos"] = async (cont) => { cont.replaceChildren(el("p", { class: "suave", texto: "Modelos de IA: en construcción." })); };
