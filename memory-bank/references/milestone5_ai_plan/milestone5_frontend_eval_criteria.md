# ✅ What We Will Evaluate

- [ ] A dedicated API integration module exists — no raw `fetch` calls inside components.
- [ ] All requests to protected endpoints include the `Authorization` header with the current user's token.
- [ ] The products page loads live data from the API and displays `current_stock` with visual stock-level indicators.
- [ ] The inbound order form submits correctly and shows a confirmation or a readable error message on every outcome — no silent failures.
- [ ] The outbound order form displays the current stock for the selected product reactively, before the user submits.
- [ ] The outbound order form shows a client-side warning when the entered quantity exceeds available stock.
- [ ] A `400` response from the outbound endpoint surfaces the API's error message visibly in the UI.
- [ ] The orders history page displays all orders with inbound/outbound distinction, product name, quantity, date, and `user_uuid`.
- [ ] All four pages redirect unauthenticated users to login.
- [ ] Entity names and field labels in the UI match the CONTEXT.md specification.
