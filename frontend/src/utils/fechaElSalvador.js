const TZ_EL_SALVADOR = 'America/El_Salvador'

/** Fecha civil en El Salvador (YYYY-MM-DD). Evita toISOString() que usa UTC. */
export function fechaHoyElSalvadorISO() {
  return new Date().toLocaleDateString('en-CA', { timeZone: TZ_EL_SALVADOR })
}
