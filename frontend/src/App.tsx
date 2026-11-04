import { BrowserRouter } from "react-router-dom";
import Layout from "@/components/Layout";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <div style={{ padding: "2rem", background: "red" }}>
          <h1>Hola mundo - React funciona</h1>
          <p>Si ves esto, React y el Layout funcionan correctamente.</p>
        </div>
      </Layout>
    </BrowserRouter>
  );
}
