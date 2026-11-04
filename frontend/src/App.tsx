import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import Layout from "@/components/Layout";
import Analysis from "@/pages/Analysis";
import PatientSearch from "@/pages/PatientSearch";
import Chat from "@/pages/Chat";

function HomeRedirect() {
  const navigate = useNavigate();
  navigate("/");
  return null;
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Analysis />} />
          <Route path="/nuevo-analisis" element={<Analysis />} />
          <Route path="/buscar" element={<PatientSearch />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="*" element={<HomeRedirect />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
