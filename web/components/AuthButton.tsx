"use client";

import { LogOut, User as UserIcon } from "lucide-react";
import { useAuth } from "./AuthProvider";

export function AuthButton() {
  const { user, loading, login, logout } = useAuth();

  if (loading) {
    return (
      <div className="text-green-500/60 text-xs uppercase">
        {`> checking session…`}
      </div>
    );
  }

  if (!user) {
    return (
      <button
        type="button"
        onClick={login}
        className="inline-flex items-center gap-2 px-3 py-1 border border-green-500/60 text-green-400 hover:bg-green-500/10 hover:text-green-300 transition rounded-sm uppercase text-xs"
      >
        <UserIcon size={14} />
        Sign in with Google
      </button>
    );
  }

  return (
    <div className="flex items-center gap-3 text-xs">
      {user.picture ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={user.picture}
          alt={user.name}
          className="w-6 h-6 border border-green-500/60"
        />
      ) : (
        <div className="w-6 h-6 border border-green-500/60 flex items-center justify-center">
          <UserIcon size={12} />
        </div>
      )}
      <span className="text-green-400 lowercase">{user.email}</span>
      <button
        type="button"
        onClick={() => logout()}
        className="inline-flex items-center gap-1 px-2 py-1 border border-green-500/60 text-green-400 hover:bg-green-500/10 hover:text-green-300 transition rounded-sm uppercase"
      >
        <LogOut size={12} />
        Logout
      </button>
    </div>
  );
}
