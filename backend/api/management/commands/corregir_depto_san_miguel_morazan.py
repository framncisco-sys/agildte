"""
Corrige el swap histórico CAT-012: San Miguel↔Morazán.

Antes (UI incorrecta): 13=San Miguel, 12=Morazán
Oficial MH:            12=San Miguel, 13=Morazán

Uso (servidor, tras deploy):
  python manage.py corregir_depto_san_miguel_morazan --dry-run
  python manage.py corregir_depto_san_miguel_morazan --apply
"""
from django.core.management.base import BaseCommand
from django.db.models import Q

from api.models import Cliente, Empresa, Venta
from api.utils.mh_direccion import normalizar_ubicacion_mh

MUNI_SM = ('21', '22', '23')
MUNI_MZ = ('27', '28')


class Command(BaseCommand):
    help = 'Corrige departamentos 12/13 (San Miguel / Morazán) en clientes, empresas y ventas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Aplica los cambios. Sin este flag solo muestra el dry-run.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo listar (por defecto si no hay --apply).',
        )

    def handle(self, *args, **options):
        aplicar = bool(options.get('apply'))
        self.stdout.write(
            self.style.WARNING('MODO: APLICAR cambios') if aplicar
            else self.style.NOTICE('MODO: dry-run (sin guardar). Use --apply para corregir.')
        )

        n_cli = self._corregir_queryset(
            Cliente.objects.all(),
            'cliente',
            aplicar,
            depto_attr='departamento',
            muni_attr='municipio',
            dist_attr='distrito',
            label_fn=lambda o: f'Cliente #{o.id} {o.nombre}',
        )
        n_emp = self._corregir_queryset(
            Empresa.objects.all(),
            'empresa',
            aplicar,
            depto_attr='departamento',
            muni_attr='municipio',
            dist_attr='distrito',
            label_fn=lambda o: f'Empresa #{o.id} {o.nombre}',
        )
        n_ven = self._corregir_queryset(
            Venta.objects.filter(
                Q(departamento_receptor__isnull=False) | Q(municipio_receptor__isnull=False)
            ),
            'venta',
            aplicar,
            depto_attr='departamento_receptor',
            muni_attr='municipio_receptor',
            dist_attr='distrito_receptor',
            label_fn=lambda o: f'Venta #{o.id} {o.numero_control or o.codigo_generacion or ""}',
        )

        self.stdout.write('')
        self.stdout.write(
            f'Resumen: clientes={n_cli}, empresas={n_emp}, ventas={n_ven} '
            + ('actualizados.' if aplicar else 'a corregir (dry-run).')
        )
        if not aplicar and (n_cli or n_emp or n_ven):
            self.stdout.write(self.style.SUCCESS(
                'En servidor ejecute: python manage.py corregir_depto_san_miguel_morazan --apply'
            ))

    def _corregir_queryset(self, qs, tipo, aplicar, *, depto_attr, muni_attr, dist_attr, label_fn):
        count = 0
        for obj in qs.iterator():
            depto = getattr(obj, depto_attr, None)
            muni = getattr(obj, muni_attr, None)
            dist = getattr(obj, dist_attr, None)
            if not depto and not muni:
                continue

            # Solo tocar casos del swap o códigos inconsistentes SM/MZ
            d0 = str(depto or '').zfill(2)[-2:] if depto else ''
            m0 = str(muni or '').zfill(2)[-2:] if muni else ''
            sospechoso = (
                (d0 == '13' and m0 in MUNI_SM)
                or (d0 == '12' and m0 in MUNI_MZ)
                or (m0 in MUNI_SM and d0 not in ('', '12'))
                or (m0 in MUNI_MZ and d0 not in ('', '13'))
            )
            if not sospechoso:
                continue

            d1, m1, di1 = normalizar_ubicacion_mh(depto, muni, dist)
            if (d1, m1, di1) == (d0 or d1, m0 or m1, str(dist or '').zfill(2)[-2:] if dist else di1):
                # Ya normalizado
                if d0 == d1 and m0 == m1 and (not dist or str(dist).zfill(2)[-2:] == di1):
                    continue

            count += 1
            self.stdout.write(
                f'  [{tipo}] {label_fn(obj)}: {d0}/{m0}/{dist or "-"} -> {d1}/{m1}/{di1}'
            )
            if aplicar:
                setattr(obj, depto_attr, d1)
                setattr(obj, muni_attr, m1)
                setattr(obj, dist_attr, di1)
                obj.save(update_fields=[depto_attr, muni_attr, dist_attr])
        return count
