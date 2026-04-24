import apiClient from './client'

export interface LoginRequest {
  username: string
  password: string
}

export interface UserInfo {
  id: string
  username: string
  role: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: UserInfo
}

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const res = await apiClient.post<LoginResponse>('/auth/login', data)
  return res.data
}
