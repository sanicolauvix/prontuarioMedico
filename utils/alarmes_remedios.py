"""
alarmes_remedios.py
Sistema de alertas de medicamentos:
  1. Notificação persistente via plyer (desktop + Android)
  2. Alarme nativo do celular via deep link / intent
  3. Arquivo .ics para Google Calendar com alarmes
  4. Thread de monitoramento que verifica a cada minuto
"""

import threading
import time
import json
import os
import platform
import subprocess
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path


# ══════════════════════════════════════════════════════════════
# 1. NOTIFICAÇÃO VIA PLYER
# ══════════════════════════════════════════════════════════════

def notificar(titulo: str, mensagem: str, urgente: bool = False):
    """
    Envia notificação do sistema. Funciona em:
    - Windows: via plyer (toast notification)
    - Linux:   via plyer ou notify-send
    - Android: via plyer
    """
    # Tenta plyer primeiro
    try:
        from plyer import notification
        notification.notify(
            title=titulo,
            message=mensagem,
            app_name="Prontuário Médico",
            app_icon="",        # path para ícone .ico/.png se tiver
            timeout=0 if urgente else 10,   # 0 = persiste até fechar
        )
        return True
    except Exception:
        pass

    # Fallback Linux: notify-send
    sistema = platform.system()
    if sistema == "Linux":
        try:
            urgency = "critical" if urgente else "normal"
            subprocess.Popen([
                "notify-send",
                f"--urgency={urgency}",
                "--expire-time=0" if urgente else "--expire-time=10000",
                "--app-name=Prontuário Médico",
                titulo, mensagem
            ])
            return True
        except Exception:
            pass

    # Fallback Windows: msg via PowerShell
    if sistema == "Windows":
        try:
            script = f"""
            Add-Type -AssemblyName System.Windows.Forms
            $notify = New-Object System.Windows.Forms.NotifyIcon
            $notify.Icon = [System.Drawing.SystemIcons]::Information
            $notify.BalloonTipTitle = '{titulo}'
            $notify.BalloonTipText = '{mensagem}'
            $notify.Visible = $true
            $notify.ShowBalloonTip(0)
            Start-Sleep 3
            $notify.Dispose()
            """
            subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-Command", script],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True
        except Exception:
            pass

    return False


# ══════════════════════════════════════════════════════════════
# 2. ALARME NATIVO DO CELULAR
# ══════════════════════════════════════════════════════════════

def criar_alarme_celular(hora: int, minuto: int, label: str):
    """
    Abre o app de alarme do celular/desktop com horário pré-definido.
    - Android: via deep link intent (funciona no Flet mobile)
    - iOS:     via URL scheme
    - Windows: via URI do relógio do Windows
    - Linux:   via GNOME Clock ou similar
    """
    sistema = platform.system()
    label_enc = label.replace(" ", "%20")

    if sistema == "Windows":
        # Abre o app Relógio do Windows na aba Alarme
        try:
            os.startfile(f"ms-clock:alarm")
            return True
        except Exception:
            pass

    elif sistema == "Linux":
        # Tenta GNOME Clock
        try:
            subprocess.Popen(["gnome-clocks"])
            return True
        except Exception:
            pass

    # Android/iOS via Flet: usa webbrowser para disparar intent
    # No Android o Flet consegue abrir URIs nativos
    try:
        # Android Clock intent
        uri_android = (
            f"intent://alarm?hour={hora}&minutes={minuto}"
            f"&message={label_enc}&vibrate=true"
            f"#Intent;scheme=android-app;package=com.google.android.deskclock;"
            f"action=SET_ALARM;end"
        )
        webbrowser.open(uri_android)
        return True
    except Exception:
        pass

    return False


# ══════════════════════════════════════════════════════════════
# 3. GERADOR DE ARQUIVO .ICS
# ══════════════════════════════════════════════════════════════

