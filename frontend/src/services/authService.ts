import type { User } from "../types/auth";
import type { CreateUserRequest, LoginResponse, UserResponse } from "../types/api/auth";
import { apiRequest } from "./api";
import { clearToken, setToken } from "../lib/authStorage";

export const authService = {
  async login(email: string, password: string): Promise<User> {
    const data = await apiRequest<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    });

    setToken(data.access_token);
    return data.user;
  },

  async register(email: string, name: string, password: string): Promise<UserResponse> {
    const body: CreateUserRequest = { email, name, password };
    return apiRequest<UserResponse>("/api/v1/users", {
      method: "POST",
      body,
      auth: false,
    });
  },

  async getMe(): Promise<User> {
    return apiRequest<UserResponse>("/api/v1/auth/me");
  },

  logout(): void {
    clearToken();
  },
};
