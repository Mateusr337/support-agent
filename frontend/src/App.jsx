import { BrowserRouter } from "react-router-dom";
import AppRouter from "./app/router.jsx";
import Providers from "./app/providers.jsx";

export default function App() {
  return (
    <Providers>
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    </Providers>
  );
}
