// Handles both the login form and the register form.
const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const formError = document.getElementById("formError");

function nextPage(user) {
  if (user.role === "admin") return "/admin";
  const next = new URLSearchParams(window.location.search).get("next");
  // only allow pages on our own site
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}

async function submitForm(form, url) {
  formError.textContent = "";
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  const body = Object.fromEntries(new FormData(form).entries());
  try {
    const { user } = await api(url, "POST", body);
    window.location.href = nextPage(user);
  } catch (err) {
    formError.textContent = err.message;
    button.disabled = false;
  }
}

if (loginForm) loginForm.addEventListener("submit", (e) => { e.preventDefault(); submitForm(loginForm, "/api/auth/login"); });
if (registerForm) registerForm.addEventListener("submit", (e) => { e.preventDefault(); submitForm(registerForm, "/api/auth/register"); });
