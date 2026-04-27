# -*- coding: utf-8 -*-
# SHARED | telas/tela_endereco.py -- gerenciado por flet_shared/sync_shared.py
# --- SHARED PARAMS ---
_APP_UA = "ProntuarioMedico/1.0"
# --- END SHARED PARAMS ---
"""
tela_endereco.py -- Tela de endereco reutilizavel (Flet 0.28.2).

Funcionalidades:
  - Busca por CEP (ViaCEP)
  - Botao GPS: captura coordenadas do dispositivo + geocoding reverso automatico
  - Colar link do WhatsApp (goo.gl, maps.google, coordenadas brutas)
    -> extrai lat/lng E faz geocoding reverso para preencher os campos
  - Colar endereco em texto livre (Google Maps, SMS) -> preenche campos sem rede
  - Botao "Localizar" faz geocoding pelo endereco digitado
  - Exibe coordenadas e link para Google Maps

Uso (modular -- clientes, fornecedores e config usam a mesma tela):
    from telas.tela_endereco import criar_tela_endereco
    criar_tela_endereco(
        page      = page,
        voltar_fn = voltar_fn,
        endereco  = {"cep":"29000000", "logradouro":"Rua X", ...},
        on_salvar = lambda end: print(end),
        titulo    = "Ponto de partida",
    )
"""

import flet as ft
import json
import logging
import threading
import urllib.parse
import urllib.request
from shared.layout import Layout

BG    = "#0D1117"; CARD  = "#161B22"
BORDA = "#21262D"; BORDA2 = "#30363D"
TXT   = "#E6EDF3"; SEC   = "#8B949E"; DIS   = "#484F58"
AZUL  = "#58A6FF"; VERD  = "#3FB950"; LRNJ  = "#F0883E"; VERM  = "#FF4444"
AMAR  = "#D29922"


# -- ViaCEP -------------------------------------------------------------------

def _buscar_cep(cep: str) -> dict:
    try:
        cep_limpo = "".join(c for c in cep if c.isdigit())
        if len(cep_limpo) != 8:
            return {}
        url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
        with urllib.request.urlopen(url, timeout=6) as r:
            dados = json.loads(r.read().decode())
        if dados.get("erro"):
            return {}
        return {
            "logradouro": dados.get("logradouro", ""),
            "bairro":     dados.get("bairro", ""),
            "cidade":     dados.get("localidade", ""),
            "estado":     dados.get("uf", ""),
        }
    except Exception as ex:
        logging.warning("[ENDERECO] ViaCEP: %s", ex)
        return {}


# -- Geocoding (endereco -> coordenadas) -------------------------------------

def _geocodificar(logradouro, numero, bairro, cidade, estado) -> tuple:
    """Tenta do mais especifico ao mais generico ate encontrar."""
    tentativas = []
    if logradouro and cidade:
        tentativas.append(f"{logradouro}, {numero}, {bairro}, {cidade}, {estado}, Brasil")
        tentativas.append(f"{logradouro}, {bairro}, {cidade}, {estado}, Brasil")
    if bairro and cidade:
        tentativas.append(f"{bairro}, {cidade}, {estado}, Brasil")
    if cidade:
        tentativas.append(f"{cidade}, {estado}, Brasil")

    for q in tentativas:
        try:
            url = (
                "https://nominatim.openstreetmap.org/search"
                f"?q={urllib.parse.quote(q)}&format=json&limit=1&countrycodes=br"
            )
            req = urllib.request.Request(url, headers={"User-Agent": _APP_UA})
            with urllib.request.urlopen(req, timeout=8) as r:
                dados = json.loads(r.read().decode())
            if dados:
                return float(dados[0]["lat"]), float(dados[0]["lon"])
        except Exception as ex:
            logging.warning("[ENDERECO] Nominatim: %s", ex)
    return None, None


# -- Geocoding reverso (coordenadas -> endereco) ------------------------------

