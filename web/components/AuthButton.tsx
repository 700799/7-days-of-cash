"use client";

import Image from "next/image";
import { LogOut, User as UserIcon } from "lucide-react";
import { useAuth } from "./AuthProvider";

export function AuthButton() {
  const { user, loading, login, logout } = useAuth();

  if (loading) {
    return (
      <div className="text-b7-green-muted text-xs uppercase">
        {`> checking session…`}
      </div>
    );
  }

  if (!user) {
    return (
      <button
        type="button"
        onClick={login}
        className="inline-flex items-center gap-2 px-3 py-1 border border-b7-green-border text-b7-green hover:bg-green-500/10 hover:text-b7-green-dim transition rounded-sm uppercase text-xs"
      >
        <UserIcon size={14} />
        Sign in with Google
      </button>
    );
  }

  return (
    <div className="flex items-center gap-3 text-xs">
      {user.picture ? (
        <Image
          src={user.picture}
          alt={user.name}
          width={32}
          height={32}
          className="border border-b7-green-border"
          unoptimized
        />
      ) : (
        <div className="w-8 h-8 border border-b7-green-border flex items-center justify-center">
          <UserIcon size={12} />
        </div>
      )}
      <span className="text-b7-green lowercase">{user.email}</span>
      <button
        type="button"
        onClick={() => logout()}
        className="inline-flex items-center gap-1 px-2 py-1 border border-b7-green-border text-b7-green hover:bg-green-500/10 hover:text-b7-green-dim transition rounded-sm uppercase"
      >
        <LogOut size={12} />
        Logout
      </button>
    </div>
  );
}
