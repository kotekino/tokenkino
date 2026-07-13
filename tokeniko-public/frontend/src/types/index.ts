export interface ApiResponse<T = unknown> {
  success: boolean;
  message?: string;
  data?: T;
}

export type NavItem = {
  label: string;
  path: string;
};