def _geocoding_reverso(lat: float, lng: float) -> dict:
    """Retorna dict com logradouro, bairro, cidade, estado, cep via Nominatim."""
    try:
        url = (
            f"https://nominatim.openstreetmap.org/reverse"
            f"?lat={lat}&lon={lng}&format=json&addressdetails=1&accept-language=pt-BR"
        )
        req = urllib.request.Request(url, headers={"User-Agent": _APP_UA})
        with urllib.request.urlopen(req, timeout=8) as r:
            dados = json.loads(r.read().decode())
        addr = dados.get("address", {})
        return {
            "logradouro": addr.get("road", addr.get("pedestrian", "")),
            "bairro":     addr.get("suburb", addr.get("neighbourhood", addr.get("quarter", ""))),
            "cidade":     addr.get("city", addr.get("town", addr.get("village", ""))),
            "estado":     addr.get("state_code", addr.get("state", ""))[:2].upper(),
            "cep":        addr.get("postcode", "").replace("-", ""),
        }
    except Exception as ex:
        logging.warning("[ENDERECO] geocoding reverso: %s", ex)
        return {}


# -- Extrator de coordenadas de links ----------------------------------------

def _extrair_coords_do_texto(texto: str):
    """
    Extrai (lat, lng) de:
    - coordenadas brutas: -20.123, -40.456
    - links google maps: ?q=, @lat,lng, /place/lat,lng
    - links curtos goo.gl / maps.app.goo.gl (resolve redirect)
    Retorna (lat, lng) ou (None, None).
    """
    import re

    # Formato 1: coordenadas diretas  -20.123, -40.456
    m = re.search(r"(-?\d{1,3}\.\d{4,})[,\s]+(-?\d{1,3}\.\d{4,})", texto)
    if m:
        return float(m.group(1)), float(m.group(2))

    # Formato 2: ?q=-20.123,-40.456  ou  @-20.123,-40.456
    m = re.search(r"[?@/](-?\d{1,3}\.\d+)[,](-?\d{1,3}\.\d+)", texto)
    if m:
        return float(m.group(1)), float(m.group(2))

    # Formato 3: link curto -- resolver redirect
    if "goo.gl" in texto or "maps.app" in texto:
        try:
            req = urllib.request.Request(
                texto.strip(), headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=8)
            url_final = resp.url
            m = re.search(r"[?@/](-?\d{1,3}\.\d+)[,](-?\d{1,3}\.\d+)", url_final)
            if m:
                return float(m.group(1)), float(m.group(2))
        except Exception as ex:
            logging.warning("[ENDERECO] resolve goo.gl: %s", ex)

    return None, None


# -- Parser de endereco copiado (sem rede) -----------------------------------

_ESTADOS_BR = {
    'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS',
    'MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC',
    'SP','SE','TO',
}

