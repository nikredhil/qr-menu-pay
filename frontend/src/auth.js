// Two independent sessions, both HS256 tokens this API issues:
//   • customer — obtained via phone OTP, used to place/track orders & pay
//   • admin    — obtained via the staff password, used for the staff dashboard
const C_TOKEN = "hsr_customer_token";
const C_PHONE = "hsr_customer_phone";
const C_NAME = "hsr_customer_name";
const A_TOKEN = "hsr_admin_token";

// --- customer ---
export function getCustomer() {
  const token = localStorage.getItem(C_TOKEN);
  if (!token) return null;
  return {
    token,
    phone: localStorage.getItem(C_PHONE) || "",
    name: localStorage.getItem(C_NAME) || "",
  };
}

export function setCustomer({ access_token, phone, name }) {
  localStorage.setItem(C_TOKEN, access_token);
  localStorage.setItem(C_PHONE, phone || "");
  localStorage.setItem(C_NAME, name || "");
}

export function clearCustomer() {
  [C_TOKEN, C_PHONE, C_NAME].forEach((k) => localStorage.removeItem(k));
}

// --- admin ---
export function getAdminToken() {
  return localStorage.getItem(A_TOKEN);
}
export function setAdminToken(token) {
  localStorage.setItem(A_TOKEN, token);
}
export function clearAdmin() {
  localStorage.removeItem(A_TOKEN);
}

export function tokenFor(kind) {
  if (kind === "admin") return getAdminToken();
  if (kind === "customer") return getCustomer()?.token || null;
  return null;
}
