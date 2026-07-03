export interface UserResponse {
  id: number;
  email: string;
  name: string;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface CreateUserRequest {
  email: string;
  name: string;
  password: string;
}
