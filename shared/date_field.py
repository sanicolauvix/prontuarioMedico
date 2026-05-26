# -*- coding: utf-8 -*-
# flet_shared/shared/date_field.py
# Componente padrao Koios: campo de data com mascara DD/MM/AAAA + picker de calendario.
#
# USO:
#   from shared.date_field import campo_data
#   row_data, f_data = campo_data(page, "Data", value=registro.get("data",""))
#   # adicione row_data ao layout; use f_data.value para ler o valor (DD/MM/AAAA)
#   # ao salvar: model.normalizar_data(f_data.value)  ->  YYYY-MM-DD para o banco
import flet as ft
import datetime

CARD = "#161B22"; BD2 = "#30363D"
TXT  = "#E6EDF3"; SEC  = "#8B949E"
AZUL = "#58A6FF"


def _para_display(s: str | None) -> str:
    """YYYY-MM-DD -> DD/MM/AAAA para exibicao. DD/MM/AAAA passa sem alteracao."""
    if not s:
        return ""
    s = str(s).strip()
    if len(s) >= 10 and s[4] == "-":
        try:
            return datetime.datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            pass
    return s


def _mask_data(tf: ft.TextField) -> None:
    """Mascara automatica DD/MM/AAAA enquanto o usuario digita."""
    def _on_change(e):
        raw = "".join(c for c in (tf.value or "") if c.isdigit())
        out = ""
        for i, c in enumerate(raw[:8]):
            if i in (2, 4):
                out += "/"
            out += c
        if tf.value != out:
            tf.value = out
            try:
                tf.update()
            except Exception:
                pass
    tf.on_change = _on_change


def campo_data(
    page: ft.Page,
    label: str,
    value: str = "",
    obrigatorio: bool = False,
    cor_acento: str = AZUL,
    largura: int | None = None,
    bgcolor: str = CARD,
    border_color: str = BD2,
) -> tuple:
    """
    Campo de data padrao Koios com mascara DD/MM/AAAA e picker de calendario.

    Retorna (row_widget, tf):
      - row_widget: adicione ao layout
      - tf: leia tf.value para obter o valor (sempre DD/MM/AAAA)
      - ao salvar: normalizar_data(tf.value) converte para YYYY-MM-DD
    """
    tf = ft.TextField(
        label=f"{label}{' *' if obrigatorio else ''}",
        value=_para_display(value),
        hint_text="DD/MM/AAAA",
        bgcolor=bgcolor,
        border_color=border_color,
        focused_border_color=cor_acento,
        label_style=ft.TextStyle(color=SEC, size=11),
        text_style=ft.TextStyle(color=TXT),
        border_radius=8,
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=largura is None,
        width=largura,
    )
    _mask_data(tf)

    btn_cal = ft.Container(
        content=ft.Icon("calendar_month_rounded", size=20, color=cor_acento),
        padding=ft.padding.all(10),
        border_radius=8,
        bgcolor=f"{cor_acento}18",
        ink=True,
        tooltip="Escolher data",
    )

    def _abrir_picker(e=None):
        data_ini = datetime.date.today()
        val = (tf.value or "").strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                data_ini = datetime.datetime.strptime(val[:10], fmt).date()
                break
            except Exception:
                pass

        picker = ft.DatePicker(
            value=datetime.datetime(data_ini.year, data_ini.month, data_ini.day),
            first_date=datetime.datetime(1900, 1, 1),
            last_date=datetime.datetime(2100, 12, 31),
        )

        def _selecionar(e):
            if picker.value:
                tf.value = picker.value.strftime("%d/%m/%Y")
            try:
                if picker in page.overlay:
                    page.overlay.remove(picker)
                tf.update()
                page.update()
            except Exception:
                pass

        def _dispensar(e):
            try:
                if picker in page.overlay:
                    page.overlay.remove(picker)
                page.update()
            except Exception:
                pass

        picker.on_change    = _selecionar
        picker.on_dismissal = _dispensar
        page.overlay.append(picker)
        try:
            page.update()
            picker.pick_date()
        except Exception:
            pass

    btn_cal.on_click = _abrir_picker

    row = ft.Row(
        [tf, btn_cal],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        tight=largura is not None,
    )
    return row, tf