def gerar_ics_remedio(remedio: dict, horarios: list[dict]) -> str:
    """
    Gera arquivo .ics com eventos recorrentes para o remédio.
    Cada horário vira um evento com alarme 5 min antes.
    horarios = [{"hora": 8, "minuto": 0}, {"hora": 20, "minuto": 0}]
    """
    try:
        from icalendar import Calendar, Event, Alarm, vText, vDatetime
        from datetime import timezone
    except ImportError:
        # Gera manualmente sem a lib
        return _gerar_ics_manual(remedio, horarios)

    cal = Calendar()
    cal.add("prodid", "-//Prontuário Médico//BR")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", "Medicamentos")

    nome     = remedio.get("nome", "Remédio")
    dosagem  = remedio.get("dosagem", "")
    freq     = remedio.get("frequencia", "")
    descricao = f"{nome} {dosagem}\n{freq}".strip()

    # Data de início
    hoje = datetime.now()
    try:
        d, m, a = remedio["data_inicio"].split("/")
        inicio = datetime(int(a), int(m), int(d))
    except Exception:
        inicio = hoje

    # Data de fim
    fim = None
    if remedio.get("data_fim"):
        try:
            d, m, a = remedio["data_fim"].split("/")
            fim = datetime(int(a), int(m), int(d))
        except Exception:
            pass

    for horario in horarios:
        hora   = horario.get("hora", 8)
        minuto = horario.get("minuto", 0)

        dt_inicio = inicio.replace(hour=hora, minute=minuto, second=0, microsecond=0)

        evento = Event()
        evento.add("summary",     vText(f"💊 {nome} {dosagem}"))
        evento.add("description", vText(descricao))
        evento.add("dtstart",     dt_inicio)
        evento.add("dtend",       dt_inicio + timedelta(minutes=15))

        # Recorrência diária até a data fim (ou 1 ano)
        dt_fim_rrule = fim if fim else inicio + timedelta(days=365)
        until_str = dt_fim_rrule.strftime("%Y%m%dT%H%M%SZ")
        evento.add("rrule", {"freq": "daily", "until": dt_fim_rrule})

        # Alarme 5 minutos antes
        alarme = Alarm()
        alarme.add("action",  "AUDIO")
        alarme.add("trigger", timedelta(minutes=-5))
        alarme.add("description", vText(f"Tome {nome}!"))
        evento.add_component(alarme)

        # Segundo alarme: na hora exata
        alarme2 = Alarm()
        alarme2.add("action",  "DISPLAY")
        alarme2.add("trigger", timedelta(0))
        alarme2.add("description", vText(f"💊 {nome} {dosagem} — {freq}"))
        evento.add_component(alarme2)

        cal.add_component(evento)

    return cal.to_ical().decode("utf-8")


def _gerar_ics_manual(remedio: dict, horarios: list[dict]) -> str:
    """Gera .ics manualmente sem a lib icalendar."""
    nome    = remedio.get("nome", "Remédio")
    dosagem = remedio.get("dosagem", "")
    freq    = remedio.get("frequencia", "")

    hoje = datetime.now()
    try:
        d, m, a = remedio["data_inicio"].split("/")
        inicio = datetime(int(a), int(m), int(d))
    except Exception:
        inicio = hoje

    try:
        d, m, a = remedio["data_fim"].split("/")
        fim = datetime(int(a), int(m), int(d))
    except Exception:
        fim = inicio + timedelta(days=365)

    until_str = fim.strftime("%Y%m%dT%H%M%SZ")

    linhas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Prontuário Médico//BR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Medicamentos",
    ]

    for i, horario in enumerate(horarios):
        hora   = horario.get("hora", 8)
        minuto = horario.get("minuto", 0)
        dt     = inicio.replace(hour=hora, minute=minuto, second=0)
        dt_end = dt + timedelta(minutes=15)
        uid    = f"remedio-{remedio.get('id','0')}-{i}@prontuario"

        linhas += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{dt_end.strftime('%Y%m%dT%H%M%S')}",
            f"RRULE:FREQ=DAILY;UNTIL={until_str}",
            f"SUMMARY:💊 {nome} {dosagem}",
            f"DESCRIPTION:{nome} {dosagem}\\n{freq}",
            "BEGIN:VALARM",
            "TRIGGER:-PT5M",
            "ACTION:AUDIO",
            f"DESCRIPTION:Tome {nome}!",
            "END:VALARM",
            "BEGIN:VALARM",
            "TRIGGER:PT0S",
            "ACTION:DISPLAY",
            f"DESCRIPTION:💊 {nome} — {freq}",
            "END:VALARM",
            "END:VEVENT",
        ]

    linhas.append("END:VCALENDAR")
    return "\r\n".join(linhas)


def salvar_ics(remedio: dict, horarios: list[dict], pasta: str = ".") -> str:
    """Salva o .ics em disco e retorna o caminho."""
    conteudo = gerar_ics_remedio(remedio, horarios)
    nome_arq = re.sub(r"[^a-zA-Z0-9]", "_", remedio.get("nome", "remedio"))
    caminho  = os.path.join(pasta, f"alarme_{nome_arq}.ics")
    Path(caminho).write_text(conteudo, encoding="utf-8")
    return caminho


import re   # garante import após uso acima


# ══════════════════════════════════════════════════════════════
# 4. THREAD DE MONITORAMENTO
# ══════════════════════════════════════════════════════════════

