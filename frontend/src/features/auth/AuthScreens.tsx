export function LoginScreen() {
  return (
    <main className="page">
      <section className="card" aria-labelledby="login-title">
        <h1 id="login-title">Chat với tài liệu</h1>
        <p>Đăng nhập bằng tài khoản công ty để bắt đầu.</p>
        <a className="button" href={`/auth/login?return_to=${encodeURIComponent(window.location.pathname)}`}>
          Đăng nhập
        </a>
      </section>
    </main>
  );
}

export function NoAccessScreen() {
  return (
    <main className="page">
      <section className="card" aria-labelledby="access-title">
        <h1 id="access-title">Chưa được cấp quyền</h1>
        <p>Tài khoản của bạn chưa được bật quyền truy cập.</p>
        <button className="button" type="button" onClick={() => { void fetch("/auth/logout", { method: "POST", credentials: "include" }).finally(() => { window.location.href = "/login"; }); }}>
          Đăng nhập bằng tài khoản khác
        </button>
      </section>
    </main>
  );
}
