// Author self sign-up. New authors start with no books (their titles appear once publishing begins).
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import Alert from "../../components/common/Alert";
import Button from "../../components/common/Button";
import { Input } from "../../components/common/Field";
import AuthLayout from "./AuthLayout";

export default function SignupPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "", phone: "", city: "" });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const mismatch = form.confirm && form.confirm !== form.password;

  const submit = async (e) => {
    e.preventDefault();
    if (mismatch) return;
    setSubmitting(true);
    setError(null);
    try {
      const { confirm, ...data } = form; // eslint-disable-line no-unused-vars
      await register({ ...data, phone: data.phone || null, city: data.city || null });
      navigate("/books", { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  };

  const fieldError = (key) => error?.details?.[key];

  return (
    <AuthLayout title="Create an account" subtitle="Join BookLeaf to track your books and get support">
      <form onSubmit={submit} className="space-y-4" noValidate>
        {error && <Alert tone="error">{error.message}</Alert>}
        <Input id="name" label="Full name" autoComplete="name" required value={form.name} onChange={set("name")} error={fieldError("name")} />
        <Input id="email" label="Email" type="email" autoComplete="email" required value={form.email} onChange={set("email")} error={fieldError("email")} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            id="password"
            label="Password"
            type="password"
            autoComplete="new-password"
            required
            hint="At least 8 characters"
            value={form.password}
            onChange={set("password")}
            error={fieldError("password")}
          />
          <Input
            id="confirm"
            label="Confirm password"
            type="password"
            autoComplete="new-password"
            required
            value={form.confirm}
            onChange={set("confirm")}
            error={mismatch ? "Passwords don't match" : null}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input id="phone" label="Phone (optional)" autoComplete="tel" value={form.phone} onChange={set("phone")} error={fieldError("phone")} />
          <Input id="city" label="City (optional)" value={form.city} onChange={set("city")} error={fieldError("city")} />
        </div>
        <Button type="submit" loading={submitting} disabled={mismatch} className="w-full">
          Create account
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-brand-700 hover:underline">
          Log in
        </Link>
      </p>
    </AuthLayout>
  );
}