class MonitorAlarmes:
    """
    Roda em background e dispara notificações nos horários certos.
    Persiste os horários agendados em alarmes.json.
    """

    ARQUIVO_ALARMES = "alarmes_remedios.json"

    def __init__(self):
        self._stop   = threading.Event()
        self._thread = None
        self._alarmes: list[dict] = []
        self._disparados: set = set()   # uid dos já disparados hoje
        self._carregar()

    def _carregar(self):
        try:
            if Path(self.ARQUIVO_ALARMES).exists():
                self._alarmes = json.loads(
                    Path(self.ARQUIVO_ALARMES).read_text(encoding="utf-8")
                )
        except Exception:
            self._alarmes = []

    def _salvar(self):
        try:
            Path(self.ARQUIVO_ALARMES).write_text(
                json.dumps(self._alarmes, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    def adicionar_alarme(self, remedio_id: int, nome: str, dosagem: str,
                          horarios: list[dict]):
        """
        horarios = [{"hora": 8, "minuto": 0}, {"hora": 20, "minuto": 0}]
        """
        # Remove alarmes anteriores do mesmo remédio
        self._alarmes = [a for a in self._alarmes if a.get("remedio_id") != remedio_id]
        self._alarmes.append({
            "remedio_id": remedio_id,
            "nome":       nome,
            "dosagem":    dosagem,
            "horarios":   horarios,
            "ativo":      True,
        })
        self._salvar()

    def remover_alarme(self, remedio_id: int):
        self._alarmes = [a for a in self._alarmes if a.get("remedio_id") != remedio_id]
        self._salvar()

    def listar_alarmes(self) -> list[dict]:
        return [a for a in self._alarmes if a.get("ativo")]

    def _checar(self):
        """Chamado a cada minuto. Dispara notificações nos horários."""
        agora     = datetime.now()
        hoje_str  = agora.strftime("%Y-%m-%d")
        hora_min  = (agora.hour, agora.minute)

        for alarme in self._alarmes:
            if not alarme.get("ativo"):
                continue
            nome    = alarme["nome"]
            dosagem = alarme.get("dosagem", "")

            for horario in alarme.get("horarios", []):
                h = horario.get("hora", 0)
                m = horario.get("minuto", 0)

                if (h, m) == hora_min:
                    uid = f"{alarme['remedio_id']}-{hoje_str}-{h:02d}{m:02d}"
                    if uid in self._disparados:
                        continue

                    self._disparados.add(uid)

                    # Notificação persistente
                    notificar(
                        titulo=f"💊 Hora do remédio!",
                        mensagem=f"{nome} {dosagem}",
                        urgente=True,
                    )

                    # Abre app de alarme do celular também
                    criar_alarme_celular(h, m, f"{nome} {dosagem}")

        # Limpa disparados de dias anteriores
        self._disparados = {
            uid for uid in self._disparados
            if hoje_str in uid
        }

    def iniciar(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def _loop():
            while not self._stop.is_set():
                try:
                    self._checar()
                except Exception as e:
                    print(f"[monitor_alarmes] Erro: {e}")
                # Espera até o próximo minuto exato
                agora   = datetime.now()
                espera  = 60 - agora.second
                self._stop.wait(espera)

        self._thread = threading.Thread(target=_loop, daemon=True, name="MonitorAlarmes")
        self._thread.start()
        print("[monitor_alarmes] Iniciado.")

    def parar(self):
        self._stop.set()


# Instância global — importada pelo app.py
monitor = MonitorAlarmes()


# ══════════════════════════════════════════════════════════════
# 5. HELPERS PARA A TELA DE REMÉDIOS
# ══════════════════════════════════════════════════════════════

def calcular_horarios_por_intervalo(intervalo_horas: int,
                                     hora_inicio: int = 8) -> list[dict]:
    """
    Dado um intervalo (ex: 8h), retorna os horários do dia.
    hora_inicio = hora da primeira dose (padrão: 8h da manhã).
    """
    if not intervalo_horas or intervalo_horas <= 0:
        return [{"hora": hora_inicio, "minuto": 0}]

    horarios = []
    hora = hora_inicio
    while hora < hora_inicio + 24:
        horarios.append({"hora": hora % 24, "minuto": 0})
        hora += intervalo_horas
        if len(horarios) >= 24 // intervalo_horas:
            break

    return horarios


def agendar_remedio(remedio: dict, intervalo_horas: int,
                     hora_inicio: int = 8, salvar_ics_em: str = ".") -> str:
    """
    Agenda alarmes para um remédio e gera o .ics.
    Retorna caminho do arquivo .ics gerado.
    """
    horarios = calcular_horarios_por_intervalo(intervalo_horas, hora_inicio)

    # Adiciona ao monitor de background
    monitor.adicionar_alarme(
        remedio_id=remedio.get("id", 0),
        nome=remedio.get("nome", "Remédio"),
        dosagem=remedio.get("dosagem", ""),
        horarios=horarios,
    )

    # Gera .ics
    caminho_ics = salvar_ics(remedio, horarios, pasta=salvar_ics_em)

    return caminho_ics


def abrir_ics_no_calendario(caminho_ics: str):
    """Abre o .ics no app padrão (Google Calendar, Outlook, etc.)."""
    try:
        sistema = platform.system()
        if sistema == "Windows":
            os.startfile(caminho_ics)
        elif sistema == "Darwin":
            subprocess.Popen(["open", caminho_ics])
        else:
            subprocess.Popen(["xdg-open", caminho_ics])
        return True
    except Exception:
        webbrowser.open(f"file://{os.path.abspath(caminho_ics)}")
        return False