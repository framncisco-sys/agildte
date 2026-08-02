# Schemas oficiales MH (svfe-json-schemas) — Normativa / transmisión V2+
#
# Fuente: carpeta svfe-json-schemas (mayo 2026)
# Uso: referencia + validación runtime (api.utils.mh_schema_validator) para 01/03/14
#
# Mapa rápido:
#   v2/fe-f-v2.json              Factura (01) version 2     ✅ builder + validación
#   v4/fe-ccf-v4.json            CCF (03) version 4         ✅ builder + validación
#   v4/fe-nc-v4.json             NC (05) version 4          ⚠ builder aún v3
#   v4/fe-nd-v4.json             ND (06) version 4          ⚠ builder aún v3
#   v2/fe-fse-v2.json            FSE (14) version 2         ✅ builder + validación
#   v2/fe-cr-v2.json             Retención (07) version 2   ⚠ builder aún v1
#   v2/fe-cl-v2.json             Liquidación (08) version 2 ⚠ builder aún v1
#   v2/fe-dcl-v2.json            DCL (09) version 2         ⚠ builder aún v1
#   v2/fe-cd-v2.json             Donación (15) version 2    ⚠ builder aún v1
#   v3/invalidacion-schema-v3.json
#   v4/contingencia-schema-v4.json
#   v1/fe-eret-v1.json           Evento Retorno (18)
#   v1/fe-eop-v1.json            Operaciones Especiales (17)
