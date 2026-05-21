"""
Tareas de facturación en segundo plano.
Procesa ventas: firma DTE, envío a MH, envío de correo.
Compatible con Celery, worker Docker (procesar_tareas_facturacion --loop)
o disparo en hilo tras encolar (encolar_y_disparar_facturacion).
"""
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional

from django.db import close_old_connections, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Reintentos con exponential backoff: 1min, 5min, 15min, 45min, 2h
BACKOFF_MINUTES = [1, 5, 15, 45, 120]
MAX_INTENTOS = len(BACKOFF_MINUTES) + 2  # Hasta ~6 intentos


def procesar_factura_venta(venta_id: int) -> dict:
    """
    Procesa una factura: firma, envía a MH, envía correo si aceptada.
    Retorna dict con exito, mensaje, estado.
    """
    from .models import Venta, TareaFacturacion
    from .services.facturacion_service import (
        FacturacionService,
        FacturacionServiceError,
        EnvioMHTransitorioError,
    )
    from .services.email_service import enviar_factura_email

    try:
        venta = Venta.objects.select_related('empresa', 'cliente').prefetch_related('detalles__producto').get(pk=venta_id)
    except Venta.DoesNotExist:
        return {'exito': False, 'mensaje': 'Venta no encontrada', 'estado': 'Error'}

    if not venta.empresa:
        return {'exito': False, 'mensaje': 'Venta sin empresa', 'estado': 'Error'}

    try:
        servicio = FacturacionService(venta.empresa)
        resultado = servicio.procesar_factura(venta)
        venta.refresh_from_db()

        if resultado.get('exito') and venta.estado_dte == 'AceptadoMH':
            # Enviar correo solo cuando MH aceptó el DTE.
            # enviar_factura_email ya maneja sus propios errores internamente;
            # el try/except aquí es una red de seguridad extra para no bloquear el flujo.
            try:
                enviar_factura_email(venta)
            except Exception as e:
                logger.warning(f"No se pudo enviar correo para venta {venta_id}: {e}")

            tarea = getattr(venta, 'tarea_facturacion', None)
            if tarea and tarea.enviar_whatsapp_despues:
                from .services.whatsapp_post_factura import enviar_whatsapp_tras_correo_si_aplica
                tel = (tarea.whatsapp_telefono_destino or '').strip()
                wa_err = enviar_whatsapp_tras_correo_si_aplica(
                    venta, enviar=True, telefono=tel,
                )
                if wa_err:
                    logger.warning('WhatsApp venta %s: %s', venta_id, wa_err)

        return {
            'exito': resultado.get('exito', False),
            'mensaje': resultado.get('mensaje', 'Procesado'),
            'estado': 'Completada' if resultado.get('exito') else 'Error',
        }
    except EnvioMHTransitorioError as e:
        raise  # Re-lanzar para que el caller programe reintento
    except FacturacionServiceError as e:
        logger.error(f"Error facturación venta {venta_id}: {e}")
        return {'exito': False, 'mensaje': str(e), 'estado': 'Error'}
    except Exception as e:
        logger.exception(f"Error inesperado venta {venta_id}: {e}")
        return {'exito': False, 'mensaje': str(e), 'estado': 'Error'}


