"""Capturas reales para el manual de usuario (docs/img/), recorriendo la aplicación con las cuentas de demostración.

    python scripts/capturas_manual.py [http://localhost:8001]

Requiere Playwright (`pip install playwright` y `python -m playwright install chromium`). Conviene ejecutarlo contra una base recién
sembrada (`python -m src.sistema.semilla --reiniciar`): registra dos tickets de ejemplo y no guarda soluciones rápidas.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows (cp1252) no muestra ✔ ni otros caracteres
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "docs" / "img"
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
CUENTAS = {"usuario": ("ana.torres@empresa.local", "Usuario123"), "soporte": ("marcela.vega@soporte.local", "Soporte123"),
           "admin": ("admin@soporte.local", "Admin123")}
api = httpx.Client(base_url=BASE, timeout=60)


def token(rol):
    c, p = CUENTAS[rol]
    return {"Authorization": "Bearer " + api.post("/api/auth/login", json={"correo": c, "contrasena": p}).json()["token"]}


def foto(page, nombre, completa=False):
    page.wait_for_timeout(500)
    page.screenshot(path=str(SALIDA / f"{nombre}.png"), full_page=completa)
    print("  ✔", nombre)


def entrar(page, rol):
    page.goto(BASE + "/")
    page.wait_for_selector(".lateral, .login")
    if page.locator(".lateral").count():
        page.get_by_role("button", name="Cerrar sesión").click()
    page.get_by_label("Correo").fill(CUENTAS[rol][0])
    page.get_by_label("Contraseña").fill(CUENTAS[rol][1])
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.wait_for_selector(".lateral")


def ir(page, ruta, esperar="h1"):
    page.goto(f"{BASE}/#/{ruta}")
    page.wait_for_selector(esperar)
    page.wait_for_timeout(700)


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    h_sop = token("soporte")
    tickets_sop = api.get("/api/tickets", headers=h_sop).json()
    en_progreso = next(t for t in tickets_sop if t["estado"] == "En progreso")
    cerrado = next(t for t in tickets_sop if t["estado"] == "Cerrado" and not t.get("resuelto_con_solucion_rapida"))
    h_ana = token("usuario")
    resuelto_ana = next((t for t in api.get("/api/tickets", headers=h_ana).json() if t["estado"] == "Resuelto"), None)

    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        page = nav.new_page(viewport={"width": 1366, "height": 860}, locale="es-ES")
        print("Usuario")
        page.goto(BASE + "/")
        page.wait_for_selector("form")
        foto(page, "01_inicio_sesion")
        entrar(page, "usuario")
        ir(page, "nuevo")
        page.get_by_label("Título").fill("No puedo entrar a mi correo, dice contraseña incorrecta")
        page.get_by_label("Descripción").fill("Desde esta mañana Outlook me pide la contraseña y dice que es incorrecta.")
        page.get_by_role("button", name="Analizar").click()
        page.wait_for_selector(".solucion-rapida")
        foto(page, "02_usuario_solucion_rapida", completa=True)
        ir(page, "nuevo")
        page.get_by_label("Título").fill("El servidor de archivos no responde")
        page.get_by_label("Descripción").fill("Nadie en el piso 3 puede abrir la unidad del servidor de archivos desde las 9:00; aparece error de red.")
        page.get_by_label("Impacto").select_option("Alto")
        page.get_by_label("Urgencia").select_option("Alta")
        page.get_by_label("Usuarios afectados").fill("40")
        page.get_by_role("button", name="Analizar").click()
        page.wait_for_selector("text=Análisis de la IA")
        foto(page, "03_usuario_analisis_ia", completa=True)
        page.get_by_role("button", name="Registrar ticket").click()
        page.wait_for_selector("text=Ticket registrado")
        foto(page, "04_usuario_ticket_registrado")
        ir(page, "mis-tickets", ".tabla")
        foto(page, "05_usuario_mis_tickets")
        if resuelto_ana:
            ir(page, "ticket/" + resuelto_ana["id"], ".tarjeta")
            foto(page, "06_usuario_confirmar_o_reabrir", completa=True)

        print("Soporte")
        entrar(page, "soporte")
        ir(page, "bandeja", ".tabla")
        foto(page, "07_soporte_bandeja")
        ir(page, "ticket/" + en_progreso["id"], ".tarjeta")
        foto(page, "08_soporte_detalle_y_analisis_ia", completa=True)
        ir(page, "ticket/" + cerrado["id"], ".tarjeta")
        page.get_by_role("button", name="Guardar como solución rápida").click()
        page.wait_for_selector(".form-solucion")
        page.locator(".form-solucion").scroll_into_view_if_needed()
        foto(page, "09_soporte_guardar_solucion_rapida")
        ir(page, "panel")
        foto(page, "10_soporte_mi_resumen", completa=True)

        print("Administrador")
        entrar(page, "admin")
        ir(page, "panel")
        foto(page, "11_admin_panel", completa=True)
        ir(page, "tickets", ".tabla")
        foto(page, "12_admin_todos_los_tickets")
        ir(page, "tecnicos", ".tabla")
        foto(page, "13_admin_tecnicos")
        ir(page, "usuarios", ".tabla")
        foto(page, "14_admin_usuarios")
        ir(page, "soluciones", ".tabla")
        foto(page, "15_admin_soluciones_rapidas")
        ir(page, "modelos")
        foto(page, "16_admin_modelos", completa=True)
        page.goto(BASE + "/laboratorio")
        page.wait_for_selector("#estado-modelo")
        page.wait_for_timeout(1500)
        foto(page, "17_laboratorio")
        nav.close()
    print(f"Capturas en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
