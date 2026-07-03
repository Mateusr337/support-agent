import { BrowserRouter } from "react-router-dom";
import AppRouter from "./app/router";
import Providers from "./app/providers";

export default function App() {
  return (
    <Providers>
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    </Providers>
  );
}
