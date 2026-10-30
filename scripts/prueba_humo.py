"""Prueba de humo del flujo principal contra un servidor en marcha (local o Docker). Sigue el guion de demostración.

    python scripts/prueba_humo.py [http://localhost:8001]

Deja tickets nuevos en la base de datos (no borra nada); al terminar restablece la disponibilidad del técnico que modifica.
"""
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
c = httpx.Client(base_url=BASE, timeout=60)


def entrar(correo, clave):
    r = c.post("/api/auth/login", json={"correo": correo, "contrasena": clave})
    assert r.status_code == 200, f"login {correo}: {r.status_code} {r.text}"
    return {"Authorization": "Bearer " + r.json()["token"]}


def ok(cond, texto):
    print(("  ✔ " if cond else "  ✘ ") + texto)
    if not cond:
        raise SystemExit(f"FALLÓ: {texto}")


print(f"Prueba de humo contra {BASE}")
ok(c.get("/api/salud").json()["estado"] == "ok", "servicio y modelos disponibles")
ok(c.get("/").status_code == 200 and c.get("/laboratorio").status_code == 200, "interfaz del sistema y laboratorio")
ana, admin = entrar("ana.torres@empresa.local", "Usuario123"), entrar("admin@soporte.local", "Admin123")

print("1. Solución rápida: Ana registra un problema de correo")
datos = {"titulo": "No puedo entrar a mi correo, dice contraseña incorrecta", "descripcion": "No puedo entrar a mi correo, dice contraseña incorrecta",
         "impacto": "Bajo", "urgencia": "Media", "usuarios_afectados": 1}
a = c.post("/api/tickets/analizar", headers=ana, json=datos).json()
ok(a["solucion_rapida"] is not None, f"la IA sugiere una solución rápida: {a['solucion_rapida']['problema'][:50] if a['solucion_rapida'] else '-'}")
t1 = c.post("/api/tickets", headers=ana, json={**datos, "resuelto_con_solucion_rapida": True}).json()
ok(t1["estado"] == "Cerrado" and t1["resuelto_con_solucion_rapida"], f"{t1['codigo']} queda Cerrado con solución rápida")

print("2. Incidente grave: Red / Crítica, asignado automáticamente")
grave = {"titulo": "El servidor de archivos no responde", "descripcion": "El servidor de archivos no responde, hay una caída de la red en todo el piso y nadie puede trabajar",
         "impacto": "Alto", "urgencia": "Alta", "usuarios_afectados": 40}
t2 = c.post("/api/tickets", headers=ana, json=grave).json()
ok(t2["categoria"] == "Red" and t2["prioridad"] == "Crítica" and t2["tecnico"], f"{t2['codigo']}: {t2['categoria']} / {t2['prioridad']} → {t2['tecnico']['nombre']}")

print("3. El técnico asignado lo ve primero, revisa el análisis y lo resuelve")
tec = next(x for x in c.get("/api/admin/tecnicos", headers=admin).json() if x["id"] == t2["tecnico"]["id"])
ht = entrar(tec["correo"], "Soporte123")
bandeja = c.get("/api/tickets", headers=ht).json()
ok(bandeja[0]["id"] == t2["id"], "aparece primero en su bandeja (Crítica)")
d = c.get(f"/api/tickets/{t2['id']}", headers=ht).json()
ok(len(d["analisis"]["tecnicos_sugeridos"]) == 8 and len(d["analisis"]["similares"]) == 5, "ve el Análisis de la IA (ranking de 8 técnicos y 5 similares)")
ok(c.put(f"/api/tickets/{t2['id']}/estado", headers=ht, json={"estado": "En progreso"}).status_code == 200, "pasa a En progreso")
ok(c.post(f"/api/tickets/{t2['id']}/comentarios", headers=ht, json={"texto": "Revisando el switch del piso"}).status_code == 201, "comenta")
ok(c.put(f"/api/tickets/{t2['id']}/estado", headers=ht, json={"estado": "Resuelto"}).status_code == 422, "no se puede resolver sin solución")
ok(c.put(f"/api/tickets/{t2['id']}/estado", headers=ht, json={"estado": "Resuelto", "solucion": "Se reinició el switch del piso 3"}).json()["estado"] == "Resuelto", "resuelto con solución")
ok(c.post(f"/api/tickets/{t2['id']}/confirmar", headers=ana).json()["estado"] == "Cerrado", "Ana confirma y queda Cerrado")

print("4. Corrección de la clasificación")
t3 = c.post("/api/tickets", headers=ana, json={"titulo": "El monitor parpadea", "descripcion": "La pantalla de mi monitor parpadea", "impacto": "Bajo", "urgencia": "Baja", "usuarios_afectados": 1}).json()
h3 = entrar(next(x for x in c.get("/api/admin/tecnicos", headers=admin).json() if x["id"] == t3["tecnico"]["id"])["correo"], "Soporte123")
nueva = "Software" if t3["categoria"] != "Software" else "Red"
d3 = c.post(f"/api/tickets/{t3['id']}/corregir", headers=h3, json={"categoria": nueva}).json()
ok(d3["categoria"] == nueva and len(d3["correcciones"]) == 1, f"{t3['codigo']} corregido a {nueva}; queda registrado")
ok(len(c.get("/api/correcciones").json()) >= 1, "la corrección está en data/correcciones.csv para el reentrenamiento")

print("5. Balanceo: el técnico más apto no disponible → pasa al siguiente")
mejor = t2["tecnico"]["id"]
c.put(f"/api/admin/tecnicos/{mejor}", headers=admin, json={"disponible": False})
try:
    t4 = c.post("/api/tickets", headers=ana, json=grave).json()
    ok(t4["tecnico"]["id"] != mejor, f"{t4['codigo']} se asigna a {t4['tecnico']['nombre']} y no a {t2['tecnico']['nombre']}")
    nota = next(x for x in c.get(f"/api/tickets/{t4['id']}", headers=admin).json()["analisis"]["tecnicos_sugeridos"] if x["id_tecnico"] == mejor)["nota"]
    ok(bool(nota), f"el análisis lo explica: «{nota}»")
finally:
    c.put(f"/api/admin/tecnicos/{mejor}", headers=admin, json={"disponible": True})

print("6. Panel y modelos")
p = c.get("/api/panel/resumen", headers=admin).json()
ok(p["total"] >= 4 and sum(p["por_estado"].values()) == p["total"], f"panel con {p['total']} tickets; {p['resueltos_con_solucion_rapida']} resueltos con solución rápida")
m = c.get("/api/metricas").json()
ok(m["version"] and c.get("/api/modelos").json()["activa"] == m["version"], f"modelos {m['version']} activos con métricas")
print("Prueba de humo correcta.")
