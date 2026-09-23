"""
Integración Sistema Contable → AgilDTE (resumen IVA mensual).
Diseñado para desarrollo LOCAL; no desplegar al VPS hasta validar.

GET híbrido:
  - ventas / débito / retención → AgilDTE en vivo (tabla Venta)
  - compras / crédito fiscal → último resumen publicado por el contable
    (si el servidor contable no publica, se mantiene el valor anterior; nunca se borra)
"""
from __future__ import annotations

import calendar
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Empresa, ResumenIvaMensualContable, Venta
from .utils.tenant import get_empresa_ids_allowlist, require_empresa_allowed


def _solo_digitos(valor) -> str:
    return re.sub(r'\D', '', str(valor or ''))


def _dec(valor, default='0') -> Decimal:
    try:
        return Decimal(str(valor if valor is not None else default)).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default).quantize(Decimal('0.01'))


def _periodo_actual() -> str:
    return timezone.localdate().strftime('%Y-%m')


def _parse_uuid(valor) -> str | None:
    """Normaliza UUID del contable; None si vacío o inválido."""
    if valor is None:
        return None
    s = str(valor).strip()
    if not s:
        return None
    try:
        import uuid as _uuid
        return str(_uuid.UUID(s))
    except (TypeError, ValueError, AttributeError):
        return None


