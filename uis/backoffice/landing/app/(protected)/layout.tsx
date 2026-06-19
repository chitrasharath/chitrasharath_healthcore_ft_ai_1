import { AuthGuard } from "@/components/auth/auth-guard";

export default function ProtectedLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <AuthGuard>{children}</AuthGuard>;
}