def _parse_endereco(texto: str) -> dict:
    """
    Interpreta string de endereco copiado (Google Maps, SMS, etc.)
    e retorna dict com: logradouro, numero, complemento, bairro, cidade, estado, cep.
    Nao faz chamada de rede.
    """
    import re
    resultado = {}
    t = texto.strip()

    # Remove sufixos desnecessarios
    t = re.sub(r',?\s*Brasil\s*$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\bCEP:?\s*', '', t, flags=re.IGNORECASE)

    # Extrai CEP
    m_cep = re.search(r'\b(\d{5}-?\d{3})\b', t)
    if m_cep:
        resultado['cep'] = re.sub(r'\D', '', m_cep.group(1))
        t = (t[:m_cep.start()] + t[m_cep.end():]).strip(' ,')

    # Normaliza separadores: " - " e "/" viram ","
    t = re.sub(r'\s*[-/]\s*', ', ', t)
    t = re.sub(r',\s*,+', ',', t)
    t = t.strip(', ')

    partes = [p.strip() for p in t.split(',') if p.strip()]
    if not partes:
        return resultado

    # Primeira parte: logradouro + numero
    primeira = partes[0]
    m_num = re.search(r'\s+(\d+\w*)\s*$', primeira)
    if not m_num:
        m_num = re.search(r',?\s*n[o.]?\s*(\d+\w*)', primeira, flags=re.IGNORECASE)
    if m_num:
        resultado['numero']     = m_num.group(1)
        resultado['logradouro'] = primeira[:m_num.start()].strip().rstrip(',').strip()
    else:
        resultado['logradouro'] = primeira
        # Numero pode estar sozinho na segunda parte (ex: "Rua X, 123, Bairro, Cidade, SP")
        if len(partes) > 1 and re.match(r'^\d+\w*$', partes[1]):
            resultado['numero'] = partes[1]
            partes = [partes[0]] + partes[2:]

    if len(partes) == 1:
        return resultado

    # Procura UF nas partes restantes
    uf_idx = None
    for i, parte in enumerate(partes[1:], 1):
        m_uf = re.search(r'\b([A-Z]{2})\b', parte)
        if m_uf and m_uf.group(1) in _ESTADOS_BR:
            resultado['estado'] = m_uf.group(1)
            uf_idx = i
            cidade_na_parte = parte[:m_uf.start()].strip().rstrip(',').strip()
            if cidade_na_parte:
                resultado['cidade'] = cidade_na_parte
            elif i > 1:
                resultado['cidade'] = partes[i - 1]
            break

    # Partes intermediarias: bairro / complemento
    _COMPL = re.compile(
        r'^(ap(to?|artamento)?|bl(oco?)?|sala|casa|loja|galpao|conj\.?|fund)',
        re.IGNORECASE,
    )
    fim = uf_idx if uf_idx is not None else len(partes)
    meio = [p for p in partes[1:fim] if p != resultado.get('cidade', '')]
    if meio:
        if len(meio) > 1 and _COMPL.match(meio[0]):
            resultado['complemento'] = meio[0]
            resultado['bairro']      = meio[1]
            if len(meio) > 2:
                resultado['complemento'] += ', ' + ', '.join(meio[2:])
        else:
            resultado['bairro'] = meio[0]
            if len(meio) > 1:
                resultado['complemento'] = ', '.join(meio[1:])

    return resultado


# -- Tela principal -----------------------------------------------------------

