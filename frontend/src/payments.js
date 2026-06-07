import { api } from "./api";

let razorpayScript = null;

function loadRazorpay() {
  if (window.Razorpay) return Promise.resolve(true);
  if (!razorpayScript) {
    razorpayScript = new Promise((resolve) => {
      const s = document.createElement("script");
      s.src = "https://checkout.razorpay.com/v1/checkout.js";
      s.onload = () => resolve(true);
      s.onerror = () => resolve(false);
      document.body.appendChild(s);
    });
  }
  return razorpayScript;
}

// Drives a real Razorpay Checkout for an order. Opens the hosted sheet (which
// natively offers UPI — GPay / PhonePe / Paytm — cards and netbanking), then
// verifies the signature server-side. Resolves with the verified order.
export async function payWithRazorpay(intent, { name, contact }) {
  const ok = await loadRazorpay();
  if (!ok) throw new Error("Could not load the payment gateway. Check your connection.");

  return new Promise((resolve, reject) => {
    const rzp = new window.Razorpay({
      key: intent.key_id,
      order_id: intent.razorpay_order_id,
      amount: intent.amount,
      currency: intent.currency,
      name: intent.name,
      description: intent.description,
      prefill: { name: name || "", contact: contact || "" },
      theme: { color: "#ed7d31" },
      handler: async (resp) => {
        try {
          const result = await api.verifyRazorpay({
            order_id: intent.order_id,
            razorpay_order_id: resp.razorpay_order_id,
            razorpay_payment_id: resp.razorpay_payment_id,
            razorpay_signature: resp.razorpay_signature,
          });
          resolve(result);
        } catch (err) {
          reject(err);
        }
      },
      modal: {
        ondismiss: () => reject(new Error("Payment cancelled")),
      },
    });
    rzp.on("payment.failed", (resp) =>
      reject(new Error(resp?.error?.description || "Payment failed"))
    );
    rzp.open();
  });
}