def _resolver_empresa_contable(request, *, empresa_id_raw=None, contable_uuid_raw=None, nrc_raw=None):
    """
    Resuelve la empresa AgilDTE por vínculo estable (UUID del contable), no por PK autoincremental.

    Orden:
      1) sistema_contable_empresa_id (UUID único e intransferible del contable)
      2) empresa_id numérico (solo caché / compatibilidad)
      3) NRC (primer vínculo; amarra el UUID si viene en el request)

    Así una reconstrucción de Docker/DB no rompe el sync: se vuelve a pegar el mismo UUID
    en la ficha AgilDTE (o se empareja por NRC) y el contable no depende del id 3/4/5…
    """
    contable_uuid = _parse_uuid(contable_uuid_raw)
    if contable_uuid:
        emp = Empresa.objects.filter(sistema_contable_empresa_id=contable_uuid).first()
        if emp is not None:
            r = require_empresa_allowed(request, emp.id)
            if r is not None:
                return None, r
            return emp, None

    # UUID aún no amarrado: preferir NRC (estable) antes que el id numérico (cambia en rebuilds).
    nrc = _solo_digitos(nrc_raw)
    if nrc:
        candidatas = [e for e in Empresa.objects.all() if _solo_digitos(e.nrc) == nrc]
        if len(candidatas) == 1:
            emp = candidatas[0]
            r = require_empresa_allowed(request, emp.id)
            if r is not None:
                return None, r
            if contable_uuid and not emp.sistema_contable_empresa_id:
                conflicto = Empresa.objects.filter(sistema_contable_empresa_id=contable_uuid).exclude(pk=emp.id).exists()
                if not conflicto:
                    emp.sistema_contable_empresa_id = contable_uuid
                    emp.sync_contable_habilitado = True
                    emp.save(update_fields=['sistema_contable_empresa_id', 'sync_contable_habilitado'])
            return emp, None
        if len(candidatas) > 1:
            return None, Response(
                {
                    'error': 'Varias empresas AgilDTE con el mismo NRC. Pegue el UUID del contable en «Sistema contable empresa id».',
                    'code': 'nrc_ambiguo',
                },
                status=status.HTTP_409_CONFLICT,
            )

    if empresa_id_raw is not None and str(empresa_id_raw).strip() != '':
        try:
            empresa_id = int(empresa_id_raw)
        except (TypeError, ValueError):
            return None, Response({'error': 'empresa_id inválido'}, status=status.HTTP_400_BAD_REQUEST)
        r = require_empresa_allowed(request, empresa_id)
        if r is not None:
            return None, r
        try:
            emp = Empresa.objects.get(pk=empresa_id)
        except Empresa.DoesNotExist:
            return None, Response({'error': 'Empresa no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        if contable_uuid and not emp.sistema_contable_empresa_id:
            conflicto = Empresa.objects.filter(sistema_contable_empresa_id=contable_uuid).exclude(pk=emp.id).exists()
            if not conflicto:
                emp.sistema_contable_empresa_id = contable_uuid
                emp.sync_contable_habilitado = True
                emp.save(update_fields=['sistema_contable_empresa_id', 'sync_contable_habilitado'])
        return emp, None

    return None, Response(
        {
            'error': (
                'No se encontró empresa. Pegue el UUID del contable en AgilDTE '
                '(«Sistema contable empresa id») o envíe NRC único.'
            ),
            'code': 'empresa_no_resuelta',
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _totales_ventas_agildte(empresa_id: int, periodo: str) -> dict:
    """Ventas del mes desde AgilDTE (en vivo)."""
    try:
        anio, mes = int(periodo[:4]), int(periodo[5:7])
    except (TypeError, ValueError):
        return {'ventas': 0.0, 'debito': 0.0, 'retencion': 0.0}

    first_day = timezone.datetime(anio, mes, 1).date()
    _, last_day_num = calendar.monthrange(anio, mes)
    last_day = timezone.datetime(anio, mes, last_day_num).date()

    qs = Venta.objects.filter(
        empresa_id=empresa_id,
        estado_dte__in=['AceptadoMH', 'Enviado'],
        fecha_emision__gte=first_day,
        fecha_emision__lte=last_day,
    )
    try:
        emp = Empresa.objects.get(pk=empresa_id)
        qs = qs.filter(ambiente_emision=emp.ambiente)
    except Empresa.DoesNotExist:
        pass

    agg = qs.aggregate(
        gravada=Sum('venta_gravada'),
        exenta=Sum('venta_exenta'),
        nosuj=Sum('venta_no_sujeta'),
        debito=Sum('debito_fiscal'),
        ret1=Sum('iva_retenido_1'),
        ret2=Sum('iva_retenido_2'),
    )
    gravada = float(agg['gravada'] or 0)
    exenta = float(agg['exenta'] or 0)
    nosuj = float(agg['nosuj'] or 0)
    debito = float(agg['debito'] or 0)
    retencion = float(agg['ret1'] or 0) + float(agg['ret2'] or 0)
    ventas = round(gravada + exenta + nosuj, 2)
    return {
        'ventas': ventas,
        'debito': round(debito, 2),
        'retencion': round(retencion, 2),
    }


def _serializar_hibrido(empresa_id: int, periodo: str, obj: ResumenIvaMensualContable | None) -> dict:
    vivos = _totales_ventas_agildte(empresa_id, periodo)
    compras = float(obj.compras) if obj else 0.0
    credito = float(obj.credito_fiscal) if obj else 0.0
    debito = vivos['debito']
    retencion = vivos['retencion']
    valor_pagar = round(debito - credito - retencion, 2)

    return {
        'empresa_id': empresa_id,
        'periodo': periodo,
        'ventas': vivos['ventas'],
        'debito': debito,
        'retencion': retencion,
        'compras': compras,
        'credito_fiscal': credito,
        'valor_a_pagar': valor_pagar,
        'generado_en': obj.generado_en.isoformat() if obj and obj.generado_en else None,
        'origen_compras': (obj.origen if obj else None) or None,
        'origen_ventas': 'agildte',
        'checksum': (obj.checksum if obj else '') or '',
        'nrc_reportado': (obj.nrc_reportado if obj else '') or '',
        'documento_reportado': (obj.documento_reportado if obj else '') or '',
        'actualizado_en': obj.actualizado_en.isoformat() if obj and obj.actualizado_en else None,
        'tiene_datos_compras': obj is not None,
        'tiene_datos': obj is not None or vivos['ventas'] > 0 or vivos['debito'] > 0,
        'origen': 'hibrido',
    }


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def resumen_iva_mes_contable_api(request):
    """
    GET  → híbrido (ventas AgilDTE en vivo + último resumen de compras del contable).
    POST → upsert del bloque compras/crédito. No borra datos si un envío falla (solo upsert).
    """
    if request.method == 'GET':
        return _get_resumen(request)
    return _post_resumen(request)


def _get_resumen(request):
    empresa_ids = get_empresa_ids_allowlist(request)
    if not empresa_ids:
        return Response({'error': 'Autenticación requerida'}, status=status.HTTP_401_UNAUTHORIZED)

    empresa, err = _resolver_empresa_contable(
        request,
        empresa_id_raw=request.query_params.get('empresa_id'),
        contable_uuid_raw=request.query_params.get('sistema_contable_empresa_id')
        or request.query_params.get('contable_empresa_id'),
        nrc_raw=request.query_params.get('nrc'),
    )
    if err is not None:
        return err

    periodo = (request.query_params.get('periodo') or _periodo_actual()).strip()
    if not re.fullmatch(r'\d{4}-\d{2}', periodo):
        return Response({'error': 'periodo debe ser YYYY-MM'}, status=status.HTTP_400_BAD_REQUEST)

    obj = ResumenIvaMensualContable.objects.filter(empresa_id=empresa.id, periodo=periodo).first()
    payload = _serializar_hibrido(empresa.id, periodo, obj)
    payload['sistema_contable_empresa_id'] = (
        str(empresa.sistema_contable_empresa_id) if empresa.sistema_contable_empresa_id else None
    )
    return Response(payload)


def _post_resumen(request):
    empresa_ids = get_empresa_ids_allowlist(request)
    if not empresa_ids:
        return Response({'error': 'Autenticación requerida'}, status=status.HTTP_401_UNAUTHORIZED)

    data = request.data if isinstance(request.data, dict) else {}
    empresa, err = _resolver_empresa_contable(
        request,
        empresa_id_raw=data.get('empresa_id'),
        contable_uuid_raw=data.get('sistema_contable_empresa_id') or data.get('contable_empresa_id'),
        nrc_raw=data.get('nrc') or data.get('nrc_reportado'),
    )
    if err is not None:
        return err

    if not empresa.sync_contable_habilitado and not empresa.dashboard_compras_premium_enabled:
        return Response(
            {
                'error': 'La empresa no tiene sync contable ni dashboard compras premium habilitado.',
                'code': 'sync_contable_disabled',
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    periodo = str(data.get('periodo') or _periodo_actual()).strip()
    if not re.fullmatch(r'\d{4}-\d{2}', periodo):
        return Response({'error': 'periodo debe ser YYYY-MM'}, status=status.HTTP_400_BAD_REQUEST)

    nrc_reportado = _solo_digitos(data.get('nrc') or data.get('nrc_reportado'))
    nrc_empresa = _solo_digitos(empresa.nrc)
    if nrc_reportado and nrc_empresa and nrc_reportado != nrc_empresa:
        return Response(
            {
                'error': 'El NRC reportado no coincide con el NRC de la empresa en AgilDTE.',
                'code': 'nrc_mismatch',
                'nrc_empresa': nrc_empresa,
                'nrc_reportado': nrc_reportado,
            },
            status=status.HTTP_409_CONFLICT,
        )

    documento_reportado = _solo_digitos(
        data.get('documento_identidad') or data.get('nit') or data.get('documento_reportado')
    )
    documento_empresa = _solo_digitos(empresa.nit or empresa.user_api_mh)
    documento_diverge = bool(
        documento_reportado and documento_empresa and documento_reportado != documento_empresa
    )
    if documento_diverge and not bool(data.get('documento_confirmado')):
        return Response(
            {
                'error': 'NIT/DUI no coincide con AgilDTE. Confirme en el sistema contable que es el mismo contribuyente.',
                'code': 'documento_mismatch',
                'documento_empresa': documento_empresa,
                'documento_reportado': documento_reportado,
            },
            status=status.HTTP_409_CONFLICT,
        )

    compras = _dec(data.get('compras'))
    credito = _dec(data.get('credito_fiscal'))
    ventas_snap = _dec(data.get('ventas'))
    debito_snap = _dec(data.get('debito'))
    retencion_snap = _dec(data.get('retencion'))
    if 'valor_a_pagar' in data and data.get('valor_a_pagar') is not None:
        valor_snap = _dec(data.get('valor_a_pagar'))
    else:
        valor_snap = (debito_snap - credito - retencion_snap).quantize(Decimal('0.01'))

    generado_en = None
    raw_gen = data.get('generado_en')
    if raw_gen:
        generado_en = parse_datetime(str(raw_gen))
        if generado_en is None:
            try:
                generado_en = datetime.fromisoformat(str(raw_gen).replace('Z', '+00:00'))
            except ValueError:
                generado_en = timezone.now()
    if generado_en is None:
        generado_en = timezone.now()

    contable_uuid = _parse_uuid(data.get('sistema_contable_empresa_id') or data.get('contable_empresa_id'))
    if contable_uuid and str(empresa.sistema_contable_empresa_id or '') != contable_uuid:
        if not empresa.sistema_contable_empresa_id:
            conflicto = Empresa.objects.filter(sistema_contable_empresa_id=contable_uuid).exclude(pk=empresa.id).exists()
            if not conflicto:
                empresa.sistema_contable_empresa_id = contable_uuid
                empresa.sync_contable_habilitado = True
                empresa.save(update_fields=['sistema_contable_empresa_id', 'sync_contable_habilitado'])

    obj, created = ResumenIvaMensualContable.objects.update_or_create(
        empresa_id=empresa.id,
        periodo=periodo,
        defaults={
            'ventas': ventas_snap,
            'debito': debito_snap,
            'retencion': retencion_snap,
            'compras': compras,
            'credito_fiscal': credito,
            'valor_a_pagar': valor_snap,
            'generado_en': generado_en,
            'origen': str(data.get('origen') or 'sistema_contable')[:40],
            'checksum': str(data.get('checksum') or '')[:64],
            'nrc_reportado': nrc_reportado[:20],
            'documento_reportado': documento_reportado[:30],
        },
    )

    payload = _serializar_hibrido(empresa.id, periodo, obj)
    payload['created'] = created
    payload['documento_diverge'] = documento_diverge
    payload['sistema_contable_empresa_id'] = (
        str(empresa.sistema_contable_empresa_id) if empresa.sistema_contable_empresa_id else None
    )
    return Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
