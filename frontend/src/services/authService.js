import { apiRequest } from "./api.js";
import { clearToken, setToken } from "../lib/authStorage.js";

export const authService = {
  async login(email, password) {
    const data = await apiRequest("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    });

    setToken(data.access_token);
    return data.user;
  },

  async register(email, name, password) {
    return apiRequest("/api/v1/users", {
      method: "POST",
      body: { email, name, password },
      auth: false,
    });
  },

  async getMe() {
    return apiRequest("/api/v1/auth/me");
  },

  logout() {
    clearToken();
  },
};