def ejecutar_tarea(tarea_id: int) -> bool:
    """
    Ejecuta una tarea de facturación. Retorna True si completó (éxito o error final), False si debe reintentar.
    """
    from .models import TareaFacturacion
    from .services.facturacion_service import EnvioMHTransitorioError

    try:
        tarea = TareaFacturacion.objects.select_related('venta').get(pk=tarea_id)
    except TareaFacturacion.DoesNotExist:
        return True

    if tarea.estado not in ('Pendiente', 'Error'):
        if tarea.estado == 'Completada':
            return True
        # Procesando - podría ser un worker que murió
        tarea.estado = 'Pendiente'
        tarea.save(update_fields=['estado'])

    tarea.estado = 'Procesando'
    tarea.save(update_fields=['estado', 'actualizada_at'])

    try:
        resultado = procesar_factura_venta(tarea.venta_id)
        tarea.intentos += 1
        tarea.error_mensaje = resultado.get('mensaje', '')
        tarea.proximo_reintento = None

        if resultado.get('estado') == 'Completada':
            tarea.estado = 'Completada'
            tarea.save(update_fields=['estado', 'intentos', 'error_mensaje', 'proximo_reintento', 'actualizada_at'])
            return True
        else:
            tarea.estado = 'Error'
            tarea.save(update_fields=['estado', 'intentos', 'error_mensaje', 'proximo_reintento', 'actualizada_at'])
            return True  # Error final, no reintentar

    except EnvioMHTransitorioError as e:
        tarea.intentos += 1
        tarea.error_mensaje = str(e)[:500]
        tarea.estado = 'Error'

        if tarea.intentos < MAX_INTENTOS:
            idx = min(tarea.intentos - 1, len(BACKOFF_MINUTES) - 1)
            mins = BACKOFF_MINUTES[idx]
            tarea.proximo_reintento = timezone.now() + timedelta(minutes=mins)
            tarea.save(update_fields=['estado', 'intentos', 'error_mensaje', 'proximo_reintento', 'actualizada_at'])
            logger.info(f"Tarea {tarea_id} programada para reintento en {mins} min")
            return False
        else:
            tarea.proximo_reintento = None
            tarea.save(update_fields=['estado', 'intentos', 'error_mensaje', 'proximo_reintento', 'actualizada_at'])
            return True


def _ejecutar_tarea_en_hilo(tarea_id: int) -> None:
    """Ejecuta una tarea fuera del ciclo HTTP (cierra conexiones Django al terminar)."""
    close_old_connections()
    try:
        ejecutar_tarea(tarea_id)
    except Exception:
        logger.exception('Error en hilo de facturación tarea_id=%s', tarea_id)
    finally:
        close_old_connections()


def _disparar_en_hilo(callback) -> None:
    threading.Thread(target=callback, daemon=True).start()


def encolar_y_disparar_facturacion(
    venta_id: int,
    *,
    enviar_whatsapp: bool = False,
    whatsapp_telefono: str = '',
) -> int:
    """
    Encola TareaFacturacion y, tras commit, procesa en segundo plano.
    Evita que la factura quede PENDIENTE si no hay cron/worker externo.
    """
    from .models import TareaFacturacion

    tarea, _ = TareaFacturacion.objects.get_or_create(
        venta_id=venta_id,
        defaults={'estado': 'Pendiente'},
    )
    if tarea.estado == 'Completada':
        return tarea.id
    if tarea.estado not in ('Pendiente', 'Error'):
        tarea.estado = 'Pendiente'
    tarea.enviar_whatsapp_despues = bool(enviar_whatsapp)
    tarea.whatsapp_telefono_destino = (whatsapp_telefono or '')[:32]
    tarea.save(
        update_fields=[
            'estado',
            'actualizada_at',
            'enviar_whatsapp_despues',
            'whatsapp_telefono_destino',
        ]
    )

    tarea_id = tarea.id

    def _schedule():
        _disparar_en_hilo(lambda: _ejecutar_tarea_en_hilo(tarea_id))

    transaction.on_commit(_schedule)
    return tarea_id


def disparar_procesamiento_cola(limite: int = 20) -> None:
    """Procesa la cola en hilo (p. ej. al desactivar contingencia)."""
    def _schedule():
        def _run():
            close_old_connections()
            try:
                procesar_tareas_pendientes(limite=limite)
            except Exception:
                logger.exception('Error procesando cola de facturación')
            finally:
                close_old_connections()

        _disparar_en_hilo(_run)

    transaction.on_commit(_schedule)


def procesar_tareas_pendientes(limite: int = 20) -> int:
    """
    Procesa tareas pendientes o con proximo_reintento <= now.
    Retorna número de tareas procesadas.
    """
    from django.db.models import Q
    from .models import TareaFacturacion

    ahora = timezone.now()
    tareas = list(TareaFacturacion.objects.filter(
        estado__in=('Pendiente', 'Error')
    ).filter(
        Q(proximo_reintento__isnull=True) | Q(proximo_reintento__lte=ahora)
    ).select_related('venta')[:limite])

    procesadas = 0
    for t in tareas:
        ejecutar_tarea(t.id)
        procesadas += 1
    return procesadas
