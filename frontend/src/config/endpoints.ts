export const API_ENDPOINTS = {
  users: '/api/v1/users',
  roles: '/api/v1/roles',
  permissions: '/api/v1/permissions',
  telefonos: '/api/v1/telefonos',
  dispositivos: '/api/v1/dispositivos',
  trabajadores: '/api/v1/trabajadores',
  dashboard: '/api/v1/dashboard',
  auth: {
    login: '/api/v1/auth/login',
    logout: '/api/v1/auth/logout',
    refresh: '/api/v1/auth/refresh',
    me: '/api/v1/auth/me',
  },
} as const;

type FlatKey = Exclude<keyof typeof API_ENDPOINTS, 'auth'>
export type APIEndpoint = typeof API_ENDPOINTS[FlatKey]

export const getEndpoint = (key: FlatKey, id?: string | number): string => {
  const endpoint = API_ENDPOINTS[key]
  if (id) {
    return `${endpoint}/${id}`
  }
  return endpoint
}

export const getListEndpoint = (
  key: FlatKey,
  options?: {
    page?: number;
    perPage?: number;
    search?: string;
    filters?: Record<string, string>;
  }
): string => {
  const params = new URLSearchParams();
  
  if (options?.page) params.set('page', String(options.page));
  if (options?.perPage) params.set('per_page', String(options.perPage));
  if (options?.search) params.set('search', options.search);
  
  if (options?.filters) {
    Object.entries(options.filters).forEach(([k, v]) => {
      if (v) params.set(k, v);
    });
  }
  
  const queryString = params.toString();
  return queryString ? `${API_ENDPOINTS[key]}?${queryString}` : API_ENDPOINTS[key];
};
