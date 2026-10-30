"""Prueba de extremo a extremo (navegador real con Playwright) del guion de demostración por rol.

Se ejecuta aparte, contra la aplicación en marcha y con los datos de demostración recién cargados:

    set E2E_BASE=http://localhost:8001          (PowerShell: $env:E2E_BASE="http://localhost:8001")
    python -m pytest tests/e2e -v

Sin E2E_BASE (o sin Playwright instalado) se omite: `pytest` a secas no la ejecuta. Deja tickets nuevos en la base de datos.
"""
import os

import pytest

BASE = os.getenv("E2E_BASE")
sync_api = pytest.importorskip("playwright.sync_api")
pytestmark = pytest.mark.skipif(not BASE, reason="definir E2E_BASE con la URL de la aplicación en marcha")

ANA = ("ana.torres@empresa.local", "Usuario123")
ADMIN = ("admin@soporte.local", "Admin123")


@pytest.fixture(scope="module")
def navegador():
    with sync_api.sync_playwright() as pw:
        nav = pw.chromium.launch()
        yield nav
        nav.close()


@pytest.fixture
def pagina(navegador):
    contexto = navegador.new_context(viewport={"width": 1366, "height": 860}, locale="es-ES")
    pagina = contexto.new_page()
    errores = []
    pagina.on("pageerror", lambda e: errores.append(str(e)))
    yield pagina
    contexto.close()
    assert not errores, f"errores de JavaScript: {errores}"


def entrar(pagina, cred):
    pagina.goto(BASE + "/")
    pagina.get_by_label("Correo").fill(cred[0])
    pagina.get_by_label("Contraseña").fill(cred[1])
    pagina.get_by_role("button", name="Entrar", exact=True).click()
    pagina.wait_for_selector(".lateral")


def salir(pagina):
    pagina.get_by_role("button", name="Cerrar sesión").click()
    pagina.wait_for_selector(".login")


def nuevo_ticket(pagina, titulo, descripcion, impacto="Medio", urgencia="Media", usuarios="1"):
    pagina.goto(BASE + "/#/nuevo")
    pagina.get_by_label("Título").fill(titulo)
    pagina.get_by_label("Descripción").fill(descripcion)
    pagina.get_by_label("Impacto").select_option(impacto)
    pagina.get_by_label("Urgencia").select_option(urgencia)
    pagina.get_by_label("Usuarios afectados").fill(usuarios)
    pagina.get_by_role("button", name="Analizar").click()
    pagina.wait_for_selector("text=Análisis de la IA")


def test_usuario_resuelve_con_solucion_rapida(pagina):
    entrar(pagina, ANA)
    nuevo_ticket(pagina, "No puedo entrar a mi correo, dice contraseña incorrecta", "No puedo entrar a mi correo, dice contraseña incorrecta",
                 "Bajo", "Media")
    pagina.wait_for_selector(".solucion-rapida")
    pagina.get_by_role("button", name="Sí, se resolvió").click()
    pagina.wait_for_selector("text=cerrado con la solución rápida")


def test_incidente_critico_lo_atiende_el_tecnico_asignado(pagina):
    entrar(pagina, ANA)
    nuevo_ticket(pagina, "El servidor de archivos no responde", "Nadie en el piso puede abrir la unidad del servidor de archivos; error de red",
                 "Alto", "Alta", "40")
    pagina.wait_for_selector("text=Crítica")
    pagina.get_by_role("button", name="Registrar ticket").click()
    pagina.wait_for_selector("text=Ticket registrado")
    texto = pagina.locator(".exito").inner_text()
    codigo = texto.split()[0]
    tecnico = texto.split("asignado a ")[1].rstrip(".").strip()
    salir(pagina)

    # el técnico asignado entra (correo nombre.apellido@soporte.local) y lo ve en su bandeja
    partes = tecnico.lower().translate(str.maketrans("áéíóúñ", "aeioun")).split()
    entrar(pagina, (f"{partes[0]}.{partes[-1]}@soporte.local", "Soporte123"))
    pagina.goto(BASE + "/#/bandeja")
    pagina.get_by_text(codigo).first.click()
    pagina.wait_for_selector("text=Análisis de la IA")
    pagina.get_by_role("button", name="Pasar a En progreso").click()
    pagina.get_by_placeholder("Solución aplicada (obligatoria)").fill("Se reinició el servicio de archivos y se verificó el acceso.")
    pagina.get_by_role("button", name="Marcar como resuelto").click()
    pagina.wait_for_selector("text=Guardar como solución rápida")
    salir(pagina)

    # la solicitante confirma
    entrar(pagina, ANA)
    pagina.goto(BASE + "/#/mis-tickets")
    pagina.get_by_text(codigo).first.click()
    pagina.get_by_role("button", name="Confirmar y cerrar").click()
    pagina.wait_for_selector("text=Este ticket está cerrado.")


def test_administrador_recorre_sus_pantallas(pagina):
    entrar(pagina, ADMIN)
    for ruta, titulo in (("panel", "Panel de métricas"), ("tickets", "Todos los tickets"), ("tecnicos", "Técnicos"),
                         ("usuarios", "Usuarios"), ("soluciones", "Soluciones rápidas"), ("modelos", "Modelos de IA")):
        pagina.goto(f"{BASE}/#/{ruta}")
        pagina.wait_for_selector(f"h1:has-text('{titulo}')")
    pagina.wait_for_selector("text=/Correcciones válidas|Se necesitan al menos/")


def test_laboratorio_pide_administrador_para_cambiar_datos(pagina):
    pagina.goto(BASE + "/laboratorio")
    pagina.wait_for_selector("#sesion-lab")
    pagina.wait_for_selector("text=Sin sesión (solo lectura)")
    pagina.get_by_role("button", name="Entrar como Administrador").click()
    pagina.locator("#l-correo").fill(ADMIN[0])
    pagina.locator("#l-contrasena").fill(ADMIN[1])
    pagina.locator("#form-login button[type=submit]").click()
    pagina.wait_for_selector("text=Administrador del sistema · Administrador")
