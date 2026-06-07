import { Routes, Route, Navigate } from "react-router-dom";
import Landing from "./pages/Landing.jsx";
import TableMenu from "./pages/TableMenu.jsx";
import OrderStatus from "./pages/OrderStatus.jsx";
import AdminLogin from "./pages/AdminLogin.jsx";
import AdminMenu from "./pages/AdminMenu.jsx";
import AdminTables from "./pages/AdminTables.jsx";
import AdminOrders from "./pages/AdminOrders.jsx";
import { getAdminToken } from "./auth";

function RequireAdmin({ children }) {
  return getAdminToken() ? children : <Navigate to="/admin/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      {/* The QR codes encode this route, one per table. */}
      <Route path="/t/:tableId" element={<TableMenu />} />
      <Route path="/order/:orderId" element={<OrderStatus />} />

      <Route path="/admin/login" element={<AdminLogin />} />
      <Route path="/admin" element={<Navigate to="/admin/orders" replace />} />
      <Route
        path="/admin/orders"
        element={
          <RequireAdmin>
            <AdminOrders />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/menu"
        element={
          <RequireAdmin>
            <AdminMenu />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/tables"
        element={
          <RequireAdmin>
            <AdminTables />
          </RequireAdmin>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
