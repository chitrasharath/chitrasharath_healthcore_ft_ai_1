import type { ReactNode } from "react";

type AuthFormCardProps = {
  title: string;
  children: ReactNode;
};

export const AuthFormCard = ({ title, children }: AuthFormCardProps) => (
  <main className="mx-auto flex flex-1 items-center justify-center px-4 py-8 sm:px-6">
    <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg sm:p-8">
      <h1 className="text-xl font-bold text-slate-900">{title}</h1>
      <div className="mt-6">{children}</div>
    </div>
  </main>
);
