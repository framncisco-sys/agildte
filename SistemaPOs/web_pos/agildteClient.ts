/**
 * Programador: Oscar Amaya Romero
 *
 * Cliente API para backend Django REST (AgilDTE), pensado para Vite/React.
 * Variables: VITE_AGILDTE_BASE_URL (sin barra final), credenciales vía login en UI
 * (no guardar superusuario en el bundle).
 *
 * CORS: el admin del backend debe incluir el origen del POS en CORS_ALLOWED_ORIGINS.
 */

const API_PREFIX = "/api";

export type LoginProfile = {
  access: string;
  refresh: string | null;
  empresaDefaultId: number | null;
  empresasIds: number[];
};

function baseUrl(): string {
  const u = (import.meta.env.VITE_AGILDTE_BASE_URL as string | undefined)?.trim()?.replace(/\/$/, "");
  if (!u) throw new Error("Defina VITE_AGILDTE_BASE_URL en .env");
  return u;
}

function parseEmpresaFromUser(user: Record<string, unknown>): { defaultId: number | null; ids: number[] } {
  let defaultId: number | null = null;
  const ed = user["empresa_default"];
  if (ed && typeof ed === "object" && ed !== null && "id" in ed) {
    const id = (ed as { id: unknown }).id;
    if (typeof id === "number") defaultId = id;
    else if (typeof id === "string" && /^\d+$/.test(id)) defaultId = parseInt(id, 10);
  }
  const ids: number[] = [];
  for (const key of ["empresas", "empresas_asignadas", "mis_empresas"]) {
    const raw = user[key];
    if (!Array.isArray(raw)) continue;
    for (const item of raw) {
      if (item && typeof item === "object" && "id" in item) {
        const id = (item as { id: unknown }).id;
        if (typeof id === "number") ids.push(id);
        else if (typeof id === "string" && /^\d+$/.test(id)) ids.push(parseInt(id, 10));
      } else if (typeof item === "number") ids.push(item);
    }
    break;
  }
  if (defaultId != null && !ids.includes(defaultId)) ids.unshift(defaultId);
  return { defaultId, ids };
}

/** empresa_default y empresas en la raíz del JSON (respuesta real de AgilDTE). */
function parseEmpresaFromRoot(data: Record<string, unknown>): { defaultId: number | null; ids: number[] } {
  let defaultId: number | null = null;
  const ed = data["empresa_default"];
  if (ed && typeof ed === "object" && ed !== null && "id" in ed) {
    const id = (ed as { id: unknown }).id;
    if (typeof id === "number") defaultId = id;
    else if (typeof id === "string" && /^\d+$/.test(id)) defaultId = parseInt(id, 10);
  }
  const ids: number[] = [];
  const rawList = data["empresas"];
  if (Array.isArray(rawList)) {
    for (const item of rawList) {
      if (item && typeof item === "object" && "id" in item) {
        const id = (item as { id: unknown }).id;
        if (typeof id === "number") ids.push(id);
        else if (typeof id === "string" && /^\d+$/.test(id)) ids.push(parseInt(id, 10));
      } else if (typeof item === "number") ids.push(item);
    }
  }
  if (defaultId != null && !ids.includes(defaultId)) ids.unshift(defaultId);
  return { defaultId, ids };
}

function mergeEmpresaLogin(
  data: Record<string, unknown>,
  user: Record<string, unknown>
): { defaultId: number | null; ids: number[] } {
  const fromUser = parseEmpresaFromUser(user);
  const fromRoot = parseEmpresaFromRoot(data);
  const defaultId = fromUser.defaultId ?? fromRoot.defaultId;
  const seen = new Set<number>();
  const ids: number[] = [];
  for (const eid of [...fromUser.ids, ...fromRoot.ids]) {
    if (!seen.has(eid)) {
      seen.add(eid);
      ids.push(eid);
    }
  }
  if (defaultId != null && !seen.has(defaultId)) {
    ids.unshift(defaultId);
  }
  return { defaultId, ids };
}

export class AgilDTEClient {
  private access: string | null = null;
  private refresh: string | null = null;
  private empresaId: number | null = null;

  setEmpresaId(id: number | null): void {
    this.empresaId = id;
  }

  getEmpresaId(): number | null {
    return this.empresaId;
  }

