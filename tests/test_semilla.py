"""Prueba de la semilla de historial (fase 5): tickets de demostración registrados con la IA real."""
import pytest
from sqlalchemy import func, select

from src.sistema import db as bd
from src.sistema import ia, semilla_historial
from src.sistema.modelos import AnalisisIA, Tecnico, Ticket

pytestmark = pytest.mark.usefixtures("bd_limpia")


def test_semilla_de_historial(cliente, tmp_path, monkeypatch):
    import src.training.reentrenar as re_mod
    monkeypatch.setattr(re_mod, "CORRECCIONES", tmp_path / "no_debe_crearse.csv")
    with bd.SessionLocal() as s:
        semilla_historial.sembrar_historial(s, n_total=20)
    with bd.SessionLocal() as s:
        tickets = s.scalars(select(Ticket).order_by(Ticket.codigo)).all()
        assert len(tickets) == 20 and [t.codigo for t in tickets][:2] == ["TK-0001", "TK-0002"]
        por_estado = {e: sum(1 for t in tickets if t.estado == e) for e in ("Cerrado", "Resuelto", "En progreso", "Abierto")}
        assert por_estado == {"Cerrado": 12, "Resuelto": 3, "En progreso": 3, "Abierto": 2}
        assert s.scalar(select(func.count()).select_from(AnalisisIA)) == 20          # todos con análisis real de la IA
        assert all(t.categoria and t.prioridad and t.creado_en <= t.actualizado_en for t in tickets)
        assert all(t.tecnico_id is not None for t in tickets if not t.resuelto_con_solucion_rapida)
        assert all(t.solucion for t in tickets if t.estado in ("Resuelto", "Cerrado"))
        # las cargas abiertas que quedan no saturan a nadie
        cargas = ia.contexto_tecnicos(s)
        assert all(cargas["cargas"][t.id] <= t.limite_carga for t in s.scalars(select(Tecnico)))
        assert sum(cargas["cargas"].values()) == por_estado["En progreso"] + por_estado["Abierto"]
    assert not (tmp_path / "no_debe_crearse.csv").exists()  # la semilla no escribe en data/correcciones.csv
