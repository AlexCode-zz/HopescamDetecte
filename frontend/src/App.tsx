import { BrowserRouter } from "react-router-dom";
import Layout from "@/components/Layout";
import Analysis from "@/pages/Analysis";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Analysis />
      </Layout>
    </BrowserRouter>
  );
}