  async login(usernameOrEmail: string, password: string): Promise<LoginProfile> {
    const payload: Record<string, string> = { password };
    if (usernameOrEmail.includes("@")) payload.email = usernameOrEmail.trim();
    else payload.username = usernameOrEmail.trim();

    const r = await fetch(`${baseUrl()}${API_PREFIX}/auth/login/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = (await r.json().catch(() => ({}))) as Record<string, unknown>;
    if (!r.ok) throw new Error(`Login ${r.status}: ${JSON.stringify(data)}`);

    const access = (data.access as string) || (data.token as string);
    const refresh = (data.refresh as string) || null;
    if (!access) throw new Error("Respuesta sin access JWT");

    const user = (data.user || data.usuario || data.perfil || {}) as Record<string, unknown>;
    const { defaultId, ids } = mergeEmpresaLogin(data, user);
    this.access = access;
    this.refresh = refresh;
    if (this.empresaId == null && defaultId != null) this.empresaId = defaultId;

    return { access, refresh, empresaDefaultId: defaultId, empresasIds: ids };
  }

  private async doRefresh(): Promise<boolean> {
    if (!this.refresh) return false;
    const r = await fetch(`${baseUrl()}${API_PREFIX}/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: this.refresh }),
    });
    if (!r.ok) return false;
    const data = (await r.json()) as { access?: string };
    if (!data.access) return false;
    this.access = data.access;
    return true;
  }

  async request<T = unknown>(
    path: string,
    init: RequestInit & { params?: Record<string, string | number | boolean | undefined> } = {},
    retry401 = true
  ): Promise<T> {
    if (!this.access) throw new Error("No autenticado");

    const { params, ...rest } = init;
    let url = `${baseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
    const q = new URLSearchParams();
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined && v !== null) q.set(k, String(v));
      }
    }
    if (this.empresaId != null && !q.has("empresa_id") && !q.has("empresa")) {
      q.set("empresa_id", String(this.empresaId));
    }
    const qs = q.toString();
    if (qs) url += (url.includes("?") ? "&" : "?") + qs;

    const headers = new Headers(rest.headers);
    headers.set("Authorization", `Bearer ${this.access}`);
    if (!headers.has("Content-Type") && rest.body && typeof rest.body === "string") {
      headers.set("Content-Type", "application/json");
    }

    const r = await fetch(url, { ...rest, headers });

    if (r.status === 401 && retry401) {
      const ok = await this.doRefresh();
      if (ok) return this.request<T>(path, init, false);
      throw new Error("401: sesión expirada; vuelva a iniciar sesión.");
    }
    if (r.status === 403) throw new Error("403: empresa no permitida u operación denegada.");

    const text = await r.text();
    let body: unknown = text;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      /* texto plano */
    }
    if (!r.ok) throw new Error(`API ${r.status}: ${typeof body === "string" ? body : JSON.stringify(body)}`);
    return body as T;
  }

  async listProductos(extra?: Record<string, string | number | boolean | undefined>) {
    return this.request<unknown>(`${API_PREFIX}/productos/`, { method: "GET", params: extra });
  }

  async listClientes(extra?: Record<string, string | number | boolean | undefined>) {
    return this.request<unknown>(`${API_PREFIX}/clientes/`, { method: "GET", params: extra });
  }

  async createCliente(body: Record<string, unknown>) {
    const b = { ...body };
    if (this.empresaId != null) {
      b.empresa_id ??= this.empresaId;
      b.empresa ??= this.empresaId;
    }
    return this.request<unknown>(`${API_PREFIX}/clientes/`, {
      method: "POST",
      body: JSON.stringify(b),
    });
  }

  /**
   * Ver comentario largo en agildte_client.py (Python) sobre campos obligatorios
   * de crear-con-detalles; ajustar el body al serializer del backend.
   */
  async crearVentaConDetalles(body: Record<string, unknown>) {
    const b = { ...body };
    if (this.empresaId != null) {
      b.empresa_id ??= this.empresaId;
      b.empresa ??= this.empresaId;
    }
    return this.request<unknown>(`${API_PREFIX}/ventas/crear-con-detalles/`, {
      method: "POST",
      body: JSON.stringify(b),
    });
  }

  /** Mismo cuerpo que crearVentaConDetalles; respuesta { ok, mensaje, venta } desde AgilDTE. */
  async procesarVentaPos(body: Record<string, unknown>) {
    const b = { ...body };
    if (this.empresaId != null) {
      b.empresa_id ??= this.empresaId;
      b.empresa ??= this.empresaId;
    }
    return this.request<{ ok?: boolean; mensaje?: string; venta?: unknown }>(
      `${API_PREFIX}/pos/procesar-venta/`,
      {
        method: "POST",
        body: JSON.stringify(b),
      }
    );
  }

  async generarDteVenta(ventaId: number) {
    return this.request<unknown>(`${API_PREFIX}/ventas/${ventaId}/generar-dte/`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  }
}