def criar_tela_endereco(
    page: ft.Page,
    voltar_fn,
    endereco: dict = None,
    on_salvar=None,
    titulo: str = "Endereco",
):
    lay = Layout(page)
    end = endereco or {}
    lat = [end.get("lat")]
    lng = [end.get("lng")]

    def _snack(msg, cor=VERD):
        page.snack_bar = ft.SnackBar(ft.Text(msg, color=TXT), bgcolor=cor)
        page.snack_bar.open = True
        try: page.update()
        except Exception: pass

    # -- Campos de endereco ---------------------------------------------------

    def _tf(hint, valor="", largura=None, teclado=ft.KeyboardType.TEXT):
        kwargs = dict(
            hint_text=hint, value=valor,
            bgcolor=CARD, border_color=BORDA2, focused_border_color=AZUL,
            text_style=ft.TextStyle(color=TXT),
            border_radius=8, keyboard_type=teclado,
        )
        if largura:
            kwargs["width"] = largura
        else:
            kwargs["expand"] = True
        return ft.TextField(**kwargs)

    f_cep         = _tf("00000-000",       end.get("cep", ""),         largura=130,
                        teclado=ft.KeyboardType.NUMBER)
    f_logradouro  = _tf("Rua, Avenida...", end.get("logradouro", ""))
    f_numero      = _tf("No",              end.get("numero", ""),      largura=80)
    f_complemento = _tf("Apto, Bloco...",  end.get("complemento", ""))
    f_bairro      = _tf("Bairro",          end.get("bairro", ""))
    f_cidade      = _tf("Cidade",          end.get("cidade", ""))
    f_estado      = _tf("UF",              end.get("estado", ""),      largura=70)

    # -- Status / coords ------------------------------------------------------

    status_cep  = ft.Text("", size=11, color=VERD)
    status_geo  = ft.Text("", size=11, color=SEC)
    status_link = ft.Text("", size=11, color=SEC)
    coords_txt  = ft.Text(
        f"{lat[0]:.6f}, {lng[0]:.6f}" if lat[0] else "",
        size=11, color=VERD,
    )

    # -- Painel de coordenadas ------------------------------------------------

    mapa_col = ft.Column(spacing=0)

    def _atualizar_mapa():
        mapa_col.controls.clear()
        if lat[0] and lng[0]:
            btn_ver = ft.Container(
                content=ft.Row([
                    ft.Icon("map_rounded", size=14, color=AZUL),
                    ft.Text("Ver no Google Maps", size=12, color=AZUL,
                            weight=ft.FontWeight.W_600),
                ], spacing=6, tight=True),
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border_radius=8, bgcolor=f"{AZUL}22", ink=True,
                border=ft.Border(
                    top=ft.BorderSide(1, AZUL), bottom=ft.BorderSide(1, AZUL),
                    left=ft.BorderSide(1, AZUL), right=ft.BorderSide(1, AZUL)),
            )
            def _abrir(e, la=lat, ln=lng):
                page.launch_url(f"https://www.google.com/maps?q={la[0]},{ln[0]}")
            btn_ver.on_click = _abrir

            mapa_col.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("check_circle_rounded", size=16, color=VERD),
                        ft.Text("Localizacao encontrada!", size=13, color=VERD,
                                weight=ft.FontWeight.W_600),
                    ], spacing=6),
                    ft.Container(height=4),
                    ft.Text(f"Lat: {lat[0]:.6f}  |  Lng: {lng[0]:.6f}",
                            size=11, color=TXT),
                    ft.Container(height=8),
                    btn_ver,
                ], spacing=2),
                padding=ft.padding.all(14), border_radius=10, bgcolor=CARD,
                border=ft.Border(
                    top=ft.BorderSide(1, BORDA), bottom=ft.BorderSide(1, BORDA),
                    left=ft.BorderSide(3, VERD),  right=ft.BorderSide(1, BORDA)),
            ))
        try: page.update()
        except Exception: pass

    def _preencher_campos(dados: dict):
        """Preenche os campos de endereco a partir de um dict."""
        if dados.get("logradouro"): f_logradouro.value = dados["logradouro"]
        if dados.get("bairro"):     f_bairro.value     = dados["bairro"]
        if dados.get("cidade"):     f_cidade.value     = dados["cidade"]
        if dados.get("estado"):     f_estado.value     = dados["estado"]
        if dados.get("cep"):        f_cep.value        = dados["cep"]

    # -- Buscar CEP -----------------------------------------------------------

    def _on_cep(e):
        cep = f_cep.value.strip()
        if len("".join(c for c in cep if c.isdigit())) == 8:
            status_cep.value = "Buscando CEP..."
            status_cep.color = SEC
            try: page.update()
            except Exception: pass
            def _run():
                dados = _buscar_cep(cep)
                if dados:
                    _preencher_campos(dados)
                    status_cep.value = "CEP encontrado!"
                    status_cep.color = VERD
                else:
                    status_cep.value = "CEP nao encontrado"
                    status_cep.color = AMAR
                try: page.update()
                except Exception: pass
            threading.Thread(target=_run, daemon=True).start()

    f_cep.on_change = _on_cep

    # -- GPS do dispositivo (lazy -- registrado no primeiro clique) -----------

    _gl = [None]

    def _get_geolocator():
        if _gl[0] is None:
            _gl[0] = ft.Geolocator(
                location_settings=ft.GeolocatorSettings(
                    accuracy=ft.GeolocatorPositionAccuracy.BEST,
                ),
            )
            page.overlay.append(_gl[0])
            try: page.update()
            except Exception: pass
        return _gl[0]

    status_gps = ft.Text("", size=11, color=SEC)

    btn_gps = ft.Container(
        content=ft.Row([
            ft.Icon("gps_fixed_rounded", size=14, color=BG),
            ft.Text("Usar localizacao atual (GPS)", size=12, color=BG,
                    weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border_radius=8, bgcolor=VERD, ink=True,
    )

    def _obter_gps(e=None):
        btn_gps.bgcolor = DIS
        btn_gps.ink     = False
        status_gps.value = "Aguardando GPS..."
        status_gps.color = SEC
        try: page.update()
        except Exception: pass

        def _run():
            try:
                gl = _get_geolocator()
                perm = gl.request_permission()
                negado = str(perm).lower() not in ("always", "whileinuse",
                                                    "geolocatorpermissionstatus.always",
                                                    "geolocatorpermissionstatus.whileinuse")
                if negado:
                    status_gps.value = "Permissao de localizacao negada"
                    status_gps.color = VERM
                    btn_gps.bgcolor  = VERD
                    btn_gps.ink      = True
                    try: page.update()
                    except Exception: pass
                    return
                pos = gl.get_current_position()
                if pos and pos.latitude and pos.longitude:
                    _lat, _lng = pos.latitude, pos.longitude
                    lat[0] = _lat
                    lng[0] = _lng
                    coords_txt.value = f"{_lat:.6f}, {_lng:.6f}"
                    status_gps.value = "GPS obtido! Buscando endereco..."
                    status_gps.color = AZUL
                    try: page.update()
                    except Exception: pass
                    _atualizar_mapa()
                    addr = _geocoding_reverso(_lat, _lng)
                    if addr:
                        _preencher_campos(addr)
                        status_gps.value = "Localizacao e endereco preenchidos!"
                        status_gps.color = VERD
                    else:
                        status_gps.value = "Coordenadas GPS obtidas!"
                        status_gps.color = VERD
                else:
                    status_gps.value = "GPS nao retornou posicao -- tente novamente"
                    status_gps.color = AMAR
            except Exception as ex:
                status_gps.value = f"Erro GPS: {str(ex)[:50]}"
                status_gps.color = VERM
                logging.warning("[ENDERECO] GPS: %s", ex)
            finally:
                btn_gps.bgcolor = VERD
                btn_gps.ink     = True
                try: page.update()
                except Exception: pass

        threading.Thread(target=_run, daemon=True).start()

    btn_gps.on_click = _obter_gps

    # -- Colar link do WhatsApp -----------------------------------------------

    f_link_wap = ft.TextField(
        hint_text="Cole aqui o link de localizacao do WhatsApp...",
        bgcolor=CARD, border_color=BORDA2, focused_border_color=VERD,
        text_style=ft.TextStyle(color=TXT),
        border_radius=8,
    )

    btn_extrair = ft.Container(
        content=ft.Row([
            ft.Icon("content_paste_rounded", size=14, color=BG),
            ft.Text("Extrair", size=12, color=BG, weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border_radius=8, bgcolor=VERD, ink=True,
    )

    def _extrair_link(e=None):
        texto = f_link_wap.value.strip()
        if not texto:
            _snack("Cole o link primeiro", AMAR)
            return
        status_link.value = "Extraindo coordenadas..."
        status_link.color = SEC
        btn_extrair.bgcolor = DIS
        btn_extrair.ink     = False
        try: page.update()
        except Exception: pass

        def _run():
            _lat, _lng = _extrair_coords_do_texto(texto)
            if _lat and _lng:
                # Validar Brasil
                if not (-35 < _lat < 5 and -75 < _lng < -28):
                    status_link.value = "Coordenadas fora do Brasil"
                    status_link.color = AMAR
                    btn_extrair.bgcolor = VERD
                    btn_extrair.ink     = True
                    try: page.update()
                    except Exception: pass
                    return
                lat[0] = _lat
                lng[0] = _lng
                coords_txt.value   = f"{_lat:.6f}, {_lng:.6f}"
                status_link.value  = "Coordenadas extraidas! Buscando endereco..."
                status_link.color  = AZUL
                f_link_wap.value   = ""
                try: page.update()
                except Exception: pass

                addr = _geocoding_reverso(_lat, _lng)
                if addr:
                    _preencher_campos(addr)
                    status_link.value = "Endereco preenchido automaticamente!"
                    status_link.color = VERD
                    status_geo.value  = "Localizacao definida via link!"
                    status_geo.color  = VERD
                else:
                    status_link.value = "Coordenadas OK -- endereco nao encontrado"
                    status_link.color = AMAR
                _atualizar_mapa()
            else:
                status_link.value = "Nao foi possivel extrair coordenadas do link"
                status_link.color = VERM

            btn_extrair.bgcolor = VERD
            btn_extrair.ink     = True
            try: page.update()
            except Exception: pass

        threading.Thread(target=_run, daemon=True).start()

    btn_extrair.on_click = _extrair_link

    # -- Colar endereco copiado (texto livre) ---------------------------------

    f_end_texto = ft.TextField(
        hint_text="Ex: Rua X, 123 - Bairro, Cidade - SP",
        bgcolor=CARD, border_color=BORDA2, focused_border_color=LRNJ,
        text_style=ft.TextStyle(color=TXT),
        border_radius=8,
    )
    status_end_texto = ft.Text("", size=11, color=SEC)

    btn_buscar_end = ft.Container(
        content=ft.Row([
            ft.Icon("content_paste_go_rounded", size=14, color=BG),
            ft.Text("Preencher campos", size=12, color=BG,
                    weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border_radius=8, bgcolor=LRNJ, ink=True,
    )

    def _buscar_por_texto(e=None):
        texto = f_end_texto.value.strip()
        if not texto:
            _snack("Cole o endereco primeiro", AMAR)
            return
        campos = _parse_endereco(texto)
        if not campos:
            status_end_texto.value = "Nao foi possivel interpretar o endereco"
            status_end_texto.color = VERM
            try: page.update()
            except Exception: pass
            return
        if campos.get("logradouro"): f_logradouro.value  = campos["logradouro"]
        if campos.get("numero"):     f_numero.value      = campos["numero"]
        if campos.get("complemento"):f_complemento.value = campos["complemento"]
        if campos.get("bairro"):     f_bairro.value      = campos["bairro"]
        if campos.get("cidade"):     f_cidade.value      = campos["cidade"]
        if campos.get("estado"):     f_estado.value      = campos["estado"]
        if campos.get("cep"):        f_cep.value         = campos["cep"]
        f_end_texto.value      = ""
        status_end_texto.value = "Campos preenchidos! Use 'Localizar pelo endereco' para obter coordenadas."
        status_end_texto.color = VERD
        try: page.update()
        except Exception: pass

    btn_buscar_end.on_click = _buscar_por_texto

    # -- Localizar pelo endereco ----------------------------------------------

    btn_localizar = ft.Container(
        content=ft.Row([
            ft.Icon("my_location_rounded", size=14, color=BG),
            ft.Text("Localizar pelo endereco", size=12, color=BG,
                    weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border_radius=8, bgcolor=AZUL, ink=True,
    )

    def _localizar(e=None):
        if not f_cidade.value.strip():
            _snack("Preencha pelo menos a cidade", AMAR)
            return
        btn_localizar.bgcolor = DIS
        btn_localizar.ink     = False
        status_geo.value      = "Buscando localizacao..."
        status_geo.color      = SEC
        try: page.update()
        except Exception: pass

        def _run():
            _lat, _lng = _geocodificar(
                f_logradouro.value, f_numero.value,
                f_bairro.value, f_cidade.value, f_estado.value,
            )
            if _lat and _lng:
                lat[0] = _lat
                lng[0] = _lng
                coords_txt.value = f"{_lat:.6f}, {_lng:.6f}"
                status_geo.value = "Localizacao encontrada!"
                status_geo.color = VERD
                _atualizar_mapa()
            else:
                status_geo.value = "Nao encontrado -- tente com menos detalhes"
                status_geo.color = AMAR
            btn_localizar.bgcolor = AZUL
            btn_localizar.ink     = True
            try: page.update()
            except Exception: pass

        threading.Thread(target=_run, daemon=True).start()

    btn_localizar.on_click = _localizar

    # -- Salvar ---------------------------------------------------------------

    def _salvar(e):
        resultado = {
            "cep":         f_cep.value.strip(),
            "logradouro":  f_logradouro.value.strip(),
            "numero":      f_numero.value.strip(),
            "complemento": f_complemento.value.strip(),
            "bairro":      f_bairro.value.strip(),
            "cidade":      f_cidade.value.strip(),
            "estado":      f_estado.value.strip(),
            "lat":         lat[0],
            "lng":         lng[0],
        }
        partes = [
            f"{resultado['logradouro']}, {resultado['numero']}".strip(", "),
            resultado["complemento"],
            resultado["bairro"],
            f"{resultado['cidade']}/{resultado['estado']}".strip("/"),
            resultado["cep"],
        ]
        resultado["endereco_fmt"] = " -- ".join(p for p in partes if p)
        try:
            if on_salvar:
                on_salvar(resultado)
            _snack("Endereco salvo!")
            voltar_fn()
        except Exception as ex:
            logging.exception("[ENDERECO] _salvar: %s", ex)
            _snack(f"Erro: {str(ex)[:60]}", VERM)

    btn_salvar = ft.Container(
        content=ft.Row([
            ft.Icon("save_rounded", size=16, color=BG),
            ft.Text("Salvar endereco", size=14, color=BG,
                    weight=ft.FontWeight.W_700),
        ], spacing=6, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=20, vertical=14),
        border_radius=10, bgcolor=AZUL, ink=True, expand=True,
    )
    btn_salvar.on_click = _salvar

    # -- Cabecalho ------------------------------------------------------------

    btn_voltar = ft.Container(
        content=ft.Row([
            ft.Icon("arrow_back", size=16, color=AZUL),
            ft.Text("Voltar", size=13, color=AZUL),
        ], spacing=4, tight=True),
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        border_radius=8, ink=True,
    )
    btn_voltar.on_click = lambda e: voltar_fn()

    cabecalho = ft.Container(
        content=ft.Row([
            btn_voltar,
            ft.Row([
                ft.Icon("location_on_rounded", size=20, color=AZUL),
                ft.Text(titulo, size=16, weight=ft.FontWeight.W_700, color=TXT),
            ], spacing=8, tight=True),
            ft.Container(expand=True),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=lay.cabecalho_padding(),
        border=ft.Border(bottom=ft.BorderSide(1, BORDA)),
    )

    # -- Inicializar mapa se ja tem coords ------------------------------------

    _atualizar_mapa()

    # -- Layout ---------------------------------------------------------------

    conteudo = ft.Column([
        ft.Text("CEP", size=11, color=SEC),
        ft.Row([f_cep, status_cep], spacing=8,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Container(height=8),

        ft.Text("Logradouro e Numero", size=11, color=SEC),
        ft.Row([f_logradouro, f_numero], spacing=8),
        ft.Container(height=8),

        ft.Text("Complemento", size=11, color=SEC),
        f_complemento,
        ft.Container(height=8),

        ft.Text("Bairro", size=11, color=SEC),
        f_bairro,
        ft.Container(height=8),

        ft.Text("Cidade e Estado", size=11, color=SEC),
        ft.Row([f_cidade, f_estado], spacing=8),
        ft.Container(height=16),

        # Painel de localizacao
        ft.Container(
            content=ft.Column([
                ft.Text("Localizacao no mapa", size=13, color=TXT,
                        weight=ft.FontWeight.W_600),
                ft.Container(height=10),

                # GPS do dispositivo
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon("gps_fixed_rounded", size=14, color=VERD),
                            ft.Text("Capturar com GPS", size=12, color=VERD,
                                    weight=ft.FontWeight.W_600),
                        ], spacing=6),
                        ft.Text("Esteja no local do cliente e toque o botao abaixo",
                                size=11, color=DIS),
                        ft.Container(height=8),
                        btn_gps,
                        ft.Container(height=4),
                        status_gps,
                    ], spacing=4),
                    padding=ft.padding.all(12),
                    border_radius=8, bgcolor=f"{VERD}11",
                    border=ft.Border(
                        top=ft.BorderSide(1, f"{VERD}44"),
                        bottom=ft.BorderSide(1, f"{VERD}44"),
                        left=ft.BorderSide(2, VERD),
                        right=ft.BorderSide(1, f"{VERD}44")),
                ),
                ft.Container(height=10),

                # Colar link WhatsApp
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon("chat_rounded", size=14, color=VERD),
                            ft.Text("Colar link do WhatsApp", size=12, color=VERD,
                                    weight=ft.FontWeight.W_600),
                        ], spacing=6),
                        ft.Text("Cole o link de localizacao enviado pelo cliente",
                                size=11, color=DIS),
                        ft.Container(height=6),
                        f_link_wap,
                        ft.Container(height=6),
                        ft.Row([btn_extrair], alignment=ft.MainAxisAlignment.END),
                        status_link,
                    ], spacing=4),
                    padding=ft.padding.all(12),
                    border_radius=8, bgcolor=f"{VERD}11",
                    border=ft.Border(
                        top=ft.BorderSide(1, f"{VERD}44"),
                        bottom=ft.BorderSide(1, f"{VERD}44"),
                        left=ft.BorderSide(2, VERD),
                        right=ft.BorderSide(1, f"{VERD}44")),
                ),
                ft.Container(height=10),

                # Colar endereco copiado (texto livre do Google Maps / SMS)
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon("content_paste_rounded", size=14, color=LRNJ),
                            ft.Text("Colar endereco copiado", size=12, color=LRNJ,
                                    weight=ft.FontWeight.W_600),
                        ], spacing=6),
                        ft.Text("Cole o endereco copiado do Google Maps ou SMS",
                                size=11, color=DIS),
                        ft.Container(height=6),
                        f_end_texto,
                        ft.Container(height=6),
                        ft.Row([btn_buscar_end],
                               alignment=ft.MainAxisAlignment.END),
                        status_end_texto,
                    ], spacing=4),
                    padding=ft.padding.all(12),
                    border_radius=8, bgcolor=f"{LRNJ}11",
                    border=ft.Border(
                        top=ft.BorderSide(1, f"{LRNJ}44"),
                        bottom=ft.BorderSide(1, f"{LRNJ}44"),
                        left=ft.BorderSide(2, LRNJ),
                        right=ft.BorderSide(1, f"{LRNJ}44")),
                ),
                ft.Container(height=10),

                btn_localizar,
                ft.Container(height=4),
                status_geo,
                coords_txt,
                ft.Container(height=8),
                mapa_col,
            ], spacing=2),
            padding=ft.padding.all(14), border_radius=10, bgcolor=CARD,
            border=ft.Border(
                top=ft.BorderSide(1, BORDA), bottom=ft.BorderSide(1, BORDA),
                left=ft.BorderSide(1, BORDA), right=ft.BorderSide(1, BORDA)),
        ),
        ft.Container(height=20),
    ], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

    corpo = ft.Column([
        ft.Container(height=lay.spacer_topo, bgcolor=BG),
        cabecalho,
        ft.Container(
            content=conteudo,
            padding=ft.padding.symmetric(horizontal=16),
            expand=True,
        ),
        ft.Container(
            content=ft.Row([btn_salvar]),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border=ft.Border(top=ft.BorderSide(1, BORDA)),
            bgcolor=BG,
        ),
    ], expand=True, spacing=0)

    try: larg = page.width or 800
    except Exception: larg = 800

    cf = ft.Row([
        ft.Container(expand=True),
        ft.Container(content=corpo, width=480),
        ft.Container(expand=True),
    ], expand=True) if larg > 500 else corpo

    return ft.Container(bgcolor=BG, expand=True, content=cf)
