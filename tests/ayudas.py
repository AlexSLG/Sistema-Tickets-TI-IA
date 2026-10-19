"""Constantes y funciones auxiliares de las pruebas del sistema."""
from src.sistema import db as bd
from src.sistema.modelos import Tecnico

ADMIN = ("admin@soporte.local", "Admin123")
ANA = ("ana.torres@empresa.local", "Usuario123")
LUIS = ("luis.paz@empresa.local", "Usuario123")
MARCELA = ("marcela.vega@soporte.local", "Soporte123")

SERVIDOR = {"titulo": "El servidor de archivos no responde",
            "descripcion": "El servidor de archivos no responde, hay una caída de la red en todo el piso y nadie puede trabajar",
            "impacto": "Alto", "urgencia": "Alta", "usuarios_afectados": 40}
CORREO_CLAVE = {"titulo": "No puedo entrar a mi correo, dice contraseña incorrecta",
                "descripcion": "No puedo entrar a mi correo, dice contraseña incorrecta", "impacto": "Bajo", "urgencia": "Media", "usuarios_afectados": 1}
MONITOR = {"titulo": "El monitor parpadea", "descripcion": "La pantalla de mi monitor parpadea", "impacto": "Bajo", "urgencia": "Baja", "usuarios_afectados": 1}


def entrar(cliente, cred):
    r = cliente.post("/api/auth/login", json={"correo": cred[0], "contrasena": cred[1]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def credencial_tecnico(tecnico_id):
    with bd.SessionLocal() as s:
        return (s.get(Tecnico, tecnico_id).usuario.correo, "Soporte123")


def registrar(cliente, h, datos=SERVIDOR, **extra):
    r = cliente.post("/api/tickets", headers=h, json={**datos, **extra})
    assert r.status_code == 201, r.text
    return r.json()
