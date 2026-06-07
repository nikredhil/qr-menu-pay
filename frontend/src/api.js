import { tokenFor } from "./auth";

export const BASE = (import.meta.env.VITE_API_BASE || "http://localhost:8000").replace(/\/$/, "");

// auth: false (public) | "customer" | "admin"
async function request(path, { method = "GET", body, auth = false } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = tokenFor(auth);
    if (!token) throw new Error(`401: ${auth} sign-in required`);
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const data = await res.json();
      detail = data.detail ? `${res.status}: ${data.detail}` : `${res.status}`;
    } catch {
      detail = `${res.status}: ${await res.text()}`;
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // --- public ---
  config: () => request("/config"),
  menu: () => request("/menu").then((d) => d.items),
  getTable: (id) => request(`/tables/${encodeURIComponent(id)}`),

  // --- customer auth (OTP) ---
  requestOtp: (phone, name) =>
    request("/auth/otp/request", { method: "POST", body: { phone, name: name || null } }),
  verifyOtp: (phone, code) =>
    request("/auth/otp/verify", { method: "POST", body: { phone, code } }),

  // --- customer orders ---
  placeOrder: (body) => request("/orders", { method: "POST", body, auth: "customer" }),
  myOrders: () => request("/orders/mine", { auth: "customer" }).then((d) => d.items),
  getOrder: (id) => request(`/orders/${id}`, { auth: "customer" }),

  // --- payments ---
  createIntent: (orderId) =>
    request("/payments/intent", { method: "POST", body: { order_id: orderId }, auth: "customer" }),
  verifyRazorpay: (payload) =>
    request("/payments/razorpay/verify", { method: "POST", body: payload, auth: "customer" }),
  confirmDemo: (orderId, razorpayOrderId, outcome = "success") =>
    request("/payments/demo/confirm", {
      method: "POST",
      body: { order_id: orderId, razorpay_order_id: razorpayOrderId, outcome },
      auth: "customer",
    }),
  payCash: (orderId) =>
    request("/payments/cash", { method: "POST", body: { order_id: orderId }, auth: "customer" }),

  // --- admin auth ---
  adminLogin: (password) =>
    request("/auth/admin/login", { method: "POST", body: { password } }),

  // --- admin: menu ---
  adminMenu: () => request("/menu?all_items=true").then((d) => d.items),
  createMenuItem: (body) => request("/menu", { method: "POST", body, auth: "admin" }),
  updateMenuItem: (id, patch) =>
    request(`/menu/${id}`, { method: "PATCH", body: patch, auth: "admin" }),
  deleteMenuItem: (id) => request(`/menu/${id}`, { method: "DELETE", auth: "admin" }),

  // --- admin: tables ---
  adminTables: () => request("/tables", { auth: "admin" }).then((d) => d.items),
  createTable: (body) => request("/tables", { method: "POST", body, auth: "admin" }),
  deleteTable: (id) => request(`/tables/${encodeURIComponent(id)}`, { method: "DELETE", auth: "admin" }),

  // --- admin: orders ---
  adminOrders: () => request("/orders", { auth: "admin" }).then((d) => d.items),
  setOrderStatus: (id, status) =>
    request(`/orders/${id}/status`, { method: "PATCH", body: { status }, auth: "admin" }),
  markCashCollected: (id) =>
    request(`/payments/${id}/cash-collected`, { method: "POST", auth: "admin" }),
};

// ---------- shared helpers ----------
export const MENU_CATEGORIES = [
  "Starters",
  "Soups & Salads",
  "Main Course",
  "Breads & Rice",
  "Chinese",
  "Beverages",
  "Desserts",
];

export function rupees(amount) {
  const n = Number(amount || 0);
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

export const STATUS_META = {
  placed: { label: "Placed", className: "bg-blue-100 text-blue-700" },
  preparing: { label: "Preparing", className: "bg-amber-100 text-amber-700" },
  served: { label: "Served", className: "bg-emerald-100 text-emerald-700" },
  cancelled: { label: "Cancelled", className: "bg-red-100 text-red-700" },
};

export const PAY_META = {
  pending: { label: "Payment pending", className: "bg-slate-100 text-slate-600" },
  paid: { label: "Paid", className: "bg-emerald-100 text-emerald-700" },
  failed: { label: "Payment failed", className: "bg-red-100 text-red-700" },
  refunded: { label: "Refunded", className: "bg-slate-100 text-slate-600" },
};
